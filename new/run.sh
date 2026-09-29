#!/bin/bash
# Le nouveau pipeline, d'un bout à l'autre, pour un enregistrement.
#   new/run.sh NOM AUDIO.mp3 TEXTE.json [ETIQUETTES_A_PRIORI.txt]
# ex. new/run.sh hamzia hamzia.mp3 hamzia_verses.json old/hamzia_labels.txt
set -euo pipefail
NAME=$1; AUDIO=$2; TEXT=$3; PRIOR=${4:-}
cd "$(dirname "$0")/.."
mkdir -p new/work
python new/emit.py "$AUDIO" "new/work/$NAME.pt"
if [ -n "$PRIOR" ]; then
  python new/find_lines.py "new/work/$NAME.pt" "$TEXT" "new/work/${NAME}_candidates.json" --prior "$PRIOR"
else
  python new/find_lines.py "new/work/$NAME.pt" "$TEXT" "new/work/${NAME}_candidates.json" --window-min 40
fi
python new/decide.py "new/work/${NAME}_candidates.json" "new/work/${NAME}_decision.json"
python new/export.py "$NAME" "$TEXT" "new/work/${NAME}_decision.json"
