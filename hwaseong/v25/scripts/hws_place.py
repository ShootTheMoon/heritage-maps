# -*- coding: utf-8 -*-
r"""scene_dump.json → OVERDARE 배치 JSON (산곡 sgk_placements 형식). Blender 불필요(stdlib).
Usage: python hws_place.py [UGCLocalAssetTable.json]
  * 정적물(01_JAM/02_DOORS/03_TERRAIN): position = bbox 중심(엔진), orientation = (0, YAW_FIX→-180, 0), size = bbox cm(Y/Z 스왑)
  * 마스터 인스턴스(10_MASTERS): position = 바닥중심 + 마스터 centre_offset(회전·스케일 적용), yaw = rot_z + 180
  * 식생: 산곡 asset_ids.json (MST_*) meshId/textureId 재사용 — 같은 onlyoneshot 프로젝트 전제
  meshId 는 UGCLocalAssetTable 이 주어지면 bundleName(=파일 stem)으로 해석, 없으면 "" 로 남긴다.
Outputs: items_static.json, _place\place_###.json (200개 청크), placements.csv, unresolved.txt"""
import io, json, math, os, sys, csv

OUT = r"C:\Users\HSP\Desktop\blender\ovdr_export\hwaseong_v25"
SGK_IDS = r"C:\Users\HSP\Desktop\blender\JSN_Sangok2\06_OVERDARE\asset_ids.json"
CONTAINER = "Workspace.HWS_Hwaseong"


def load_table(path):
    if not path or not os.path.exists(path):
        return {}
    raw = io.open(path, "rb").read()
    txt = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", "ignore")
    t = json.loads(txt).get("localAssetList", {})
    by = {}; tex = {}
    for cid, v in t.items():
        if v.get("worldAssetType") == "STATIC_MESH":
            by.setdefault(v.get("name", ""), []).append((v.get("createdTime", ""), int(cid)))
        elif v.get("worldAssetType") == "TEXTURE":
            tex.setdefault(v.get("name", ""), []).append((v.get("createdTime", ""), int(cid)))
    ids = {k: str(max(vs)[1]) for k, vs in by.items()}
    for k in [k for k in ids if k.startswith("HWS_DOOR_") and ("_MG_" in k or "_OS_" in k)]:
        ids.pop(k)   # ASCII door imports are the pre-bake versions
    ids["__tex__"] = {k: str(max(vs)[1]) for k, vs in tex.items()}
    return ids


SOLID = ("담장", "여장", "암문", "Hay", "Mud", "Old", "BOULDER", "소나무")   # walls, props, boulders, pines collide; grass does not
QUERY = ("담장", "여장", "암문", "Hay", "Mud", "Old", "BOULDER")            # raycast-visible (kunai stops). pines stay CanQuery=false so arrows/kunai fly through canopies
def solid(name):
    return any(k in name for k in SOLID)
def query(name):
    return any(k in name for k in QUERY)


def rot(p, yaw):
    r = math.radians(yaw); return (p[0] * math.cos(r) - p[1] * math.sin(r), p[0] * math.sin(r) + p[1] * math.cos(r), p[2])


def main(table_path=None):
    d = json.load(io.open(os.path.join(OUT, "scene_dump.json"), encoding="utf-8"))
    X0, YF = d["x0_cm"], d["yaw_fix"]
    ids = load_table(table_path); texids = ids.pop("__tex__", {})
    tmap_p = os.path.join(OUT, "texture_map.json"); tmap = json.load(io.open(tmap_p, encoding="utf-8")) if os.path.exists(tmap_p) else {}
    tmap["HWS_TER_11"] = "HWS_TER_12"          # batch-0 tile: its texture registered under a colliding name
    def tex_for(stem):
        k = tmap.get(stem) or ("T_" + stem if stem.startswith(("HWS_TER_", "HWS_OUT_")) else None)
        if isinstance(k, list): k = k[0] if k else None
        return texids.get(k, "") if k else ""
    sgk = {k: v for k, v in json.load(io.open(SGK_IDS, encoding="utf-8")).items()} if os.path.exists(SGK_IDS) else {}
    eng = lambda x, y, z: [round(x * 100 + X0, 1), round(z * 100, 1), round(-y * 100, 1)]
    yaw_e = lambda a: round(((a + YF + 180) % 360) - 180, 2)
    unresolved = set(); statics = []
    for s in d["statics"]:
        stem = os.path.splitext(os.path.basename(s["file"]))[0]
        mn, mx = s["bbox_min_m"], s["bbox_max_m"]; c = [(mn[i] + mx[i]) / 2 for i in range(3)]
        mid = ids.get(stem, "")
        if stem.startswith("HWS_DOOR_"):                 # 2026-09-09 08:10 re-export under HWS_DR_* (ASCII, frame 1) takes priority
            mid = ids.get(stem.replace("HWS_DOOR_", "HWS_DR4_"), "") or ids.get(stem.replace("HWS_DOOR_", "HWS_DR3_"), "") or ids.get(stem.replace("HWS_DOOR_", "HWS_DR_"), "") or mid
        if not mid and stem.startswith("HWS_DOOR_"):   # baked door FBX were re-imported under Hangul names
            hk = stem.replace("_MG_", "_주문_").replace("_OS_", "_옹성_").replace("_L_", "_좌_").replace("_R_", "_우_")
            mid = ids.get(hk, "")
        unresolved.add(stem) if not mid else None
        statics.append({"className": "MeshPart", "name": stem, "props": {"meshId": "ovdrassetid://" + mid if mid else "", "material": "Basic", "color": [200, 200, 200], "position": eng(*c), "orientation": [0.0, yaw_e(0.0), 0.0],
                        "size": [max(1.0, round((mx[0] - mn[0]) * 100, 1)), max(1.0, round((mx[2] - mn[2]) * 100, 1)), max(1.0, round((mx[1] - mn[1]) * 100, 1))],
                        "anchored": True, "mobility": "Movable" if stem.startswith("HWS_DOOR_") else "Static", "castShadow": True, "canCollide": bool(s.get("collide", False)), "canQuery": bool(s.get("collide", False)),   # CanQuery=false 면 레이캐스트(쿠나이·화살)가 통과한다
                        "doubleSided": stem.startswith("HWS_DOOR_"),   # door leaves are single-sided sheets: back face was culled -> looked missing
                        "raw": ({"TextureId": "ovdrassetid://" + tex_for(stem)} if tex_for(stem) else {})}})
        if not tex_for(stem): unresolved.add("TEX:" + stem)
    items = []; rows = []
    for it in d["instances"]:
        m = it["master"]; sc = it.get("scale", 1.0); yaw = it["yaw_deg"]
        if it.get("sangok_asset"):
            a = sgk.get(m)
            if not a:
                unresolved.add(m); continue
            mn, mx = it["bbox_min_m"], it["bbox_max_m"]; c = [(mn[i] + mx[i]) / 2 for i in range(3)]
            size = [round((mx[0] - mn[0]) * 100, 1), round((mx[2] - mn[2]) * 100, 1), round((mx[1] - mn[1]) * 100, 1)]
            mid, tid = a["meshId"], a.get("textureId", "")
        else:
            mm = d["masters"][m]; stem = os.path.splitext(os.path.basename(mm["file"]))[0]
            off = rot([v * sc for v in mm["centre_offset_m"]], yaw)
            c = [it["pos_m"][i] + off[i] for i in range(3)]
            size = [round(v * sc, 1) for v in mm["size_cm"]]
            mid = ids.get(stem, ""); tid = tex_for(stem); unresolved.add(stem) if not mid else None
        mid = mid if (not mid or mid.startswith("ovdrassetid")) else "ovdrassetid://" + mid; tid = tid if (not tid or tid.startswith("ovdrassetid")) else "ovdrassetid://" + tid
        items.append({"className": "MeshPart", "name": "HWS_" + it["name"].replace("/", "_"), "props": {"meshId": mid, "material": "Basic", "color": [200, 200, 200], "position": eng(*c), "orientation": [0.0, yaw_e(yaw), 0.0],
                      "size": size, "anchored": True, "mobility": "Static", "castShadow": True, "canCollide": solid(it["name"]), "canQuery": query(it["name"]),
                      "raw": ({"TextureId": tid} if tid else {})}})
        rows.append([m, it["name"], *[round(v, 3) for v in it["pos_m"]], yaw, sc])
    os.makedirs(os.path.join(OUT, "_place"), exist_ok=True)
    json.dump(statics, io.open(os.path.join(OUT, "items_static.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for k in range(0, len(items), 200):
        json.dump(items[k:k + 200], io.open(os.path.join(OUT, "_place", "place_%03d.json" % (k // 200)), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with io.open(os.path.join(OUT, "placements.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["master", "name", "x_m", "y_m", "z_m", "yaw_deg", "scale"]); w.writerows(rows)
    io.open(os.path.join(OUT, "unresolved.txt"), "w", encoding="utf-8").write("\n".join(sorted(unresolved)))
    xs = [s["props"]["position"][0] for s in statics + items]
    print("STATICS %d  INSTANCES %d (chunks %d)  UNRESOLVED %d  X range %d..%d  container %s" % (
        len(statics), len(items), (len(items) + 199) // 200, len(unresolved), min(xs), max(xs), CONTAINER))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
