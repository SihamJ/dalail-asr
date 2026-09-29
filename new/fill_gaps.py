#!/usr/bin/env python3
"""Étape 3 bis — les lignes restées « non chantées » cherchées une seconde
fois, dans LEUR trou, avec leurs voisines.

Pourquoi : la première recherche balaie ±15 min autour de chaque ligne ;
or ces textes se répètent (formules du Dalail, mètre, rime et tournures de
la Hamziyya), et le meilleur candidat d'une ligne était souvent la même
formule ailleurs — hors de l'ordre du livre, donc refusé à juste titre par
l'étape 3, et la ligne perdue alors qu'elle est chantée. Souvent aussi une
voisine s'était posée sur son audio, ne lui laissant aucun trou.

Chaque trou est réaligné avec 0 à 6 lignes placées de chaque côté : tout
le bloc ENSEMBLE, dans l'ordre, un joker avant, entre et après les lignes
(interludes, silence). La meilleure version (chaque ligne placée vaut son
score + 1.6) remplace l'existant si elle fait mieux. Une ligne placée par
l'étape 3 peut bouger, jamais disparaître. Voir solve() et polish().

Le bord de l'enregistrement peut couper une ligne en plein chant : on en
place alors le début (ou, au tout début, la fin) — marquée « cut ». Les
lignes marquées « "chanted": false » dans le texte ne sont jamais
cherchées. Une répétition n'est retenue que si elle suit sa ligne de près
(≤ 20 s).

    python new/fill_gaps.py EM.pt TEXTE.json DECISION.json CANDIDATS.json SORTIE.json"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ctc import Emissions

emf, textf, decf, candf, outf = sys.argv[1:6]
E = Emissions(emf)
lines = json.load(open(textf)); dec = json.load(open(decf)); cands = json.load(open(candf))
TAKE = -1.3      # même seuil que l'étape 3 (lignes seules, bords coupés)
JOINT = -1.6     # dans un bloc aligné dans l'ordre, l'ordre lui-même tient la
                 # ligne à sa place : on accepte un peu moins net (chant rapide)
REPEAT = .35     # une répétition score presque aussi bien que le 1er passage
NEAR = 20000     # … et le suit de près (ms)
EDGE = 500       # ms de marge sur les bords du trou
n = len(dec)
REWARD = 1.6     # l'objectif : une ligne placée vaut score + 1.6 (= −JOINT)
KMAX = 6         # au plus 6 lignes placées reprises de chaque côté d'un trou

def cut_line(em, k, head):
    """La ligne k coupée par le bord de l'enregistrement : son début (head)
    jusqu'à la fin de em, ou sa fin depuis le début de em. Le plus long
    morceau qui colle, au moins la moitié des mots (et 3)."""
    words = lines[k]["text"].split()
    for m in range(len(words) - 1, max(3, len(words) // 2) - 1, -1):
        part = " ".join(words[:m] if head else words[-m:])
        toks, owner, ws = E.tokens_of(part, keep_of(k))
        if not ws: continue
        r = E.search(em, toks, owner, len(ws))
        if r is None or r[0] < TAKE: continue
        if (em.shape[0] - r[2] if head else r[1]) > 75: continue      # 1,5 s du bord
        return (*r, ws)
    return None

def keep_of(i):
    """La lecture des mots optionnels retenue à la 1re passe (défaut : gardés)."""
    k = dec[i].get("optional_sung") if dec[i].get("filled") else None
    if k is None: k = cands[i].get("optional_sung")
    return True if k is None else k

def solve(block, c0, c1):
    """Les lignes du bloc alignées ensemble, dans l'ordre, sur E.EM[c0:c1].
    Une ligne placée par l'étape 3 peut bouger, pas disparaître ; seules
    les autres (y compris celles qu'un tour précédent a placées) peuvent
    être laissées de côté. {ligne: résultat},
    ou None si les lignes déjà placées ne tiennent pas toutes."""
    em = E.EM[c0:c1]; todo = [k for k in block if k not in skip]
    must = {k for k in block if k in first}
    kp = {k: keep_of(k) for k in block}      # la lecture des mots optionnels
    def run_of(ks):
        return E.align_run(em, [(lines[k]["text"], kp[k]) for k in ks])
    while True:
        r = run_of(todo)
        free = [x for x in range(len(todo)) if todo[x] not in must]
        if r is None:
            if not free: return None
            # le tronçon ne peut pas tous les tenir : on retire celle qui,
            # seule, ressemble le moins à ce qu'il contient
            solo = {}
            for x in free:
                best, _ = E.best_reading(em, lines[todo[x]]["text"])
                solo[x] = best[0][0] if best else float("-inf")
            todo.pop(min(free, key=solo.get)); continue
        sc = lambda x: r[x][0] if r[x] else float("-inf")
        if all(sc(x) >= JOINT for x in range(len(todo))):
            return polish(block, em, must, kp, dict(zip(todo, r)))
        if not free: return None
        # laquelle retirer ? Pas forcément la pire : des lignes absentes
        # forcées dans le tronçon écrasent les lignes chantées, qui scorent
        # alors plus mal qu'elles. On essaie les (au plus 6) pires, et on
        # retire celle dont le départ profite le plus à tout le bloc.
        cand = sorted(free, key=sc)[:6]
        if len(cand) == 1:
            todo.pop(cand[0]); continue
        def after(x):
            rr = run_of(todo[:x] + todo[x + 1:])
            return float("-inf") if rr is None else sum((y[0] if y else -5.0) + REWARD for y in rr)
        todo.pop(max(cand, key=after))

def polish(block, em, must, kp, placed):
    """Le retrait une à une peut garder la mauvaise ligne (une voisine qui
    ressemble). On essaie d'ajouter chaque ligne laissée de côté, ou de
    l'échanger contre une ligne libre proche (±3), et l'autre lecture des
    mots optionnels « (سيدنا) » des lignes libres — la 1re passe n'a rien
    appris de fiable sur elles. On garde tout ce qui fait mieux."""
    def run_of(ks, kk):
        rr = E.align_run(em, [(lines[k]["text"], kk[k]) for k in ks])
        if rr is None or any(x is None or x[0] < JOINT for x in rr): return None
        return dict(zip(ks, rr))
    opt = lambda k: "(" in lines[k]["text"] and k not in must
    better = True
    while better:
        better = False
        out = [k for k in block if k not in placed and k not in skip]
        tries = [(sorted(placed), {**kp, x: not kp[x]}) for x in placed if opt(x)]
        for y in out:
            for kk in [kp] + ([{**kp, y: not kp[y]}] if opt(y) else []):
                tries.append((sorted(list(placed) + [y]), kk))
                tries += [(sorted([k for k in placed if k != x] + [y]), kk)
                          for x in placed if x not in must and abs(x - y) <= 3]
        base = value(placed)
        for ks, kk in tries:
            got = run_of(ks, kk)
            if got and value(got) > base + .05:
                placed, kp = got, kk; better = True; break
    return {k: (*res, kp[k]) for k, res in placed.items()}

def value(placed):
    """L'objectif de l'étape 3 : chaque ligne placée vaut score + REWARD."""
    return sum(res[0] + REWARD for res in placed.values())

def old_value(block):
    return sum(dec[k]["passes"][0]["adv"] + REWARD for k in block if dec[k]["sung"])

def side(start, step, K):
    """Les K lignes placées de ce côté du trou, puis l'ancre (ou None : le
    bord de l'enregistrement). Une ligne répétée sert toujours d'ancre."""
    got = []; k = start
    while 0 <= k < n and len(got) <= K:
        if dec[k]["sung"]:
            if len(got) < K and (len(dec[k]["passes"]) > 1 or dec[k].get("cut")): return None
            got.append(k)
        k += step
    if len(got) < K: return None
    return got[:K], (got[K] if len(got) > K else None)

touched = set(); newly = set(); dropped = set()
# les lignes que le texte marque « "chanted": false » (titres, notes de
# l'édition) ne sont jamais cherchées
skip = {k for k, l in enumerate(lines) if l.get("chanted") is False}
for k in skip:
    dec[k] = {"i": k, "id": dec[k]["id"], "sung": False, "passes": []}
first = {k for k in range(n) if dec[k]["sung"]}   # placées par l'étape 3

# le bord de l'enregistrement peut couper une ligne en plein chant
cut = None
if not dec[-1]["sung"]:
    i = n - 1
    while i > 0 and not dec[i - 1]["sung"]: i -= 1
    if i > 0:
        c0 = max(0, (dec[i - 1]["passes"][-1]["t1"] - EDGE) // 20)
        r = cut_line(E.EM[c0:], i, True)
        if r: cut = (i, c0, r)
if cut is None and not dec[0]["sung"]:
    j = 0
    while j + 1 < n and not dec[j + 1]["sung"]: j += 1
    if j + 1 < n:
        c1 = min(E.frames, (dec[j + 1]["passes"][0]["t0"] + EDGE) // 20)
        r = cut_line(E.EM[:c1], j, False)
        if r: cut = (j, 0, r)
if cut:
    k, c0, (adv, f0, f1, mine, ws) = cut
    dec[k] = {"i": k, "id": dec[k]["id"], "sung": True, "filled": True, "cut": True,
              "optional_sung": cands[k].get("optional_sung"),
              "passes": [E.to_find(c0, (adv, f0, f1, mine), ws)]}
    newly.add(k); touched.add(k)
    print(f"v{k + 1:03d} coupée par le bord de l'enregistrement", flush=True)

for sweep in range(3):
    changed = False
    i = 0
    while i < n:
        if dec[i]["sung"]: i += 1; continue
        j = i
        while j + 1 < n and not dec[j + 1]["sung"]: j += 1
        best = None
        for K in range(KMAX + 1):
            L, R = side(i - 1, -1, K), side(j + 1, 1, K)
            if L is None or R is None: break
            la, ra = L[1], R[1]
            lo = la + 1 if la is not None else 0
            hi = ra if ra is not None else n
            c0 = max(0, (dec[la]["passes"][-1]["t1"] - EDGE) // 20) if la is not None else 0
            c1 = min(E.frames, (dec[ra]["passes"][0]["t0"] + EDGE) // 20) if ra is not None else E.frames
            block = list(range(lo, hi))
            placed = solve(block, c0, c1)
            if placed is None: continue
            gain = value(placed) - old_value(block)
            if gain > .05 and (best is None or gain > best[0]):
                best = (gain, block, c0, placed, K)
            if la is None and ra is None: break
        if best:
            gain, block, c0, placed, K = best
            for k in block:
                was = dec[k]["sung"]
                if k in placed:
                    adv, f0, f1, mine, ws, kk = placed[k]
                    dec[k] = {"i": k, "id": dec[k]["id"], "sung": True,
                              "filled": dec[k].get("filled", False) or not was,
                              "moved": was and not dec[k].get("filled", False),
                              "optional_sung": kk if "(" in lines[k]["text"] else None,
                              "passes": [E.to_find(c0, (adv, f0, f1, mine), ws)]}
                    touched.add(k)
                    if not was: newly.add(k); dropped.discard(k)
                elif was:
                    dec[k] = {"i": k, "id": dec[k]["id"], "sung": False, "passes": []}
                    dropped.add(k); newly.discard(k)
            print(f"v{block[0] + 1:03d}–v{block[-1] + 1:03d} réalignées (±{K} voisines) : "
                  f"{sum(k in placed for k in block)}/{len(block)} placées, gain {gain:.2f}", flush=True)
            changed = True
        i = j + 1
    if not changed: break

# les répétitions des lignes (re)placées ici : juste après, avant la suivante
for k in sorted(touched - dropped):
    if not dec[k]["sung"] or dec[k].get("cut"): continue
    p = dec[k]["passes"][0]
    nxt = next((dec[m]["passes"][0]["t0"] for m in range(k + 1, n) if dec[m]["sung"]), E.frames * 20)
    f1, lim = p["t1"] // 20, min(nxt, p["t1"] + NEAR) // 20
    if lim - f1 <= 50: continue
    toks, owner, ws = E.tokens_of(lines[k]["text"], keep_of(k))
    rr = E.search(E.EM[f1:lim], toks, owner, len(ws))
    if rr and rr[0] >= p["adv"] - REPEAT:
        dec[k]["passes"].append(E.to_find(f1, rr, ws))

json.dump(dec, open(outf, "w"), ensure_ascii=False)
filled = sum(bool(d.get("filled")) and d["sung"] for d in dec)
print(f"{filled} lignes retrouvées par la seconde passe, {sum(bool(d.get('moved')) and d['sung'] for d in dec)} "
      f"voisines déplacées, {len(dropped)} retirées ; {sum(not d['sung'] for d in dec)} restent non chantées")
