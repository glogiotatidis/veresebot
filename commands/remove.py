import telegram

from . import CommandError
from add import AddCommand


class RemoveCommand(AddCommand):
    command = '/remove'

    def remove(self, tab_id, user_id, message_id, date, amount, reason=''):
        tab = self.get_tab(tab_id)
        tab.remove(message_id, user_id, date, amount, reason)

    def process_howmuch(self, message):
        try:
            amount, reason = self.get_amount(message.text)
        except CommandError:
            self.bot.say(message, "Nope, I don't get ya")
            return
        self.remove(message.chat.id, message.from_user.id, message.message_id,
                    message.date, amount, reason)
        self.bot.say(message, '{} OK, removed {}'.format(telegram.Emoji.WHITE_HEAVY_CHECK_MARK,
                                                         amount))
