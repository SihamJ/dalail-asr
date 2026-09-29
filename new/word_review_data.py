#!/usr/bin/env python3
"""Les données de word_review.html : pour chaque enregistrement, les mots
de chaque ligne chantée avec leurs temps NOUVEAUX (un par passage d'une
ligne répétée) et ANCIENS (ceux que l'ancien apparieur old/*_match.py
attribuait aux mots du livre via Whisper — il les calculait sans les
sauvegarder ; on le relance tel quel pour les récupérer).

    python new/word_review_data.py      (après new/export.py pour les deux)"""
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
R2 = "https://pub-399f14501bad46a28b40e12c0215d805.r2.dev/"
REC = {"dalail": ("دلائل الخيرات (المراكشية)", "dalail-marrakchiya.mp3", "dalail_segments.json", "old/dalail_match.py"),
       "hamzia": ("الهمزية", "hamzia.mp3", "hamzia_verses.json", "old/hamzia_match.py")}

def old_word_times(script):
    """Relance l'ancien apparieur sans son écriture finale : book, times."""
    src = (ROOT / script).read_text()
    src = src[:src.index('lab = S / ')]
    g = {"__file__": str(ROOT / script), "__name__": "old_match"}
    exec(compile(src, script, "exec"), g)
    return g["book"], g["times"], g["norm"]

data = {}
for key, (title, mp3, textf, script) in REC.items():
    p = ROOT / f"{key}_words.json"
    if not p.exists(): continue
    lines = json.load(open(p))["lines"]
    book, times, norm = old_word_times(script)
    text = json.load(open(ROOT / textf))
    idx = {}; k = 0
    for vi, v in enumerate(text):
        for tj, w in enumerate(v["text"].split()):
            if norm(w): idx[(vi, tj)] = k; k += 1
    out = []
    for l in lines:
        if not l["sung"]: continue
        vi = l["v"] - 1; toks = text[vi]["text"].split()
        words = [w["w"] for w in l["passes"][0]["words"]]
        old = []; j = 0
        for w in words:
            while j < len(toks) and toks[j].strip("()") != w: j += 1
            t = times.get(idx.get((vi, j))) if j < len(toks) else None
            old.append(round(t[0], 2) if t else None); j += 1
        out.append({"v": l["v"], "w": words, "old": old,
                    "new": [[w["t0"] for w in p["words"]] for p in l["passes"]]})
    data[key] = {"title": title, "audio": R2 + mp3, "lines": out}
    n = sum(len(x["w"]) for x in out); o = sum(t is not None for x in out for t in x["old"])
    print(f"{key}: {len(out)} lignes, {n} mots · anciens temps pour {o} ({round(100 * o / n)} %)")
(ROOT / "word_review_data.js").write_text("const DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")
