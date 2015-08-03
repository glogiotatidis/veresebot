import re

from . import BotCommand


class LastCommand(BotCommand):
    command = '/last'

    def default(self, message):
        match = re.match('(/last)( (?P<howmany>\d+))?', message.text)
        howmany = int(match.groupdict(5)['howmany'])
        tab = self._db.get_or_create_tab(message.chat.id)[0]
        last_entries = u'\n'.join([
            u'{}: {} for {}'.format(entry.amount, entry.date.humanize(), entry.reason)
            for entry in tab.entries[:howmany]])
        if not last_entries:
            last_entries = 'No entries!'
        self._say(message, last_entries)
