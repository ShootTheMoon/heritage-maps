# -*- coding: utf-8 -*-
r"""
sgk_placements.py — placements.csv + Studio 배치 itemsFile 생성 (bpy 없음).

  python sgk_placements.py csv                       # placements_master.json + manifest → 06_OVERDARE\placements.csv
  python sgk_placements.py ids <UGCLocalAssetTable.json>   # (임포트 후) 이름→ID → asset_ids.json  (테이블은 UTF-16!)
  python sgk_placements.py items                     # asset_ids.json → _place\place_NNN.json (200/청크) + items_static.json

좌표: X = x·100 + ENGINE_X0, Y = z·100, Z = −y·100 ; yaw(엔진 Y회전) = +rot_z(deg)  [L.to_engine / L.eng_yaw]
MeshPart position = **bbox 중심**, size = bbox 치수(cm, 절대) — Shibuya 파이프라인에서 검증된 방식 (스케일 프로브로 재확인).
"""
import os, sys, json, csv, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sgk_layout as L
ROOT = os.path.dirname(HERE); OVD = os.path.join(ROOT, "06_OVERDARE"); DOC = os.path.join(ROOT, "05_Documentation")
PLACE = os.path.join(OVD, "_place"); os.makedirs(PLACE, exist_ok=True)
BATCH = 200
NEG_CENTER_FIX = False   # 오진이었다(2026-09-06 밤). 산벽 "커튼"의 진짜 원인은 Studio 의 메시 180° 회전(MESH_YAW_FIX) + Z=+y 거울상 배치. 켜지 말 것
STATIC_ORIENT = {}
STATIC_DY = {}   # 정적 이름 → 엔진 Y 추가 보정(cm). 아래 NEG_CENTER_FIX 가 자동 처리하므로 보통 비워 둔다
MESH_YAW_FIX = 180.0   # Studio 39.1 은 임포트 메시 내용을 Y축 180° 돌려 그린다 (허공 타일 12 + 축 큐브 실측 2026-09-06: FBX 원본 대비 X·Z 반전). 모든 MeshPart yaw 에 더해 상쇄
TILE_YAW_DEG = 0.0   # (실험용) 지형 타일 추가 회전. 보통 0

def manifest(): return json.load(open(os.path.join(OVD, "manifest.json"), encoding="utf-8"))

def build_csv():
    man = manifest(); pm = json.load(open(os.path.join(DOC, "placements_master.json"), encoding="utf-8"))
    rows = []; missing = set()
    for r in pm["instances"]:
        m = man.get(r["master"])
        if not m: missing.add(r["master"]); continue
        lo, hi = m["bbox_min"], m["bbox_max"]; s = r["scale"]
        # 마스터 로컬 bbox (바닥중심 피벗) → 회전 후 월드 중심. yaw 회전은 x/y 중심 오프셋에만 영향 (피벗이 x/y 중심이라 0 에 가깝다)
        cx_l, cy_l, cz_l = (lo[0] + hi[0]) / 2 * s, (lo[1] + hi[1]) / 2 * s, (lo[2] + hi[2]) / 2 * s
        th = math.radians(r["yaw"]); cx = r["x"] + cx_l * math.cos(th) - cy_l * math.sin(th); cy = r["y"] + cx_l * math.sin(th) + cy_l * math.cos(th)
        cz = r["z"] + cz_l
        size = [(hi[i] - lo[i]) * s * 100 for i in range(3)]
        EX, EY, EZ = L.to_engine(cx, cy, cz)   # 맵 회전(L.MAP_YAW_DEG) 포함
        rows.append({"master": r["master"], "name": r["name"], "X": round(EX, 1), "Y": round(EY, 1), "Z": round(EZ, 1),
                     "pitch": 0.0, "yaw": L.eng_yaw(r["yaw"] + MESH_YAW_FIX), "roll": 0.0, "sx": s, "sy": s, "sz": s,
                     "sizeX": round(size[0], 1), "sizeY": round(size[2], 1), "sizeZ": round(size[1], 1)})
    p = os.path.join(OVD, "placements.csv")
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"placements.csv {len(rows)} rows; masters missing in manifest: {sorted(missing)}")
    return rows

def refresh_ids(table_path):
    raw = open(table_path, "rb").read()
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8")
    d = json.loads(text).get("localAssetList", {})
    mesh, tex = {}, {}
    for k, v in d.items():
        t, n = v.get("worldAssetType"), v.get("name", "")
        if t == "STATIC_MESH": mesh[n] = k
        elif t == "TEXTURE": tex[n] = k
    man = manifest(); out = {}; miss = []
    for name, rec in man.items():
        mesh_name = rec.get("asset_alias", {}).get("mesh", name); tex_name = rec.get("asset_alias", {}).get("tex", rec["mats"][0] if rec["mats"] else None)
        mid = mesh.get(mesh_name); tid = tex.get(tex_name)
        if not mid or not tid: miss.append((name, bool(mid), bool(tid))); continue
        out[name] = {"meshId": mid, "textureId": tid}
    json.dump(out, open(os.path.join(OVD, "asset_ids.json"), "w", encoding="utf-8"), indent=1)
    print(f"asset_ids.json {len(out)} resolved; missing: {miss}")
    return out

def _static_pos(name, lo, hi):
    """월드좌표 정적 메시의 MeshPart 위치(cm) = bbox 중심 (Studio 는 CFrame 에 메시 bbox 중심을 놓는다 — 허공 프로브+눈금 큐브로 확인).
    NEG_CENTER_FIX 는 거울상 배치 시절의 오진용 보정. 끄고 둔다."""
    ex, ey, ez = L.to_engine((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2)
    if NEG_CENTER_FIX and ey < 0: ey = 3.0 * ey
    ey += STATIC_DY.get(name, 0.0)
    return [round(ex, 1), round(ey, 1), round(ez, 1)]

def build_items():
    ids = json.load(open(os.path.join(OVD, "asset_ids.json"), encoding="utf-8-sig")); man = manifest()   # utf-8-sig: PowerShell 이 BOM 을 붙일 수 있다
    rows = list(csv.DictReader(open(os.path.join(OVD, "placements.csv"), encoding="utf-8")))
    for f in os.listdir(PLACE):
        if f.startswith("place_"): os.remove(os.path.join(PLACE, f))
    items = []; missing = set()
    for r in rows:
        a = ids.get(r["master"])
        if not a: missing.add(r["master"]); continue
        s = float(r["sx"]) or 1.0
        items.append({"className": "MeshPart", "name": r["name"], "props": {
            "meshId": a["meshId"], "position": [float(r["X"]), float(r["Y"]), float(r["Z"])], "orientation": [0.0, float(r["yaw"]), 0.0],
            "size": [float(r["sizeX"]), float(r["sizeY"]), float(r["sizeZ"])],
            # UnitExtent = 메시 원본 bbox 반폭(스케일 전). 자리표시자 ±50 으로 넣으면 Studio 가 Size/100 을 배율로 잡아 메시 로드 후에도 유지 → 40 m 타일이 1.6 km 로 보였다 (2026-09-06 실측)
            "unit": [round(float(r["sizeX"]) / s / 2, 3), round(float(r["sizeY"]) / s / 2, 3), round(-float(r["sizeZ"]) / s / 2, 3)],
            "anchored": True, "mobility": "Static",
            "castShadow": not r["name"].startswith("SGK_Und"), "canCollide": False, "canQuery": False,
            "raw": {"TextureId": a["textureId"], "DoubleSided": any(k in r["master"] for k in ("PINE", "SAPLING", "FERN", "EULALIA", "ARTEMISIA"))}}})   # 식생 잎 카드는 양면 (산옥과 동일)
    n = 0
    for i in range(0, len(items), BATCH):
        json.dump(items[i:i + BATCH], open(os.path.join(PLACE, f"place_{n:03d}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0); n += 1
    # 정적: 월드좌표 bbox 중심
    statics = []
    for name, rec in man.items():
        if rec["kind"] != "static": continue
        a = ids.get(name)
        if not a: missing.add(name); continue
        lo, hi = rec["bbox_min"], rec["bbox_max"]
        statics.append({"className": "MeshPart", "name": name, "props": {
            "meshId": a["meshId"], "position": _static_pos(name, lo, hi),
            "orientation": list(STATIC_ORIENT.get(name, [0.0, L.eng_yaw(MESH_YAW_FIX + (TILE_YAW_DEG if name.startswith("STA_TER_") else 0.0)), 0.0])),   # 지형 타일은 각자 bbox 중심 기준 자체 회전 (2026-09-06 사용자 요청 "바닥 하나당 180도")
            "size": [round((hi[0] - lo[0]) * 100, 1), round((hi[2] - lo[2]) * 100, 1), round((hi[1] - lo[1]) * 100, 1)],
            "unit": [round((hi[0] - lo[0]) * 50, 3), round((hi[2] - lo[2]) * 50, 3), round(-(hi[1] - lo[1]) * 50, 3)],
            "anchored": True, "mobility": "Static", "castShadow": name != "STA_StreamWater", "canCollide": False, "canQuery": False,
            "raw": ({"TextureId": a["textureId"], "Transparency": 0.45, "DoubleSided": True} if name == "STA_StreamWater" else {"TextureId": a["textureId"]})}})   # 물: 익스포트 면이 전부 아래를 향해(FBX 노멀 z −1) 위에서 컬링됐다 → 양면 (2026-09-07)   # 물은 반투명 (자갈 바닥이 비친다)
    json.dump(statics, open(os.path.join(OVD, "items_static.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"instances {len(items)} → {n} chunks; statics {len(statics)}; missing ids: {sorted(missing)}")

def build_setup():
    """경계 Part 4장(items_bounds.json)과 스폰 좌표(studio_setup.json)를 레이아웃 상수에서 만든다.
    ENGINE_X0/ENGINE_Z0 만 바꾸면 맵 전체가 옮겨진다 (csv → items → sgk_collision.py → setup → -Apply → -Lua -Apply 순)."""
    X0, Z0 = L.ENGINE_X0, L.ENGINE_Z0; PX, PY = L.PLAY_X * 100, L.PLAY_Y * 100
    def bound(name, pos, size):
        return {"className": "Part", "name": name, "props": {"position": pos, "size": size, "anchored": True, "mobility": "Static",
                "canCollide": False, "canQuery": False, "castShadow": False, "transparency": 0.6, "color": [220, 40, 40]}}
    bounds = [bound("SGK_Bound_North", [X0, 800, Z0 - PY], [2 * PX + 200, 1600, 50]),   # 북 = Blender +y = 엔진 −Z (L.to_engine)
              bound("SGK_Bound_South", [X0, 800, Z0 + PY], [2 * PX + 200, 1600, 50]),
              bound("SGK_Bound_East",  [X0 + PX, 800, Z0], [50, 1600, 2 * PY + 200]),
              bound("SGK_Bound_West",  [X0 - PX, 800, Z0], [50, 1600, 2 * PY + 200])]
    json.dump(bounds, open(os.path.join(OVD, "items_bounds.json"), "w", encoding="utf-8"), indent=1)
    sw = L.SPAWN_W; se = (-sw[0], -sw[1]); SPAWN_UP = 3.0   # 지면 +3 m (기존 setup 값에서 역산)
    def sp(pt):
        e = L.to_engine(pt[0], pt[1], L.height_at(*pt) + SPAWN_UP); return [round(e[0], 1), round(e[1], 1), round(e[2], 1)]
    setup = {"spawns_engine_cm": {"Red": sp(sw), "Blue": sp(se)}, "container": "SGK_Sangok",
             "note": "SpawnLocation은 JSN_Spawn_Red/Blue를 복제→개명→위치 (TeamColor 유지). build_setup() 이 ENGINE_X0/Z0 기준으로 생성"}
    json.dump(setup, open(os.path.join(OVD, "studio_setup.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("items_bounds.json 4, studio_setup.json spawns", setup["spawns_engine_cm"])

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "csv": build_csv()
    elif a[0] == "ids": refresh_ids(a[1])
    elif a[0] == "items": build_items()
    elif a[0] == "setup": build_setup()
