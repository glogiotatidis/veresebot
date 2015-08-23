import config

from . import BotCommand


class StatsCommand(BotCommand):
    command = '/stats'

    @classmethod
    def match(cls, message):
        if message.from_user.id not in config.administrators:
            return False
        return super(StatsCommand, cls).match(message)

    def default(self, message):
        self.bot.say(message, 'Number of messages: {}'.format(
            self.bot.db.root.stats['number_of_messages']))
