#!/bin/bash
# Le nouveau pipeline, d'un bout à l'autre, pour un enregistrement.
#   new/run.sh NOM AUDIO.mp3 TEXTE.json [ETIQUETTES_A_PRIORI.txt]
# ex. new/run.sh hamzia hamzia.mp3 hamzia_verses.json old/hamzia_labels.txt
set -euo pipefail
NAME=$1
abs() { python3 -c 'import os,sys; print(os.path.abspath(sys.argv[1]))' "$1"; }
AUDIO=$(abs "$2"); TEXT=$(abs "$3"); PRIOR=${4:+$(abs "$4")}
# pages de vérification : TITLE=… et AUDIO_URL=… en variables d'environnement
# (défaut : le nom ; l'audio est lu à la racine du dépôt, sous le nom du fichier)
cd "$(dirname "$0")/.."
mkdir -p new/work
python new/emit.py "$AUDIO" "new/work/$NAME.pt"
if [ -n "$PRIOR" ]; then
  python new/find_lines.py "new/work/$NAME.pt" "$TEXT" "new/work/${NAME}_candidates.json" --prior "$PRIOR"
else
  python new/find_lines.py "new/work/$NAME.pt" "$TEXT" "new/work/${NAME}_candidates.json" --window-min 40
fi
python new/decide.py "new/work/${NAME}_candidates.json" "new/work/${NAME}_decision.json"
python new/fill_gaps.py "new/work/$NAME.pt" "$TEXT" "new/work/${NAME}_decision.json" "new/work/${NAME}_final.json"
python new/export.py "$NAME" "$TEXT" "new/work/${NAME}_final.json" --audio-file "$(basename "$AUDIO")" ${TITLE:+--title "$TITLE"} ${AUDIO_URL:+--audio-url "$AUDIO_URL"}
