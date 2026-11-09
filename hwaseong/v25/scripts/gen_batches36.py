# -*- coding: utf-8 -*-
"""Flatten all FBX into one folder (_import_all) and write 36-unit batches as Windows file-dialog lines:
"A.fbx" "B.fbx" ...   (units = material count for masters, 1 otherwise)."""
import os, io, json, shutil
OUT = r"C:\Users\HSP\Desktop\blender\ovdr_export\hwaseong_v25"
FLAT = os.path.join(OUT, "_import_all"); os.makedirs(FLAT, exist_ok=True)
dump = json.load(io.open(os.path.join(OUT, "scene_dump.json"), encoding="utf-8"))
units = {os.path.basename(m["file"]): m.get("materials", 1) for m in dump["masters"].values()}
order = [("03_TERRAIN", ["HWS_TER_11"]), ("10_MASTERS", ["HWS_NH_WALL", "HWS_NH_PARAPET"]), ("10_MASTERS", None), ("02_DOORS", None), ("03_TERRAIN", None), ("01_JAM", None)]
files, seen = [], set()
for d, only in order:
    for f in sorted(os.listdir(os.path.join(OUT, d))):
        if not f.endswith(".fbx") or (only and f[:-4] not in only) or f in seen:
            continue
        seen.add(f); files.append(f); shutil.copy2(os.path.join(OUT, d, f), os.path.join(FLAT, f))
probe, rest = files[:3], files[3:]
batches, cur, u = [probe], [], 0
for f in rest:
    w = units.get(f, 1)
    if cur and u + w > 36:
        batches.append(cur); cur, u = [], 0
    cur.append(f); u += w
if cur:
    batches.append(cur)
lines = ["# 화성 v25 임포트 — 폴더: " + FLAT, "# 파일 대화상자 이름칸에 한 줄을 통째로 붙여 넣는다. 세션 사이 저장→Studio 재시작.", ""]
for i, b in enumerate(batches):
    lines.append("## 배치 %d (%d 파일 / %d 유닛)" % (i, len(b), sum(units.get(f, 1) for f in b)))
    lines.append(" ".join('"%s"' % f for f in b)); lines.append("")
io.open(os.path.join(OUT, "IMPORT_BATCHES_hws_36.txt"), "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines))
