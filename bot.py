#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from time import sleep

import click
import telegram

import config
from database import *  # noqa
from log import logger

from commands.add import AddCommand
from commands.clear import ClearCommand
from commands.export import ExportCommand
from commands.last import LastCommand
from commands.ping import PingCommand
from commands.remove import RemoveCommand
from commands.settings import SettingsCommand
from commands.split import SplitCommand
from commands.total import TotalCommand


class VereseBot(object):
    COMMANDS = [AddCommand, RemoveCommand, TotalCommand,
                ClearCommand, LastCommand, PingCommand, ExportCommand,
                SplitCommand, SettingsCommand]

    def __init__(self):
        self._stay_awake = 30
        self.db = DB()

        # Connect to Telegram
        self._bot = telegram.Bot(token=config.token)
        self.queue = {}

    def set_bot_name(self):
        msg = self._bot.getMe()
        self.bot_name = msg.name

    def say(self, reply_to_message, text, reply_markup=None):
        # The telegram library doesn't play well with unicode, oh well.
        text = text.encode('utf-8') if isinstance(text, unicode) else text
        reply_to_message_id = reply_to_message.message_id if reply_markup else None
        return self._bot.sendMessage(chat_id=reply_to_message.chat.id,
                                     text=text,
                                     reply_to_message_id=reply_to_message_id,
                                     reply_markup=reply_markup)

    def get_updates(self):
        logger.debug('')
        last_update = self.db.root.last_update
        updates = self._bot.getUpdates(offset=last_update)
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

        for cmd in self.COMMANDS:
            if cmd.match(message):
                break
        else:
            logger.debug('No command found: {}'.format(message.message_id))
            return

        logger.debug('Calling process_{}'.format(cmd))
        cmd(bot=self)(message)


@click.command()
@click.option('--webserver/--polling', default=True)
def main(webserver):
    """Verese Telegram Bot."""
    bot = VereseBot()

    if webserver:
        import json
        from bottle import request, route, run

        if not config.webhook:
            print 'Set webhook'
            sys.exit(-1)

        bot._bot.setWebhook(config.webhook)

        @route('/', method='POST')
        def home():
            data = json.load(request.body)
            update = telegram.Update.de_json(data)
            bot.process_updates([update])
            return 'OK'

        try:
            run(host='0.0.0.0', port=config.port, reloader=False)
        finally:
            bot.db.close()

    else:
        try:
            while True:
                timeout = bot.poll()
                sleep(timeout)
        finally:
            bot.db.close()


if __name__ == "__main__":
    main()
