"""Build an FL Studio project in code: sampler channels, plugin channels from .fst presets,
patterns with notes, playlist clips and mixer-slot effects. Opened by FL like any saved project.

Layout facts (from dumping FL-saved projects/presets with flp.py):
  * channel block starts at event 64 (ChannelID.New); Sampler = Type 0, plugin generator = Type 2
  * .fst preset = [201 internal name, 212 wrapper, 213 plugin state] -> copied into a channel/slot
  * pattern = 65 (New) [+193 name] + 224 notes, 24 bytes per note
  * playlist = 233, 80 bytes per item; pattern clip index = 0x5000 + pattern, track stored as 499 - track
  * mixer insert = 236 flags then 10x 98 (slot index); a slot's plugin events precede its 98 event
"""
import copy, struct
import flp

FL = r'C:\Program Files\Image-Line\FL Studio 2025'
TEMPLATE = FL + r'\Data\Templates\Minimal\Empty\Empty.flp'
PRESETS = FL + r'\Data\Patches\Plugin presets'
PPQ = 96
BAR = PPQ * 4

# pattern clip tail copied from a real FL 25 playlist item (bytes 32..79; byte 32.. = clip id)
_ITEM_TAIL = bytes.fromhex('0e000000000000000000000000000000000000000000803f'
                           '0000000000000000000000000000f03f0000000000000000')


def _utf16(s):
    return (s + '\0').encode('utf-16-le')


def _preset_name(raw):
    """Preset internal names may be ASCII (old presets) or UTF-16 (new); FL 25 projects use UTF-16."""
    if len(raw) > 1 and raw[1] == 0:
        return raw
    return _utf16(raw.rstrip(b'\0').decode('latin-1'))


def read_fst(path):
    ev = {e: v for e, v in flp.read(path)['events'] if e in (201, 212, 213)}
    assert 201 in ev and 213 in ev, 'not a plugin preset: ' + path
    return [_preset_name(ev[201]), ev.get(212), ev[213]]


class Project:
    def __init__(self, tempo=84.0, template=TEMPLATE):
        self.p = flp.read(template)
        ev = self.p['events']
        first = next(i for i, (e, _) in enumerate(ev) if e == 64)
        end = next(i for i, (e, _) in enumerate(ev) if e == 99)  # arrangement starts after channels
        self.chan_tpl = copy.deepcopy(ev[first:end])  # the template's Sampler channel
        self.head, self.tail = ev[:first], ev[end:]
        self.channels, self.patterns, self.items, self.fx = [], [], [], []
        for e in self.head:
            if e[0] == 156:
                e[1] = struct.pack('<I', int(round(tempo * 1000)))
            elif e[0] == 9:  # Song mode (PyFLP calls it LoopActive): CLI renders use the saved mode
                e[1] = b'\x01'

    # ---- channels -------------------------------------------------------------
    def _channel(self, name, plugin=None, sample=None):
        idx = len(self.channels)
        out = []
        for eid, val in copy.deepcopy(self.chan_tpl):
            if eid == 64:
                val = struct.pack('<H', idx)
            elif eid == 21 and plugin:
                val = b'\x02'
            elif eid == 201 and plugin:
                val = plugin[0]
            elif eid == 212 and plugin and plugin[1]:
                w = bytearray(plugin[1])  # flag 0x1 = editor window open (presets carry it): open closed
                struct.pack_into('<I', w, 16, struct.unpack_from('<I', w, 16)[0] & ~0x201)
                val = bytes(w)
            elif eid == 203:
                val = _utf16(name)
            out.append([eid, val])
            if eid == 41 and plugin:  # plugin state goes right after this flag, as FL saves it
                out.append([213, plugin[2]])
            if eid == 20 and sample:  # sample path follows PingPongLoop in FL-saved sampler channels
                out.append([196, _utf16(sample)])
        self.channels.append(out)
        return idx

    def sampler(self, name, wav):
        return self._channel(name, sample=wav)

    def plugin(self, name, fst):
        return self._channel(name, plugin=read_fst(fst))

    # ---- patterns & playlist ---------------------------------------------------
    def pattern(self, name, notes):
        """notes: (channel, start_tick, length_tick, key, velocity 0-127[, pan 0-127, fine 0-240]).
        Key 60 = C5, the Sampler's default root (plays the sample unpitched)."""
        data = bytearray()
        for n in sorted(notes, key=lambda n: (n[1], n[0])):
            ch, pos, ln, key, vel = n[:5]
            pan = n[5] if len(n) > 5 else 64
            fine = n[6] if len(n) > 6 else 120
            data += struct.pack('<IHHIHHBBBBBBBB', int(pos), 0x4000, ch, max(1, int(ln)), key, 0,
                                fine, 0, 64, 0, pan, max(0, min(127, int(vel))), 128, 128)
        self.patterns.append((name, bytes(data)))
        return len(self.patterns)  # FL patterns are 1-based

    def clip(self, pattern, bar, track, bars):
        """Place a pattern on playlist track (0-based) at bar (0-based) for `bars` bars."""
        pos, ln = int(bar * BAR), int(bars * BAR)
        it = struct.pack('<IHHIHH', pos, 0x5000, 0x5000 + pattern, ln, 499 - track, 0)
        it += bytes.fromhex('7800408040648080') + struct.pack('<II', 0, ln)
        tail = bytearray(_ITEM_TAIL)
        struct.pack_into('<I', tail, 0, len(self.items))
        self.items.append(it + bytes(tail))

    # ---- mixer -----------------------------------------------------------------
    def effect(self, insert, slot, fst):
        self.fx.append((insert, slot, read_fst(fst)))

    # ---- output ----------------------------------------------------------------
    def save(self, path):
        ev = [list(e) for e in self.head]
        at = next(i for i, (e, _) in enumerate(ev) if e == 226)  # patterns sit before controllers
        pats = []
        for i, (name, data) in enumerate(self.patterns, 1):
            pats += [[65, struct.pack('<H', i)], [193, _utf16(name)], [224, data]]
        ev[at:at] = pats
        for e in ev:
            if e[0] == 67:  # currently selected pattern
                e[1] = struct.pack('<H', 1)
        for ch in self.channels:
            ev += ch
        tail = [list(e) for e in self.tail]
        for e in tail:
            if e[0] == 233:
                e[1] = b''.join(self.items)
        # effects: walk inserts (each starts with event 236) and slot markers (98)
        for insert, slot, (name, wrapper, state) in self.fx:
            n_ins = -1  # first 236 event = master insert (its flags differ: 0x0c, no routing event)
            for i, (eid, val) in enumerate(tail):
                if eid == 236:
                    n_ins += 1
                elif eid == 98 and n_ins == insert and flp.u(val) == slot:
                    # FL places a mixer plugin by its wrapper: dword0 = insert, dword1 = slot (verified by
                    # probing); presets carry other values there, and a mismatch can hang FL while loading.
                    w = bytearray(wrapper or bytes(52))
                    struct.pack_into('<II', w, 0, insert, slot)
                    struct.pack_into('<I', w, 16, struct.unpack_from('<I', w, 16)[0] & ~0x201)
                    block = [[201, name], [212, bytes(w)], [203, name], [155, b'\0\0\0\0'],
                             [128, struct.pack('<I', 5656904)], [41, b'\0'], [213, state]]
                    tail[i:i] = block
                    break
            else:
                raise ValueError('mixer insert %d slot %d not found' % (insert, slot))
        ev += tail
        self.p['events'] = ev
        self.p['channels'] = len(self.channels)
        flp.write(path, self.p)
        return path


def preset(kind, rel):
    """Path of a factory preset, e.g. preset('Generators', r'FL Keys\\Concert Piano.fst').
    Presets are often nested in sub-folders, so fall back to searching the plugin's folder by file name."""
    import os, glob
    p = '%s\\%s\\%s' % (PRESETS, kind, rel)
    if os.path.exists(p):
        return p
    plugin, name = rel.split('\\', 1)[0], os.path.basename(rel)
    hits = glob.glob('%s\\%s\\%s\\**\\%s' % (PRESETS, kind, plugin, glob.escape(name)), recursive=True)
    if not hits:
        raise FileNotFoundError(p)
    return hits[0]


if __name__ == '__main__':
    # self-check: build a tiny project and parse it back
    import os, tempfile
    pr = Project(tempo=90)
    a = pr.sampler('chop', r'C:\Windows\Media\chord.wav')
    k = pr.plugin('keys', preset('Generators', r'FL Keys\Concert Piano.fst'))
    p1 = pr.pattern('A', [(a, 0, 96, 60, 100), (k, 0, 384, 67, 90)])
    pr.clip(p1, 0, 0, 1)
    pr.effect(1, 0, preset('Effects', r'Fruity Limiter\Default.fst') if os.path.exists(preset('Effects', r'Fruity Limiter\Default.fst')) else
              next(os.path.join(dp, f) for dp, _, fs in os.walk(preset('Effects', 'Fruity Limiter')) for f in fs))
    out = pr.save(os.path.join(tempfile.gettempdir(), 'flpbuild_selftest.flp'))
    back = flp.read(out)
    ids = [e for e, _ in back['events']]
    assert back['channels'] == 2 and ids.count(64) == 2 and ids.count(224) == 1, 'roundtrip failed'
    assert len([v for e, v in back['events'] if e == 233][0]) == 80
    print('self-check ok:', out)
