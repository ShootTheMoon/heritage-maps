# -*- coding: utf-8 -*-
"""지형 마감 — Poly Haven CC0 텍스처와 HDRI.

게임 맵이라 개별 건물의 실측 높이보다 **보이는 완성도**가 중요하다는 판단으로,
지면·도로를 팔레트 단색에서 실제 텍스처로 바꾸고 조명을 HDRI 로 올린다.

에셋은 전부 **Poly Haven CC0** 라 출처 표시 의무도 없다:
    sparse_grass        성 안팎 지면 (들풀)
    dirt_floor          수레길 (밝게 다져진 흙)
    park_dirt           샛길 (중간 흙)
    brown_mud_dry       바위 재질의 바탕
    autumn_field_puresky  HDRI (맑은 오전)

**아스팔트도 보도블럭도 쓰지 않는다.** 도시가 한옥 마을이 된 뒤로 둘 다
시대가 안 맞는다. 수레길과 샛길, 흙길 두 종류로 간다.

에셋은 hwaseong_props.blend 에 구워 두었다 — 빌드 때 애드온이나 네트워크가
필요 없다. 다시 받으려면 Poly Haven 애드온에서 위 ID 로 내려받으면 된다.
"""

import os

import bpy

PROPS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "hwaseong_props.blend")

# (오브젝트 이름, 재질 이름, 타일 간격 m, 좌표계, 색보정)
#
# 'obj' = Object 좌표로 타일링. UV 가 없는 지면 판용이다.
# 'uv'  = 메시가 들고 있는 UV 그대로. **도로는 반드시 이쪽이다** — 흙길
#         텍스처의 바퀴 자국이 길을 따라 흘러야 하는데, Object 좌표로
#         타일링하면 결이 도로와 무관한 방향으로 눕는다. city._ribbon 이
#         u = 폭, v = 누적 거리를 미터 단위로 깔아 둔다.
#
# 조합을 두 번 갈았다. 처음엔 지면 sparse_grass + 수레길 dry_mud_field_001
# 이었는데 마른 잔디(카키)와 젖은 진흙(암갈)의 명도가 붙어 부감에서 길이
# **어두운 얼룩**으로만 보였다. 다음엔 지면을 leafy_grass 로 바꿨는데
# 이름과 달리 확산맵 평균이 (0.59, 0.51, 0.35) — 초록이 아니라 연한 황갈이라
# 지면과 길이 통째로 크림색이 됐다.
#
# 확산맵 평균을 직접 재서 명도로 벌렸다:
#   sparse_grass (0.31,0.24,0.08)  어두운 들풀   ← 지면
#   dirt_floor   (0.72,0.55,0.39)  밝은 다진 흙  ← 수레길
#   park_dirt    (0.48,0.39,0.24)  중간 흙       ← 샛길
# 지면은 그대로 두면 갈색이라 초록 쪽으로 살짝 당긴다.
SURFACES = [
    # 타일을 실제 풀 크기(2.5 m)로 두면 30 m만 떨어져도 밉맵에 뭉개져
    # 단색이 된다. 게임 카메라 거리에서 결이 읽히도록 크게 잡는다 —
    # 지면은 8 m, 도로는 UV 주기(ROAD_TEX_M 2.5 m)의 두 배인 5 m.
    ("지면_화성", "sparse_grass", 8.0, 'obj', (0.82, 1.15, 0.72)),
    ("도시_도로_dirt_road", "dirt_floor", 2.0, 'uv', None),
    ("도시_도로_dirt_path", "park_dirt", 2.0, 'uv', None),
    # 갓길 — 밟힌 풀. 지면(들풀)과 노면(맨흙) 사이를 이어 경계를 푼다.
    # 보정값은 **셋의 최종 색을 맞춰서** 잡았다. 지면이 (0.26,0.28,0.06),
    # 노면이 (0.72,0.55,0.39) 이므로 갓길은 그 사이에서 지면 쪽으로 기운
    # (0.42,0.40,0.20) 을 노린다. grass_path_2 원본이 (0.55,0.51,0.39)라
    # 그 비율이 아래 값이다. 처음엔 지면과 같은 보정을 썼는데 갓길이
    # 지면보다 밝은 초록 띠로 튀어 오히려 선이 하나 더 그어졌다.
    ("도시_도로_dirt_verge", "grass_path_2", 2.0, 'uv', (0.76, 0.80, 0.52)),
]
# **make_blend.py 도 월드를 'sky' 로 만든다.** 이름이 같으면 아래 _link 가
# 그 파란 그라디언트 월드를 집어 HDRI 가 안 들어온다(실제로 당했다).
WORLD = "hdri_autumn_field"
SUN_ENERGY = 1.6        # HDRI 가 환경광을 맡으므로 태양은 그림자 방향만
SHADOW_RES = 0.05       # m/텍셀. 아래 apply() 주석 참조


def _link(names, worlds=None):
    have = [n for n in names if n in bpy.data.materials]
    need = [n for n in names if n not in have]
    if need or (worlds and not any(w in bpy.data.worlds for w in worlds)):
        with bpy.data.libraries.load(PROPS, link=False) as (src, dst):
            dst.materials = [n for n in need if n in src.materials]
            if worlds:
                dst.worlds = [w for w in worlds if w in src.worlds]
    return [bpy.data.materials.get(n) for n in names]


def _tile(mat, tile_m, space='obj'):
    """Object 좌표(또는 메시 UV) + Mapping 으로 타일링한다.

    지면 판에는 UV 가 없다. Generated 를 쓰면 576×954 m 판 전체에 텍스처가
    한 장 늘어난다. Object 좌표는 로컬 미터라 scale = 1/tile_m 이면
    tile_m 마다 정확히 한 번 반복된다.

    도로는 다르다. city._ribbon 이 u = 폭 0..1, v = 진행 거리 / ROAD_TEX_M
    로 UV 를 깔아 두므로 space='uv' 로 그 UV 를 그대로 쓴다. 그래야 바퀴
    자국이 길을 따라 흐른다.

    디스플레이스먼트는 끊는다 — 이 크기 판에 걸면 렌더가 폭발하고
    오버데어는 어차피 못 받는다.
    """
    nt = mat.node_tree
    out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if out:
        for l in list(out.inputs['Displacement'].links):
            nt.links.remove(l)
    mp = next((n for n in nt.nodes if n.type == 'MAPPING'), None)
    tc = next((n for n in nt.nodes if n.type == 'TEX_COORD'), None)
    if mp is None:
        mp = nt.nodes.new('ShaderNodeMapping')
        mp.location = (-1000, 0)
    if tc is None:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        tc.location = (-1200, 0)
    for l in list(mp.inputs['Vector'].links):
        nt.links.remove(l)
    nt.links.new(tc.outputs['UV' if space == 'uv' else 'Object'],
                 mp.inputs['Vector'])
    # **vector_type 을 반드시 POINT 로 못박는다.** Poly Haven 애드온은 이걸
    # 'TEXTURE' 로 만들어 두는데, 그 모드에서는 Scale 이 **나누기**로 먹는다.
    # 2.5 m 타일을 노린 scale 0.4 가 실제로는 0.4 m 타일이 되어, 30 m 밖에서
    # 밉맵에 완전히 뭉개져 지면·도로가 **단색 판때기**로 보였다. 타일 크기를
    # 20 m, 170 m 로 바꿔도 그림이 똑같길래 텍스처가 아예 안 붙은 줄 알았다.
    mp.vector_type = 'POINT'
    s = 1.0 / tile_m
    mp.inputs['Scale'].default_value = (s, s, s)
    for nd in nt.nodes:
        if nd.type == 'TEX_IMAGE':
            for l in list(nd.inputs['Vector'].links):
                nt.links.remove(l)
            nt.links.new(mp.outputs['Vector'], nd.inputs['Vector'])


# ------------------------------------------------------------------ 수목 산포
#
# 성 밖이 흙판만 남아 휑했다. 소나무와 바위를 뿌려 채운다.
#   소나무   KCISA CC-BY, 1,969 삼각형 (이미 소품 라이브러리에 있다)
#   바위무리 Poly Haven coast_land_rocks_04, CC0, 2,000 삼각형
#
# Poly Haven boulder_01 은 쓰지 않는다 — 66k 를 COLLAPSE 로 줄이려 했더니
# 23.5k 에서 더 안 내려갔다(조각이 잘게 갈린 스캔은 한계가 있다).
COLL_VEG = "화성_수목"
SEED = 20260813          # 고정 시드 — 빌드마다 같은 배치가 나와야 한다
KEEPOUT_CITY = 155.0     # 도시(반경 150 m) 안에는 뿌리지 않는다
KEEPOUT_SPOT = 34.0      # 화서문·방화수류정·우화관 주변도 비운다
GRID = 26.0              # 격자 간격 m. 격자 위에서 흔들어 규칙성을 깬다


def _normals(mat, strength=1.0):
    """법선맵을 BSDF 에 물린다.

    Poly Haven 애드온은 확산·거칠기만 꽂고 **Normal 은 비워 둔다.** 그래서
    흙길도 잔디도 색만 있고 요철이 없어, 가까이서 보면 색칠한 판때기였다.
    법선을 물리면 같은 텍스처가 태양 아래서 결을 갖는다.

    nor_gl(OpenGL 규약)을 쓴다 — 블렌더가 기대하는 Y+ 방향이다. nor_dx 를
    그대로 물리면 요철이 반대로 파인다.
    """
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None or bsdf.inputs['Normal'].links:
        return False
    tex = next((n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image
                and 'nor_gl' in n.image.name), None)
    if tex is None:
        return False
    tex.image.colorspace_settings.name = 'Non-Color'
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nm.location = (bsdf.location.x - 300, bsdf.location.y - 400)
    nm.inputs['Strength'].default_value = strength
    nt.links.new(tex.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    return True


TINT_SUFFIX = "_tinted"


def _tint(mat, rgb):
    """베이스 컬러에 곱 보정을 건다 — **노드가 아니라 이미지 픽셀에 굽는다.**

    처음엔 이미지와 Principled Base Color 사이에 MixRGB 를 끼웠다. 블렌더
    화면은 맞았지만 **FBX 익스포터는 Base Color 에 직결된 이미지만** 텍스처로
    내보내기 때문에, 보정이 걸린 재질은 diffuse 가 통째로 빠졌다.
    CTR_01.fbx 에 dirt_floor·park_dirt 의 diffuse 는 실렸는데 보정이 걸린
    grass_path_2 만 Rough·nor_gl 만 실린 것이 그 증거다.

    그래서 보정된 사본 이미지를 한 장 만들어 **직결**로 물린다. 화면은 같고
    FBX 에도 실린다. 사본은 pack 해 두므로 .blend 밖 파일에 의존하지 않는다.
    """
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None or not bsdf.inputs['Base Color'].links:
        return
    node = bsdf.inputs['Base Color'].links[0].from_node
    if node.type != 'TEX_IMAGE' or node.image is None:
        return
    src = node.image
    if src.name.endswith(TINT_SUFFIX):
        return                          # 이미 구워진 사본이다
    name = src.name + TINT_SUFFIX
    done = bpy.data.images.get(name)
    if done is None:
        import numpy as np
        w, h = src.size
        done = bpy.data.images.new(name, w, h, alpha=True)
        done.colorspace_settings.name = src.colorspace_settings.name
        # foreach_get + numpy 로 간다. 파이썬 루프로 돌리면 2048² 한 장에
        # 십수 초가 걸린다 (픽셀 1,677만 개).
        buf = np.empty(w * h * 4, dtype=np.float32)
        src.pixels.foreach_get(buf)
        buf = buf.reshape(-1, 4)
        buf[:, 0] *= rgb[0]
        buf[:, 1] *= rgb[1]
        buf[:, 2] *= rgb[2]          # 알파는 그대로 둔다
        done.pixels.foreach_set(buf.ravel())
        done.pack()
    node.image = done


ROCK_MAT = "바위_돌"
ROCK_TINT = (0.62, 0.58, 0.54)   # 흙색을 회색 돌 쪽으로 당긴다


def _rock_material():
    """바위용 돌 재질.

    coast_land_rocks_04 원본 재질에는 **이미지 노드가 아예 없다** — 베이스
    컬러가 기본 0.8 흰색이라 흙판 위에 눈 뭉치처럼 흰 얼룩으로 박혔다.
    새로 내려받는 대신 이미 패킹된 brown_mud_dry 를 복제해 잘게 타일링하고
    색만 돌 쪽으로 당긴다 — 네트워크도 애드온도 필요 없다.
    """
    m = bpy.data.materials.get(ROCK_MAT)
    if m:
        return m
    base = _link(["brown_mud_dry"])[0]
    if base is None:
        return None
    m = base.copy()
    m.name = ROCK_MAT
    _tile(m, 1.2)                     # 바위 크기에 맞는 결
    _normals(m, 1.4)
    _tint(m, ROCK_TINT)
    return m


def scatter():
    """지면 판 위, 도시 바깥에 소나무와 바위를 뿌린다."""
    import math
    import random
    import bmesh
    from mathutils import Matrix, Vector
    from hanok import new_collection
    from .city import _prop_mesh, _stamp, _to_object_multi
    from . import layout

    ground = bpy.data.objects.get("지면_화성")
    if ground is None:
        print("수목 산포 건너뜀: 지면_화성 없음")
        return 0
    cs = [ground.matrix_world @ Vector(b) for b in ground.bound_box]
    x0, x1 = min(c.x for c in cs), max(c.x for c in cs)
    y0, y1 = min(c.y for c in cs), max(c.y for c in cs)

    site = Vector(layout.SITE_ORIGIN)
    spots = []
    for name, b in layout.BUILDINGS.items():
        if name == "도시":
            continue
        u, v = b["uv"]
        lu, lv = b.get("uv_local", (0.0, 0.0))
        spots.append((site.x + u * layout.DIST_SCALE + lu,
                      site.y + v * layout.DIST_SCALE + lv))

    # 지면에 기복이 있으니 나무·바위도 그 자리 표고에 앉혀야 한다.
    from . import dem as _dem
    d = _dem.get("장안문")

    rng = random.Random(SEED)
    coll = new_collection(COLL_VEG)
    picks = {"소나무": [], "바위무리": []}
    nx = int((x1 - x0) / GRID)
    ny = int((y1 - y0) / GRID)
    for i in range(nx):
        for j in range(ny):
            x = x0 + GRID * (i + 0.5) + rng.uniform(-GRID * 0.42, GRID * 0.42)
            y = y0 + GRID * (j + 0.5) + rng.uniform(-GRID * 0.42, GRID * 0.42)
            if math.hypot(x - site.x, y - site.y) < KEEPOUT_CITY:
                continue
            if any(math.hypot(x - sx, y - sy) < KEEPOUT_SPOT for sx, sy in spots):
                continue
            if x < x0 + 6 or x > x1 - 6 or y < y0 + 6 or y > y1 - 6:
                continue            # 판 가장자리는 비워 둔다
            r = rng.random()
            if r < 0.62:
                picks["소나무"].append((x, y, rng.uniform(0, 6.283),
                                      rng.uniform(0.75, 1.35)))
            elif r < 0.80:
                picks["바위무리"].append((x, y, rng.uniform(0, 6.283),
                                       rng.uniform(0.4, 0.9)))
            # 나머지 20% 는 비운다 — 균일하면 심어 놓은 티가 난다

    n = 0
    for name, pts in picks.items():
        if not pts:
            continue
        geom, mats = _prop_mesh(name)
        if geom is None:
            print("  소품 %s 없음" % name)
            continue
        bm = bmesh.new()
        for x, y, rot, s in pts:
            _stamp(bm, geom,
                   Matrix.Translation(Vector(
                       (x, y, 0.0 if d is None
                        else d.surface_at(x - site.x, y - site.y))))
                   @ Matrix.Rotation(rot, 4, 'Z') @ Matrix.Scale(s, 4))
            n += 1
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        if name == "바위무리":
            mats = [_rock_material()]
        # 같은 이름이 이미 있으면 블렌더가 .001 로 만들어 두 벌이 겹친다
        old = bpy.data.objects.get("수목_%s" % name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
        _to_object_multi(bm, "수목_%s" % name, mats, coll)
        if name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    print("수목 산포: 소나무 %d, 바위무리 %d (격자 %.0f m, 시드 %d)"
          % (len(picks["소나무"]), len(picks["바위무리"]), GRID, SEED))
    return n


def apply():
    """씬을 다 세운 뒤에 부른다. 지면·도로 재질과 월드를 갈아끼운다."""
    if not os.path.exists(PROPS):
        print("지형 마감 건너뜀: %s 없음" % PROPS)
        return 0
    mats = _link([m for _, m, _, _, _ in SURFACES], worlds=[WORLD])
    n = 0
    for (obj_name, mat_name, tile, space, tint), mat in zip(SURFACES, mats):
        o = bpy.data.objects.get(obj_name)
        if o is None or mat is None:
            continue
        _tile(mat, tile, space)
        _normals(mat)
        if tint:
            _tint(mat, tint)
        o.data.materials.clear()
        o.data.materials.append(mat)
        n += 1

    w = bpy.data.worlds.get(WORLD)
    if w:
        bpy.context.scene.world = w
    for o in bpy.data.objects:
        if o.type == 'LIGHT' and o.data.type == 'SUN':
            o.data.energy = SUN_ENERGY
            # 지면에 들쭉날쭉한 밝은 얼룩이 났었다. 지형 기복 탓인 줄 알고
            # 지오메트리를 파 봤지만 아니었다 — EEVEE Next 가상 그림자 맵이
            # 540 m 사이트를 기본 1 mm/텍셀로 덮으려다 페이지 풀이 말라
            # 일부 구획에 그림자를 못 그린 것이다(use_shadow 를 끄면 사라졌고
            # 해상도를 **올리면** 더 심해졌다). 이 축척에 맞게 5 cm/텍셀로
            # 낮춘다. 오버데어 익스포트에는 영향이 없다 — 미리보기 조명이다.
            o.data.shadow_maximum_resolution = SHADOW_RES

    print("지형 마감: 표면 %d, 월드 %s, 해 %.1f  (Poly Haven CC0)"
          % (n, WORLD if w else "기본", SUN_ENERGY))
    scatter()
    return n
