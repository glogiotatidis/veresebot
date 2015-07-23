import re
from time import sleep

import arrow
import telegram
import persistent
import ZODB, ZODB.FileStorage
import BTrees.OOBTree
import transaction

import config
from log import logger


class Entry(object):
    def __init__(self, id, user_id, amount, date, reason=None):
        self.id = id
        self.user_id = user_id
        self.amount = amount
        self.reason = '' if not reason else reason
        self.date = arrow.get(date)


class Tab(persistent.Persistent):
    def __init__(self, user_id):
        self.user_id = user_id
        self.grandtotal = 0
        self.entries = []

    def add(self, id, user_id, date, amount, reason=''):
        for v in self.entries:
            if v.id == id:
                # Already in list, ignore
                return
            elif v.id < id:
                break

        entry = Entry(id, user_id, amount, date, reason)
        for position, v in enumerate(self.entries):
            if v.id < entry.id:
                print 'inserting,', position, v
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


class VereseBot(object):
    COMMANDS = ['add', 'remove', 'daytotal', 'weektotal', 'monthtotal', 'yeartotal', 'grandtotal', 'start']

    def __init__(self):
        self.db = DB()
        # Connect to Telegram
        self._bot = telegram.Bot(token=config.token)
        self.queue = {}

    def say(self, reply_to_message, text, reply=False, reply_markup=None):
        return self._bot.sendMessage(chat_id=reply_to_message.chat_id,
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

    def is_command(self, message):
        return message.text.startswith('/')

    def get_command(self, message):
        try:
            cmd, content = message.text[1:].split(' ', 1)
        except ValueError:
            cmd = message.text[1:]
            content = ''

        if cmd in self.COMMANDS:
            return cmd, content

        return (None, message.text)

    def process_message(self, message):
        if isinstance(message.chat, telegram.groupchat.GroupChat):
            # Ignore group chats for the time being
            return

        if not self.is_command(message):
            key = '{}_{}'.format(message.chat_id, message.reply_to_message.message_id)
            if key in self.queue:
                k = self.queue.pop(key)
                k[0](*k[1:], content=message.text)
            return

        cmd, content = self.get_command(message)
        if not cmd:
            logger.debug('No command found: {}'.format(content))
            return

        if not hasattr(self, 'process_{}'.format(cmd)):
            raise NotImplementedError(cmd)

        logger.debug('Calling process_{}'.format(cmd))
        getattr(self, 'process_{}'.format(cmd))(message, content)

    def process_daytotal(self, message, content):
        pass

    def process_grandtotal(self, message, content):
        tab = self.db.get_or_create_tab(message.chat.id)[0]
        self.say(message, 'Total: {}'.format(tab.grandtotal))

    def process_add(self, message, content):
        if content:
            tab = self.db.get_or_create_tab(message.chat.id)[0]
            match = re.match('(?P<amount>\d+(\.\d+)?)( (?P<reason>.*))?', content)

            if not match:
                self.say(message, "I don't get ya")
                return

            amount = float(match.groupdict()['amount'])
            reason = match.groupdict()['reason']
            tab.add(message.message_id, int(message.from_user.id), message.date, amount, reason)
            self.say(message, 'Added {}'.format(amount))
        else:
            msg = self.say(message, 'How much?', reply=True, reply_markup=telegram.ForceReply(selective=True))
            self.queue['{}_{}'.format(message.chat_id, msg.message_id)] = [self.process_add, message]

    def process_start(self, message, content):
        chat_id = message.chat.id
        tab, created = self.db.get_or_create_tab(chat_id)
        self.say(message, 'Welcome mate, I just created a new tab for you.')

    def process_messages(self):
        updates = self.get_updates()

        for update in updates:
            self.process_message(update.message)
            self.db.root.last_update = update.update_id
            self.db.commit()


if __name__ == "__main__":
    bot = VereseBot()

    try:
        while True:
            bot.process_messages()
            sleep(3)
    except KeyboardInterrupt:
        bot.db_connection.close()
