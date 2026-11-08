# name=AI Bridge
# Lets an external CLI run Python inside FL with every FL API module in scope.
# FL's script sandbox blocks files, sockets and ctypes, so the transport is MIDI SysEx:
#   request  (CLI -> FL, on this script's input port):  F0 7D 41 <last> <base64 chunk> F7
#   reply    (FL -> CLI, via device.midiOutSysex on the output port with the same port number)
# Payload = base64(JSON). Request JSON: {"id", "token", "code"}. Reply: {"id", "ok", "result"|"error", "out"}.
import sys, traceback, json, io, hmac, binascii
import device

log = print  # shows in View > Script output

MODS = ['channels', 'mixer', 'plugins', 'transport', 'patterns', 'playlist', 'arrangement',
        'ui', 'general', 'device', 'midi', 'utils', 'launchMapPages', 'screen']
NS = {'MODS': MODS}
for _m in MODS:
    try:
        NS[_m] = __import__(_m)
    except ImportError:
        pass

# Replaced by `fl.py install` with a random token (also saved to ~/.fl_ai_bridge_token), so only
# something that can read the user's files can drive FL through this port.
TOKEN = '__TOKEN__'
HDR = b'\xF0\x7D\x41'  # 0x7D = non-commercial SysEx ID, 0x41 = bridge tag
CHUNK = 200            # loopMIDI default SysEx buffer is 256 bytes
_buf = []
DEBUG = False


def OnInit():
    if TOKEN == '__TOKEN__':
        log('AI Bridge: not installed with a token, run `python fl.py install`')
    else:
        log('AI Bridge ready (SysEx), output port %d' % device.getPortNumber())


def _jsonable(v):
    try:
        json.dumps(v)
        return v
    except (TypeError, ValueError):
        return repr(v)


def run(code):
    out = io.StringIO()
    old = sys.stdout
    sys.stdout = out
    try:
        try:
            res = eval(compile(code, '<ai>', 'eval'), NS)
        except SyntaxError:  # statements: the value of `result` (if set) is returned
            NS.pop('result', None)
            exec(compile(code, '<ai>', 'exec'), NS)
            res = NS.pop('result', None)
        return {'ok': True, 'result': _jsonable(res), 'out': out.getvalue()}
    except Exception:
        return {'ok': False, 'error': traceback.format_exc(), 'out': out.getvalue()}
    finally:
        sys.stdout = old


def send(obj):
    b = binascii.b2a_base64(json.dumps(obj).encode(), newline=False)
    rid = str(obj.get('id') or '00000000')[:8].ljust(8, '0').encode()  # every chunk tagged with its request id
    n = max(1, -(-len(b) // CHUNK))
    for i in range(n):
        # reply flags: 2 = more, 3 = last (distinct from request flags 0/1 so echoes are ignored)
        device.midiOutSysex(HDR + bytes([3 if i == n - 1 else 2]) + rid + bytes([i & 0x7F, i >> 7])
                            + b[i * CHUNK:(i + 1) * CHUNK] + b'\xF7')


def OnMidiIn(event):
    # Handle here (first callback) and mark handled so FL never echoes it back out to a loopback port.
    if event.status == 0xF0 and event.sysex and bytes(event.sysex).startswith(HDR):
        OnSysEx(event)


def OnSysEx(event):
    try:
        _on_sysex(event)
    except Exception:
        event.handled = True
        log('AI Bridge error:\n' + traceback.format_exc())


_parts = {}  # request id -> {chunk index: data, 'n': count}; FL may deliver a SysEx twice (OnMidiIn+OnSysEx)
_done = {}   # request id -> reply, so a client retry gets the same answer (MIDI drops some SysEx while FL
             # is playing; retries must not execute code twice)


def _on_sysex(event):
    d = bytes(event.sysex)
    if DEBUG:
        log('OnSysEx %d bytes: %r' % (len(d), d[:12]))
    if not d.startswith(HDR):
        return
    event.handled = True
    if d[3] in (2, 3):  # our own reply echoed back by a loopback port: ignore
        return
    # request chunk: HDR, flag (0 more / 1 last), 8-byte request id, chunk index, data
    rid, idx, data = d[4:12], d[12], d[13:-1]
    if rid in _done:  # duplicate delivery or client retry: never run twice, re-send the reply
        if d[3] == 1:
            send(_done[rid])
        return
    if rid not in _parts and len(_parts) > 32:  # abandoned partial requests: drop the oldest
        del _parts[next(iter(_parts))]
    parts = _parts.setdefault(rid, {})
    parts[idx] = data
    if d[3] == 1:
        parts['n'] = idx + 1
    if parts.get('n') is None or len(parts) - 1 < parts['n']:
        return  # wait for the rest (chunks may arrive twice or out of order)
    payload = b''.join(parts[i] for i in range(parts['n']))
    del _parts[rid]
    try:
        req = json.loads(binascii.a2b_base64(payload))
        ok = TOKEN != '__TOKEN__' and hmac.compare_digest(str(req.get('token', '')), TOKEN)
    except Exception:
        return
    if not ok:
        send({'id': req.get('id'), 'ok': False, 'error': 'bad token: rerun `python fl.py install`', 'out': ''})
        return
    reply = run(req.get('code', ''))
    reply['id'] = req.get('id')
    _done[rid] = reply
    for k in list(_done)[:-32]:
        del _done[k]
    send(reply)
    if DEBUG:
        log('replied %r' % reply)
