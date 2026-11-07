"""Debug helpers (synthetic). Should not ship enabled."""
from config import DEBUG


def eval_expr(expr):
    # planted: evaluates arbitrary expressions when DEBUG is on
    if DEBUG:
        return eval(expr)
    raise RuntimeError("debug disabled")
