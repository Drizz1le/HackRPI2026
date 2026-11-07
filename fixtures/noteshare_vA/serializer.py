"""Session (de)serialization (synthetic)."""
import json


def loads_session(blob):
    return json.loads(blob)


def dumps_session(obj):
    return json.dumps(obj)
