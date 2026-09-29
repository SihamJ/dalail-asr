#!/usr/bin/env python3
"""Le texte d'un enregistrement, tel que l'application Dalail l'exporte
(sections → segments, JSON), devient le TEXTE.json du pipeline — sans
changer un mot : on lit le fichier, on ne l'écrit jamais.

    python new/app_json_to_text.py APP.json TEXTE.json
        [--not-chanted ID,ID…] [--not-chanted-sections ID,ID…]
        [--prior ETIQUETTES.txt]
        [--prior-from ANCIEN_words.json]

- Chaque segment garde son identifiant : les sorties (*_words.json) sont
  donc directement rattachées aux segments de l'application.
- Le segment « prophet_names » devient une ligne par nom (identifiant de
  l'item, ex. prophet_name_001), pour que chaque nom ait son temps. En
  mode « expanded » (chaque nom suivi de sa salutation), la salutation
  fait partie de la ligne ; en mode « grouped », le nom seul.
- Les segments de type « checkpoint » (نجز الربع الأول…), ceux passés
  dans --not-chanted et toute section passée dans --not-chanted-sections
  sont marqués « "chanted": false » : jamais cherchés. (La Marrakchiya
  ne récite pas l'introduction ni les noms : elle commence à la Fatiha
  du premier hizb.)
- --prior écrit des étiquettes a priori pour new/find_lines.py : depuis
  les temps que le fichier contient déjà (audio.start / audio.end), ou,
  avec --prior-from, depuis un alignement précédent du même
  enregistrement, ligne à ligne par le texte. Les lignes sans repère sont
  interpolées entre leurs voisines."""
import argparse, json, re

ap = argparse.ArgumentParser()
ap.add_argument("app"); ap.add_argument("out")
ap.add_argument("--not-chanted", default="")
ap.add_argument("--not-chanted-sections", default="")
ap.add_argument("--prior"); ap.add_argument("--prior-from")
a = ap.parse_args()

d = json.load(open(a.app, encoding="utf-8"))
mode = (d.get("_recitationExport") or {}).get("namesMode", "expanded")
skip = {x for x in a.not_chanted.split(",") if x}
skip_sec = {x for x in a.not_chanted_sections.split(",") if x}
lines, times = [], []
for sec in d["sections"]:
    for s in sorted(sec["segments"], key=lambda s: s.get("order", 0)):
        if s.get("type") == "prophet_names":
            for it in s["items"]:
                t = it["name"] if mode == "grouped" else f'{it["name"]} {it.get("salutation", "")}'.strip()
                ln = {"id": it["id"], "text": t, "type": "prophet_name", "section": sec.get("id")}
                if sec.get("id") in skip_sec:
                    ln["chanted"] = False
                lines.append(ln)
                st, en = it.get("audioStartMs"), it.get("audioEndMs")
                times.append((st / 1000, en / 1000) if st is not None and en is not None else None)
            continue
        text = s.get("text") or ""
        if not text.strip():
            continue
        ln = {"id": s["id"], "text": text, "type": s.get("type"), "section": sec.get("id")}
        if s.get("type") == "checkpoint" or s["id"] in skip or sec.get("id") in skip_sec:
            ln["chanted"] = False
        lines.append(ln)
        au = s.get("audio") if isinstance(s.get("audio"), dict) else None
        times.append((au["start"], au["end"]) if au and au.get("start") is not None and au.get("end") is not None else None)

unknown = skip - {l["id"] for l in lines}
assert not unknown, f"--not-chanted : identifiants absents du fichier : {sorted(unknown)}"
json.dump(lines, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{a.out}: {len(lines)} lignes ({sum(l.get('chanted') is False for l in lines)} non chantées, "
      f"noms en mode « {mode} »)")

if a.prior:
    if a.prior_from:
        # un alignement précédent du même enregistrement, apparié par le texte
        bare = lambda t: re.sub(r"[ً-ٰٟـ()\s]", "", t)
        old = {}
        for l in json.load(open(a.prior_from, encoding="utf-8"))["lines"]:
            if l["passes"]:
                old.setdefault(bare(l["text"]), (l["passes"][0]["t0"], l["passes"][-1]["t1"]))
        times = [old.get(bare(l["text"])) for l in lines]
    known = [i for i, t in enumerate(times) if t]
    assert known, "aucun repère : rien pour placer les lignes a priori"
    rows = []
    for i, t in enumerate(times):
        if t is None:  # entre les repères voisins, au prorata du rang
            p = max((k for k in known if k < i), default=None)
            n = min((k for k in known if k > i), default=None)
            a0 = times[p][1] if p is not None else 0.0
            b0 = times[n][0] if n is not None else times[known[-1]][1]
            lo, hi = (p if p is not None else -1), (n if n is not None else len(times))
            f0 = (i - lo) / (hi - lo); f1 = (i + 1 - lo) / (hi - lo)
            t = (a0 + (b0 - a0) * f0, a0 + (b0 - a0) * f1)
        rows.append(f"{t[0]:.2f}\t{t[1]:.2f}\t{lines[i]['id']}\n")
    open(a.prior, "w", encoding="utf-8").writelines(rows)
    print(f"{a.prior}: {len(known)} repères sur {len(lines)} lignes, le reste interpolé")
