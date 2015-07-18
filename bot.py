from time import sleep

import telegram

import config




class VereseBot(object):
    def __init__(self):
        self._bot = telegram.Bot(token=config.token)
        self.last_update = 0

    def get_updates(self):
        updates = self._bot.getUpdates(offset=self.last_update)
        updates = [u for u in updates if u.update_id > self.last_update]
        if updates:
            self.last_update = updates[-1].update_id

        return updates

    def process_message(self, message):
        self._bot.sendMessage(chat_id=message.chat_id, text=message.text)

    def process_messages(self):
        updates = self.get_updates()
        for update in updates:
            self.process_message(update.message)


if __name__ == "__main__":
    bot = VereseBot()
    while True:
        bot.process_messages()
        sleep(3)
