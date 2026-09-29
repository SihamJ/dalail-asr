#!/bin/zsh
# Servir et ouvrir la page de vérification au niveau du mot (l'audio vient de R2).
cd "$(dirname "$0")"
PORT=8532
if ! lsof -ti :$PORT >/dev/null 2>&1; then
  python3 -m http.server $PORT >/dev/null 2>&1 &
  sleep 0.5
fi
open "http://localhost:$PORT/word_review.html"
