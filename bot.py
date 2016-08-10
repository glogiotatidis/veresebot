#!/usr/bin/env python
# -*- coding: utf-8 -*-
import importlib
import inspect
import os
import sys
from time import sleep

import click
import telegram

import config
from database import DB
from log import logger

from commands import BotCommand


class VereseBot(telegram.Bot):
    def __init__(self):
        self.commands = []
        self._stay_awake = 30
        self.db = DB()

        self.import_commands()

        # Connect to Telegram
        super(VereseBot, self).__init__(token=config.token)
        self.queue = {}

    def import_commands(self):
        for command_file in sorted(os.listdir('commands')):
            if command_file.endswith('.pyc') or command_file.startswith('__'):
                continue
            mod = importlib.import_module('commands.{}'.format(command_file[:-3]))
            for member_name, member_type in inspect.getmembers(mod):
                if inspect.isclass(member_type) and issubclass(member_type, BotCommand):
                    self.commands.append(member_type)

    def say(self, message, text, reply_markup=None, markdown=False,
            reply_to_message=True):
        # The telegram library doesn't play well with unicode, oh well.
        text = text.encode('utf-8') if isinstance(text, unicode) else text
        if reply_markup and reply_to_message:
            reply_to_message_id = message.message_id
        else:
            reply_to_message_id = None
        parse_mode = telegram.ParseMode.MARKDOWN if markdown else None
        return self.sendMessage(chat_id=message.chat.id,
                                text=text,
                                reply_to_message_id=reply_to_message_id,
                                reply_markup=reply_markup,
                                parse_mode=parse_mode)

    def get_updates(self):
        logger.debug('')
        last_update = self.db.root.last_update
        updates = self.getUpdates(offset=last_update)
        return updates

    def poll(self):
        updates = self.get_updates()
        self.process_updates(updates)
        if updates:
            self._stay_awake += 30
        else:
            if not self._stay_awake:
                logger.debug('Entering sleep mode')
                return 4

        self._stay_awake = self._stay_awake - 1 if self._stay_awake > 0 else 0
        return 1

    def process_updates(self, updates):
        last_update = self.db.root.last_update
        for update in filter(lambda x: x.update_id > last_update, updates):
            self.process_message(update.message)
            self.db.root.last_update = update.update_id
            self.db.commit()

    def process_message(self, message):
        # Update stats
        self.db.root.stats['number_of_messages'] += 1

        # Register user
        user = self.db.get_or_create_user(message.from_user.id)[0]
        user.update(message.from_user.first_name,
                    message.from_user.last_name,
                    message.from_user.username)

        # Register tab
        tab, created = self.db.get_or_create_tab(message.chat.id)

        # Register user in tab
        tab.register_user(user.id)

        reply_to_id = False
        if isinstance(message.chat, telegram.user.User):
            reply_to_id = message.message_id
        elif message.reply_to_message:
            reply_to_id = message.reply_to_message.message_id
        if reply_to_id:
            key = '{}_{}'.format(message.chat.id, reply_to_id)
            if key in self.queue:
                k = self.queue.pop(key)
                logger.debug('Calling queued {}'.format(k))
                k(message)
                return

        for cmd in self.commands:
            if cmd.match(message):
                logger.debug('Calling process_{}'.format(cmd))
                cmd(bot=self)(message)
                break
        else:
            self.say(message, 'Are you drunk matey?')
            logger.debug('No command found: {}'.format(message.message_id))
            return


@click.command()
@click.option('--webserver/--polling', default=True)
def main(webserver):
    """Verese Telegram Bot."""
    bot = VereseBot()

    if webserver:
        import json
        from urlparse import urlparse

        from bottle import request, route, run

        if not config.webhook:
            print 'Set webhook'
            sys.exit(-1)

        bot.setWebhook(config.webhook)

        @route(urlparse(config.webhook).path or '/', method='POST')
        def handle_message():
            data = json.load(request.body)
            update = telegram.Update.de_json(data)
            bot.process_updates([update])
            return 'OK'

        @route('/', method='GET')
        def home():
            return 'Hi :)'

        try:
            run(host='0.0.0.0', port=config.port, reloader=False)
        finally:
            bot.db.close()

    else:
        bot.setWebhook('')

        try:
            while True:
                timeout = bot.poll()
                sleep(timeout)
        finally:
            bot.db.close()


if __name__ == "__main__":
    main()
