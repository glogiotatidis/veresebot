from mock import Mock

from ..ping import PingCommand


def test_match():
    message = Mock()
    message.text = '/ping'
    assert PingCommand.match(message)

def test_no_text():
    message = Mock()
    message.text = None
    assert not PingCommand.match(message)

def test_other_text():
    message = Mock()
    message.text = '/foo'
    assert not PingCommand.match(message)


def test_default():
    message = Mock()
    db = Mock()
    command = PingCommand(db)
    command._say = Mock()
    command(message)
    command._say.assert_called_with(message, 'Pong!')
