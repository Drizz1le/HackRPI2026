"""Tiny synthetic target, version A. Used only to demo the diff pipeline."""


def login(username, password):
    # version A validates the inputs before using them
    if not username or not password:
        raise ValueError("username and password are required")
    if len(password) < 8:
        raise ValueError("password too short")
    return _check_credentials(username, password)


def _check_credentials(username, password):
    return username == "admin" and password == "correcthorse"
