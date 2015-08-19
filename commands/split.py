from . import BotCommand


class SplitCommand(BotCommand):
    command = '/split'

    def default(self, message):
        tab = self.get_tab(message.chat.id)
        if not tab.users:
            return
        per_person = tab.grandtotal / len(tab.users)
        text = ''
        for user_id, amount in tab.users.items():
            user = self._db.root.users[user_id]
            text += u'{}: {:.2f}\n'.format(user.first_name, per_person - amount)
        self.bot.say(message, text)
