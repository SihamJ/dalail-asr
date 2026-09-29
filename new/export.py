#!/usr/bin/env python3
"""Étape 4 — les livrables, au même format que l'ancien pipeline, plus le
niveau du mot.

    python new/export.py NOM TEXTE.json DECISION.json

écrit, à la racine du dépôt :
  NOM_labels.txt       une étiquette Audacity par ligne (même format
                       qu'avant : début, fin, [REVIEW ]vNNN, 40 caractères) ;
                       une ligne chantée deux fois a deux étiquettes
  NOM_word_labels.txt  une étiquette Audacity par mot : vNNN.MM (vNNNp2.MM
                       pour le 2e passage d'une ligne répétée)
  NOM_words.json       tout, en secondes, pour une application
et reconstruit review_data.js (la page de vérification) à partir des
recordings déjà exportés."""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
name, textf, decf = sys.argv[1:4]
lines = json.load(open(textf)); dec = json.load(open(decf))
assert len(lines) == len(dec)
WEAK = -1.2    # en dessous, un emplacement est gardé mais marqué REVIEW

rows = []
for ln, d in zip(lines, dec):
    text = ln["text"].replace("\n", " ")
    if d["sung"]:
        ps = d["passes"]
        rows.append({"t0": ps[0]["t0"] / 1000, "t1": ps[-1]["t1"] / 1000, "text": text,
                     "review": ps[0]["adv"] < WEAK, "passes": ps, "sung": True})
    else:
        rows.append({"t0": None, "t1": None, "text": text, "review": True, "passes": [], "sung": False})
for i, r in enumerate(rows):          # les lignes non chantées : un intervalle interpolé
    if r["t0"] is None:
        prev = next((x for x in reversed(rows[:i]) if x["t1"] is not None), None)
        nxt = next((x for x in rows[i + 1:] if x["t0"] is not None), None)
        r["t0"] = prev["t1"] if prev else 0.0
        r["t1"] = nxt["t0"] if nxt else r["t0"]

with open(ROOT / f"{name}_labels.txt", "w") as f:
    for vi, r in enumerate(rows):
        flag = "REVIEW " if r["review"] else ""
        spans = [(p["t0"] / 1000, p["t1"] / 1000) for p in r["passes"]] or [(r["t0"], r["t1"])]
        for t0, t1 in spans:
            f.write(f"{t0:.2f}\t{t1:.2f}\t{flag}v{vi + 1:03d} {r['text'][:40]}\n")

with open(ROOT / f"{name}_word_labels.txt", "w") as f:
    for vi, r in enumerate(rows):
        for pi, p in enumerate(r["passes"]):
            tag = f"v{vi + 1:03d}" + (f"p{pi + 1}" if pi else "")
            for wi, (w, t0, t1) in enumerate(p["words"]):
                f.write(f"{t0 / 1000:.2f}\t{t1 / 1000:.2f}\t{tag}.{wi + 1:02d} {w}\n")

out = []
for vi, (ln, r, d) in enumerate(zip(lines, rows, dec)):
    out.append({"v": vi + 1, "id": ln.get("id"), "text": ln["text"], "sung": r["sung"],
                "review": r["review"], "optional_sung": d.get("optional_sung"),
                "passes": [{"t0": round(p["t0"] / 1000, 2), "t1": round(p["t1"] / 1000, 2),
                            "score": p["adv"],
                            "words": [{"w": w, "t0": round(t0 / 1000, 2), "t1": round(t1 / 1000, 2)}
                                      for w, t0, t1 in p["words"]]} for p in r["passes"]]})
json.dump({"recording": name, "model": "rabah2026/wav2vec2-large-xlsr-53-arabic-quran-v_final",
           "units": "secondes", "lines": out}, open(ROOT / f"{name}_words.json", "w"),
          ensure_ascii=False, indent=1)

# review_data.js : une ligne par vers/segment, comme l'ancienne page l'attend
META = {"hamzia": ("الهمزية — فحص المحاذاة", "hamzia.mp3"),
        "dalail": ("دلائل الخيرات (المراكشية) — فحص المحاذاة", "dalail-marrakchiya.mp3")}
R2 = "https://pub-399f14501bad46a28b40e12c0215d805.r2.dev/"
data = {}
for key, (title, mp3) in META.items():
    p = ROOT / f"{key}_words.json"
    if not p.exists(): continue
    ws = json.load(open(p))["lines"]
    tl = {x["v"]: x for x in ws}
    lab = [l.split("\t") for l in open(ROOT / f"{key}_labels.txt", encoding="utf-8")]
    first = {}
    for t0, t1, rest in lab:
        v = int(rest.replace("REVIEW ", "")[1:4])
        first.setdefault(v, [float(t0), float(t1)]); first[v][1] = float(t1)
    data[key] = {"title": title, "audio": R2 + mp3,
                 "rows": [{"t0": first[x["v"]][0], "t1": first[x["v"]][1], "review": x["review"],
                           "label": f"v{x['v']:03d} — " + x["text"].replace("\n", " ⁘ ")} for x in ws]}
(ROOT / "review_data.js").write_text("const DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")
n_sung = sum(r["sung"] for r in rows); n_rep = sum(len(r["passes"]) > 1 for r in rows)
print(f"{name}: {n_sung}/{len(rows)} lignes chantées, {n_rep} répétées, "
      f"{sum(r['review'] for r in rows)} REVIEW → {name}_labels.txt, {name}_word_labels.txt, {name}_words.json")
