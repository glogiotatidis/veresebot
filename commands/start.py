from . import BotCommand


class StartCommand(BotCommand):
    command = '/start'

    def default(self, message):
        self.bot.say(message, ("Hi there, nice to meet you! Feel free to start right"
                               " away with a command."))
