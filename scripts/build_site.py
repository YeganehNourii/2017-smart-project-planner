#!/usr/bin/env python3
"""Copies the Python core and the sample project into site/py/ and writes a
manifest, so the static page can load them into Pyodide.

Usage: python scripts/build_site.py   (then serve site/ with any web server)
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "py"

if OUT.exists():
    shutil.rmtree(OUT)
(OUT / "planner").mkdir(parents=True)
(OUT / "samples").mkdir()

files = []
for src in sorted((ROOT / "planner").glob("*.py")):
    if src.name in ("cli.py", "__main__.py", "storage.py"):
        continue  # not needed in the browser
    shutil.copy2(src, OUT / "planner" / src.name)
    files.append(f"planner/{src.name}")
for src in sorted((ROOT / "samples").glob("*.json")):
    shutil.copy2(src, OUT / "samples" / src.name)

(OUT / "manifest.json").write_text(json.dumps({"python": files}, indent=2) + "\n")
print(f"Copied {len(files)} Python files to {OUT.relative_to(ROOT)}")
