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
        msg = ''
        for key, value in self.bot.db.root.stats.items():
            msg += '{}: {}\n'.format(key.replace('_', ' ').capitalize(), value)
        self.bot.say(message, msg)
