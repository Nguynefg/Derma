import pytest
from app.core.password_policy import valid_new_password


@pytest.mark.parametrize('password,expected', [
    ('Ab12@x', True), ('Ab1@x', False), ('abcdef', False),
    ('abcdef1!', False), ('ABCDEF1!', False), ('Abcdef12', False),
    ('Abcdef!?', False), ('Ab12 x', False),
    ('A' + 'b' * 125 + '1!', True), ('A' + 'b' * 126 + '1!', False),
])
def test_password_requirements(password, expected):
    assert valid_new_password(password) is expected
