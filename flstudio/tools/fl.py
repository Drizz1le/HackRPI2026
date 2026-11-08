"""Command-line control of a running FL Studio via the AI Bridge device script.

  python fl.py install                 copy the device script into FL's Hardware folder
  python fl.py "<python>"              run code inside FL (all FL API modules in scope)
  python fl.py api                     list every FL API function with its docstring
  python fl.py params CH [SLOT]        list all params of a plugin (SLOT given = mixer track CH, effect SLOT)
  python fl.py set CH PARAM VALUE [SLOT]   set a plugin param (0..1)
  python fl.py chop FILE OUTDIR [N] [START] [LEN]   slice audio at the N strongest onsets
  python fl.py load FILE...            load audio files into FL as new Sampler channels
  python fl.py analyze FILE [PNG]      tempo/key/loudness (+ spectrogram image)
  python fl.py listen SECONDS [OUT]    play the project, record FL's output, analyze it
"""
import base64, ctypes, json, os, sys, time, uuid
from ctypes import wintypes as wt

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.join(os.path.expanduser('~'), 'Documents', 'Image-Line', 'FL Studio', 'Settings', 'Hardware', 'AI Bridge')


TOKEN_FILE = os.path.join(os.path.expanduser('~'), '.fl_ai_bridge_token')
TO_FL = os.environ.get('FL_TO_PORT', 'loopMIDI Port')        # FL input with the AI Bridge script
# FL's script output (same port number) also lands on this loopback port; flags tell requests from replies
FROM_FL = os.environ.get('FL_FROM_PORT', 'loopMIDI Port')
HDR = b'\xF0\x7D\x41'
CHUNK = 200

# --- raw winmm SysEx I/O (no python-rtmidi wheel for this Python) ---
w = ctypes.windll.winmm


class MIDIHDR(ctypes.Structure):
    _fields_ = [('lpData', ctypes.c_void_p), ('dwBufferLength', wt.DWORD), ('dwBytesRecorded', wt.DWORD),
                ('dwUser', ctypes.c_size_t), ('dwFlags', wt.DWORD), ('lpNext', ctypes.c_void_p),
                ('reserved', ctypes.c_size_t), ('dwOffset', wt.DWORD), ('dwReserved', ctypes.c_size_t * 8)]


class CAPS(ctypes.Structure):
    _fields_ = [('wMid', wt.WORD), ('wPid', wt.WORD), ('v', wt.DWORD), ('name', wt.WCHAR * 32), ('sup', wt.DWORD)]


class OCAPS(ctypes.Structure):
    _fields_ = [('wMid', wt.WORD), ('wPid', wt.WORD), ('v', wt.DWORD), ('name', wt.WCHAR * 32),
                ('tech', wt.WORD), ('voices', wt.WORD), ('notes', wt.WORD), ('mask', wt.WORD), ('sup', wt.DWORD)]


def _dev(name, out):
    n, caps, get = (w.midiOutGetNumDevs(), OCAPS(), w.midiOutGetDevCapsW) if out else \
                   (w.midiInGetNumDevs(), CAPS(), w.midiInGetDevCapsW)
    for i in range(n):
        get(i, ctypes.byref(caps), ctypes.sizeof(caps))
        if caps.name == name:
            return i
    raise RuntimeError('MIDI port %r not found - is loopMIDI running?' % name)


def _ck(rc, what):
    if rc:
        raise RuntimeError('%s failed (MMRESULT %d)' % (what, rc))


class Link:
    """Open both ports; send() requests to FL, recv() reassembled replies."""

    def __init__(self, nbuf=1024, size=512):  # big replies arrive as bursts of chunks: keep plenty queued
        self.hin, self.hout = wt.HANDLE(), wt.HANDLE()
        _ck(w.midiInOpen(ctypes.byref(self.hin), _dev(FROM_FL, False), None, None, 0), 'midiInOpen')
        _ck(w.midiOutOpen(ctypes.byref(self.hout), _dev(TO_FL, True), None, None, 0), 'midiOutOpen')
        self.bufs = [ctypes.create_string_buffer(size) for _ in range(nbuf)]
        self.hdrs = [MIDIHDR(ctypes.cast(b, ctypes.c_void_p), size) for b in self.bufs]
        for h in self.hdrs:
            _ck(w.midiInPrepareHeader(self.hin, ctypes.byref(h), ctypes.sizeof(h)), 'midiInPrepareHeader')
            _ck(w.midiInAddBuffer(self.hin, ctypes.byref(h), ctypes.sizeof(h)), 'midiInAddBuffer')
        self.next = 0
        _ck(w.midiInStart(self.hin), 'midiInStart')

    def close(self):
        w.midiInReset(self.hin)
        for h in self.hdrs:
            w.midiInUnprepareHeader(self.hin, ctypes.byref(h), ctypes.sizeof(h))
        w.midiInClose(self.hin)
        w.midiOutClose(self.hout)

    def _sysex(self, data):
        buf = ctypes.create_string_buffer(data, len(data))
        h = MIDIHDR(ctypes.cast(buf, ctypes.c_void_p), len(data))
        _ck(w.midiOutPrepareHeader(self.hout, ctypes.byref(h), ctypes.sizeof(h)), 'midiOutPrepareHeader')
        _ck(w.midiOutLongMsg(self.hout, ctypes.byref(h), ctypes.sizeof(h)), 'midiOutLongMsg')
        while not h.dwFlags & 1:  # MHDR_DONE
            time.sleep(0.001)
        w.midiOutUnprepareHeader(self.hout, ctypes.byref(h), ctypes.sizeof(h))

    def send(self, obj):
        b = base64.b64encode(json.dumps(obj).encode())
        n = max(1, -(-len(b) // CHUNK))
        assert n < 128, 'request too large'
        rid = obj['id'].encode()  # chunk = HDR, last-flag, request id, chunk index, data
        for i in range(n):
            self._sysex(HDR + bytes([1 if i == n - 1 else 0]) + rid + bytes([i]) + b[i * CHUNK:(i + 1) * CHUNK] + b'\xF7')

    def recv(self, rid, timeout):
        parts, total, msg, end = {}, None, b'', time.time() + timeout
        tag = rid.encode()
        while time.time() < end:
            h = self.hdrs[self.next]
            if not h.dwFlags & 1:
                time.sleep(0.0005)
                continue
            msg += self.bufs[self.next].raw[:h.dwBytesRecorded]  # a long SysEx may span buffers
            h.dwFlags &= ~1
            _ck(w.midiInAddBuffer(self.hin, ctypes.byref(h), ctypes.sizeof(h)), 'midiInAddBuffer')
            self.next = (self.next + 1) % len(self.hdrs)
            if not msg.endswith(b'\xF7'):
                continue
            m, msg = msg, b''
            # 2/3 = reply chunks (0/1 are requests); bytes 4..11 = request id, so stray replies are skipped
            if not m.startswith(HDR) or m[3] not in (2, 3) or m[4:12] != tag:
                continue
            idx = m[12] | (m[13] << 7)  # chunks indexed: a re-sent reply may interleave with the first
            parts[idx] = m[14:-1]
            if m[3] == 3:
                total = idx + 1
            if total and all(i in parts for i in range(total)):
                return json.loads(base64.b64decode(b''.join(parts[i] for i in range(total))))
        raise TimeoutError('no reply from FL in %ss - is the AI Bridge script loaded?' % timeout)


def fl(code, timeout=60):
    with open(TOKEN_FILE) as f:
        token = f.read().strip()
    rid = uuid.uuid4().hex[:8]
    link = Link()
    try:
        req = {'id': rid, 'token': token, 'code': code}
        end = time.time() + timeout
        wait = 1.5
        while True:  # resend on silence: the script dedupes and replays its cached reply (exactly-once)
            link.send(req)
            try:
                r = link.recv(rid, min(wait, max(0.1, end - time.time())))
                break
            except TimeoutError:
                if time.time() >= end:
                    raise
                wait = min(wait * 1.5, 6)
    finally:
        link.close()
    if r['out']:
        print(r['out'], end='')
    if not r['ok']:
        raise RuntimeError(r['error'])
    return r['result']


API = r'''
result = {}
for n in MODS:
    m = globals().get(n)
    if m is not None:
        result[n] = {f: (getattr(m, f).__doc__ or '').strip() for f in dir(m)
                     if not f.startswith('_') and callable(getattr(m, f))}
'''

# slot -1 means a channel-rack generator, otherwise mixer track index + effect slot
PARAMS = r'''
idx, slot = %d, %d
result = [(i, plugins.getParamName(i, idx, slot), plugins.getParamValue(i, idx, slot), plugins.getParamValueString(i, idx, slot))
 for i in range(plugins.getParamCount(idx, slot)) if plugins.getParamName(i, idx, slot)]
'''


def analyze(path_or_audio, sr=None, png=None):
    """Return tempo/key/loudness/brightness and optionally save a spectrogram the AI can look at."""
    import numpy as np, librosa
    y, sr = (librosa.load(path_or_audio, sr=22050, mono=True) if isinstance(path_or_audio, str)
             else (librosa.to_mono(path_or_audio.T) if path_or_audio.ndim > 1 else path_or_audio, sr))
    if sr != 22050:
        y, sr = librosa.resample(y, orig_sr=sr, target_sr=22050), 22050
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)
    names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    # Krumhansl key profiles
    maj = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    mnr = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    scores = [(np.corrcoef(chroma, np.roll(p, k))[0, 1], names[k] + q) for p, q in ((maj, ' major'), (mnr, ' minor')) for k in range(12)]
    rms = librosa.feature.rms(y=y)[0]
    info = {'seconds': round(len(y) / sr, 2), 'tempo_bpm': round(float(np.atleast_1d(tempo)[0]), 1),
            'key': max(scores)[1], 'peak_dbfs': round(float(20 * np.log10(np.abs(y).max() + 1e-9)), 1),
            'rms_dbfs': round(float(20 * np.log10(np.sqrt((y ** 2).mean()) + 1e-9)), 1),
            'loudness_range_db': round(float(np.percentile(20 * np.log10(rms + 1e-9), 95) - np.percentile(20 * np.log10(rms + 1e-9), 10)), 1),
            'brightness_hz': round(float(librosa.feature.spectral_centroid(y=y, sr=sr).mean())),
            'silent': bool(np.abs(y).max() < 1e-4)}
    if png:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt, librosa.display
        fig, ax = plt.subplots(2, 1, figsize=(12, 6), height_ratios=[1, 3])
        librosa.display.waveshow(y, sr=sr, ax=ax[0])
        S = librosa.amplitude_to_db(np.abs(librosa.stft(y)), ref=np.max)
        librosa.display.specshow(S, sr=sr, x_axis='time', y_axis='log', ax=ax[1])
        ax[0].set_title('%s  |  %s bpm  |  %s' % (os.path.basename(png), info['tempo_bpm'], info['key']))
        fig.tight_layout()
        fig.savefig(png, dpi=80)
        plt.close(fig)
        info['spectrogram'] = png
    return info


def chop(path, outdir, n=16, start=0.0, length=None):
    """Slice at the strongest onsets (snapped back to the preceding quiet point); writes WAVs."""
    import numpy as np, librosa, soundfile as sf
    y, sr = librosa.load(path, sr=44100, mono=False, offset=start, duration=length)
    y = np.atleast_2d(y)
    mono = librosa.to_mono(y)
    env = librosa.onset.onset_strength(y=mono, sr=sr)
    on = librosa.onset.onset_detect(onset_envelope=env, sr=sr, backtrack=True, units='frames')
    strongest = sorted(on, key=lambda f: -env[min(f + 2, len(env) - 1)])[:n - 1]
    cuts = sorted(set([0] + list(librosa.frames_to_samples(strongest)) + [y.shape[1]]))
    cuts = [c for i, c in enumerate(cuts) if i == 0 or c - cuts[i - 1] > 0.08 * sr]  # drop <80ms slivers
    if cuts[-1] != y.shape[1]:
        cuts.append(y.shape[1])
    os.makedirs(outdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(path))[0][:40].strip()
    out = []
    for i in range(len(cuts) - 1):
        seg = y[:, cuts[i]:cuts[i + 1]].T.copy()
        fade = min(len(seg), int(0.004 * sr))  # 4ms fade-out, no clicks
        seg[-fade:] *= np.linspace(1, 0, fade)[:, None]
        f = os.path.join(outdir, '%s_slice%02d.wav' % (base, i + 1))
        sf.write(f, seg, sr)
        out.append((f, round(start + cuts[i] / sr, 3), round((cuts[i + 1] - cuts[i]) / sr, 3)))
    return out


# Empty strip at the bottom of the Channel Rack (next to "+"): a drop there appends channels.
# shortcut: screen position of the rack as it sits now, override with FL_DROP_XY="x,y" if the rack moves
DROP_XY = tuple(int(v) for v in os.environ.get('FL_DROP_XY', '1000,1012').split(','))


def load(files):
    """Load audio files into FL as new Sampler channels (drag-and-drop from Explorer; FL's API has no loader)."""
    import drop
    fl('ui.showWindow(1)')  # make sure the Channel Rack is open
    before = fl('channels.channelCount(1)')
    drop.drop(files, *DROP_XY)
    for _ in range(30):  # FL is busy while it loads; wait for all channels to appear
        try:
            n = fl('channels.channelCount(1)', timeout=5)
        except TimeoutError:
            continue
        if n >= before + len(files):
            break
        time.sleep(0.5)
    return before, fl('[(i, channels.getChannelName(i, 1)) for i in range(channels.channelCount(1))]')


FL_EXE = r'C:\Program Files\Image-Line\FL Studio 2025\FL64.exe'


def open_project(path, save_current=False):
    """Switch FL to another project without touching the GUI: close FL, relaunch on `path`.
    Not saving by default: if FL has an older copy of `path` open, saving would overwrite a fresh
    build (that silently turned "v10" into v9). Pass save_current=True (`open --save`) explicitly."""
    import subprocess
    if save_current:
        try:
            fl('import midi; transport.globalTransport(midi.FPT_Save, 1)', timeout=15)
            time.sleep(1.5)
        except (TimeoutError, OSError):
            pass
    subprocess.run(['powershell', '-NoProfile', '-Command',
                    '$p = Get-Process FL64 -ErrorAction SilentlyContinue; if ($p) { $p.CloseMainWindow() | Out-Null; $p.WaitForExit(20000) | Out-Null }; '
                    'if (Get-Process FL64 -ErrorAction SilentlyContinue) { exit 1 }'], check=True)
    subprocess.Popen([FL_EXE, os.path.abspath(path)])
    for _ in range(90):  # wait until the bridge script is up in the new instance
        time.sleep(1)
        try:
            return fl('ui.getProgTitle(), general.getProjectTitle(), channels.channelCount(1)', timeout=3)
        except (TimeoutError, OSError, RuntimeError):
            pass
    raise TimeoutError('FL did not come back with the bridge')


METER = r'''
import midi, time
transport.stop()
if transport.getLoopMode() == 0: transport.setLoopMode()
transport.setSongPos(%d * 4 * general.getRecPPQ(), midi.SONGLENGTH_ABSTICKS)
'''


def meters(seconds, bar=0, tracks=11):
    """Per-insert levels while the song plays from `bar`: FL's own meters, polled ~20x/s.
    Returns {insert: (name, peak dBFS, mean dBFS)} - lets the AI balance a mix by numbers."""
    import math
    fl(METER % bar)
    fl('transport.start()')
    acc = {t: [] for t in range(tracks)}
    end = time.time() + seconds
    while time.time() < end:
        try:  # FL can be slow to answer while it streams audio; a missed poll is fine
            vals = fl('[max(mixer.getTrackPeaks(t, 0), mixer.getTrackPeaks(t, 1)) for t in range(%d)]' % tracks, timeout=3)
        except TimeoutError:
            continue
        for t, v in enumerate(vals):
            acc[t].append(v)
        time.sleep(0.05)
    fl('transport.stop()')
    db = lambda x: round(20 * math.log10(max(x, 1e-6)), 1)
    names = fl('[mixer.getTrackName(t) for t in range(%d)]' % tracks)
    return {t: (names[t], db(max(v)), db(sum(v) / len(v))) for t, v in acc.items() if v}


def listen(seconds, out='listen.wav', bar=0):
    """Play the song from `bar` (song mode), record what FL outputs (system loopback), analyze it."""
    import numpy as np, soundcard as sc, soundfile as sf
    spk = sc.default_speaker()
    mic = sc.get_microphone(spk.id, include_loopback=True)
    sr = 44100
    fl('import midi\ntransport.stop()\nif transport.getLoopMode() == 0: transport.setLoopMode()\n'
       'transport.setSongPos(%d * 4 * general.getRecPPQ(), midi.SONGLENGTH_ABSTICKS)' % bar)
    with mic.recorder(samplerate=sr, channels=2) as rec:
        fl('transport.start()')
        audio = rec.record(numframes=int(seconds * sr))
    fl('transport.stop()')
    sf.write(out, audio, sr)
    return analyze(audio, sr, png=os.path.splitext(out)[0] + '.png')


def main(a):
    if not a:
        print(__doc__)
    elif a[0] == 'install':
        import secrets
        try:  # keep an existing token so a reinstall doesn't lock out a running script
            with open(TOKEN_FILE) as f:
                token = f.read().strip() or secrets.token_hex(16)
        except FileNotFoundError:
            token = secrets.token_hex(16)
        os.makedirs(HW, exist_ok=True)
        with open(os.path.join(HERE, 'device_AIBridge.py')) as f:
            src = f.read().replace("'__TOKEN__'", repr(token), 1)
        with open(os.path.join(HW, 'device_AIBridge.py'), 'w') as f:
            f.write(src)
        with open(TOKEN_FILE, 'w') as f:
            f.write(token)
        print('installed to', HW, '- reload the script in FL (View > Script output > Reload script)')
    elif a[0] == 'api':
        for mod, fns in fl(API).items():
            print('== ' + mod)
            for f, doc in fns.items():
                print('  %s.%s  %s' % (mod, f, doc.splitlines()[0] if doc else ''))
    elif a[0] == 'params':
        for i, name, val, s in fl(PARAMS % (int(a[1]), int(a[2]) if len(a) > 2 else -1)):
            print('%5d  %-40s %.4f  %s' % (i, name, val, s))
    elif a[0] == 'chop':  # chop FILE OUTDIR [N] [START_SEC] [LENGTH_SEC]
        args = [a[1], a[2]] + [int(a[3])] * (len(a) > 3) + [float(x) for x in a[4:6]]
        for f, t, d in chop(*args):
            print('%7.3fs  %6.3fs  %s' % (t, d, f))
    elif a[0] == 'load':
        before, chans = load(a[1:])
        print('channels before: %d' % before)
        for i, name in chans:
            print('%3d  %s' % (i, name))
    elif a[0] == 'analyze':  # analyze FILE [PNG]
        print(json.dumps(analyze(a[1], png=a[2] if len(a) > 2 else None), indent=1))
    elif a[0] == 'meters':  # meters SECONDS [START_BAR]
        for t, (name, pk, avg) in meters(float(a[1]), int(a[2]) if len(a) > 2 else 0).items():
            print('%2d %-14s peak %6.1f dB   avg %6.1f dB' % (t, name, pk, avg))
    elif a[0] == 'open':  # open PROJECT.flp (saves the current one first)
        print(open_project(a[1], save_current='--save' in a))
    elif a[0] == 'listen':  # listen SECONDS [OUT.wav] [START_BAR]
        print(json.dumps(listen(float(a[1]), a[2] if len(a) > 2 else 'listen.wav', int(a[3]) if len(a) > 3 else 0), indent=1))
    elif a[0] == 'set':
        slot = int(a[4]) if len(a) > 4 else -1
        fl('plugins.setParamValue(%r, %d, %d, %d)' % (float(a[3]), int(a[2]), int(a[1]), slot))
    else:
        r = fl(' '.join(a))
        if r is not None:
            print(json.dumps(r, indent=1))


if __name__ == '__main__':
    main(sys.argv[1:])
