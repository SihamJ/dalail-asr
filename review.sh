#!/bin/zsh
# Serve the alignment review tool and open it in the browser.
# The audio streams from R2, so the server only carries the HTML+JS.
cd "$(dirname "$0")"
PORT=8097
if ! lsof -ti :$PORT >/dev/null 2>&1; then
  # a server that answers byte ranges: a browser can only jump inside an
  # audio file served that way (python's http.server cannot)
  python3 new/rangeserve.py $PORT >/dev/null 2>&1 &
  sleep 0.5
fi
# a constant-bitrate copy of a recording, if one is here, replaces its
# audio: the original Nourach MP3 is variable-bitrate, and a browser jumping
# into it lands up to two minutes off (2026-09-30). audio-cbr/README.
Q=""
for f in audio-cbr/*.mp3(N); do
  n=$(basename "$f" .mp3); n=${n#dalail-}
  Q="$Q${Q:+&}$n=/audio-cbr/$(basename "$f")"
done
open "http://localhost:$PORT/review.html${Q:+?$Q}"
