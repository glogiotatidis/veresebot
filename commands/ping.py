from . import BotCommand


class PingCommand(BotCommand):
    command = '/ping'

    def default(self, message):
        self.bot.say(message, 'Pong!')
