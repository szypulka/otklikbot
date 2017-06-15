# -*- coding: utf-8 -*-

import time
import json
from json.decoder import JSONDecodeError

import requests
from telebot.apihelper import ApiException
from urllib3.exceptions import NewConnectionError

import config

REDMINE_API_URL = config.redmine_api_url
CHANNEL_NAME = config.telegram_channel_name


def build_issue(issue):
    return {
        'newsline': '{}'.format(issue['subject']),
        'link': '<a href="{}/issues/{}">ПСР #{}</a>'.format(REDMINE_API_URL, issue['id'], issue['id']),
        'id': issue['id']
    }


def build_post(status_line, item):
    return '{}\n{}\n{}\n'.format(
        status_line,
        item['newsline'],
        item['link']
    )


class LittleBot(object):
    """ Takes updates via Redmine REST API"""

    def __init__(self, telegram_bot, redis, logger):
        self.session = requests.Session()
        self.session.headers.update(
            {
                'Content-Type': 'application/json',
                'X-Redmine-API-Key': config.redmine_apikey
            }
        )

        self.bot = telegram_bot
        self.database = redis
        self.logger = logger

        self.statuses = None

    def __api_request(self, api_string):

        request_url = REDMINE_API_URL + api_string

        try:
            msg = self.session.get(request_url)
            return json.loads(msg.text)
        except NewConnectionError:
            self.logger.error('Failed to establish a new connection to %s', request_url)
        except JSONDecodeError:
            self.logger.error('RedMine API on %d responds with %s %s %s',
                              request_url, msg.status_code, msg.reason, msg.text)

    def __get_statuses(self):
        msg = self.__api_request('/issue_statuses.json')
        if msg:
            self.statuses = msg['issue_statuses']

    def get_issues(self, status_id=1):
        msg = self.__api_request('/issues.json?status_id={}&project_id=1'.format(status_id))

        if msg:
            current_issues = (build_issue(issue) for issue in msg['issues'])
            return sorted(current_issues, key=lambda k: k['id'])

    def _filter_not_reported(self, items, db_table='latest_new_issue'):
        return [item for item in items if item['id'] > int(self.database.get(db_table))]

    def post_comment(self, item):
        post = build_post('Появился новый ПСР:', item)
        try:
            self.bot.send_message(CHANNEL_NAME, post, parse_mode='html', disable_web_page_preview=True)
            self.database.set('latest_new_issue', item['id'])
            self.logger.debug('Message about issue#{} %s is sent.', item['id'])
        except ApiException as error:
            self.logger.warning('Message about issue#%s is not sent. %s', item['id'], error)

    def post_news(self, status_id=1):
        '''
        Checks Redmine for new issues and sends them to Telegram
        :param status_id: Status of issues to filter
        :return: None
        '''
        items = self.get_issues(status_id)
        self.logger.debug('Issues with status_id %s are: %s', status_id, items)

        fresh_items = self._filter_not_reported(items)
        for item in fresh_items:
            self.post_comment(item)
            time.sleep(1)
