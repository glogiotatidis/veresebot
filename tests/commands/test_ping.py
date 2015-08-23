from commands.ping import PingCommand


def test_default(bot, message):
    command = PingCommand(bot)
    command(message)
    command.bot.say.assert_called_with(message, 'Pong!')
