"""Open a tiny generated project with one effect and report whether FL loads it (bridge answers) or hangs.
usage: python tools/fxprobe.py "Fruity Blood Overdrive\\Drive.fst" [insert] [slot] [nodata]"""
import os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import flpbuild
from fl import fl, FL_EXE

rel = sys.argv[1]
ins = int(sys.argv[2]) if len(sys.argv) > 2 else 1
slot = int(sys.argv[3]) if len(sys.argv) > 3 else 0
pr = flpbuild.Project(tempo=82)
pr.sampler('s', r'C:\Windows\Media\chord.wav')
pr.effect(ins, slot, flpbuild.preset('Effects', rel))
if 'nodata' in sys.argv:
    pr.fx[-1][2][2] = b''
out = pr.save(os.path.abspath('out/_fxprobe.flp'))
subprocess.run(['taskkill', '/F', '/IM', 'FL64.exe'], capture_output=True)
time.sleep(1)
subprocess.Popen([FL_EXE, out])
for i in range(25):
    time.sleep(2)
    try:
        r = fl('[(t, s, plugins.getPluginName(t, s)) for t in range(5) for s in range(10) if mixer.isTrackPluginValid(t, s)]', timeout=2)
        print('OK after %ds:' % (i * 2), r)
        break
    except Exception:
        pass
else:
    print('HANG')
subprocess.run(['taskkill', '/F', '/IM', 'FL64.exe'], capture_output=True)
