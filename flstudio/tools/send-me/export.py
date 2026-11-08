"""Export a version: exports/vN/<name> vN.{flp,wav,mp3,png,json}, rendered by FL's command line.

usage: python tools/export.py N ["notes about this version"]
Requires the project to be saved in FL first (mix.py saves). FL is closed for the render (the CLI
renderer only runs when no FL instance is open) and reopened on the project afterwards.
"""
import glob, json, os, re, shutil, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from fl import FL_EXE, analyze

SRC = os.path.join(ROOT, 'out', 'Send Me.flp')
FFMPEG = (glob.glob(os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe')) or ['ffmpeg'])[0]


def close_fl():
    subprocess.run(['powershell', '-NoProfile', '-Command',
                    '$p = Get-Process FL64 -ErrorAction SilentlyContinue; if ($p) { $p.CloseMainWindow() | Out-Null; '
                    '$p.WaitForExit(20000) | Out-Null }; Get-Process FL64 -ErrorAction SilentlyContinue | Stop-Process -Force'])
    time.sleep(1)


def loudness(wav):
    out = subprocess.run([FFMPEG, '-hide_banner', '-nostats', '-i', wav, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    summ = out[out.rfind('Summary:'):]
    grab = lambda k: float(re.search(k + r':\s+(-?[\d.]+|-inf)', summ).group(1).replace('-inf', '-99'))
    return {'integrated_lufs': grab('I'), 'lra_lu': grab('LRA'), 'true_peak_dbfs': grab('Peak')}


def export(n, notes=''):
    name = 'Send Me v%s' % n
    d = os.path.join(ROOT, 'exports', 'v%s' % n)
    os.makedirs(d, exist_ok=True)
    close_fl()
    flp = os.path.join(d, name + '.flp')
    shutil.copy(SRC, flp)
    wav = flp[:-4] + '.wav'
    if os.path.exists(wav):
        os.remove(wav)
    subprocess.run([FL_EXE, '/R', '/Ewav', flp], timeout=900)
    for _ in range(120):  # the renderer may hand off to a child process: wait for the file to settle
        if os.path.exists(wav) and not subprocess.run(['powershell', '-NoProfile', '-Command', 'Get-Process FL64 -ErrorAction SilentlyContinue'], capture_output=True, text=True).stdout.strip():
            break
        time.sleep(2)
    if not os.path.exists(wav):
        raise RuntimeError('render produced no WAV')
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', wav, '-b:a', '320k', wav[:-4] + '.mp3'], check=True)
    info = analyze(wav, png=wav[:-4] + '.png')
    info.update(loudness(wav))
    info['notes'] = notes
    from master import master  # offline master next to the raw render: "<name> vN (master).wav/.mp3"
    m = master(wav, wav[:-4] + ' (master).wav')
    info['master'] = {'after': m['after'], 'glue_gr_db': m['glue_gr_db'], 'limiter_max_gr_db': m['limiter_max_gr_db']}
    json.dump(info, open(wav[:-4] + '.json', 'w'), indent=1)
    subprocess.Popen([FL_EXE, SRC])  # back to work on the live project
    return info


if __name__ == '__main__':
    print(json.dumps(export(sys.argv[1], ' '.join(sys.argv[2:])), indent=1))
