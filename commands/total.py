import random
from functools import partial

import telegram

from . import BotCommand


class TotalCommand(BotCommand):
    def __init__(self, *args, **kwargs):
        self.commands = [
            {'text': "Today's Total",
             'function': self.get_todays_total},
            {'text': 'Grand Total',
             'function': self.get_grand_total},
            ]
        super(TotalCommand, self).__init__(*args, **kwargs)

    def default(self, message):
        keyboard = [["Today's Total", 'Grand Total']]
        reply_markup = telegram.ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True,
            one_time_keyboard=True, selective=True)
        msg = self._say(message, 'Choose', reply_markup=reply_markup)
        if isinstance(message.chat, telegram.user.User):
            # This is a direct chat with a user, reply to message will not
            # get populated. Instead wait for the message with id msg+1
            msg_id = msg.message_id+1
        else:
            msg_id = msg.message_id
        self.queue(message.chat.id, msg_id, partial(self.process_which_total))

    def process_which_total(self, message):
        if not message.text:
            self._say(message, 'Nope')
            return

        for command in self.commands:
            if message.text == command['text']:
                command['function'](message)

    def get_todays_total(self, message):
        tab = self.get_tab(message.chat.id)
        self._say(message, "Today's Total: {}".format(tab.get_todays_total()),
                  reply_markup = telegram.ReplyKeyboardHide())

    def get_grand_total(self, message):
        tab = self.get_tab(message.chat.id)
        emoji = getattr(telegram.Emoji,
                        random.choice(['ASTONISHED_FACE', 'FACE_SCREAMING_IN_FEAR']))
        self._say(message, 'Grand Total: {} {}'.format(tab.grandtotal, emoji),
                  reply_markup = telegram.ReplyKeyboardHide())

    @classmethod
    def match(cls, message):
        if message.text and message.text.startswith('/total'):
            return True
