# -*- coding: utf-8 -*-

import os

import logging
from logging.handlers import RotatingFileHandler

import redis
import telebot

import config
from little_bot import LittleBot

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
FORMATTER = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
FILE_HANDLER = RotatingFileHandler(
    ''.join((os.path.splitext(os.path.basename(__file__))[0], os.path.extsep, 'log')),
    maxBytes=1024 * 1024,
    backupCount=10)
FILE_HANDLER.setLevel(logging.DEBUG)
FILE_HANDLER.setFormatter(FORMATTER)
LOGGER.addHandler(FILE_HANDLER)


ISSUES_BASE = redis.StrictRedis(host='localhost', port=6379, db=1)

if not ISSUES_BASE.exists('latest_new_issue'):
    ISSUES_BASE.set('latest_new_issue', 0)


if __name__ == '__main__':
    BOT = telebot.TeleBot(config.telegram_token)
    LOGGER.info('Latest reported new issue is #%s', int(ISSUES_BASE.get('latest_new_issue')))

    NEW_ISSUES_BOT = LittleBot(telegram_bot=BOT, redis=ISSUES_BASE, logger=LOGGER)
    NEW_ISSUES_BOT.post_news(1)

    ISSUES_BASE.bgsave()
