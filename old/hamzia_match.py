#!/usr/bin/env python3
"""Audacity labels for the Hamziyya — v3: banded global alignment.

v1 (global difflib): 3/462 — exact-only matching left common words as the
only anchors, and LCS stitched them across half an hour.
v2 (moving window): 10/462 then death — a cursor heuristic cannot survive
40% missing audio: it drifts 9s per miss while the audio moves 20.

v3 does what both were approximating: Needleman-Wunsch over the two word
streams, monotonic by construction, with FUZZY match scores (Whisper's
garbles are rasm-close: الأمياء≈الانبياء) and cheap gaps (the interludes
and dropouts are 40% of the audio — skipping book verses must be cheap).
Banded to keep 2651×4203 tractable.
"""
import difflib
import json
import pathlib
import re

S = pathlib.Path(__file__).parent          # old/: transcripts in, labels out
ROOT = S.parent                            # the reference texts
MARKS = re.compile(r"[ً-ْٰۖ-ۭـ]")
NONLETTER = re.compile(r"[^ء-ي ]")
FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
                      "ؤ": "و", "ئ": "ي", "ى": "ي", "ة": "ه"})


def norm(w: str) -> str:
    w = MARKS.sub("", w)
    w = NONLETTER.sub("", w)
    return w.translate(FOLD).replace("ء", "").strip()


verses = json.loads((ROOT / "hamzia_verses.json").read_text())
book = []                          # (norm, verse_idx)
for vi, v in enumerate(verses):
    for w in v["text"].split():
        n = norm(w)
        if n:
            book.append((n, vi))

asr = json.loads((S / "hamzia.asr.json").read_text())
hyp = []                           # (norm, start, end)
for seg in asr["segments"]:
    for w in seg["words"]:
        n = norm(w["word"])
        if n:
            hyp.append((n, w["start"], w["end"]))

NH, NB = len(hyp), len(book)
print(f"book: {NB} words / {len(verses)} verses | asr: {NH} words")

# ---- scoring -------------------------------------------------------------
_fuzz = {}
def score(wh: str, wb: str) -> float:
    if wh == wb:
        return 3.0
    if len(wb) < 3 or len(wh) < 2:
        return -1.0
    key = (wh, wb)
    r = _fuzz.get(key)
    if r is None:
        r = difflib.SequenceMatcher(None, wh, wb).ratio()
        _fuzz[key] = r
    return 2.0 if r >= 0.66 else -1.0

GAP_H = -0.35    # unmatched ASR word (hallucination, refrain)
GAP_B = -0.25    # unmatched book word (unheard — cheap, 40% is missing)

# ---- banded NW -----------------------------------------------------------
# The diagonal is time-proportional; the band must absorb the worst local
# excursion (long interludes ↔ dense verse runs).
BAND = 700
NEG = float("-inf")
prev = [0.0] * (NB + 1)
for j in range(1, NB + 1):
    prev[j] = prev[j - 1] + GAP_B
back = []                          # per-i: dict j -> move ('d','h','b')
for i in range(1, NH + 1):
    ci = int(i * NB / NH)
    lo, hi = max(1, ci - BAND), min(NB, ci + BAND)
    cur = [NEG] * (NB + 1)
    cur[lo - 1] = prev[lo - 1] + GAP_H if prev[lo - 1] != NEG else NEG
    moves = {}
    wh = hyp[i - 1][0]
    for j in range(lo, hi + 1):
        d = prev[j - 1] + score(wh, book[j - 1][0]) if prev[j - 1] != NEG else NEG
        h = prev[j] + GAP_H if prev[j] != NEG else NEG
        b = cur[j - 1] + GAP_B if cur[j - 1] != NEG else NEG
        best = max(d, h, b)
        cur[j] = best
        moves[j] = "d" if best == d else ("h" if best == h else "b")
    back.append((lo, hi, moves))
    prev = cur

# ---- traceback -----------------------------------------------------------
times = {}                         # book idx -> (t0, t1)
i, j = NH, NB
while i > 0 and j > 0:
    lo, hi, moves = back[i - 1]
    m = moves.get(j)
    if m is None:                  # outside the band — slide book-side
        j -= 1
        continue
    if m == "d":
        if score(hyp[i - 1][0], book[j - 1][0]) > 0:
            times[j - 1] = (hyp[i - 1][1], hyp[i - 1][2])
        i, j = i - 1, j - 1
    elif m == "h":
        i -= 1
    else:
        j -= 1

print(f"matched book words: {len(times)}/{NB}")

# ---- per-verse windows ---------------------------------------------------
rows = []
for vi, v in enumerate(verses):
    idxs = [k for k, (_, x) in enumerate(book) if x == vi]
    hit = sorted(times[k] for k in idxs if k in times)
    nm = len(hit)
    row = {"vi": vi, "text": v["text"].replace("\n", " "),
           "n": len(idxs), "m": nm}
    if nm / max(1, len(idxs)) >= 0.35:
        row.update(t0=hit[0][0], t1=hit[-1][1], review=False)
    else:
        row.update(t0=None, t1=None, review=True)
    rows.append(row)

anchored = [r for r in rows if not r["review"]]
print(f"anchored verses: {len(anchored)}/{len(rows)}")

for i, r in enumerate(rows):       # interpolate the gaps
    if r["review"]:
        prev_r = next((x for x in reversed(rows[:i]) if x.get("t1")), None)
        nxt = next((x for x in rows[i + 1:] if x.get("t0")), None)
        r["t0"] = prev_r["t1"] if prev_r else 0.0
        r["t1"] = nxt["t0"] if nxt else r["t0"]

for a, b in zip(rows, rows[1:]):   # monotonic
    if b["t0"] < a["t1"]:
        mid = round((b["t0"] + a["t1"]) / 2, 2)
        a["t1"] = b["t0"] = mid

lab = S / "hamzia_labels.txt"
with lab.open("w") as f:
    for r in rows:
        flag = "REVIEW " if r["review"] else ""
        f.write(f"{r['t0']:.2f}\t{r['t1']:.2f}\t{flag}v{r['vi']+1:03d} "
                f"{r['text'][:40]}\n")
print(f"labels → {lab.name}: {len(anchored)} auto, "
      f"{len(rows) - len(anchored)} flagged REVIEW")
