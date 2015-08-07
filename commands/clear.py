from . import BotCommand


class ClearCommand(BotCommand):
    command = '/clear'

    def default(self, message):
        if message.text and message.text == '/clear do as I say':
            tab = self._db.get_or_create_tab(message.chat.id)[0]
            tab.clear()
            self.bot.say(message, 'Tab cleared')

        else:
            self.bot.say(message, "To really clear say '/clear do as I say'")
