from functools import partial

import telegram
from tzwhere import tzwhere

from . import BotCommand

TZ = tzwhere.tzwhere()


class SettingsCommand(BotCommand):
    command = '/settings'

    def default(self, message):
        keyboard = [['Set timezone']]
        reply_markup = telegram.ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True,
            one_time_keyboard=True, selective=True)
        msg = self._say(message, 'Settings', reply_markup=reply_markup)
        self.queue(msg, partial(self.process_settings))

    def process_settings(self, message):
        if message.text and message.text == 'Set timezone':
            msg = self._say(message, "Send me your location and I'll do the rest",
                            telegram.ForceReply(selective=True))
            self.queue(msg, partial(self.set_timezone))

        else:
            self._say(message, 'Nope')

    def set_timezone(self, message):
        tab, created = self._db.get_or_create_tab(message.chat.id)
        tz = TZ.tzNameAt(message.location.latitude, message.location.longitude)
        tab.set_timezone(tz)
        self._say(message, 'Timezone set to {}'.format(tz))
