#!/usr/bin/env python3
"""Étape 2 — où chaque ligne du texte est chantée, trouvé par le son.

Chaque ligne est alignée (alignement forcé CTC) contre un tronçon de
l'enregistrement autour de sa position a priori, avec un « joker » qui
absorbe tout le reste : ses lettres ne se posent que là où elles sont
chantées. On garde jusqu'à 5 emplacements candidats par ligne ; l'étape 3
tranche pour tout le texte à la fois.

    python new/find_lines.py EM.pt TEXTE.json SORTIE.json [--prior LABELS.txt] [--window-min 15]

TEXTE.json : liste de {"id", "text"} dans l'ordre du livre.
--prior : un fichier d'étiquettes Audacity (une ligne par entrée du texte,
dans le même ordre) qui dit où chercher ; sans lui, la position a priori
est proportionnelle au nombre de mots, et il faut une fenêtre plus large."""
import argparse, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ctc import Emissions

ap = argparse.ArgumentParser()
ap.add_argument("em"); ap.add_argument("text"); ap.add_argument("out")
ap.add_argument("--prior"); ap.add_argument("--window-min", type=float, default=15)
ap.add_argument("--cost", type=float, default=1.0); ap.add_argument("--beta", type=float, default=1.2)
a = ap.parse_args()
E = Emissions(a.em, a.cost, a.beta)
lines = json.load(open(a.text))
total_ms = E.frames * 20
if a.prior:
    prior = []
    for row in open(a.prior, encoding="utf-8"):
        t0, t1 = row.split("\t")[:2]; prior.append((float(t0) * 1000, float(t1) * 1000))
    assert len(prior) == len(lines), f"{a.prior}: {len(prior)} étiquettes pour {len(lines)} lignes"
else:
    n = [len(l["text"].split()) for l in lines]; cum = 0; prior = []
    for k in n:
        prior.append((total_ms * cum / sum(n), total_ms * (cum + k) / sum(n))); cum += k
W = int(a.window_min * 60 * 50)
res = []
for i, (ln, (p0, p1)) in enumerate(zip(lines, prior)):
    c0 = max(0, int(p0) // 20 - W); c1 = min(E.frames, int(p1) // 20 + W)
    best, has_opt = E.best_reading(E.EM[c0:c1], ln["text"])
    if best is None:
        res.append({"i": i, "id": ln.get("id"), "finds": []}); continue
    first, toks, owner, words, keep = best
    finds = [first]
    em2 = E.EM[c0:c1].clone()
    for _ in range(4):                        # les emplacements suivants
        for f in finds: em2[f[1]:f[2], :E.STAR] = -1e4
        r = E.search(em2, toks, owner, len(words))
        if not r or r[0] < first[0] - 1.0: break
        finds.append(r)
    out = [E.to_find(c0, f, words) for f in sorted(finds, key=lambda f: f[1])]
    res.append({"i": i, "id": ln.get("id"), "optional_sung": keep if has_opt else None, "finds": out})
    print(f"{i + 1}/{len(lines)} {ln.get('id')}: {len(out)} candidats", flush=True)
json.dump(res, open(a.out, "w"), ensure_ascii=False)
