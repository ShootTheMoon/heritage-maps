# -*- coding: utf-8 -*-
"""ovdr_export/hwaseong_v25 -> IMPORT_BATCHES_hws.md + import_batches.json (<=12 files per Studio session)."""
import os, io, json
OUT = r"C:\Users\HSP\Desktop\blender\ovdr_export\hwaseong_v25"
order = [("03_TERRAIN", ["HWS_TER_11"]), ("10_MASTERS", ["HWS_NH_WALL", "HWS_NH_PARAPET"]), ("10_MASTERS", None), ("02_DOORS", None), ("03_TERRAIN", None), ("01_JAM", None)]
tris = {}
for mf in ("manifest_v25_jam.json", "manifest_v25_doors.json", "manifest_v25_terrain.json", "manifest_v25_stage3.json"):
    p = os.path.join(OUT, mf)
    if os.path.exists(p):
        for f in json.load(io.open(p, encoding="utf-8"))["files"]:
            tris[f["file"]] = f["tris"]
files, seen = [], set()
for d, only in order:
    for f in sorted(os.listdir(os.path.join(OUT, d))):
        stem = f[:-4]
        if not f.endswith(".fbx") or (only and stem not in only) or stem in seen:
            continue
        seen.add(stem); files.append(d + "/" + f)
batches = [files[:3]] + [files[3 + i:3 + i + 12] for i in range(0, len(files) - 3, 12)]
lines = ["# 화성 v25 Studio 벌크 임포트 순서 (세션당 ≤12 파일, 세션 사이 저장→Studio 재시작, 재임포트 금지)", "",
         "배치 0 = 프로브 3개(지형 타일 1 · 담장 마스터 1 · 여장 1). 배치 후 `-Resolve` 성 확인은 `python hws_place.py <UGCLocalAssetTable.json>` 의 UNRESOLVED 수로 본다.",
         "식생 848개는 산곡 MST_* 에셋 재사용 — 임포트 금지.", ""]
for i, b in enumerate(batches):
    lines.append("## 배치 %d (%d 파일)" % (i, len(b)))
    lines += ["- [ ] `%s`  tris %s" % (x.replace("/", "\\"), tris.get(x, "?")) for x in b]
    lines.append("")
io.open(os.path.join(OUT, "IMPORT_BATCHES_hws.md"), "w", encoding="utf-8").write("\n".join(lines))
json.dump(batches, io.open(os.path.join(OUT, "import_batches.json"), "w", encoding="utf-8"), indent=1)
print("files", len(files), "batches", len(batches))
for i, b in enumerate(batches[:2]):
    print("batch", i, b)
