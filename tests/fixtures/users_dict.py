import pytest

@pytest.fixture(scope='function')
def users_dict():
    _users_dict = {}
    return _users_dict