#!/usr/bin/env python3
"""Étape 2 — où chaque ligne du texte est chantée, trouvé par le son.

Chaque ligne est alignée (alignement forcé CTC) contre un tronçon de
l'enregistrement autour de sa position a priori, avec un « joker » qui
absorbe tout le reste (autres lignes, interludes, silence) : ses lettres ne
se posent que là où elles sont chantées. On garde jusqu'à 5 emplacements
candidats par ligne ; l'étape 3 tranche pour tout le texte à la fois.

    python new/find_lines.py EM.pt TEXTE.json SORTIE.json [--prior LABELS.txt] [--window-min 15]

TEXTE.json : liste de {"id", "text"} dans l'ordre du livre.
--prior : un fichier d'étiquettes Audacity (une ligne par entrée du texte,
dans le même ordre) qui dit où chercher ; sans lui, la position a priori
est proportionnelle au nombre de mots, et il faut une fenêtre plus large.

Deux réglages comptent (voir le README) : le blanc CTC coûte BETA par
trame et le joker COST, avec COST < BETA < 4/3·COST. Un modèle CTC donne
le blanc à la plupart des trames ; laissé gratuit, il permettrait
d'égrener les lettres d'une ligne sur des minutes."""
import argparse, json, unicodedata
import torch, torchaudio.functional as F

ap = argparse.ArgumentParser()
ap.add_argument("em"); ap.add_argument("text"); ap.add_argument("out")
ap.add_argument("--prior"); ap.add_argument("--window-min", type=float, default=15)
ap.add_argument("--cost", type=float, default=1.0); ap.add_argument("--beta", type=float, default=1.2)
a = ap.parse_args()
dev = "cuda" if torch.cuda.is_available() else "cpu"
D = torch.load(a.em); em = D["em"].float(); vocab = D["vocab"]
blank = vocab.get("<pad>", 0); sep = vocab.get("|")
star = em.max(dim=1, keepdim=True).values - a.cost      # le joker : n'importe quel son
em = em.clone(); em[:, blank] -= a.beta
EM = torch.cat([em, star], 1).to(dev); STAR = em.shape[1]
FOLD = {"ٱ": "ا", "ـ": ""}

def letters(w):
    out = []
    for ch in unicodedata.normalize("NFC", w):
        if ch in vocab: out.append(ch)
        elif ch in FOLD and FOLD[ch] in vocab: out.append(FOLD[ch])
        elif unicodedata.normalize("NFD", ch)[0] in vocab: out.append(unicodedata.normalize("NFD", ch)[0])
    return out

def tokens_of(text, keep_optional):
    """Les lettres d'une ligne entre deux jokers ; les mots (entre
    parenthèses) sont gardés ou retirés ensemble."""
    toks, owner, words = [STAR], [None], []
    for raw in text.split():
        opt = raw.startswith("(") or raw.endswith(")")
        disp = raw.strip("()")
        if opt and not keep_optional: continue
        ls = letters(disp)
        if not ls: continue
        if len(toks) > 1: toks.append(sep); owner.append(None)
        for ch in ls: toks.append(vocab[ch]); owner.append(len(words))
        words.append(disp)
    toks.append(STAR); owner.append(None)
    return toks, owner, words

def search(em, toks, owner, nwords):
    ali, sc = F.forced_align(em.unsqueeze(0), torch.tensor([toks], device=dev), blank=blank)
    ali = ali[0].tolist()
    spans = {}; ti = -1; prev = None
    for f, lab in enumerate(ali):
        if lab != blank and lab != prev: ti += 1
        prev = lab
        if lab == blank or ti < 0 or owner[ti] is None: continue
        sp = spans.setdefault(owner[ti], [f, f]); sp[1] = f
    if len(spans) < nwords: return None
    f0 = min(v[0] for v in spans.values()); f1 = max(v[1] for v in spans.values()) + 1
    # score : combien les lettres collent mieux que le joker, par trame
    adv = (sc[0][f0:f1].sum().item() - em[f0:f1, STAR].sum().item()) / max(1, f1 - f0)
    return adv, f0, f1, spans

lines = json.load(open(a.text))
total_ms = EM.shape[0] * 20
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
    c0 = max(0, int(p0) // 20 - W); c1 = min(EM.shape[0], int(p1) // 20 + W)
    best = None
    has_opt = "(" in ln["text"]
    for keep in ([True, False] if has_opt else [True]):
        toks, owner, words = tokens_of(ln["text"], keep)
        if not words: continue
        r = search(EM[c0:c1], toks, owner, len(words))
        if r and (best is None or r[0] > best[0][0]): best = (r, toks, owner, words, keep)
    if best is None:
        res.append({"i": i, "id": ln.get("id"), "finds": []}); continue
    (adv, f0, f1, spans), toks, owner, words, keep = best
    finds = [(adv, f0, f1, spans)]
    em2 = EM[c0:c1].clone()
    for _ in range(4):                        # les emplacements suivants
        for (_, x0, x1, _) in finds: em2[x0:x1, :STAR] = -1e4
        r = search(em2, toks, owner, len(words))
        if not r or r[0] < adv - 1.0: break
        finds.append(r)
    out = [{"adv": round(f[0], 3), "t0": (c0 + f[1]) * 20, "t1": (c0 + f[2]) * 20,
            "words": [[w, (c0 + f[3][k][0]) * 20, (c0 + f[3][k][1] + 1) * 20] for k, w in enumerate(words)]}
           for f in sorted(finds, key=lambda f: f[1])]
    res.append({"i": i, "id": ln.get("id"), "optional_sung": keep if has_opt else None, "finds": out})
    print(f"{i + 1}/{len(lines)} {ln.get('id')}: {len(out)} candidats", flush=True)
json.dump(res, open(a.out, "w"), ensure_ascii=False)
