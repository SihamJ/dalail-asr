#!/usr/bin/env python3
"""Préparer le texte d'un nouvel enregistrement : un fichier texte brut,
une ligne (ou un vers) par rangée, dans l'ordre où il est chanté, devient
le TEXTE.json que le pipeline attend.

    python new/text_from_txt.py NOM texte.txt NOM_text.json

Les rangées vides sont ignorées. Un vers en deux hémistiches peut s'écrire
sur une rangée, les deux moitiés séparées par « * » : elles seront gardées
ensemble (comme dans hamzia_verses.json). Mettez entre parenthèses les mots
que le munshid peut omettre — (سيدنا) — le pipeline essaie avec et sans."""
import json, sys
name, src, out = sys.argv[1:4]
rows = [r.strip() for r in open(src, encoding="utf-8") if r.strip()]
data = [{"id": f"{name}_{i + 1:03d}", "text": r.replace(" * ", "\n").replace("*", "\n")} for i, r in enumerate(rows)]
json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{out}: {len(data)} lignes")
