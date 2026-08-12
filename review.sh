#!/bin/zsh
# Serve the alignment review tool and open it in the browser.
# The audio streams from R2, so the server only carries the HTML+JS.
cd "$(dirname "$0")"
PORT=8097
if ! lsof -ti :$PORT >/dev/null 2>&1; then
  python3 -m http.server $PORT >/dev/null 2>&1 &
  sleep 0.5
fi
open "http://localhost:$PORT/review.html"
