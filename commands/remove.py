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
            self._say(message, "Nope, I don't get ya")
            return
        self.remove(message.chat.id, message.from_user.id, message.message_id,
                    message.date, amount, reason)
        self._say(message, 'Removed {}'.format(amount))
