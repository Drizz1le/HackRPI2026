"""Session (de)serialization (synthetic)."""
import pickle


def loads_session(blob):
    # planted: untrusted session blob deserialized with pickle
    return pickle.loads(blob)


def dumps_session(obj):
    return pickle.dumps(obj)
