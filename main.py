# -*- coding: utf-8 -*-

import os

import time
import json
import logging
from logging.handlers import RotatingFileHandler

import redis
import requests
import telebot
import urllib3

import config

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
FORMATTER = logging.Formatter('%(asctime)s %(levelname)s [%(processName)s: %(threadName)s] %(message)s')
FILE_HANDLER = RotatingFileHandler(
    ''.join((os.path.splitext(os.path.basename(__file__))[0], os.path.extsep, 'log')),
    maxBytes=1024 * 1024,
    backupCount=10)
FILE_HANDLER.setLevel(logging.DEBUG)
FILE_HANDLER.setFormatter(FORMATTER)
LOGGER.addHandler(FILE_HANDLER)

TELEGRAM_URL = 'https://api.telegram.org/bot{}/'.format(config.telegram_token)
REDMINE_API_URL = config.redmine_api_url
CHANNEL_NAME = config.telegram_channel_name

ISSUES_BASE = redis.StrictRedis(host='localhost', port=6379, db=1)

if not ISSUES_BASE.exists('latest_new_issue'):
    ISSUES_BASE.set('latest_new_issue', 0)


class LittleBot(object):
    """ Takes updates via Redmine REST API"""

    def __init__(self, telegram_bot):
        self.session = requests.Session()
        self.headers = {'Content-Type': 'application/json',
                        'X-Redmine-API-Key': config.redmine_apikey}
        self.bot = telegram_bot
        self.statuses = None

    def __api_request(self, api_string):
        request_url = REDMINE_API_URL + api_string

        try:
            msg = self.session.get(request_url, headers=self.headers)
        except urllib3.exceptions.NewConnectionError:
            logging.error('Failed to establish a new connection to %s', request_url)
            return

        if msg.status_code == 200:
            return json.loads(msg.text)
        else:
            logging.error('RedMine API on %d responds with %s %s %s',
                          request_url, msg.status_code, msg.reason, msg.text)
            return

    def __get_statuses(self):
        msg = self.__api_request('/issue_statuses.json')
        if msg:
            self.statuses = msg['issue_statuses']

    def get_issues(self, status_id=1):
        msg = self.__api_request('/issues.json?status_id={}'.format(status_id))

        if msg:
            current_issues = [
                {
                    'newsline': '{}'.format(issue['subject']),
                    'link': '<a href="{}/issues/{}">ПСР #{}</a>'.format(REDMINE_API_URL, issue['id'], issue['id']),
                    'id': issue['id']
                }
                for issue in msg['issues']
            ]
            return sorted(current_issues, key=lambda k: k['id'])
        else:
            return None

    def post_news(self):

        items = self.get_issues(2)
        if items:
            for item in items:
                if item['id'] <= int(ISSUES_BASE.get('latest_new_issue')):
                    LOGGER.debug('No new messages sent')
                    break
                post = 'Появился ПСР со статусом В работе:\n{}\n{}\n'.format(
                    item['newsline'],
                    item['link']
                )
                try:
                    self.bot.send_message(CHANNEL_NAME, post, parse_mode='html', disable_web_page_preview=True)
                    ISSUES_BASE.set('latest_new_issue', item['id'])
                    LOGGER.debug('Message about issue#{} %s is sent.', item['id'])
                except telebot.apihelper.ApiException as error:
                    LOGGER.warning('Message about issue#%s is not sent. %s', item['id'], error)
                time.sleep(1)
        return


if __name__ == '__main__':
    BOT = telebot.TeleBot(config.telegram_token)
    LOGGER.info('Latest reported new issue is #%s', ISSUES_BASE.get('latest_new_issue'))

    NEW_ISSUES_BOT = LittleBot(telegram_bot=BOT)
    NEW_ISSUES_BOT.post_news()

    ISSUES_BASE.bgsave()
