"""Apply routing, insert names and the mix to the open project through FL's API, then save.

Plugin knobs are set by *name and real unit* ("Gain" -> 3.0 dB, "Band 1 freq" -> 120 Hz): FL only
exposes 0..1 values, so `setv` binary-searches the knob until FL's own display string reads the
target. Targets come from docs/research.md (MBDTF mix notes).
"""
import json, sys
from fl import fl

# fader value (0.8 = 0 dB, 0.9 = +2.8, 0.7 = -2.9, 0.6 = -6.0). v5: sample-forward like v1 (the
# best-liked) with v4's cleaner low end - sample +2.8 dB, drums/bass/pads stepped back.
# v7: kick+808 bus -4 dB, hats/snare up (v6 vs Kanye median: 60-120 Hz 34.7% vs 13.5%, 1-4 kHz 2.3% vs 11%)
VOL = {1: 0.55, 2: 0.72, 3: 0.66, 4: 0.90, 5: 0.80, 6: 0.56, 7: 0.50, 8: 0.62, 9: 0.52, 10: 0.56,
       11: 0.62, 12: 0.52}  # v10: groove bus (break/perc/tamb/tribal), layers bus (spiccato/organ/bells)
CHOP_INSERTS = (4, 5)  # their Sampler channels go from the -5.2 dB default to 0 dB
PAN = {3: 0.06}

# (insert, slot, param name, target) - numbers in the knob's display unit, strings for switches
KNOBS = [
    # master: clip-style loudness without a brick wall (research: -7..-8 LUFS, ceiling -0.3 dBTP)
    (0, 3, 'Gain', 3.5), (0, 3, 'Limiter ceiling', -1.0),  # v11: v10 hit +0.2 dBTP
    # v8 master tilt toward the measured Kanye curve (v7: 60-120 Hz 29% vs 13.5%, 120-250 4.5% vs 11.8%,
    # 1-4 kHz 4.5% vs 11%)
    (0, 0, 'Band 2 type', 'Peaking'), (0, 0, 'Band 2 freq', 90.0), (0, 0, 'Band 2 level', -3.0),
    (0, 0, 'Band 3 type', 'Peaking'), (0, 0, 'Band 3 freq', 220.0), (0, 0, 'Band 3 level', 1.5),
    (0, 0, 'Band 5 type', 'Peaking'), (0, 0, 'Band 5 freq', 2500.0), (0, 0, 'Band 5 level', 2.5),
    # sample body + presence
    (4, 0, 'Band 2 type', 'Peaking'), (4, 0, 'Band 2 freq', 200.0), (4, 0, 'Band 2 level', 2.5),  # v6: crest was 8.9 dB vs 10-14 on Kanye records
    # kick bus: catch peaks only
    (1, 1, 'Gain', 2.0), (1, 1, 'Limiter ceiling', 0.0),
    # snare/clap: 4:1, 15 ms attack, 100 ms release (research drum-bus starting point)
    (2, 1, 'Gain', 3.0), (2, 1, 'Comp threshold', -14.0), (2, 1, 'Comp ratio', 4.0),
    (2, 1, 'Comp attack time', 15.0), (2, 1, 'Comp release time', 100.0),
    # sample: HPF 120 Hz under the new bass, LPF 11 kHz, -2.5 dB pocket at 3 kHz, light grit, 2:1 glue
    # v6: HPF 90 (120 steep took the sample's 120-250 Hz body: 2.5% vs 10-26% on Kanye records);
    # no vocalist on this instrumental, so +1.5 dB presence at 3 kHz instead of a vocal pocket
    (4, 0, 'Band 1 freq', 90.0), (4, 0, 'Band 7 freq', 12000.0),
    (4, 0, 'Band 4 type', 'Peaking'), (4, 0, 'Band 4 freq', 3000.0), (4, 0, 'Band 4 level', 3.0),
    # strings/choir bed out of the sub (element scan: low strings 30% <60 Hz) - the 808 owns it
    (7, 0, 'Band 1 freq', 100.0),
    (3, 0, 'Band 1 freq', 45.0),
    # v10: break high-passed so its kick doesn't fight ours (Runaway: the break sits UNDER the programmed kick)
    (11, 0, 'Band 1 freq', 150.0), (12, 0, 'Band 1 freq', 140.0),
    # v5: denser sample compression (v1's preset ran 8:1 +8.6 dB - part of why its sample felt so present)
    (4, 1, 'Pre amp', 0.3), (4, 2, 'Threshold', -18.0), (4, 2, 'Ratio', 4.0), (4, 2, 'Gain', 6.0),
    (4, 2, 'Attack', 20.0), (4, 2, 'Release', 150.0),
    # bass: soft clip for harmonics that read on small speakers
    (6, 0, 'Threshold', -2.0),
    # brass + Dean lead: grit, not fuzz
    (9, 0, 'Pre amp', 0.3), (10, 0, 'Pre amp', 0.4),
]

HELPERS = r'''
import re
def _num(s):
    s = s.replace(',', '')
    if 'INF' in s.upper():
        return -1e9 if '-' in s else 1e9
    m = re.search(r'-?\d+(\.\d+)?', s)
    return float(m.group()) if m else None

def _pidx(t, s, name):
    for i in range(plugins.getParamCount(t, s)):
        if plugins.getParamName(i, t, s) == name:
            return i
    raise KeyError('%s not on %d.%d %s' % (name, t, s, plugins.getPluginName(t, s)))

def setv(t, s, name, target):
    """Set a mixer-plugin knob to a display value (number in its unit, or an option string)."""
    i = _pidx(t, s, name)
    rd = lambda v: (plugins.setParamValue(v, i, t, s), plugins.getParamValueString(i, t, s))[1]
    if isinstance(target, str):
        for k in range(201):
            if rd(k / 200).strip().lower() == target.lower():
                return target
        raise ValueError('%s: option %r not found' % (name, target))
    lo, hi = 0.0, 1.0
    up = (_num(rd(1.0)) or 0) >= (_num(rd(0.0)) or 0)
    for _ in range(40):
        mid = (lo + hi) / 2
        v = _num(rd(mid))
        if (v < target) == up:
            lo = mid
        else:
            hi = mid
    return rd((lo + hi) / 2)
'''


def apply(mixfile, knobs=KNOBS, save=True):
    m = json.load(open(mixfile))
    fl(HELPERS)
    code = ['r = %r' % {int(k): v for k, v in m['route'].items()},
            'nm = %r' % {int(k): v for k, v in m['names'].items()},
            'for ins, chans in r.items():',
            '    mixer.setTrackName(ins, nm[ins])',
            '    for ch in chans: channels.setTargetFxTrack(ch, ins)',
            'for ins, v in %r.items(): mixer.setTrackVolume(ins, v)' % VOL,
            'for ins, v in %r.items(): mixer.setTrackPan(ins, v)' % PAN,
            'for ins in %r:' % (CHOP_INSERTS,),
            '    for ch in r.get(ins, []): channels.setChannelVolume(ch, 1.0)']
    fl('\n'.join(code))
    report = []
    for t, s, name, target in knobs:
        got = fl('setv(%d, %d, %r, %r)' % (t, s, name, target), timeout=90)
        report.append('%d.%d %-20s -> %s' % (t, s, name, got))
    if save:  # FL's command-line render uses the saved mode: always save in Song mode
        fl('import midi\ntransport.stop()\nif transport.getLoopMode() == 0: transport.setLoopMode()\n'
           'transport.globalTransport(midi.FPT_Save, 1)')
    return report


if __name__ == '__main__':
    print('\n'.join(apply(sys.argv[1])))
