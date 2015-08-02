import telegram


class CommandError(Exception):
    pass


class BotCommand(object):
    def __init__(self, bot, *args, **kwargs):
        self.bot = bot
        self._db = self.bot.db
        self._say = self.bot.say

    def __call__(self, message, *args, **kwargs):
        return self.default(message, *args, **kwargs)

    def queue(self, message, next_cmd):
        if isinstance(message.chat, telegram.user.User):
            # This is a direct chat with a user, reply to message will not
            # get populated. Instead wait for the message with id msg+1
            msg_id = message.message_id+1
        else:
            msg_id = message.message_id
        self.bot.queue['{}_{}'.format(message.chat.id, msg_id)] = next_cmd

    @classmethod
    def match(cls, message):
        return False

    def get_tab(self, tab_id):
        return self._db.get_or_create_tab(tab_id)[0]
