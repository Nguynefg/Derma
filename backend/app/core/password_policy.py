"""Shared rules for new user/admin passwords; existing logins remain valid."""

import string

PASSWORD_REQUIREMENT = (
    "Mật khẩu phải có từ 6–128 ký tự, gồm chữ hoa, chữ thường, số và ký tự đặc biệt."
)


def valid_new_password(password: str) -> bool:
    return (
        6 <= len(password) <= 128
        and any(c in string.ascii_uppercase for c in password)
        and any(c in string.ascii_lowercase for c in password)
        and any(c in string.digits for c in password)
        and any(c in string.punctuation for c in password)
    )
