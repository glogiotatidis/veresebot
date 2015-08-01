#!/usr/bin/env python
# -*- coding: utf-8 -*-
from time import sleep

import telegram

import config
from database import DB
from log import logger

from commands.add import AddCommand
from commands.clear import ClearCommand
from commands.export import ExportCommand
from commands.last import LastCommand
from commands.ping import PingCommand
from commands.remove import RemoveCommand
from commands.settimezone import SetTimezoneCommand
from commands.split import SplitCommand
from commands.total import TotalCommand


class VereseBot(object):
    COMMANDS = [AddCommand, RemoveCommand, TotalCommand,
                ClearCommand, LastCommand, PingCommand, ExportCommand,
                SplitCommand] #SetTimezoneCommand]

    def __init__(self):
        self._stay_awake = 30
        self.db = DB()

        # Connect to Telegram
        self._bot = telegram.Bot(token=config.token)
        self.queue = {}

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
        try:
            last_update = self.db.root.last_update
        except AttributeError:
            last_update = 0

        updates = self._bot.getUpdates(offset=last_update)
        updates = [u for u in updates if u.update_id > last_update]
        return updates

    def process_messages(self):
        updates = self.get_updates()

        for update in updates:
            self.process_message(update.message)
            self.db.root.last_update = update.update_id
            self.db.commit()

        if updates:
            self._stay_awake += 30
        else:
            if not self._stay_awake:
                logger.debug('Entering sleep mode')
                return 4

        self._stay_awake = self._stay_awake - 1 if self._stay_awake > 0 else 0
        return 1

    def process_message(self, message):
        # Register user
        user = self.db.get_or_create_user(message.from_user.id)[0]
        user.update(message.from_user.first_name,
                    message.from_user.last_name,
                    message.from_user.username)

        # Register tab
        tab, created = self.db.get_or_create_tab(message.chat.id)

        # Register user in tab
        tab.register_user(user.id)

        if message.reply_to_message:
            key = '{}_{}'.format(message.chat.id, message.reply_to_message.message_id)
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


if __name__ == "__main__":
    bot = VereseBot()
    try:
        while True:
            timeout = bot.process_messages()
            sleep(timeout)
    except KeyboardInterrupt:
        bot.db.close()
