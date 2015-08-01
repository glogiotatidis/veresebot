from . import BotCommand


class PingCommand(BotCommand):
    @classmethod
    def match(cls, message):
        if message.text and message.text.startswith('/ping'):
            return True

    def default(self, message):
        self._say(message, 'Pong!')
