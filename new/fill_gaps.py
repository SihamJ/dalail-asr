#!/usr/bin/env python3
"""Étape 3 bis — les lignes restées « non chantées » cherchées une seconde
fois, dans LEUR trou : entre la fin de la ligne placée avant elles et le
début de la ligne placée après.

Pourquoi : la première recherche balaie ±15 min autour de chaque ligne ;
or ces textes se répètent (formules du Dalail, mètre, rime et tournures de
la Hamziyya), et le meilleur candidat d'une ligne était souvent la même
formule ailleurs — hors de l'ordre du livre, donc refusé à juste titre par
l'étape 3, et la ligne perdue alors qu'elle est chantée.

Les lignes manquantes d'un même trou sont alignées ENSEMBLE, dans l'ordre,
avec un joker avant, entre et après elles (interludes, silence) : chacune
ne peut prendre que sa place dans la suite, et aucune ne peut avaler ses
voisines — les chercher une à une laissait la première prendre l'audio des
suivantes, qui se ressemblent. Une ligne qui colle mal (score < −1.3) est
retirée et le trou réaligné sans elle ; ce qui reste est « non chanté ».
Une répétition n'est retenue que si elle suit sa ligne de près (≤ 20 s).

    python new/fill_gaps.py EM.pt TEXTE.json DECISION.json CANDIDATS.json SORTIE.json"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ctc import Emissions

emf, textf, decf, candf, outf = sys.argv[1:6]
E = Emissions(emf)
lines = json.load(open(textf)); dec = json.load(open(decf)); cands = json.load(open(candf))
TAKE = -1.3      # même seuil que l'étape 3
REPEAT = .35     # une répétition score presque aussi bien que le 1er passage
NEAR = 20000     # … et le suit de près (ms)
EDGE = 500       # ms de marge sur les bords du trou
n = len(dec); filled = 0

def keep_of(i):
    """La lecture des mots optionnels retenue à la 1re passe (défaut : gardés)."""
    k = cands[i].get("optional_sung")
    return True if k is None else k

i = 0
while i < n:
    if dec[i]["sung"]: i += 1; continue
    j = i
    while j + 1 < n and not dec[j + 1]["sung"]: j += 1
    run = list(range(i, j + 1))
    prev_end = max((p["t1"] for k in range(i - 1, -1, -1) if dec[k]["sung"] for p in dec[k]["passes"]), default=0)
    next_start = dec[j + 1]["passes"][0]["t0"] if j + 1 < n else E.frames * 20
    c0 = max(0, (prev_end - EDGE) // 20); c1 = min(E.frames, (next_start + EDGE) // 20)
    em = E.EM[c0:c1]
    todo = run[:]
    placed = {}
    while todo:
        r = E.align_run(em, [(lines[k]["text"], keep_of(k)) for k in todo])
        if r is None:
            # le trou ne peut pas tous les tenir : on retire celle qui, seule,
            # ressemble le moins à ce qu'il contient
            solo = []
            for k in todo:
                best, _ = E.best_reading(em, lines[k]["text"])
                solo.append(best[0][0] if best else float("-inf"))
            todo.pop(min(range(len(todo)), key=lambda x: solo[x]))
            continue
        worst = min(range(len(todo)), key=lambda x: r[x][0] if r[x] else float("-inf"))
        if r[worst] is None or r[worst][0] < TAKE:
            todo.pop(worst); continue
        placed = {k: res for k, res in zip(todo, r)}
        break
    ordered = sorted(placed)
    for idx, k in enumerate(ordered):
        adv, f0, f1, mine, ws = placed[k]
        first = (adv, f0, f1, mine)
        passes = [first]
        # une répétition : juste après, avant la ligne suivante du trou
        nxt_f = placed[ordered[idx + 1]][1] if idx + 1 < len(ordered) else em.shape[0]
        lim = min(nxt_f, f1 + NEAR // 20)
        if lim - f1 > 50:
            toks, owner, ws2 = E.tokens_of(lines[k]["text"], keep_of(k))
            sub = em[f1:lim]
            rr = E.search(sub, toks, owner, len(ws2))
            if rr and rr[0] >= adv - REPEAT:
                passes.append((rr[0], rr[1] + f1, rr[2] + f1, {w: [a + f1, b + f1] for w, (a, b) in rr[3].items()}))
        dec[k] = {"i": k, "id": dec[k]["id"], "sung": True, "filled": True,
                  "optional_sung": cands[k].get("optional_sung"),
                  "passes": [E.to_find(c0, f, ws) for f in passes]}
        filled += 1
    if run:
        print(f"trou v{i + 1:03d}–v{j + 1:03d} : {len(placed)}/{len(run)} placées", flush=True)
    i = j + 1
json.dump(dec, open(outf, "w"), ensure_ascii=False)
print(f"{filled} lignes retrouvées dans leur trou ; {sum(not d['sung'] for d in dec)} restent non chantées")
