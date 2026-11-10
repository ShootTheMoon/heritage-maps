"""placements.csv -> studiorpc_instance_upsert 용 배치 JSON 재생성.

Blender 안에서 실행한다 (mathutils 가 필요하다):

    exec(open(r"C:\\Work\\blender\\JSN_Sangok\\_ovdr\\regen_batches.py").read())

좌표 규약이 이 파일 안에 있다. 파라미터만으로는 못 바꾼다.
근거는 Desktop\\blender\\gyeongbokgung\\export_overdare.py — 경복궁을 이 Studio 에
실제로 배치해 검증된 파이프라인이다.

  축   : X = bx*100,  Y = bz*100,  Z = -by*100        (to_ovdr, 행렬식 +1)
  회전 : R_e = M * R_b * M^T 에 월드 Y 180도를 얹고 ZXY 로 분해.
         - 순서는 ZXY 다. YXZ 로 분해하면 최대 160도, 24%가 10도 초과로 틀어진다.
         - 180도는 이 FBX 세트 고유의 보정이다. 위치 파이프라인과 회전 파이프라인이
           서로 다른 정면을 쓰고 있어서, 좌표는 맞는데 회전만 반대로 들어온다.
           2026-08-19 인게임 확인: 이걸 넣기 전에는 지형 16장이 각자 뒤집혀
           판때기처럼 갈라져 보이고 스커트가 띠로 드러났다.
  피벗 : 임포터가 bbox 중심으로 재중심화한다.
         마스터는 피벗이 바닥 중앙(FBX 실측: 11개 전부 bbox min z = 0)이므로
         로컬 up 으로 h/2 올린다. 안 올리면 곰솔이 8.5 m 파묻힌다.
         STATIC 은 월드 좌표가 구워져 있어 각자의 bbox 중심에 놓는다.
"""

import os, csv, json, math
from mathutils import Matrix, Euler, Vector

OV     = r"C:\Work\blender\JSN_Sangok\_ovdr"
CSVP   = r"C:\Work\blender\JSN_Sangok\06_OVERDARE\placements.csv"
OUT    = os.path.join(OV, "batches")
OFFSET = -60000.0                                  # 경복궁/창덕궁과 겹치지 않게 서쪽 600 m
PARENT = "D53E1E7344D56B5159E6EA88BD8EB424"        # Model "JSN_Sangok"
BATCH  = 100

M  = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))    # blender(x,y,z) -> engine(x,z,-y)
Y180 = Matrix.Rotation(math.radians(180.0), 3, 'Y')  # 엔진 up = Y. 회전만 붙는 보정
DS = {"MST_PINE", "MST_EULALIA", "MST_ARTEMISIA"}  # 알파 카드 — 단면이면 잎이 절반 사라진다
ORDER = ["MST_ROCK_MASS", "MST_ROCK_A", "MST_ROCK_B", "MST_ROCK_C", "MST_ROCK_D",
         "MST_ROCK_E", "MST_ROCK_F", "MST_EULALIA", "MST_ARTEMISIA", "MST_PEBBLE", "MST_PINE"]


def _load(name):
    return json.load(open(os.path.join(OV, name), encoding="utf-8-sig"))


def solve(row, mdim):
    """CSV 한 행 -> (position, orientation_deg, size_cm)."""
    mk, sx = row["master"], float(row["sx"])
    d = mdim[mk]["ovdr_cm"]
    # CSV 규약: pitch = rot_x, roll = rot_y, yaw = -rot_z
    Rb = Euler((math.radians(float(row["pitch"])),
                math.radians(float(row["roll"])),
                math.radians(-float(row["yaw"]))), 'XYZ').to_matrix()
    Re = M @ Rb @ M.transposed()
    h  = d[1] * sx
    lift = Re @ Vector((0.0, h / 2.0, 0.0))        # 바닥 중앙 -> bbox 중심
    # 리프트는 보정 전 Re 로 계산한다 — 위치는 이미 맞고 회전만 뒤집혀 있다.
    eu = (Y180 @ Re).to_euler('ZXY')
    pos = (float(row["X"]) + OFFSET + lift.x,
           float(row["Y"]) + lift.y,
           -float(row["Z"]) + lift.z)              # CSV Z 는 +by*100 이라 뒤집는다
    # Size 는 백분율이 아니라 cm 실치수다. 2026-08-19 인게임 실측으로 확정:
    # Size=100 을 넣은 지형 타일(UnitExtent 3250)이 1 m 큐브로 렌더돼 보이지 않았고,
    # 같은 자리에 Size 6500 인 엔진 Part 를 놓자 65 m 슬래브로 나왔다.
    return pos, (math.degrees(eu.x), math.degrees(eu.y), math.degrees(eu.z)), \
           (d[0] * sx, d[1] * sx, d[2] * sx)


def mesh_item(name, mid, tid, pos, ori, siz, ds):
    return {"class": "MeshPart", "parentGuid": PARENT, "name": name, "properties": {
        "MeshId": "ovdrassetid://%s" % mid, "TextureId": "ovdrassetid://%s" % tid,
        "CFrame": {"Position": {"X": round(pos[0], 2), "Y": round(pos[1], 2), "Z": round(pos[2], 2)},
                   "Orientation": {"X": round(ori[0], 3), "Y": round(ori[1], 3), "Z": round(ori[2], 3)}},
        "Size": {"X": round(siz[0], 2), "Y": round(siz[1], 2), "Z": round(siz[2], 2)},
        "Anchored": True, "CanCollide": False, "CastShadow": True,
        "DoubleSided": bool(ds), "Color": {"R": 255, "G": 255, "B": 255}, "Transparency": 0}}


def main():
    ids  = _load("asset_ids_local.json")
    mdim = _load("master_dims.json")
    sdim = _load("static_dims.json")
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".json"):
            os.remove(os.path.join(OUT, f))

    def dump(obj, fn):
        open(os.path.join(OUT, fn), "w", encoding="utf-8").write(
            json.dumps(obj, indent=1, ensure_ascii=False))

    # STATIC 19 — 각자의 bbox 중심. 리프트는 없지만 회전 180도 보정은 똑같이 받는다.
    # 타일은 각자 셀 중앙에 놓인 6500x6500 정사각이라 제자리 180도로 등록이 맞는다.
    skeys = ["STA_STEPS", "STA_StreamWater", "STA_TribWater"] + \
            ["STA_TER_%d%d" % (r, c) for r in range(4) for c in range(4)]
    st = [mesh_item(k, ids[k]["meshId"], ids[k]["textureId"],
                    (sdim[k]["center_ovdr_cm"][0] + OFFSET,
                     sdim[k]["center_ovdr_cm"][1],
                     -sdim[k]["center_ovdr_cm"][2]),
                    (0, 180, 0), sdim[k]["size_ovdr_cm"], False) for k in skeys]
    dump(st, "static.json")

    rows = list(csv.DictReader(open(CSVP, encoding="utf-8")))
    rows.sort(key=lambda r: (ORDER.index(r["master"]), r["name"]))
    items = []
    for r in rows:
        pos, ori, siz = solve(r, mdim)
        a = ids[r["master"]]
        items.append(mesh_item(r["name"], a["meshId"], a["textureId"],
                               pos, ori, siz, r["master"] in DS))

    man = [{"file": "static.json", "count": len(st), "note": "지형16+수면2+석단1 (bbox중심)"}]
    for n, i in enumerate(range(0, len(items), BATCH)):
        fn = "place_%03d.json" % n
        dump(items[i:i + BATCH], fn)
        man.append({"file": fn, "count": len(items[i:i + BATCH]),
                    "note": "%s ~ %s" % (rows[i]["master"],
                                         rows[min(i + BATCH - 1, len(rows) - 1)]["master"])})

    # 캘리브레이션 — 기준자 Part 가 Size 규약(cm vs 백분율)을 판별한다.
    p, pd = ids["MST_PINE"],   mdim["MST_PINE"]["ovdr_cm"]
    rb, rd = ids["MST_ROCK_B"], mdim["MST_ROCK_B"]["ovdr_cm"]
    ruler = {"class": "Part", "parentGuid": PARENT, "name": "ZZCAL_RULER_1698", "properties": {
        "Shape": "Block",
        "CFrame": {"Position": {"X": OFFSET - 800, "Y": 500 + pd[1] / 2, "Z": 0},
                   "Orientation": {"X": 0, "Y": 0, "Z": 0}},
        "Size": {"X": 100, "Y": round(pd[1], 2), "Z": 100},
        "Anchored": True, "CanCollide": False, "CastShadow": True,
        "Color": {"R": 255, "G": 40, "B": 40}, "Material": "Unlit", "Transparency": 0}}
    cal = [ruler,
               mesh_item("ZZCAL_PINE_S100", p["meshId"], p["textureId"],
                         (OFFSET, 500 + pd[1] / 2, 0), (0, 0, 0), pd, True),
               mesh_item("ZZCAL_PINE_S050", p["meshId"], p["textureId"],
                         (OFFSET + 2000, 500 + pd[1] * 0.25, 0), (0, 0, 0), [v * 0.5 for v in pd], True),
               mesh_item("ZZCAL_ROCKB_Y90", rb["meshId"], rb["textureId"],
                         (OFFSET + 4000, 500 + rd[1] / 2, 0), (0, 90, 0), rd, False)]
    dump(cal, "calib.json")
    man.append({"file": "calib.json", "count": len(cal), "note": "검증 후 삭제"})
    dump(man, "_manifest.json")
    print("생성: 파일 %d / STATIC %d / 인스턴스 %d / 캘리브 %d"
          % (len(man), len(st), len(items), len(cal)))


main()