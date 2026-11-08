"""Minimal FL Studio project (.flp) / preset (.fst) event reader & writer.

Format (reverse-engineered, cross-checked against PyFLP and files saved by FL 25):
  "FLhd" u32 len=6, i16 format, u16 n_channels, u16 ppq
  "FLdt" u32 len, then events:  id<64: 1-byte value, <128: 2 bytes, <192: 4 bytes,
  >=192: varint length + data.   .fst files are the same container (format 0x20 = channel state).
"""
import struct


def _varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def parse_events(data):
    ev, i = [], 0
    while i < len(data):
        eid = data[i]
        i += 1
        if eid < 64:
            size = 1
        elif eid < 128:
            size = 2
        elif eid < 192:
            size = 4
        else:
            size = shift = 0
            while True:
                b = data[i]
                i += 1
                size |= (b & 0x7F) << shift
                shift += 7
                if not b & 0x80:
                    break
        ev.append([eid, bytes(data[i:i + size])])
        i += size
    return ev


def read(path):
    raw = open(path, 'rb').read()
    assert raw[:4] == b'FLhd', 'not an FL file'
    fmt, nch, ppq = struct.unpack('<hHH', raw[8:14])
    assert raw[14:18] == b'FLdt'
    (n,) = struct.unpack('<I', raw[18:22])
    return {'format': fmt, 'channels': nch, 'ppq': ppq, 'events': parse_events(raw[22:22 + n])}


def encode(events):
    out = bytearray()
    for eid, val in events:
        out.append(eid)
        if eid >= 192:
            out += _varint(len(val))
        else:
            assert len(val) == (1 if eid < 64 else 2 if eid < 128 else 4), (eid, val)
        out += val
    return bytes(out)


def write(path, proj):
    body = encode(proj['events'])
    head = b'FLhd' + struct.pack('<IhHH', 6, proj['format'], proj['channels'], proj['ppq'])
    open(path, 'wb').write(head + b'FLdt' + struct.pack('<I', len(body)) + body)


def u(v):
    """Event value as int for fixed-size events."""
    return int.from_bytes(v, 'little', signed=False)


def b(eid, value):
    """Build a fixed-size event from an int (or a data/text event from bytes/str)."""
    if eid >= 192:
        if isinstance(value, str):
            value = (value + '\0').encode('utf-16-le')
        return [eid, value]
    size = 1 if eid < 64 else 2 if eid < 128 else 4
    return [eid, int(value).to_bytes(size, 'little', signed=value < 0)]


def text(v):
    try:
        return v.decode('utf-16-le').rstrip('\0')
    except UnicodeDecodeError:
        return v.decode('latin-1').rstrip('\0')


def names():
    """id -> name map from PyFLP's enums (reference only)."""
    import pyflp, pkgutil, importlib, enum
    out = {}
    for m in pkgutil.iter_modules(pyflp.__path__):
        mod = importlib.import_module('pyflp.' + m.name)
        for obj in vars(mod).values():
            if isinstance(obj, type) and issubclass(obj, enum.Enum) and obj.__name__.endswith('ID'):
                for e in obj:
                    v = e.value[0] if isinstance(e.value, tuple) else e.value
                    if isinstance(v, int):
                        out.setdefault(v, '%s.%s' % (obj.__name__, e.name))
    return out


if __name__ == '__main__':
    import sys
    p = read(sys.argv[1])
    nm = names()
    print('format', p['format'], 'channels', p['channels'], 'ppq', p['ppq'], 'events', len(p['events']))
    for k, (eid, v) in enumerate(p['events']):
        shown = u(v) if eid < 192 else (repr(text(v))[:70] if eid in (192, 193, 194, 195, 196, 197, 199, 200, 201, 203, 204, 205, 206, 231, 241) else '<%d bytes> %s' % (len(v), v[:24].hex()))
        print('%5d %3d %-34s %s' % (k, eid, nm.get(eid, '?'), shown))
