import importlib
import os
from collections import defaultdict

import ZODB
import ZODB.FileStorage
import arrow
import persistent
import transaction
import zodburi

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

    def get_entries(self, from_date=None, to_date=None):
        if from_date and to_date and from_date > to_date:
            return []

        entries = []
        for entry in self.entries:
            if to_date and to_date < entry.date:
                continue

            if from_date:
                if entry.date >= from_date:
                    entries.append(entry)
                else:
                    break

        return entries

    def get_total(self, from_date=None, to_date=None):
        if not from_date and not to_date:
            return self.grandtotal

        if from_date and to_date and from_date > to_date:
            return -1

        total = 0
        entries = self.get_entries(from_date, to_date)
        for entry in entries:
            total += entry.amount

        return total


class DB(object):

    def __init__(self):
        # Setup DB
        storage = zodburi.resolve_uri(config.database_url)[0]()
        self._db = ZODB.DB(storage)
        self._connection = self._db.open()
        self.root = self._connection.root
        self.migrate()

    def migrate(self):
        for migration_file in sorted(os.listdir('migrations')):
            if migration_file.endswith('.pyc') or not migration_file.startswith('migration_'):
                continue
            mod = importlib.import_module('migrations.{}'.format(migration_file[:-3]))
            if not mod.Migration.is_applicable(self.root):
                logger.debug('Skipping migration {}'.format(mod.Migration.DB_VERSION))
                continue
            migration = mod.Migration(self.root)
            logger.info('Applying migration {}'.format(migration.DB_VERSION))
            migration.apply()

    def get_or_create_tab(self, tab_id):
        if tab_id in self.root.tabs:
            return self.root.tabs[tab_id], False

        tab = Tab(tab_id)
        self.root.tabs[tab_id] = tab
        self.root.stats['number_of_tabs'] += 1
        logger.debug('Created tab {}'.format(tab_id))
        return tab, True

    def get_or_create_user(self, user_id):
        if user_id in self.root.users:
            return self.root.users[user_id], False

        user = User(user_id)
        self.root.users[user_id] = user
        self.root.stats['number_of_users'] += 1
        logger.debug('Created user {}'.format(user_id))
        return user, True

    def commit(self):
        transaction.commit()

    def close(self):
        self._db.close()
