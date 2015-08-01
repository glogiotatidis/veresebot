#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import defaultdict
from time import sleep

import arrow
import telegram
import persistent
import ZODB
import ZODB.FileStorage
import BTrees.OOBTree
import transaction

import config
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


class User(persistent.Persistent):
    def __init__(self, user_id):
        self.id = user_id

    def update(self, first_name, last_name, username):
        self.first_name = first_name or ''
        self.last_name = last_name or ''
        self.username = username or ''
        self._p_changed__ = True


class Entry(object):
    def __init__(self, message_id, user_id, amount, date, reason=None):
        self.message_id = message_id
        self.user_id = user_id
        self.amount = amount
        self.reason = 'stuff' if not reason else reason
        self.date = date


class Tab(persistent.Persistent):
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.grandtotal = 0
        self.entries = []
        self.tz = 'UTC'
        self.users = defaultdict(int)

    def clear(self):
        self.entries = []
        self.grandtotal = 0
        self.users = defaultdict(int)
        self._p_changed__ = True

    def set_timezone(self, tz):
        self.tz = tz

    def remove(self, message_id, user_id, date, amount, reason=None):
        return self.add(message_id, user_id, date, -1 * amount, reason)

    def register_user(self, user_id):
        self.users[user_id]

    def add(self, message_id, user_id, date, amount, reason=''):
        position = 0
        for position, v in enumerate(self.entries):
            if v.message_id == message_id:
                # Already in list, ignore
                logger.debug('not adding {}, already in list'.format(amount))
                return
            elif v.message_id < message_id:
                break

        date = arrow.get(date).to(self.tz)
        entry = Entry(message_id, user_id, amount, date, reason)
        logger.debug('adding {}'.format(amount))
        self.entries.insert(position, entry)

        self.grandtotal += amount
        self.users[user_id] += amount

        self._p_changed__ = True


class DB(object):
    def __init__(self):
        # Setup DB
        storage = ZODB.FileStorage.FileStorage(config.db_filename)
        self._db = ZODB.DB(storage)
        self._connection = self._db.open()
        self.root = self._connection.root
        if not hasattr(self.root, 'tabs'):
            self.root.tabs = BTrees.OOBTree.BTree()
        if not hasattr(self.root, 'users'):
            self.root.users = BTrees.OOBTree.BTree()

    def get_or_create_tab(self, tab_id):
        if tab_id in self.root.tabs:
            return self.root.tabs[tab_id], False

        tab = Tab(tab_id)
        self.root.tabs[tab_id] = tab
        return tab, True

    def get_or_create_user(self, user_id):
        if user_id in self.root.users:
            return self.root.users[user_id], False

        user = User(user_id)
        self.root.users[user_id] = user
        logger.debug('Created user {}'.format(user_id))
        return user, True

    def commit(self):
        transaction.commit()

    def close(self):
        self._db.close()


class VereseBot(object):
    COMMANDS = [AddCommand, RemoveCommand, TotalCommand,
                ClearCommand, LastCommand, PingCommand, ExportCommand,
                SplitCommand, SetTimezoneCommand]

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
