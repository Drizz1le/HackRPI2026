"""Token and session auth (synthetic)."""
import hashlib
import hmac


def _sign(token, secret):
    return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def verify_token(token, expected, secret):
    if not token or len(token) < 16:
        return False
    signed = _sign(token, secret)
    # constant-time comparison avoids timing side channels
    return hmac.compare_digest(signed, expected)
