#!/usr/bin/env python3
"""Pull dalail-al-khayrat's ordered segments from the app's JSON."""
import json
import pathlib
from collections import Counter

S = pathlib.Path(__file__).parent
src = S / "dalail/base/assets/flutter_assets/assets/data/texts/dalail-al-khayrat.json"
d = json.loads(src.read_text())

segs = []
for sec in d["sections"]:
    for sg in sec["segments"]:
        t = sg.get("text") or ""
        if t.strip():
            segs.append({"id": sg.get("id"), "type": sg.get("type"),
                         "section": sec.get("title"), "text": t})

out = S / "dalail_segments.json"
out.write_text(json.dumps(segs, ensure_ascii=False, indent=1))
print("segments:", len(segs), Counter(s["type"] for s in segs))
lens = sorted(len(s["text"].split()) for s in segs)
print(f"words/segment: median {lens[len(lens)//2]}, max {lens[-1]}")
for s in segs[:3]:
    print("  ", (s["type"] or "?")[:8], s["text"][:60].replace("\n", " "))
