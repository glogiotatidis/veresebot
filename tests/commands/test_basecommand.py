from commands import BotCommand


class FakeCommand(BotCommand):
    command = '/fake'

    def default(self, message):
        pass


def test_match(message):
    message.text = '/fake'
    assert FakeCommand.match(message)


def test_no_text(message):
    message.text = None
    assert not FakeCommand.match(message)


def test_other_text(message):
    message.text = '/foo'
    assert not FakeCommand.match(message)
