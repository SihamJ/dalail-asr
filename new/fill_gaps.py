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

    python new/fill_gaps.py EM.pt TEXTE.json DECISION.json CANDIDATS.json SORTIE.json
        [--names-keep-optional]

--names-keep-optional : la lecture dit « سيدنا » devant chaque nom. Le
modèle reconnaît mal ce « سيدنا » chanté : laissé au score, il l'omettait,
et chaque nom s'allumait une à deux secondes trop tard, sur « سيدنا »
(Nourach, vérifié fenêtre par fenêtre avec Whisper, 2026-09-30). Le forcer
dans l'alignement du bloc déformait ses voisins et faisait tomber des noms.
Le placement reste donc celui d'avant ; une dernière étape cherche
« سيدنا » dans les secondes qui précèdent chaque nom placé, et la ligne
commence là (« سيدنا » devient son premier mot)."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ctc import Emissions

emf, textf, decf, candf, outf = sys.argv[1:6]
NAMES_KEEP = "--names-keep-optional" in sys.argv[6:]
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
    bord de l'enregistrement). Une ligne répétée peut bouger comme les
    autres : ses répétitions tombent avec l'ancienne place et sont
    recherchées de nouveau à la nouvelle (une fausse répétition l'avait
    figée sur l'audio de sa voisine, v309 de la Marrakchiya). Seule une
    ligne coupée par le bord reste fixe."""
    got = []; k = start
    while 0 <= k < n and len(got) <= K:
        if dec[k]["sung"]:
            if len(got) < K and dec[k].get("cut"): return None
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

# Une suite de lignes pareilles à un mot près — les 201 noms du Prophète ﷺ,
# chacun suivi de la même salutation — est alignée d'UN bloc, dans l'ordre,
# entre la ligne placée avant elle et celle placée après : cherchée ligne à
# ligne, la salutation commune trouvait 201 places presque égales, et un
# nom glissait sur l'audio de son voisin (Siham, 2026-09-29, Nourach).
# Chaque salutation doit alors prendre son tour ; seuls les noms décident.
# Les mots optionnels « (سيدنا) » : les deux lectures, pour tout le bloc.
k = 0
while k < n:
    if lines[k].get("type") != "prophet_name" or k in skip:
        k += 1; continue
    i0 = k
    while k + 1 < n and lines[k + 1].get("type") == "prophet_name" and k + 1 not in skip:
        k += 1
    i1 = k; k += 1
    la = next((m for m in range(i0 - 1, -1, -1) if dec[m]["sung"]), None)
    ra = next((m for m in range(i1 + 1, n) if dec[m]["sung"]), None)
    c0 = max(0, (dec[la]["passes"][-1]["t1"] - EDGE) // 20) if la is not None else 0
    c1 = min(E.frames, (dec[ra]["passes"][0]["t0"] + EDGE) // 20) if ra is not None else E.frames
    block = list(range(i0, i1 + 1))
    best = None
    for keep in (True, False):
        r = E.align_run(E.EM[c0:c1], [(lines[m]["text"], keep) for m in block])
        if r is None: continue
        tot = sum((x[0] if x else -5.0) for x in r)
        if best is None or tot > best[0]: best = (tot, r, keep)
    if best is None:
        print(f"noms v{i0 + 1:03d}–v{i1 + 1:03d} : trou trop court", flush=True); continue
    _, r, keep = best
    ok = 0
    for m, x in zip(block, r):
        if x is None or x[0] < JOINT:
            dec[m] = {"i": m, "id": dec[m]["id"], "sung": False, "passes": []}; continue
        adv, f0, f1, mine, ws = x
        dec[m] = {"i": m, "id": dec[m]["id"], "sung": True, "filled": True, "joint": True,
                  "optional_sung": keep if "(" in lines[m]["text"] else None,
                  "passes": [E.to_find(c0, (adv, f0, f1, mine), ws)]}
        touched.add(m); ok += 1
    print(f"noms v{i0 + 1:03d}–v{i1 + 1:03d} alignés d'un bloc : {ok}/{len(block)} "
          f"({(c0 * 20) / 60000:.1f}–{(c1 * 20) / 60000:.1f} min, « سيدنا » {'lu' if keep else 'omis'})", flush=True)

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

# « (سيدنا) » devant les noms, quand la lecture le dit (voir en tête) : le
# nom reste où il est ; la ligne recule jusqu'au début de « سيدنا », cherché
# entre la fin de la ligne d'avant (au plus 3 s plus tôt) et le nom
if NAMES_KEEP:
    got = refit = miss = 0
    last = None                                   # la dernière ligne placée avant k
    for k in range(n):
        if not dec[k]["sung"]: continue
        opt = [w.strip("()") for w in lines[k]["text"].split() if w.startswith("(")]
        p = dec[k]["passes"][0]; ws = p.get("words") or []
        if lines[k].get("type") == "prophet_name" and opt and ws and ws[0][0] != opt[0]:
            name, n0, n1 = ws[0]
            a0 = (n0 - 3000) // 20; b0 = n1 // 20
            toks, owner, tw = E.tokens_of(f"({opt[0]}) {name}", True)
            rr = E.search(E.EM[a0:b0], toks, owner, len(tw))
            f = E.to_find(a0, rr, tw) if rr else None
            ok = f is not None and abs(f["words"][1][1] - n0) <= 400 and f["words"][0][2] <= n0 + 200
            if ok and last is not None:
                pp = dec[last]["passes"][-1]
                s0 = f["words"][0][1]
                if s0 < pp["t1"]:
                    # la fin de la ligne d'avant s'était étirée sur ce « سيدنا » :
                    # elle est réalignée seule, de son début jusqu'à lui
                    pre = bool(pp["words"]) and pp["words"][0][0] == opt[0]
                    lt, lo, lw = E.tokens_of(lines[last]["text"], True if pre else keep_of(last))
                    lo0 = max(0, pp["t0"] // 20 - 5)
                    r2 = E.search(E.EM[lo0:s0 // 20], lt, lo, len(lw)) if s0 // 20 - lo0 > 10 else None
                    # sans perdre plus de 0.5, ni passer sous le seuil de
                    # vérification de l'export (-1.2) si elle était au-dessus
                    if r2 and r2[0] >= pp["adv"] - 0.5 and (r2[0] >= -1.2 or pp["adv"] < -1.2):
                        dec[last]["passes"][-1] = E.to_find(lo0, r2, lw); refit += 1
                    else:
                        # la ligne d'avant reste : « سيدنا » cherché après elle
                        a1 = max(pp["t1"], n0 - 3000) // 20
                        r3 = E.search(E.EM[a1:b0], toks, owner, len(tw)) if b0 - a1 > 10 else None
                        f = E.to_find(a1, r3, tw) if r3 else None
                        ok = f is not None and abs(f["words"][1][1] - n0) <= 400 and f["words"][0][2] <= n0 + 200
            if ok:
                p["words"] = [[opt[0], f["words"][0][1], min(f["words"][0][2], n0)]] + ws
                p["t0"] = f["words"][0][1]; got += 1
            else:
                miss += 1
        last = k
    print(f"« سيدنا » placé devant {got} noms, dont {refit} en réalignant la fin du nom d'avant "
          f"({miss} laissés tels quels)", flush=True)

json.dump(dec, open(outf, "w"), ensure_ascii=False)
filled = sum(bool(d.get("filled")) and d["sung"] for d in dec)
print(f"{filled} lignes retrouvées par la seconde passe, {sum(bool(d.get('moved')) and d['sung'] for d in dec)} "
      f"voisines déplacées, {len(dropped)} retirées ; {sum(not d['sung'] for d in dec)} restent non chantées")
