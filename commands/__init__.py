class CommandError(Exception):
    pass


class BotCommand(object):
    def __init__(self, bot, *args, **kwargs):
        self.bot = bot
        self._db = self.bot.db
        self._say = self.bot.say

    def __call__(self, message, *args, **kwargs):
        return self.default(message, *args, **kwargs)

    def queue(self, chat_id, msg_id, next_cmd):
        self.bot.queue['{}_{}'.format(chat_id, msg_id)] = next_cmd

    @classmethod
    def match(cls, message):
        return False

    def get_tab(self, tab_id):
        return self._db.get_or_create_tab(tab_id)[0]
