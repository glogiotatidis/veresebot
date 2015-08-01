import re
from functools import partial

import telegram

from . import BotCommand, CommandError


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
        self.add(message.chat.id, message.from_user.id, message.message_id,
                 message.date, amount, reason)
        self._say(message, telegram.Emoji.THUMBS_UP_SIGN)

    @classmethod
    def match(cls, message):
        if message.text and message.text.startswith('/add'):
            return True