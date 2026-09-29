#!/usr/bin/env python3
"""Les données de word_review.html : pour chaque enregistrement exporté
(chaque *_words.json de la racine), les mots
de chaque ligne chantée avec leurs temps NOUVEAUX (un par passage d'une
ligne répétée) et ANCIENS (ceux que l'ancien apparieur old/*_match.py
attribuait aux mots du livre via Whisper — il les calculait sans les
sauvegarder ; on le relance tel quel pour les récupérer).

    python new/word_review_data.py      (après new/export.py pour les deux)"""
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
def old_word_times(script):
    """Relance l'ancien apparieur sans son écriture finale : book, times."""
    src = (ROOT / script).read_text()
    src = src[:src.index('lab = S / ')]
    g = {"__file__": str(ROOT / script), "__name__": "old_match"}
    exec(compile(src, script, "exec"), g)
    return g["book"], g["times"], g["norm"]

data = {}
for p in sorted(ROOT.glob("*_words.json")):
    W = json.load(open(p)); key = W["recording"]
    lines = W["lines"]
    text = json.load(open(ROOT / W["text_file"]))
    old_script = f"old/{key}_match.py"
    have_old = (ROOT / old_script).exists()
    if have_old:
        book, times, norm = old_word_times(old_script)
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
            t = times.get(idx.get((vi, j))) if (have_old and j < len(toks)) else None
            old.append(round(t[0], 2) if t else None); j += 1
        out.append({"v": l["v"], "w": words, "old": old,
                    "new": [[w["t0"] for w in p["words"]] for p in l["passes"]]})
    data[key] = {"title": W.get("title", key), "audio": W.get("audio", f"{key}.mp3"), "lines": out,
                 "has_old": have_old}
    n = sum(len(x["w"]) for x in out); o = sum(t is not None for x in out for t in x["old"])
    print(f"{key}: {len(out)} lignes, {n} mots" + (f" · anciens temps pour {o} ({round(100 * o / n)} %)" if have_old else " · pas d'ancien pipeline"))
(ROOT / "word_review_data.js").write_text("const DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")
