#!/usr/bin/env python3
"""Étape 1 — les probabilités de lettres du modèle acoustique pour tout un
enregistrement, calculées une fois (fenêtres de 20 s qui se chevauchent,
chacune ne garde que son milieu propre) et sauvegardées.

    python new/emit.py AUDIO.mp3 SORTIE.pt [--model ID]

GPU NVIDIA utilisé s'il est présent (≈ 20 s pour 2 h d'audio) ; sinon le
CPU (bien plus lent : compter de l'ordre d'une heure pour 2 h d'audio)."""
import argparse, subprocess
import numpy as np, torch
from transformers import AutoProcessor, Wav2Vec2ForCTC

MODEL = "rabah2026/wav2vec2-large-xlsr-53-arabic-quran-v_final"

ap = argparse.ArgumentParser()
ap.add_argument("audio"); ap.add_argument("out"); ap.add_argument("--model", default=MODEL)
a = ap.parse_args()
dev = "cuda" if torch.cuda.is_available() else "cpu"
proc = AutoProcessor.from_pretrained(a.model)
model = Wav2Vec2ForCTC.from_pretrained(a.model).to(dev).eval()
if dev == "cuda": model = model.half()
raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", a.audio, "-ac", "1", "-ar", "16000",
                      "-f", "f32le", "-"], capture_output=True, check=True).stdout
wav = np.frombuffer(raw, dtype=np.float32).copy()
HOP, WIN, STEP, EDGE = 320, 20 * 16000, 16 * 16000, 2 * 16000     # 20 ms par trame
blank = proc.tokenizer.get_vocab().get("<pad>", 0)
G = len(wav) // HOP + 1; em = None; s = 0
while True:
    x = proc(wav[s:s + WIN], sampling_rate=16000, return_tensors="pt").input_values.to(dev)
    if dev == "cuda": x = x.half()
    with torch.inference_mode():
        lg = torch.log_softmax(model(x).logits[0].float(), -1).cpu()
    if em is None:
        em = torch.full((G, lg.shape[1]), -1e4, dtype=torch.float16); em[:, blank] = 0
    last = s + WIN >= len(wav)
    k0 = 0 if s == 0 else EDGE // HOP
    k1 = lg.shape[0] if last else (WIN - EDGE) // HOP
    g0 = s // HOP; n = min(k1, G - g0) - k0
    if n > 0: em[g0 + k0:g0 + k0 + n] = lg[k0:k0 + n].half()
    if last: break
    s += STEP
torch.save({"em": em, "vocab": proc.tokenizer.get_vocab(), "hop_ms": 20, "model": a.model}, a.out)
print(f"{a.out}: {em.shape[0]} trames, {len(wav) / 16000 / 60:.1f} min, {dev}")
