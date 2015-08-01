from functools import partial

import telegram
from tzwhere import tzwhere

from . import BotCommand

TZ = tzwhere.tzwhere()


class SetTimezoneCommand(BotCommand):
    @classmethod
    def match(cls, message):
        if message.text and message.text.startswith('/set_timezone'):
            return True

    def default(self, message):
        msg = self._say(message, "Send me your location and I'll do the rest",
                        telegram.ForceReply(selective=True))
        self.queue(message.chat.id, msg.message_id, partial(self.process_location))

    def process_location(self, message):
        tab, created = self._db.get_or_create_tab(message.chat.id)
        tz = TZ.tzNameAt(message.location.latitude, message.location.longitude)
        tab.set_timezone(tz)
        self._say(message, 'Timezone set to {}'.format(tz))
