from functools import partial

import requests
import telegram

from . import BotCommand


class SettingsCommand(BotCommand):
    command = '/settings'

    def default(self, message):
        keyboard = [['Set timezone']]
        reply_markup = telegram.ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True,
            one_time_keyboard=True, selective=True)
        msg = self.bot.say(message, 'Settings', reply_markup=reply_markup)
        self.queue(msg, partial(self.process_settings))

    def process_settings(self, message):
        if message.text and message.text == 'Set timezone':
            msg = self.bot.say(message, "Send me your location and I'll do the rest",
                               telegram.ForceReply(selective=True))
            self.queue(msg, partial(self.set_timezone))

        else:
            self.bot.say(message, 'Nope')

    def set_timezone(self, message):
        if not message.location:
            self.bot.say(message, "Nope that didn't work, try again.")
            return

        tab, created = self._db.get_or_create_tab(message.chat.id)

        geonames_url = 'http://api.geonames.org/timezoneJSON?lat={lat}&lng={lon}&username=demo'
        res = requests.get(geonames_url.format(lat=message.location.latitude,
                                               lon=message.location.longitude)).json()

        if 'timezoneId' not in res:
            self.bot.say(message, 'Cannot set timezone')
            return

        tab.set_timezone(res['timezoneId'])
        self.bot.say(message, 'Timezone set to {}'.format(res['timezoneId']))
