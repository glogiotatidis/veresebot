import random
from functools import partial

import arrow
import telegram

from . import BotCommand


class TotalCommand(BotCommand):
    command = '/total'

    def __init__(self, *args, **kwargs):
        self.commands = [
            {'text': "Today's Total",
             'function': self.get_todays_total},
            {'text': 'This Month',
             'function': self.get_month_total},
            {'text': 'Last Month',
             'function': self.get_last_month_total},
            {'text': 'Grand Total',
             'function': self.get_grand_total},
            ]
        super(TotalCommand, self).__init__(*args, **kwargs)

    def default(self, message):
        keyboard = [["Today's Total"],
                    ["This Month", "Last Month"],
                    ['Grand Total']]
        reply_markup = telegram.ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True,
            one_time_keyboard=True, selective=True)
        msg = self._say(message, 'Choose', reply_markup=reply_markup)
        self.queue(msg, partial(self.process_which_total))

    def process_which_total(self, message):
        if not message.text:
            self._say(message, 'Nope')
            return

        for command in self.commands:
            if message.text == command['text']:
                command['function'](message)

    def get_month_total(self, message):
        tab = self.get_tab(message.chat.id)
        from_date = arrow.now(tab.tz).floor('month')
        self._say(message, "Month's Total: {}".format(tab.get_total(from_date=from_date)),
                  reply_markup=telegram.ReplyKeyboardHide())

    def get_last_month_total(self, message):
        tab = self.get_tab(message.chat.id)
        from_date, to_date = arrow.now(tab.tz).replace(months=-1).span('month')
        total = tab.get_total(from_date=from_date, to_date=to_date)
        self._say(message, "Last Month's Total: {}".format(total),
                  reply_markup=telegram.ReplyKeyboardHide())

    def get_todays_total(self, message):
        tab = self.get_tab(message.chat.id)
        today = arrow.now(tab.tz).floor('day')
        self._say(message, "Today's Total: {}".format(tab.get_total(from_date=today)),
                  reply_markup=telegram.ReplyKeyboardHide())

    def get_grand_total(self, message):
        tab = self.get_tab(message.chat.id)
        emoji = getattr(telegram.Emoji,
                        random.choice(['ASTONISHED_FACE', 'FACE_SCREAMING_IN_FEAR']))
        self._say(message, 'Grand Total: {} {}'.format(tab.grandtotal, emoji),
                  reply_markup=telegram.ReplyKeyboardHide())
