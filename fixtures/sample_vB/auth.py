"""Tiny synthetic target, version B. Used only to demo the diff pipeline."""


def login(username, password):
    # version B dropped the input validation (the planted change)
    return _check_credentials(username, password)


def _check_credentials(username, password):
    return username == "admin" and password == "correcthorse"
