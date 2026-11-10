# -*- coding: utf-8 -*-
"""KCISA 장안문 모델 — 수급 · 정규화 · 감축.

여기 있는 상수는 전부 **모델을 실제로 재서 얻은 값**이다. 추정이 아니다.
한 번 돌리면 janganmun.blend 가 나오고, 그 뒤로는 build_hs 가 그것만 읽는다.

────────────────────────────────────────────────────────────────────────
출처
  스케치팹 UID 807b2e1a414c4db4989ec1c0365dba89
  한국문화정보원(KCISA) @kcisameta, **CC BY 4.0** — 출처 표시 의무
  원본 1,675,036 삼각형 / 67 오브젝트 / 50 머티리얼 (각 1024² PBR)

이 모델은 포토그래메트리 덩어리가 아니라 부재별로 분리된 UE 제작 에셋이다
(MI_ = Material Instance). 그래서 재질별로 메시가 이미 갈려 있고,
오버데어 MeshPart 가 텍스처를 하나만 받는 구조와 잘 맞는다.
────────────────────────────────────────────────────────────────────────
"""

import math
import re
from collections import defaultdict

UID = "807b2e1a414c4db4989ec1c0365dba89"
ATTRIBUTION = "3D 모델: 한국문화정보원(KCISA), CC BY 4.0"

# ---------------------------------------------------------------- 스케일
#
# blender-mcp 의 download_sketchfab_model 은 최대 변을 target_size 로 **강제
# 정규화**한다. 실측 모델인데 임의 배율이 씌워지는 셈이라 되돌려야 한다.
#
# target_size=40 으로 받았을 때 보고된 배율이 0.244064 였다.
#   원본 최대 변 = 40 / 0.244064 = 163.89
# 원본이 이미 미터인지 확인해야 한다. 같은 비율로 높이를 환산하면
#   Z = 5.521 / 0.244064 = 22.62 m
# 장안문은 우리나라 성문 중 가장 크고 **숭례문(약 22 m)보다 높다**.
# 22.62 m 는 이 사실과 맞고, 다른 어떤 단위 가정도 맞지 않는다
# (cm 로 보면 1.6 m, 척으로 보면 50 m — 둘 다 말이 안 된다).
# → 원본 glTF 는 실측 미터다. 다운로더 배율만 되돌리면 된다.
DOWNLOAD_TARGET = 40.0
DOWNLOAD_FACTOR = 0.244064          # 위 target_size 로 받았을 때 보고된 값
RESTORE = 1.0 / DOWNLOAD_FACTOR     # ≈ 4.0973

# ---------------------------------------------------------------- 기준면
#
# z 히스토그램과 오브젝트별 최저점으로 찾았다. 계단(G_Stair)·금속문
# (G_MetalDoor)·홍예(G_Arch)·성벽(Fortification)이 **전부 정확히 같은 z**
# 에서 시작한다 — 저작자가 잡아 둔 지면이다. 그 아래 0.51 m 는 기초라
# 묻혀도 된다.
# 장안문은 -12.96, 팔달문은 -20.44 로 서로 다르다. 그래서 상수로 박지 않고
# find_ground() 가 **최빈 최저점**으로 잰다 — 계단·금속문·홍예·성벽처럼 땅에
# 닿는 부재들이 전부 정확히 같은 z 에서 시작하는 것이 저작자가 잡아 둔 지면이다.
YAW_DEG = -90.0                     # 옹성(성 바깥)이 -Y 를 보도록. 저작 규약

# 정규화 결과 (검산용)
EXTENT_M = (163.89, 60.49, 22.62)   # X 성벽 방향, Y 성 안팎, Z 높이
# 경복궁 일곽이 84 × 176 m 였으니 같은 급이다.

# ---------------------------------------------------------------- 감축
#
# 원본 167만은 경복궁 전체 출고량(589,412)의 2.9배다. 그대로 넣으면
# 화성 하나가 궁궐 세 채를 먹는다.
#
# 균일 비율은 낭비다. 공포(ComplexBracket)는 40만 삼각형으로 예산의 24% 를
# 먹는데 화면에서는 처마 밑 그림자에 묻히고, 지붕은 절반 값에 실루엣을
# 전부 만든다. 역할별로 비율을 갈랐다.
ORNAMENT = ("Flag", "RoofStatue", "Cannon", "ComplexBracket", "Note", "Signboard")
ROOFISH = ("Roof", "Rafter", "RoofBoard", "Ridge", "Purlin", "PurlinSupport",
           "B_RoofBoard", "G_RoofBoard")
STRUCT = ("CastleWall", "Parapet", "Fortification", "GateHouse", "CW_",
          "Column", "Floor", "Arch", "Stair", "Wall", "RammedEarth", "Pedestal")

# 예산 기준은 **경복궁 실적 589,412 삼각형**이다. 화성 하나가 궁궐 한 채
# 분량을 쓰는 셈이고, 그 이상은 스튜디오에 손으로 임포트할 파일만 늘어난다.
# 처음엔 416k(비율 0.12/0.25/0.45/0.40)로 잡았다가 완성도 우선으로 올렸다.
RATIO_ORNAMENT, RATIO_ROOF, RATIO_STRUCT, RATIO_DEFAULT = 0.20, 0.35, 0.60, 0.55
MIN_TRIS = 1500                     # 이보다 싼 부재는 건드리지 않는다

# 위 비율의 실측 결과: 1,675,036 → 약 58만 (경복궁 589,412 과 같은 급)


def base_name(mat):
    """MI_T_B_GateHouse_001 -> B_GateHouse_001. CW_ 같은 의미 있는 접두사는 남긴다."""
    return re.sub(r'^MI_(T_)?', '', mat).replace('.', '_') or "Misc"


def ratio_for(mat):
    m = base_name(mat)
    if any(k in m for k in ORNAMENT):
        return RATIO_ORNAMENT
    if any(m.startswith(k) or ("_" + k) in m for k in ROOFISH):
        return RATIO_ROOF
    if any(k in m for k in STRUCT):
        return RATIO_STRUCT
    return RATIO_DEFAULT


# ---------------------------------------------------------------- 그룹 분할
#
# sites.py HSF['collections'] 의 키와 **정확히** 같아야 한다.
# 다르면 export_overdare.group_of 가 MISC 로 떨어뜨린다.
PROPS = ("Flag", "Cannon", "Note", "Signboard", "GateGuardPost")
STONE = ("B_", "CW_", "G_", "GH_", "Fortification", "RammedEarth", "Pedestal")

COLL_GATE, COLL_WALL, COLL_PROP = "화성_장안문", "화성_성벽", "화성_소품"

# 건물마다 컬렉션 세트가 다르다. 같은 컬렉션에 섞으면 sites.group_of 가
# 팔달문 부재를 장안문 그룹으로 분류한다 — sites.py 가 막으려던 바로 그 오분류다.
JANGAN = (COLL_GATE, COLL_WALL, COLL_PROP)
PALDAL = ("화성_팔달문", "화성_팔달문_성벽", "화성_팔달문_소품")


def collection_for(mat, colls=JANGAN):
    gate, wall, prop = colls
    m = base_name(mat)
    if any(k in m for k in PROPS):
        return prop
    if any(m.startswith(k) for k in STONE):
        return wall
    return gate


# ------------------------------------------------------------------ bpy 구간
# 여기서부터는 Blender 안에서만 쓴다. 위쪽 상수/함수는 bpy 없이 import 된다.


def find_ground(objs, tol=0.02):
    """저작자가 잡아 둔 지면 z 를 잰다.

    땅에 닿는 부재(계단·금속문·홍예·성벽)는 전부 **정확히 같은 z** 에서
    시작한다. 그 최빈값이 지면이다. 그 아래로 내려가는 것(기초)은 소수다.
    최저점을 그냥 쓰면 기초 깊이만큼 통째로 떠오른다.
    """
    from mathutils import Vector
    from collections import Counter
    c = Counter()
    for o in objs:
        z0 = min((o.matrix_world @ Vector(b)).z for b in o.bound_box)
        c[round(z0 / tol)] += 1
    return max(c.items(), key=lambda kv: (kv[1], -kv[0]))[0] * tol


def normalise(objs, restore=RESTORE, gate_mats=None, yaw_deg=YAW_DEG, ground=None):
    """다운로드 직후의 오브젝트들을 실측 미터·저작 규약으로 되돌린다.

    1) 부모 empty 체인을 끊고(트랜스폼 유지) 다운로더 배율을 되돌린다
    2) 지면을 z=0 으로, 건물 중심을 원점으로
    3) 옹성(성 바깥)이 -Y 를 보도록 yaw
    4) 트랜스폼을 굽는다 — 익스포터 preflight 가 비단위 스케일과 미러를 잡는다

    restore 는 모델마다 다르다 — 다운로더가 보고한 배율의 역수를 넘긴다.
    gate_mats 를 주면 그 부재들의 bbox 중심을 원점으로 삼는다. 없으면 전체 중심.
    yaw_deg 도 모델마다 다르다. 성문은 성벽이 Y 로 뻗은 채 들어와서 -90 이
    맞지만, 우화관처럼 정면이 이미 X 로 긴 건물은 돌리면 오히려 틀어진다.
    """
    import bpy
    from mathutils import Vector, Matrix

    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

    for o in objs:
        o.scale = [s * restore for s in o.scale]
        o.location = [v * restore for v in o.location]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    def gbox(names=None):
        cs = []
        for o in objs:
            if names and not (o.data.materials
                              and o.data.materials[0].name in names):
                continue
            cs += [o.matrix_world @ Vector(c) for c in o.bound_box]
        return (Vector((min(c.x for c in cs), min(c.y for c in cs), min(c.z for c in cs))),
                Vector((max(c.x for c in cs), max(c.y for c in cs), max(c.z for c in cs))))

    mn, mx = gbox(gate_mats)
    ctr = (mn + mx) / 2
    # find_ground 는 성문에서만 믿을 수 있다. 우화관처럼 부재 대부분이 기단
    # **위**에서 시작하는 단일 건물은 마루 높이를 지면으로 오인한다
    # (실제로 5.16 m 띄웠다). 그런 모델은 ground 를 직접 넘긴다.
    if ground is None:
        ground = find_ground(objs)

    M = (Matrix.Rotation(math.radians(yaw_deg), 4, 'Z')
         @ Matrix.Translation(Vector((-ctr.x, -ctr.y, -ground))))
    for o in objs:
        o.matrix_world = M @ o.matrix_world
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return objs


def decimate(objs, overrides=None):
    """역할별 비율로 Decimate 모디파이어를 건다. 적용은 익스포터가 한다.

    use_collapse_triangulate=False — 켜면 UV 가 찢어진다. 이 모델은 색이
    전부 텍스처에 있어서 UV 가 깨지면 아무 의미가 없다.
    """
    import bpy
    for o in objs:
        for m in [m for m in o.modifiers if m.type == 'DECIMATE']:
            o.modifiers.remove(m)
        if sum(max(0, len(p.vertices) - 2) for p in o.data.polygons) <= MIN_TRIS:
            continue
        mat = o.data.materials[0].name if o.data.materials else "Misc"
        # overrides 는 {머티리얼_부분문자열: 비율}. 모델마다 예산이 한쪽으로
        # 쏠릴 때 쓴다 — 우화관은 지붕 한 덩어리가 78만으로 모델의 80% 다.
        r = ratio_for(mat)
        for k, v in (overrides or {}).items():
            if k in mat:
                r = v
                break
        d = o.modifiers.new("데시메이트", 'DECIMATE')
        d.decimate_type = 'COLLAPSE'
        d.ratio = r
        d.use_collapse_triangulate = False
    return objs


def strip_to_basecolor():
    """색 맵만 남기고 노멀·러프니스·스페큘러 텍스처를 끊는다.

    **오버데어 MeshPart 는 TextureId 를 하나만 받는다** (ovdr_level.ps1).
    노멀을 구워 봐야 받아 줄 자리가 없는데 FBX 용량만 3배가 된다.
    장안문은 머티리얼이 50개라 이 차이가 수십 MB다.

    덤으로 image.copy() 함정도 여기서 피한다 — 복사본은 원본의 packed 바이트를
    그대로 물고 오므로, 크기를 줄여도 FBX 는 원본을 굽는다. 원본 이미지를
    그대로 쓰고 노드만 끊으면 그 문제가 아예 생기지 않는다.
    """
    import bpy
    KEEP = ("baseColor", "diffuse", "albedo", "BaseColor")
    kept, cut = set(), 0
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        for n in list(mat.node_tree.nodes):
            if n.type != 'TEX_IMAGE':
                continue
            nm = n.image.name if n.image else ""
            if any(k in nm for k in KEEP):
                kept.add(nm)
            else:
                mat.node_tree.nodes.remove(n)
                cut += 1
    # 참조가 끊긴 이미지는 .blend 에 남아 용량만 먹는다
    for im in list(bpy.data.images):
        if im.users == 0 and im.name not in kept:
            bpy.data.images.remove(im)
    return len(kept), cut


def organise(objs, colls=JANGAN, label="장안문"):
    """이름을 붙이고 익스포트 그룹 컬렉션으로 나눈다. 통계를 돌려준다."""
    import bpy
    made = {}
    for n in colls:
        c = bpy.data.collections.get(n) or bpy.data.collections.new(n)
        if n not in {x.name for x in bpy.context.scene.collection.children}:
            bpy.context.scene.collection.children.link(c)
        made[n] = c

    seen = defaultdict(int)
    for o in sorted(objs, key=lambda x: x.name):
        mat = o.data.materials[0].name if o.data.materials else "Misc"
        if mat == "WorldGridMaterial":      # UE 기본 머티리얼 조각. 4 삼각형짜리 쓰레기
            bpy.data.objects.remove(o, do_unlink=True)
            continue
        b = base_name(mat)
        seen[b] += 1
        o.name = "%s_%s_%02d" % (label, b, seen[b])
        o.data.name = o.name + "_mesh"
        for c in list(o.users_collection):
            c.objects.unlink(o)
        made[collection_for(mat, colls)].objects.link(o)

    dg = bpy.context.evaluated_depsgraph_get()
    stat = {}
    for n, c in made.items():
        t = 0
        for o in c.objects:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            t += sum(max(0, len(p.vertices) - 2) for p in me.polygons)
            ev.to_mesh_clear()
        stat[n] = (len(c.objects), t)
    return stat
