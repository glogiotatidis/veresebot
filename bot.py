#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from time import sleep

import arrow
import telegram
import persistent
import ZODB, ZODB.FileStorage
import BTrees.OOBTree
import transaction
# from tzwhere import tzwhere

import config
from log import logger


class Entry(object):
    def __init__(self, id, user_id, amount, date, reason=None):
        if not reason:
            reason = 'stuff'
        self.id = id
        self.user_id = user_id
        self.amount = amount
        self.reason = '' if not reason else reason
        self.date = date


class Tab(persistent.Persistent):
    def __init__(self, user_id):
        self.user_id = user_id
        self.grandtotal = 0
        self.entries = []
        self.tz = 'UTC'

    def clear(self):
        self.entries = []
        self.grandtotal = 0
        self._p_changed__ = True

    def set_timezone(self, tz):
        self.tz = tz

    def remove(self, id, user_id, date, amount, reason=None):
        return self.add(id, user_id, date, -1 * amount, reason)

    def add(self, message_id, user_id, date, amount, reason=''):
        for v in self.entries:
            if v.id == message_id:
                # Already in list, ignore
                logger.debug('not adding {}, already in list'.format(amount))
                return
            elif v.id < message_id:
                break

        date = arrow.get(date).to(self.tz)
        entry = Entry(message_id, user_id, amount, date, reason)
        for position, v in enumerate(self.entries):
            if v.id < entry.id:
                logger.debug('adding {}'.format(amount))
                self.entries.insert(position, entry)
                break
        else:
            self.entries.append(entry)

        self.grandtotal += amount
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

    def get_or_create_tab(self, id):
        if id in self.root.tabs:
            return self.root.tabs[id], False

        tab = Tab(id)
        self.root.tabs[id] = tab
        return tab, True

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

    def get_tab(self, id):
        return self._db.get_or_create_tab(id)[0]


class TotalCommand(BotCommand):
    def __init__(self, *args, **kwargs):
        self.commands = [
             {'text': 'Day Total',
              'function': self.get_day_total},
             {'text': 'Week Total',
              'function': self.get_week_total},
             {'text': 'Month Total',
              'function': self.get_month_total},
             {'text': 'Year Total',
              'function': self.get_year_total},
             {'text': 'Grand Total',
              'function': self.get_grand_total}
        ]
        super(TotalCommand, self).__init__(*args, **kwargs)

    def default(self, message):
        text = '\n'.join(['({}) for {}'.format(i+1, cmd['text']) for i, cmd in enumerate(self.commands)])
        msg = self._say(message, text, reply_markup=telegram.ForceReply(selective=True))
        self.queue(message.chat.id, msg.message_id, {'call': self.process_which_total})

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
        if hasattr(message, 'text') and message.text.startswith('/total'):
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
            self.queue(message.chat.id, msg.message_id, {'call': self.process_howmuch})

    def process_howmuch(self, message):
        try:
            amount, reason = self.get_amount(message.text)
        except CommandError:
            self._say(message, "Nope, I don't get ya")
            return
        self.add(message.chat.id, message.from_user.id, message.message_id, message.date, amount, reason)
        self._say(message, 'Added {}'.format(amount))

    @classmethod
    def match(cls, message):
        if hasattr(message, 'text') and message.text.startswith('/add'):
            return True


class RemoveCommand(AddCommand):
    @classmethod
    def match(cls, message):
        if hasattr(message, 'text') and message.text.startswith('/remove'):
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
        self.remove(message.chat.id, message.from_user.id, message.message_id, message.date, amount, reason)
        self._say(message, 'Removed {}'.format(amount))


class StartCommand(BotCommand):
    def default(self, message):
        chat_id = message.chat.id
        tab, created = self._db.get_or_create_tab(chat_id)
        self._say(message, 'Welcome mate, I just created a new tab for you.')

    @classmethod
    def match(cls, message):
        if hasattr(message, 'text') and message.text.startswith('/start'):
            return True


class ClearCommand(BotCommand):
    @classmethod
    def match(cls, message):
        if hasattr(message, 'text') and message.text.startswith('/clear'):
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
        if hasattr(message, 'text') and message.text.startswith('/last'):
            return True

    def default(self, message):
        match = re.match('(/last)( (?P<howmany>\d+))?', message.text)
        howmany = int(match.groupdict(5)['howmany'])
        tab = self._db.get_or_create_tab(message.chat.id)[0]
        last_entries = u'\n'.join([
            u'{}: {} for {}'.format(entry.amount, entry.date.humanize(), entry.reason) for entry in tab.entries[:howmany]])
        if not last_entries:
            last_entries = 'No entries!'
        self._say(message, last_entries)


class PingCommand(BotCommand):
    @classmethod
    def match(cls, message):
        if hasattr(message, 'text') and message.text.startswith('/ping'):
            return True

    def default(self, message):
        self._say(message, 'Pong!')


class VereseBot(object):
    COMMANDS = [StartCommand, AddCommand, RemoveCommand, TotalCommand, ClearCommand, LastCommand, PingCommand]

    def __init__(self):
        self.db = DB()
        # self.tz = tzwhere.tzwhere()

        # Connect to Telegram
        self._bot = telegram.Bot(token=config.token)
        self.queue = {}

    def say(self, reply_to_message, text, reply_markup=None):
        return self._bot.sendMessage(chat_id=reply_to_message.chat.id,
                                     text=text,
                                     reply_to_message_id=reply_to_message.message_id,
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
            print [tab[1].grandtotal for tab in self.db.root.tabs.items()]

    def process_message(self, message):
        if isinstance(message.chat, telegram.groupchat.GroupChat):
            # Ignore group chats for the time being
            return

        if message.reply_to_message:
            key = '{}_{}'.format(message.chat.id, message.reply_to_message.message_id)
            if key in self.queue:
                k = self.queue.pop(key)
                logger.debug('Calling queued {}'.format(k['call']))
                k['call'](message, **k.get('parameters', {}))
                return

        for cmd in self.COMMANDS:
            if cmd.match(message):
                break
        else:
            logger.debug('No command found: {}'.format(message.message_id))
            return

        logger.debug('Calling process_{}'.format(cmd))
        cmd(bot=self)(message)

    # def process_location(self, message, content):
    #     tab, created = self.db.get_or_create_tab(message.chat.id)
    #     tz = self.tz.tzNameAt(content.latitude, content.longitude)
    #     tab.set_timezone(tz)
    #     self.say(message, 'Timezone {}'.format(tz))



if __name__ == "__main__":
    bot = VereseBot()

    try:
        while True:
            bot.process_messages()
            sleep(1)
    except KeyboardInterrupt:
        bot.db.close()
