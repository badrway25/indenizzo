"""One-shot script to fix Windows backslashes in pexels manifest local_path."""

import json
from pathlib import Path

p = Path("media/pexels/pexels_manifest.json")
m = json.load(p.open(encoding="utf-8"))
changed = 0
for _k, e in m.items():
    if "\\" in e.get("local_path", ""):
        e["local_path"] = e["local_path"].replace("\\", "/")
        changed += 1
json.dump(m, p.open("w", encoding="utf-8"), indent=2, ensure_ascii=False, sort_keys=True)
print(f"fixed {changed} entries")
