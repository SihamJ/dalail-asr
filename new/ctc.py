"""Le cœur commun aux deux passes de recherche : les probabilités de
l'étape 1 rechargées avec le joker et le coût du blanc, et la recherche
d'une ligne (alignement forcé CTC entre deux jokers) dans un tronçon.

Le blanc coûte BETA par trame et le joker COST, avec COST < BETA < 4/3·COST :
un modèle CTC donne le blanc à la plupart des trames, même en pleine
parole ; gratuit, il permettrait d'égrener les lettres d'une ligne sur des
minutes. Le joker (« n'importe quel son ») absorbe ce qui n'est pas la
ligne : autres lignes, interludes, silence."""
import unicodedata
import torch, torchaudio.functional as F

FOLD = {"ٱ": "ا", "ـ": ""}


class Emissions:
    def __init__(self, path, cost=1.0, beta=1.2):
        self.dev = "cuda" if torch.cuda.is_available() else "cpu"
        D = torch.load(path)
        em = D["em"].float(); self.vocab = D["vocab"]
        self.blank = self.vocab.get("<pad>", 0); self.sep = self.vocab.get("|")
        star = em.max(dim=1, keepdim=True).values - cost
        em = em.clone(); em[:, self.blank] -= beta
        self.EM = torch.cat([em, star], 1).to(self.dev); self.STAR = em.shape[1]
        self.frames = self.EM.shape[0]

    def letters(self, w):
        v = self.vocab; out = []
        for ch in unicodedata.normalize("NFC", w):
            if ch in v: out.append(ch)
            elif ch in FOLD and FOLD[ch] in v: out.append(FOLD[ch])
            elif unicodedata.normalize("NFD", ch)[0] in v: out.append(unicodedata.normalize("NFD", ch)[0])
        return out

    def tokens_of(self, text, keep_optional):
        """Les lettres d'une ligne entre deux jokers ; les mots (entre
        parenthèses) sont gardés ou retirés ensemble."""
        toks, owner, words = [self.STAR], [None], []
        for raw in text.split():
            opt = raw.startswith("(") or raw.endswith(")")
            disp = raw.strip("()")
            if opt and not keep_optional: continue
            ls = self.letters(disp)
            if not ls: continue
            if len(toks) > 1: toks.append(self.sep); owner.append(None)
            for ch in ls: toks.append(self.vocab[ch]); owner.append(len(words))
            words.append(disp)
        toks.append(self.STAR); owner.append(None)
        return toks, owner, words

    def search(self, em, toks, owner, nwords):
        """La ligne dans le tronçon em : (score, première trame, fin, mots)."""
        if len(toks) * 2 > em.shape[0]: return None
        ali, sc = F.forced_align(em.unsqueeze(0), torch.tensor([toks], device=self.dev), blank=self.blank)
        ali = ali[0].tolist()
        spans = {}; ti = -1; prev = None
        for f, lab in enumerate(ali):
            if lab != self.blank and lab != prev: ti += 1
            prev = lab
            if lab == self.blank or ti < 0 or owner[ti] is None: continue
            sp = spans.setdefault(owner[ti], [f, f]); sp[1] = f
        if len(spans) < nwords: return None
        f0 = min(v[0] for v in spans.values()); f1 = max(v[1] for v in spans.values()) + 1
        # le score : combien les lettres collent mieux que le joker, par trame
        adv = (sc[0][f0:f1].sum().item() - em[f0:f1, self.STAR].sum().item()) / max(1, f1 - f0)
        return adv, f0, f1, spans

    def best_reading(self, em, text):
        """La ligne cherchée avec et sans ses mots optionnels ; la meilleure."""
        best = None
        has_opt = "(" in text
        for keep in ([True, False] if has_opt else [True]):
            toks, owner, words = self.tokens_of(text, keep)
            if not words: continue
            r = self.search(em, toks, owner, len(words))
            if r and (best is None or r[0] > best[0][0]): best = (r, toks, owner, words, keep)
        return best, has_opt

    def to_find(self, c0, f, words):
        """Un emplacement en millisecondes absolues."""
        adv, f0, f1, spans = f
        return {"adv": round(adv, 3), "t0": (c0 + f0) * 20, "t1": (c0 + f1) * 20,
                "words": [[w, (c0 + spans[k][0]) * 20, (c0 + spans[k][1] + 1) * 20] for k, w in enumerate(words)]}
