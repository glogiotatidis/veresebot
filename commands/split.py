from functools import partial

import arrow
import telegram

from . import BotCommand


class SplitCommand(BotCommand):
    command = '/split'

    def __init__(self, *args, **kwargs):
        self.commands = [
            {'text': "Split All",
             'function': self.get_all_split},
            {'text': 'Split this Month',
             'function': self.get_this_month_split},
            {'text': 'Split last Month',
             'function': self.get_last_month_split},
            ]
        super(SplitCommand, self).__init__(*args, **kwargs)

    def default(self, message):
        keyboard = [["Split All"],
                    ["Split this Month"],
                    ["Split last Month"]
                    ]
        reply_markup = telegram.ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True,
            one_time_keyboard=True, selective=True)
        msg = self.bot.say(message, 'Choose', reply_markup=reply_markup)
        self.queue(msg, partial(self.process_which_split))

    def process_which_split(self, message):
        if not message.text:
            self.bot.say(message, 'Nope')
            return

        for command in self.commands:
            if message.text == command['text']:
                command['function'](message)

    def _split(self, entries):
        total = 0
        users = {}
        if not entries:
            return 'No entries!'

        for entry in entries:
            total += entry.amount
            users[entry.user_id] = users.get(entry.user_id, 0) + entry.amount
        per_person = total / len(users)

        text = ''
        for user_id, amount in users.items():
            user = self._db.root.users[user_id]
            text += u'{}: {:.2f}\n'.format(user.first_name, per_person - amount)
        return text

    def get_all_split(self, message):
        tab = self.get_tab(message.chat.id)
        if not tab.users:
            return
        text = self._split(tab.entries)
        self.bot.say(message, text)

    def get_this_month_split(self, message):
        tab = self.get_tab(message.chat.id)
        if not tab.users:
            return
        from_date = arrow.now(tab.tz).floor('month')
        entries = tab.get_entries(from_date)
        text = self._split(entries)
        self.bot.say(message, text)

    def get_last_month_split(self, message):
        tab = self.get_tab(message.chat.id)
        if not tab.users:
            return
        from_date, to_date = arrow.now(tab.tz).replace(months=-1).span('month')
        entries = tab.get_entries(from_date, to_date)
        text = self._split(entries)
        self.bot.say(message, text)
