#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from collections import defaultdict
from functools import partial
from time import sleep

import arrow
import telegram
import persistent
import ZODB, ZODB.FileStorage
import BTrees.OOBTree
import transaction
from tzwhere import tzwhere

import config
from log import logger


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

class CommandError(Exception):
    pass


class BotCommand(object):
    def __init__(self, bot, *args, **kwargs):
        self.bot = bot
        self._db = self.bot.db
        self._say = self.bot.say

    def __call__(self, message, *args, **kwargs):
        return self.default(message, *args, **kwargs)

    def queue(self, chat_id, msg_id, next_cmd):
        self.bot.queue['{}_{}'.format(chat_id, msg_id)] = next_cmd

    @classmethod
    def match(cls, message):
        return False

    def get_tab(self, tab_id):
        return self._db.get_or_create_tab(tab_id)[0]


class TotalCommand(BotCommand):
    def __init__(self, *args, **kwargs):
        self.commands = [
             # {'text': 'Day Total',
             #  'function': self.get_day_total},
             # {'text': 'Week Total',
             #  'function': self.get_week_total},
             # {'text': 'Month Total',
             #  'function': self.get_month_total},
             # {'text': 'Year Total',
             #  'function': self.get_year_total},
             {'text': 'Grand Total',
              'function': self.get_grand_total}
        ]
        super(TotalCommand, self).__init__(*args, **kwargs)

    def default(self, message):
        text = '\n'.join(['({}) for {}'.format(i+1, cmd['text']) for i, cmd in enumerate(self.commands)])
        msg = self._say(message, text, reply_markup=telegram.ForceReply(selective=True))
        self.queue(message.chat.id, msg.message_id, partial(self.process_which_total))

    def process_which_total(self, message):
        if not message.text:
            self._say(message, 'Nope')
            return

        for i, command in enumerate(self.commands):
            if message.text == str(i+1):
                command['function'](message)

    def get_day_total(self, message):
        pass

    def get_week_total(self, message):
        pass

    def get_month_total(self, message):
        pass

    def get_year_total(self, message):
        pass

    def get_grand_total(self, message):
        tab = self.get_tab(message.chat.id)
        self._say(message, 'Grand Total: {}'.format(tab.grandtotal))

    @classmethod
    def match(cls, message):
        if message.text and message.text.startswith('/total'):
            return True


class AddCommand(BotCommand):
    def get_amount(self, content):
        match = re.match('((/add )|(/remove ))?(?P<amount>\d+(\.\d+)?)( (?P<reason>.*))?', content)
        if not match:
            raise CommandError()

        amount = float(match.groupdict()['amount'])
        reason = match.groupdict()['reason']
        return amount, reason

    def add(self, tab_id, user_id, message_id, date, amount, reason=''):
        tab = self.get_tab(tab_id)
        tab.add(message_id, user_id, date, amount, reason)

    def default(self, message):
        content = message.text.split(' ', 1)[1] if len(message.text.split(' ', 1)) == 2 else ''
        if content:
            self.process_howmuch(message)
        else:
            msg = self._say(message, 'How much?', reply_markup=telegram.ForceReply(selective=True))
            self.queue(message.chat.id, msg.message_id, partial(self.process_howmuch))

    def process_howmuch(self, message):
        try:
            amount, reason = self.get_amount(message.text)
        except CommandError:
            self._say(message, "Nope, I don't get ya")
            return
        self.add(message.chat.id, message.from_user.id, message.message_id, message.date, amount, reason)
        self._say(message, telegram.Emoji.THUMBS_UP_SIGN)

    @classmethod
    def match(cls, message):
        if message.text and message.text.startswith('/add'):
            return True


class RemoveCommand(AddCommand):
    @classmethod
    def match(cls, message):
        if message.text and message.text.startswith('/remove'):
            return True

    def remove(self, tab_id, user_id, message_id, date, amount, reason=''):
        tab = self.get_tab(tab_id)
        tab.remove(message_id, user_id, date, amount, reason)

    def process_howmuch(self, message):
        try:
            amount, reason = self.get_amount(message.text)
        except CommandError:
            self._say(message, "Nope, I don't get ya")
            return
        self.remove(message.chat.id, message.from_user.id, message.message_id,
                    message.date, amount, reason)
        self._say(message, 'Removed {}'.format(amount))


class ClearCommand(BotCommand):
    @classmethod
    def match(cls, message):
        if message.text and message.text.startswith('/clear'):
            return True

    def default(self, message):
        if message.text and message.text == '/clear do as I say':
            tab = self._db.get_or_create_tab(message.chat.id)[0]
            tab.clear()
            self._say(message, 'Tab cleared')

        else:
            self._say(message, "To really clear say '/clear do as I say'")


class LastCommand(BotCommand):
    @classmethod
    def match(cls, message):
        if message.text and message.text.startswith('/last'):
            return True

    def default(self, message):
        match = re.match('(/last)( (?P<howmany>\d+))?', message.text)
        howmany = int(match.groupdict(5)['howmany'])
        tab = self._db.get_or_create_tab(message.chat.id)[0]
        last_entries = u'\n'.join([
            u'{}: {} for {}'.format(entry.amount, entry.date.humanize(), entry.reason)
            for entry in tab.entries[:howmany]])
        if not last_entries:
            last_entries = 'No entries!'
        self._say(message, last_entries)


class PingCommand(BotCommand):
    @classmethod
    def match(cls, message):
        if message.text and message.text.startswith('/ping'):
            return True

    def default(self, message):
        self._say(message, 'Pong!')


class SplitCommand(BotCommand):
    @classmethod
    def match(cls, message):
        if message.text and message.text.startswith('/split'):
            return True

    def default(self, message):
        tab = self.get_tab(message.chat.id)
        if not tab.users:
            return
        per_person = tab.grandtotal / len(tab.users)
        text = ''
        for user_id, amount in tab.users.items():
            user = self._db.root.users[user_id]
            text += u'{}: {}\n'.format(user.first_name, per_person - amount)
        self._say(message, text)


class SetTimezoneCommand(BotCommand):
    @classmethod
    def match(cls, message):
        if message.text and message.text.startswith('/set_timezone'):
            return True

    def default(self, message):
        msg = self._say(message, "Send me your location and I'll do the rest",
                        telegram.ForceReply(selective=True))
        self.queue(message.chat.id, msg.message_id, partial(self.process_location))

    def process_location(self, message):
        tab, created = self._db.get_or_create_tab(message.chat.id)
        tz = self.bot.tz.tzNameAt(message.location.latitude, message.location.longitude)
        tab.set_timezone(tz)
        self._say(message, 'Timezone set to {}'.format(tz))


class ExportCommand(BotCommand):
    @classmethod
    def match(cls, message):
        if message.text and message.text.startswith('/export'):
            return True

    def default(self, message):
        import cStringIO
        import csv
        import os
        from tempfile import NamedTemporaryFile

        tab = self.get_tab(message.chat.id)
        csvfile = NamedTemporaryFile(suffix='.csv', prefix='verese-export-', delete=False)

        spamwriter = csv.writer(csvfile, delimiter=',')
        spamwriter.writerow(['Person', 'Amount', 'Date', 'Reason'])
        for entry in tab.entries:
            user = self._db.root.users[entry.user_id]
            user_repr = '{} {}'.format(user.first_name, user.last_name)
            spamwriter.writerow([user_repr, entry.amount, entry.date, entry.reason])
        csvfile.close()

        self.bot._bot.sendDocument(chat_id=message.chat.id, document=open(csvfile.name, 'rb'))
        os.unlink(csvfile.name)


class VereseBot(object):
    COMMANDS = [AddCommand, RemoveCommand, TotalCommand,
                ClearCommand, LastCommand, PingCommand, ExportCommand,
                SplitCommand, SetTimezoneCommand]

    def __init__(self):
        self._stay_awake = 30
        self.db = DB()
        self.tz = tzwhere.tzwhere()

        # Connect to Telegram
        self._bot = telegram.Bot(token=config.token)
        self.queue = {}

    def say(self, reply_to_message, text, reply_markup=None):
        # The telegram library doesn't play well with unicode, oh well.
        text = text.encode('utf-8') if isinstance(text, unicode) else text
        reply_to_message_id=reply_to_message.message_id if reply_markup else None
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
