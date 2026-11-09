# -*- coding: utf-8 -*-
"""Rename 02_DOORS FBX to ASCII (Studio asset names) and patch manifests + scene_dump accordingly."""
import os, io, json, re
OUT = r"C:\Users\HSP\Desktop\blender\ovdr_export\hwaseong_v25"
MAP = {"옹성": "OS", "주문": "MG", "좌": "L", "우": "R"}
def ascii_name(n):
    for k, v in MAP.items():
        n = n.replace(k, v)
    return n
ren = {}
d = os.path.join(OUT, "02_DOORS")
for f in os.listdir(d):
    if f.endswith(".fbx") and re.search(r"[^\x00-\x7f]", f):
        new = ascii_name(f); os.replace(os.path.join(d, f), os.path.join(d, new)); ren["02_DOORS/" + f] = "02_DOORS/" + new
        ren[f[:-4]] = new[:-4]
for mf in ("manifest_v25_doors.json", "manifest_v25_stage3.json", "scene_dump.json"):
    p = os.path.join(OUT, mf)
    if not os.path.exists(p):
        continue
    s = io.open(p, encoding="utf-8").read()
    for a, b in ren.items():
        s = s.replace(a, b)
    io.open(p, "w", encoding="utf-8").write(s)
print("renamed", len([k for k in ren if k.endswith(".fbx")]), sorted(os.listdir(d)))
