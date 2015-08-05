import csv
import os


from . import BotCommand


class ExportCommand(BotCommand):
    command = '/export'

    def default(self, message):
        from tempfile import mkstemp

        tab = self.get_tab(message.chat.id)

        csvhandle, csvfilename = mkstemp(suffix='.csv', prefix='verese-export-')
        with os.fdopen(csvhandle, 'wb') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')
            csvwriter.writerow(['Person', 'Amount', 'Date', 'Reason'])
            for entry in tab.entries:
                user = self._db.root.users[entry.user_id]
                user_repr = '{} {}'.format(user.first_name, user.last_name).strip()
                row = [u'{}'.format(x).encode('utf-8')
                       for x in [user_repr, entry.amount, entry.date, entry.reason]]
                csvwriter.writerow(row)

        self.bot._bot.sendDocument(chat_id=message.chat.id, document=open(csvfilename, 'rb'))
        os.unlink(csvfilename)
