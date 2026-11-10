# -*- coding: utf-8 -*-
"""수원 화성 조립.

경복궁·덕수궁의 build_* 와 달리 지오메트리를 만들지 않는다. KCISA 실측
모델을 정규화해 둔 hwaseong.blend 에서 컬렉션을 가져와 사이트에 앉힌다.

    blender -b -noaudio -P make_blend.py -- palaces.blend

hwaseong.blend 가 없으면 make_blend 가 잡아서 건너뛴다. 만드는 법은
heritage.py 주석 참조 — 스케치팹에서 UID 로 받아 normalise → strip_to_basecolor
→ decimate → organise 순으로 돌린다.
"""

import math
import os

import bpy

import hanok
from . import heritage, layout

BLEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "hwaseong.blend")


def _append(path, names):
    """hwaseong.blend 의 컬렉션을 현재 씬으로 가져온다.

    링크가 아니라 append 다 — 익스포터가 모디파이어를 적용하고 matrix_world 를
    굽기 때문에 로컬 사본이어야 한다.
    """
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.collections = [c for c in names if c in src.collections]
    got = []
    linked = {x.name for x in bpy.context.scene.collection.children}
    for c in bpy.data.collections:
        if c.name in names and c.name not in linked:
            bpy.context.scene.collection.children.link(c)
            got.append(c)
    return got


def _build_ground(bounds):
    """건물들을 받칠 지면 슬래브. **사이트 전체에 한 장만 깐다.**

    지면이 없으면 건물이 하늘에 떠 보인다 — 경복궁도 조정에 지면 박스를 깐다.
    예전엔 순수 축정렬 박스라 HGD 그룹으로 **네이티브 Part** 가 됐지만,
    실제 표고로 기복을 준 뒤로는 격자 메시다. extract_boxes 가 조용히
    None 을 돌려주고 일반 메시로 나간다 — 4,700 삼각형이라 예산에 무해하다.

    예전엔 city.py 가 도시마다 지반을 한 장씩 더 깔았다. 장안문·팔달문
    두 도시에서 **똑같은 회색 판이 두 장** 생기고 이 슬래브까지 겹쳐
    경계에 단차가 보였다. 도시 지반은 없애고 여기로 일원화했다.

    재질도 'floor'(전돌 0.17)에서 'concrete_d'(0.34)로 바꿨다 — 차도
    (0.075)와 보도(0.56)가 이 명도를 사이에 두고 갈려야 도로망이 읽힌다.
    """
    import bmesh
    from mathutils import Vector
    from hanok import new_collection, bm_box, bm_to_object

    (x0, x1), (y0, y1) = bounds
    # 150 m 도시 반경 바깥에 얇은 들판 고리만 남긴다. 80 m 여유는
    # 빈 들판을 지나치게 키워 전체 맵이 산곡의 네 배가 되게 했다.
    pad = 30.0
    x0, x1, y0, y1 = x0 - pad, x1 + pad, y0 - pad, y1 + pad
    coll = new_collection("화성_지면")

    from . import dem as _dem
    d = _dem.get("장안문")
    if d is None:
        bm = bmesh.new()
        bm_box(bm, (x0 + x1) / 2, (y0 + y1) / 2, -0.25, x1 - x0, y1 - y0, 0.5)
        bm_to_object(bm, "지면_화성", 'concrete_d', coll)
        return coll

    # --- 실제 표고로 기복을 준다 (AWS Terrain Tiles). 장안문 61.0 m 를 0 으로
    # 정규화한 상대 높이라, 기존 z=0 규약이 그대로 유지된다.
    #
    # **격자는 dem.GRID_M 교점에 정확히 맞춘다.** 임의 위치로 잘라 놓으면
    # 도로·건물이 부르는 dem.surface_at 의 격자와 어긋나 다시 땅에 잠긴다.
    S = _dem.GRID_M
    site = Vector(layout.SITE_ORIGIN)
    i0 = int(math.floor((x0 - site.x) / S))
    i1 = int(math.ceil((x1 - site.x) / S))
    j0 = int(math.floor((y0 - site.y) / S))
    j1 = int(math.ceil((y1 - site.y) / S))

    bm = bmesh.new()
    grid = {}
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            grid[(i, j)] = bm.verts.new(
                (site.x + i * S, site.y + j * S, d.node(i, j)))
    for i in range(i0, i1):
        for j in range(j0, j1):
            # surface_at 이 가정하는 (0,0)-(1,1) 대각과 같은 감김
            bm.faces.new((grid[(i, j)], grid[(i + 1, j)],
                          grid[(i + 1, j + 1)], grid[(i, j + 1)]))

    # 치마 — 판이 종잇장이면 낮은 각도에서 지평선이 그대로 비친다.
    zmin = min(v.co.z for v in grid.values()) - 8.0
    ring = ([(i, j0) for i in range(i0, i1 + 1)]
            + [(i1, j) for j in range(j0, j1 + 1)]
            + [(i, j1) for i in range(i1, i0 - 1, -1)]
            + [(i0, j) for j in range(j1, j0 - 1, -1)])
    skirt = {k: bm.verts.new((grid[k].co.x, grid[k].co.y, zmin)) for k in set(ring)}
    for a, b in zip(ring, ring[1:]):
        if a == b:
            continue
        bm.faces.new((grid[a], grid[b], skirt[b], skirt[a]))

    # bm_to_object 가 bm 을 해제하므로 통계는 **먼저** 뽑는다.
    lo = min(v.co.z for v in grid.values())
    hi = max(v.co.z for v in grid.values())
    # recalc_face_normals 은 부르지 않는다 — 바닥이 없는 열린 껍질이라
    # 휴리스틱이 윗면까지 뒤집을 수 있다. 위 감김이 이미 +Z 다.
    bm_to_object(bm, "지면_화성", 'concrete_d', coll)
    print("  지면: %dx%d 격자 (%.0f m), 실제 표고 %.1f~%.1f m"
          % (i1 - i0, j1 - j0, S, lo, hi))
    return coll


def build_all():
    """화성 건물들을 씬에 세우고 배치표대로 앉힌다."""
    if not os.path.exists(BLEND):
        raise FileNotFoundError(
            "%s 가 없다. heritage.py 주석대로 KCISA 모델을 받아 정규화할 것." % BLEND)

    # KCISA 스캔은 hwaseong.blend 에서 가져오고,
    want = [c for b in layout.BUILDINGS.values()
            if not b.get("procedural") for c in b["collections"]]
    _append(BLEND, want)
    # 스캔이 없는 것(화서문·공심돈·방화수류정)은 여기서 절차 생성한다.
    # **layout.BUILDINGS 가 부르지 않으면 만들지도 않는다.** 예전에는 무조건
    # 만들어 놓고 배치 루프에서만 걸렀는데, 그러면 배치되지 않은 채 원점
    # 근처에 그대로 남아 씬에 잔여물이 됐다(익스포트는 --groups 로 걸러져
    # 안 나갔지만 블렌더 화면에는 보였다).
    uigwe_colls = {c for b in layout.BUILDINGS.values()
                   if b.get("procedural") for c in b["collections"]}
    if uigwe_colls & {"화성_화서문", "화성_공심돈", "화성_방화수류정"}:
        from . import build_uigwe
        build_uigwe.build_all()
    else:
        print("의궤 시설물 건너뜀 — layout.BUILDINGS 에 없다")
    # 장안문 주변 실측 도시 — OSM footprint 압출. 좌표가 이미 앵커 기준이다.
    from . import city
    city.build_all()

    from mathutils import Matrix, Vector
    site = (Matrix.Translation(Vector(layout.SITE_ORIGIN))
            @ Matrix.Rotation(math.radians(layout.AXIS_DEG), 4, 'Z'))

    # 지면에 기복을 주면 z=0 에 앉힌 기념물이 뜨거나 묻힌다. 놓는 자리의
    # 표고만큼 같이 올린다. 도시(uv 0,0)는 city.py 가 이미 자체 처리했다.
    from . import dem as _dem
    d = _dem.get("장안문")

    dg = bpy.context.evaluated_depsgraph_get()
    total_obj, total_tris = 0, 0
    xs, ys = [], []
    for name, b in layout.BUILDINGS.items():
        objs = [o for cn in b["collections"]
                for o in (bpy.data.collections.get(cn).objects
                          if bpy.data.collections.get(cn) else [])]
        if not objs:
            print("  화성 %s: 컬렉션이 비었다 — 건너뜀" % name)
            continue
        u, v = b["uv"]
        lu, lv = b.get("uv_local", (0.0, 0.0))
        # 건물 자기 회전을 먼저 걸고, 그 위에 사이트 배치를 덧씌운다.
        # hanok.place_objects 와 같은 합성 규약이다 (대입 아님).
        # uv 는 DIST_SCALE 로 압축하지만 uv_local 은 하지 않는다 — 공심돈처럼
        # 실제로 붙어 있는 것끼리의 간격까지 눌리면 서로 겹친다.
        px = u * layout.DIST_SCALE + lu
        py = v * layout.DIST_SCALE + lv
        # 도시는 uv (0,0) 이라 height_at 이 정확히 0 — 자기 자리에서 이미
        # city.py 가 건물마다 따로 올렸으므로 이중으로 올라가지 않는다.
        pz = 0.0 if d is None else d.surface_at(px, py)
        local = (Matrix.Translation(Vector((px, py, pz)))
                 @ Matrix.Rotation(math.radians(b["yaw"]), 4, 'Z'))
        hanok.place_objects(objs, matrix=site @ local)

        t = 0
        for o in objs:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            t += sum(max(0, len(p.vertices) - 2) for p in me.polygons)
            ev.to_mesh_clear()
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c)
                xs.append(w.x)
                ys.append(w.y)
        total_obj += len(objs)
        total_tris += t
        print("  화성 %-4s 메시 %2d  삼각형 %7d  (%s)" % (name, len(objs), t, b["note"]))

    if xs:
        _build_ground(((min(xs), max(xs)), (min(ys), max(ys))))

    print("화성 합계: 메시 %d / 삼각형 %d (감축 후)" % (total_obj, total_tris))
    print("  %s" % heritage.ATTRIBUTION)
    return total_obj, total_tris
