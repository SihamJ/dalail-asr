#!/usr/bin/env python3
"""Étape 3 bis — les lignes restées « non chantées » cherchées une seconde
fois, mais seulement dans LEUR trou : entre la fin de la ligne placée
avant elles et le début de la ligne placée après.

Pourquoi : la première recherche balaie ±15 min autour de chaque ligne ;
or ces textes se répètent (formules du Dalail, rimes et tournures de la
Hamziyya), et le meilleur candidat d'une ligne était souvent la même
formule ailleurs — hors de l'ordre du livre, donc refusé à juste titre par
l'étape 3, et la ligne perdue alors qu'elle est chantée. Dans son trou, les
imitations ailleurs ne peuvent plus concourir. Une ligne dont le trou ne
contient rien qui lui ressemble reste non chantée.

    python new/fill_gaps.py EM.pt TEXTE.json DECISION.json SORTIE.json"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ctc import Emissions

emf, textf, decf, outf = sys.argv[1:5]
E = Emissions(emf)
lines = json.load(open(textf)); dec = json.load(open(decf))
TAKE = -1.3      # même seuil que l'étape 3 (REWARD)
REPEAT = .35
PACE = 300       # ms par mot au plus vite : un trou plus court ne peut pas tenir la ligne
EDGE = 500       # ms de marge sur les bords du trou
n = len(dec); filled = 0
for i in range(n):
    if dec[i]["sung"]: continue
    prev_end = max((p["t1"] for j in range(i - 1, -1, -1) if dec[j]["sung"] for p in dec[j]["passes"]), default=0)
    nxt = next((j for j in range(i + 1, n) if dec[j]["sung"]), None)
    next_start = dec[nxt]["passes"][0]["t0"] if nxt is not None else E.frames * 20
    # laisser la place aux autres lignes manquantes du même trou
    later = sum(len(lines[k]["text"].split()) for k in range(i + 1, nxt if nxt is not None else n))
    hi = next_start - later * PACE
    words = len(lines[i]["text"].split())
    if hi - prev_end < words * PACE: continue
    c0 = max(0, (prev_end - EDGE) // 20); c1 = min(E.frames, (hi + EDGE) // 20)
    em = E.EM[c0:c1]
    best, has_opt = E.best_reading(em, lines[i]["text"])
    if best is None or best[0][0] < TAKE: continue
    first, toks, owner, ws, keep = best
    passes = [first]
    em2 = em.clone()
    for _ in range(2):                  # une répétition, dans ce même trou
        for f in passes: em2[f[1]:f[2], :E.STAR] = -1e4
        r = E.search(em2, toks, owner, len(ws))
        if not r or r[0] < first[0] - REPEAT: break
        if any(not (r[1] >= f[2] - 40 or r[2] <= f[1] + 40) for f in passes): break
        passes.append(r)
    dec[i] = {"i": i, "id": dec[i]["id"], "sung": True, "filled": True,
              "optional_sung": keep if has_opt else None,
              "passes": [E.to_find(c0, f, ws) for f in sorted(passes, key=lambda f: f[1])]}
    filled += 1
    print(f"{dec[i]['id']}: placée dans son trou ({len(passes)} passage(s), score {round(first[0], 2)})", flush=True)
json.dump(dec, open(outf, "w"), ensure_ascii=False)
print(f"{filled} lignes retrouvées dans leur trou ; {sum(not d['sung'] for d in dec)} restent non chantées")
