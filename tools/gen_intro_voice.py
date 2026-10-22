"""Intro voiceover 'EX SPORTS. IT'S IN THE FAME.' in British English, pre-rendered OFFLINE with Piper TTS.
Voice: en_GB 'vctk' medium, speaker p243 (VCTK corpus, University of Edinburgh, CC BY 4.0; Piper is MIT).
The game ships the WAVs - no runtime TTS, no network.
'EX' is rendered from phonemes with a held 's' and a short real pause before 'SPORTS', so it is heard as
'EX SPORTS' rather than run together.
Piper sampling is random per run, so several takes were rendered and the shipped intro_vo1.wav is the take
that faster-whisper (small.en + base.en) transcribed as 'X Sports' / 'X. Sports. It's in the fame.' both
standalone and in the full intro mix. Re-running may need the same check.
Run: /workspace/piperenv/bin/python tools/gen_intro_voice.py   (writes assets/sfx/intro_vo1.wav + intro_vo2.wav)"""
import os, json, wave
import numpy as np
from piper import PiperVoice, SynthesisConfig
MODEL = os.environ.get("PIPER_MODEL", "/workspace/piper_voices/en_GB-vctk-medium.onnx")
SPEAKER = "p243"
v = PiperVoice.load(MODEL)
sid = json.load(open(MODEL + ".json"))["speaker_id_map"][SPEAKER]
sr = v.config.sample_rate

def cfg(ls):
    return SynthesisConfig(speaker_id=sid, length_scale=ls, noise_scale=0.333, noise_w_scale=0.6)

def f32(x):
    x = np.asarray(x, np.float32)
    return x / 32768 if np.abs(x).max() > 2 else x

def ph_audio(ph, ls=1.1):
    return f32(v.phoneme_ids_to_audio(v.phonemes_to_ids(ph), cfg(ls)))

def text_audio(text, ls):
    return np.concatenate([f32(c.audio_float_array) for c in v.synthesize(text, syn_config=cfg(ls))])

def trim(x, thr=0.003, pre=0.01, post=0.06):
    nz = np.nonzero(np.abs(x) > thr)[0]
    return x[max(0, nz[0] - int(pre * sr)):min(x.size, nz[-1] + int(post * sr))]

ex = trim(ph_audio(["ˈ", "ɛ", "ɛ", "k", "s", "s", "!"]), post=0.03)
sports = trim(ph_audio(["s", "p", "ˈ", "ɔ", "ː", "t", "s", "."]))
vo1 = np.concatenate([ex, np.zeros(int(0.14 * sr), np.float32), sports])
vo2 = trim(text_audio("It's in the fame.", 1.05))
for fn, x in ((os.environ.get("VO1_OUT", "intro_vo1.wav"), vo1), ("intro_vo2.wav", vo2)):
    x = x / np.abs(x).max() * 0.95
    with wave.open(os.path.join("assets", "sfx", fn), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((x * 32767).astype("<i2").tobytes())
    print(fn, "%.2f s" % (x.size / sr), sr)
