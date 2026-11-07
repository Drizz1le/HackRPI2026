"""Deprecated helpers kept for backward compatibility (synthetic)."""


def old_hash(value):
    # legacy weak hash, unused
    return sum(ord(c) for c in value) % 9973
