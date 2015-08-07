from commands.ping import PingCommand


def test_match(message):
    message.text = '/ping'
    assert PingCommand.match(message)


def test_no_text(message):
    message.text = None
    assert not PingCommand.match(message)


def test_other_text(message):
    message.text = '/foo'
    assert not PingCommand.match(message)


def test_default(bot, message):
    command = PingCommand(bot)
    command(message)
    command.bot.say.assert_called_with(message, 'Pong!')
