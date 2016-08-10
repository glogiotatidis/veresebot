import arrow
import telegram

from . import BotCommand


class TotalCommand(BotCommand):
    command = '/total'

    def default(self, message):
        text = ''
        tab = self.get_tab(message.chat.id)

        from_date = arrow.now(tab.tz).floor('day')
        total = tab.get_total(from_date=from_date)
        text += "Today's Total: *{:.2f}*\n".format(total)

        from_date = arrow.now(tab.tz).floor('week')
        total = tab.get_total(from_date=from_date)
        text += "Week's Total: *{:.2f}*\n".format(total)

        from_date = arrow.now(tab.tz).floor('month')
        total = tab.get_total(from_date=from_date)
        text += "Current Month's Total: *{:.2f}*\n".format(total)

        from_date, to_date = arrow.now(tab.tz).replace(months=-1).span('month')
        total = tab.get_total(from_date=from_date, to_date=to_date)
        text += "Last Month's Total: *{:.2f}*\n".format(total)

        from_date = arrow.now(tab.tz).floor('year')
        total = tab.get_total(from_date=from_date)
        text += "Current Year's Total: *{:.2f}*\n".format(total)

        self.bot.say(message, text, reply_markup=telegram.ReplyKeyboardHide(),
                     markdown=True, reply_to_message=False)
