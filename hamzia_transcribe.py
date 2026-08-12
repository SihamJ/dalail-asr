#!/usr/bin/env python3

import json
import time
from pathlib import Path

from faster_whisper import WhisperModel

LAB = Path.home() / "dalail-lab"
audio = LAB / "hamzia.mp3"
out = LAB / "hamzia.asr.json"

t0 = time.time()
# Take 2: the batched pipeline's VAD heard melody, decided «music, not
# speech», and kept 263 words of a two-hour qasida. Munshid audio needs the
# detector out of the way entirely.
model = WhisperModel("large-v3", device="cuda", compute_type="float16")
segs, info = model.transcribe(
    str(audio), language="ar", word_timestamps=True,
    vad_filter=False,
    condition_on_previous_text=False)
doc = {"language": "ar", "segments": []}
for s in segs:
    doc["segments"].append({
        "start": s.start, "end": s.end, "text": s.text,
        "words": [{"word": w.word, "start": w.start, "end": w.end}
                  for w in (s.words or [])]})
out.write_text(json.dumps(doc, ensure_ascii=False))
n = sum(len(s["words"]) for s in doc["segments"])
print(f"done: {n} words, {len(doc['segments'])} segments, "
      f"{time.time() - t0:.0f}s wall")
