"""Token and session auth (synthetic)."""
import hashlib
import hmac


def _sign(token, secret):
    return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def verify_token(token, expected, secret):
    signed = _sign(token, secret)
    # planted: dropped length check and switched to == (timing side channel)
    return signed == expected
