from functools import partial

import telegram

from . import BotCommand


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
        text = '\n'.join(['({}) for {}'.format(i+1, cmd['text'])
                          for i, cmd in enumerate(self.commands)])
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
