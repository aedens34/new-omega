#!/usr/bin/env python3
"""Zip the gunpack folder into dist/omega_guns_gunpack.zip (gunpack.meta.json at the zip root, as TACZ requires)."""
import os, zipfile
here = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(here, "..", "src", "main", "resources", "assets", "tacz", "custom", "omega_guns")
dist = os.path.join(here, "..", "dist")
os.makedirs(dist, exist_ok=True)
out = os.path.join(dist, "omega_guns_gunpack.zip")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(src):
        for f in sorted(files):
            p = os.path.join(root, f)
            z.write(p, os.path.relpath(p, src).replace(os.sep, "/"))
print("Built", os.path.abspath(out))
