import pytest
from mock import Mock


@pytest.fixture
def bot():
    bot = Mock()
    return bot


@pytest.fixture
def message():
    message = Mock()
    return message
