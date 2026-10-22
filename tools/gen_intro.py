"""Generate the 6-second intro assets for EX SPORTS SFC 27 (run from the repo root).
- assets/intro_logo.png : the EX SPORTS logo (from ex_sports_logo_source.png), trimmed to the circle, 1024x1024 RGBA
- assets/sfx/intro.wav  : an original code-generated sting (filtered-noise whoosh + low thump + short bell chord)
No third-party audio; deterministic (fixed seed)."""
import wave, numpy as np
from PIL import Image

im = Image.open("ex_sports_logo_source.png").convert("RGBA")
bb = im.split()[3].getbbox(); pad = 8
box = (max(0, bb[0] - pad), max(0, bb[1] - pad), min(im.width, bb[2] + pad), min(im.height, bb[3] + pad))
im.crop(box).resize((1024, 1024), Image.LANCZOS).save("assets/intro_logo.png", optimize=True)

SR = 44100; DUR = 2.6; HIT = 1.1                     # impact lands 1.1 s into the file
t = np.arange(int(SR * DUR)) / SR
rng = np.random.default_rng(27)
# whoosh: noise through a resonant band-pass whose centre sweeps up toward the hit, then a short tail
noise = rng.standard_normal(t.size)
fc = np.where(t < HIT, 300 + 2600 * (t / HIT) ** 2, 2900 * np.exp(-(t - HIT) * 6) + 250)
out = np.zeros_like(t); y1 = y2 = 0.0; q = 6.0
for i in range(t.size):                              # simple state-variable band-pass
    f = 2 * np.sin(np.pi * fc[i] / SR)
    hp = noise[i] - y2 - y1 / q; y1 += f * hp; y2 += f * y1; out[i] = y1
env = np.where(t < HIT, (t / HIT) ** 2.2, np.exp(-(t - HIT) * 9))
whoosh = out / (np.abs(out).max() + 1e-9) * env * 0.55
# thump: pitched-down sine at the hit
th = np.clip(t - HIT, 0, None); on = (t >= HIT).astype(float)
thump = on * np.sin(2 * np.pi * (48 * th + 60 * (1 - np.exp(-th * 18)) / 18 * 1.0)) * np.exp(-th * 7) * 0.8
# bell chord (A5, E6, A6 with slight inharmonic partials), short and clean
bell = np.zeros_like(t)
for f0, a in ((880.0, 0.22), (1318.5, 0.15), (1760.0, 0.10)):
    for k, (m, g) in enumerate(((1.0, 1.0), (2.76, 0.25), (5.4, 0.08))):
        bell += a * g * np.sin(2 * np.pi * f0 * m * th) * np.exp(-th * (2.2 + 1.5 * k))
bell *= on * (1 - np.exp(-th * 400))
mix = whoosh + thump + bell
mix *= np.clip((DUR - t) / 0.25, 0, 1)                # clean tail-out
mix = mix / np.abs(mix).max() * 0.6          # leaves headroom: the voiceover sits on top
pcm = (mix * 32767).astype("<i2")
with wave.open("assets/sfx/intro.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print("ok", box, pcm.size / SR)
