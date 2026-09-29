#!/usr/bin/env python3
"""Étape 3 — tout le texte décidé ensemble : un emplacement par ligne, dans
l'ordre du livre, aucun tronçon d'audio revendiqué deux fois ; une ligne
sans emplacement convenable est « non chantée ». Les autres candidats d'une
ligne qui la suivent de près (≤ 20 s), avant la suivante, sont ses
répétitions (un vers chanté deux fois donne deux passages).

    python new/decide.py CANDIDATS.json SORTIE.json"""
import json, sys
R = json.load(open(sys.argv[1]))
REWARD = 1.3   # un emplacement vaut d'être pris au-dessus d'un score de −1.3
TOL = 800      # ms de chevauchement toléré avec la ligne précédente
REPEAT = .35   # une répétition score presque aussi bien que le premier passage
NEAR = 20000   # … et le suit de près : au plus 20 s après le passage précédent
cands = [r["finds"] for r in R]; n = len(R)
states = {-1: (0.0, None)}   # fin du dernier passage placé → (score, chemin)
for i in range(n):
    nxt = {}
    for last_end, (sc, path) in states.items():
        if last_end not in nxt or sc > nxt[last_end][0]: nxt[last_end] = (sc, (path, i, -1))
        for c, f in enumerate(cands[i]):
            if f["t0"] < last_end - TOL: continue
            s2 = sc + f["adv"] + REWARD
            if f["t1"] not in nxt or s2 > nxt[f["t1"]][0]: nxt[f["t1"]] = (s2, (path, i, c))
    pruned, top = {}, float("-inf")
    for k, v in sorted(nxt.items()):
        if v[0] > top: pruned[k] = v; top = v[0]
    states = pruned
score, path = max(states.values(), key=lambda v: v[0])
choice = [-1] * n
while path:
    path, i, c = path; choice[i] = c
out = []
for i, c in enumerate(choice):
    if c == -1:
        out.append({"i": i, "id": R[i]["id"], "sung": False, "passes": []}); continue
    main = cands[i][c]
    nxt_t0 = next((cands[j][choice[j]]["t0"] for j in range(i + 1, n) if choice[j] != -1), 1e12)
    passes = [main]
    for k, f in enumerate(cands[i]):
        if k == c: continue
        if f["t0"] >= main["t1"] - TOL and f["t0"] <= passes[-1]["t1"] + NEAR and f["t1"] <= nxt_t0 + TOL \
           and f["adv"] >= main["adv"] - REPEAT \
           and all(f["t0"] >= p["t1"] - TOL or f["t1"] <= p["t0"] + TOL for p in passes):
            passes.append(f)
    passes.sort(key=lambda f: f["t0"])
    out.append({"i": i, "id": R[i]["id"], "sung": True, "optional_sung": R[i].get("optional_sung"),
                "passes": passes})
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False)
sung = sum(o["sung"] for o in out)
rep = sum(len(o["passes"]) > 1 for o in out)
print(f"{sung}/{n} lignes placées, {rep} répétées")
