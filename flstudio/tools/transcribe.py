"""Transcribe a (vocal) stem with word timestamps -> JSON, so chops can be cut on exact lyric phrases."""
import json, sys
import whisper

import librosa

src, out = sys.argv[1], sys.argv[2]
audio = librosa.load(src, sr=16000, mono=True)[0]  # no ffmpeg on this machine: hand whisper the samples
r = whisper.load_model('small').transcribe(audio, word_timestamps=True, language='en')
segs = [{'start': round(s['start'], 2), 'end': round(s['end'], 2), 'text': s['text'].strip(),
         'words': [(w['word'].strip(), round(w['start'], 2), round(w['end'], 2)) for w in s['words']]}
        for s in r['segments']]
json.dump(segs, open(out, 'w'), indent=1)
for s in segs:
    print('%7.2f %7.2f  %s' % (s['start'], s['end'], s['text']))
