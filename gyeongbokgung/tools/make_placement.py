# -*- coding: utf-8 -*-
"""매니페스트 + 오버데어 에셋 테이블 → **해석이 끝난 배치 지시서**.

왜 필요한가
    manifest.json 은 블렌더가 아는 것만 담는다. 실제 배치에는
    `expected_asset_name` → contentId 조회, 레벨 원점 보정, 팔레트 색 결정이
    더 필요하고, 그걸 배치하는 쪽에서 매번 다시 하면 규약이 어긋나기 쉽다.
    여기서 한 번에 풀어 **그대로 쓰면 되는 값**으로 만든다.

    조회는 반드시 contentId 로 한다. 같은 이름으로 재발행한 에셋이 여럿이면
    `createdTime` 이 가장 늦은 항목을 고르고, 선택 결과를 로그로 남긴다.

    blender 파이썬 없이 도는 순수 표준 라이브러리 스크립트다.

    python make_placement.py --groups-exclude CTB --out placement_phase1.json
"""
import argparse
import collections
import glob
import io
import json
import os
import sys

# 레벨 원점 보정. 매니페스트는 장안문 문루 중심을 (120000, 5000, 0) 으로
# 잡는다(sites.py HSF: origin_m 1200 m, floor_y_cm 5000). 그 차이를 뺀다.
#
# **ΔX 는 -70000 이 아니다.** 레벨에 있던 `PLACE NEW MAP CENTER HERE` 표지판이
# X=50000 이라 처음엔 -70000 을 썼는데, 반경 150 m 로 줄인 v23 도 폭이 372 m 라
# 서쪽 끝이 X 30800 까지 내려와 **창덕궁(27000~33000)과 22 m 겹쳤다.**
# 표지판은 지금 레벨에서 사라졌고, 대신 창덕궁 동쪽 끝에서 98 m 떼어 놓는다.
#   v23 전체 X 100800~138000 → ΔX -58000 → **42800~80000**
#   가장 가까운 이웃 창덕궁 33000 과 9800 cm 여유. 나머지는 400 m 이상 떨어져 있다.
# **재익스포트가 필요 없다** — 임포터가 메시를 bbox 로 재중심화하므로
# FBX 는 월드 위치를 안 들고 있고, 위치는 전적으로 CFrame 이 정한다.
DELTA = (-58000.0, -5000.0, 0.0)

# 플레이 공간에서 화성을 줄일 때의 기준점(= 보정 후 맵 중심). 위치·크기를 같은
# 배율로 줄여 부재 사이가 벌어지지 않게 한다. --scale 1.0 이면 안 쓰인다.
SCALE_PIVOT = (61400.0, 0.0, 0.0)

# 알파 카드(잎)를 쓰는 그룹. 단면으로 놓으면 잎이 절반 사라진다.
DOUBLE_SIDED_GROUPS = {"VEG", "CTP"}

# 텍스처가 붙은 메시는 Color 를 255 로 둔다 — 200 이면 텍스처가 78% 로
# 어두워진다(200/255 = 0.784).
WHITE = [255, 255, 255]
FALLBACK = {"color3": [180, 180, 180], "material": "Basic", "transparency": 0.0}


def asset_table():
    cfg = glob.glob(os.path.expanduser(r"~\.overdare\mcp\studios\*.json"))
    if not cfg:
        sys.exit("Studio 설정을 못 찾았다 — Studio 가 떠 있어야 한다")
    c = json.load(io.open(cfg[0], encoding="utf-8"))
    cwd = c["cwd"].replace("/", "\\")
    p = os.path.join(cwd, "UGCLocalAssetTable.json")
    t = json.load(io.open(p, encoding="utf-8"))["localAssetList"]
    by = collections.defaultdict(list)
    for cid, v in t.items():
        if v.get("worldAssetType") == "STATIC_MESH":
            by[v.get("name", "")].append({
                "contentId": cid,
                "createdTime": v.get("createdTime", ""),
            })
    return cwd, by


def latest_asset(name, candidates):
    """동명 STATIC_MESH 중 가장 최근 발행본을 결정적으로 고른다."""
    chosen = max(candidates, key=lambda v: (
        v["createdTime"],
        int(v["contentId"]),
    ))
    if len(candidates) > 1:
        ordered = sorted(candidates, key=lambda v: (
            v["createdTime"], int(v["contentId"])
        ))
        print("동명 최신 선택: %s -> %s (%s), 후보 %s" % (
            name,
            chosen["contentId"],
            chosen["createdTime"] or "createdTime 없음",
            ", ".join("%s@%s" % (
                v["contentId"], v["createdTime"] or "?"
            ) for v in ordered),
        ))
    return chosen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=r"C:\Users\HSP\Desktop\blender\ovdr_export\hwaseong_v22\manifest.json")
    ap.add_argument("--out", default="placement.json")
    ap.add_argument("--groups-exclude", default="")
    ap.add_argument("--groups-only", default="")
    ap.add_argument("--parent", default="Hwaseong Place")
    ap.add_argument("--scale", type=float, default=1.0,
                    help="장안문 중심 기준 배치 배율 (예: 0.6)")
    args = ap.parse_args()
    if args.scale <= 0:
        ap.error("--scale 은 0보다 커야 한다")

    m = json.load(io.open(args.manifest, encoding="utf-8"))
    cwd, by = asset_table()
    pal = m.get("palette", {})
    perfile = collections.Counter(x["file"] for x in m["meshes"])

    excl = {g for g in args.groups_exclude.split(",") if g}
    only = {g for g in args.groups_only.split(",") if g}

    items, missing, ambiguous = [], [], []
    for x in m["meshes"]:
        g = x["group"]
        if excl and g in excl:
            continue
        if only and g not in only:
            continue
        # 파일에 메시가 하나뿐이면 에셋 이름에 슬러그 접미사가 안 붙는다
        cands = [x["expected_asset_name"]]
        if perfile[x["file"]] == 1:
            cands.append(x["file"][:-4])
        hit = next((n for n in cands if n in by), None)
        if hit is None:
            missing.append({"file": x["file"], "slug": x["slug"],
                            "expected": x["expected_asset_name"]})
            continue
        chosen = latest_asset(hit, by[hit])

        cf, sz = x["cframe_cm"], x["size_cm"]
        world = (
            cf["X"] + DELTA[0],
            cf["Y"] + DELTA[1],
            cf["Z"] + DELTA[2],
        )
        scaled_world = tuple(
            SCALE_PIVOT[i] + (world[i] - SCALE_PIVOT[i]) * args.scale
            for i in range(3)
        )
        p = pal.get(x["material_key"])
        textured = True          # v22 는 260개 파일 전부 텍스처가 실려 있다
        if p:
            color, mat, tr = p["color3"], p["material"], p["transparency"]
        elif textured:
            color, mat, tr = WHITE, "Basic", 0.0
        else:
            color, mat, tr = FALLBACK["color3"], FALLBACK["material"], 0.0

        items.append({
            "name": x["slug"],
            "group": g,
            "file": x["file"],
            "tris": x["tris"],
            "meshId": "ovdrassetid://%s" % chosen["contentId"],
            "textureId": "",          # 자동으로 안 채워지면 여기에 넣는다
            "cframe": {"X": round(scaled_world[0], 3),
                       "Y": round(scaled_world[1], 3),
                       "Z": round(scaled_world[2], 3)},
            "orientation": {"X": 0, "Y": 0, "Z": 0},
            # SIZE_MODE 가 확정되기 전이라 두 후보를 다 담는다. 명세 5.2 참조.
            "size_literal_cm": {"X": sz["X"] * args.scale,
                                "Y": sz["Y"] * args.scale,
                                "Z": sz["Z"] * args.scale},
            "size_unit_ratio": {"X": 100 * args.scale,
                                "Y": 100 * args.scale,
                                "Z": 100 * args.scale},
            "color": {"R": color[0], "G": color[1], "B": color[2]},
            "material": mat,
            "transparency": tr,
            "anchored": True,
            "canCollide": False,
            "collisionProfile": "NoCollision",
            "castShadow": True,
            "doubleSided": g in DOUBLE_SIDED_GROUPS,
        })

    lo = [1e18] * 3
    hi = [-1e18] * 3
    for it in items:
        for i, a in enumerate("XYZ"):
            lo[i] = min(lo[i], it["cframe"][a] - it["size_literal_cm"][a] / 2)
            hi[i] = max(hi[i], it["cframe"][a] + it["size_literal_cm"][a] / 2)

    doc = {
        "schema": "overdare-placement/1",
        "source_manifest": args.manifest,
        "level_project": cwd,
        "parent_model": args.parent,
        "origin_delta_cm": {"X": DELTA[0], "Y": DELTA[1], "Z": DELTA[2]},
        "placement_scale": args.scale,
        "scale_pivot_cm": {"X": SCALE_PIVOT[0], "Y": SCALE_PIVOT[1],
                           "Z": SCALE_PIVOT[2]},
        "size_mode": None,        # 5.2 캘리브레이션 전에는 정할 수 없다
        "counts": {"items": len(items),
                   "missing": len(missing),
                   "ambiguous": len(ambiguous),
                   "by_group": dict(collections.Counter(i["group"] for i in items))},
        "bounds_cm": {"min": {"X": round(lo[0]), "Y": round(lo[1]), "Z": round(lo[2])},
                      "max": {"X": round(hi[0]), "Y": round(hi[1]), "Z": round(hi[2])}},
        "missing": missing,
        "ambiguous": ambiguous,
        "items": items,
    }
    io.open(args.out, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print("배치 항목 %d / 누락 %d / 이름중복 %d" % (len(items), len(missing), len(ambiguous)))
    print("그룹:", doc["counts"]["by_group"])
    print("범위 X %d~%d  Y %d~%d  Z %d~%d" % (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    print("저장:", os.path.abspath(args.out))
    if missing:
        print("!! 누락이 있다 — 임포트가 덜 됐다. 배치하지 말 것.")
    if ambiguous:
        print("!! 최신 발행본을 결정할 수 없는 이름이 있다 — 배치하지 말 것.")


if __name__ == "__main__":
    main()
