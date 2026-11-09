# -*- coding: utf-8 -*-
"""장면을 세워 .blend 로 저장한다. GUI 로 열어 보기 위한 것.

    blender -b -noaudio -P make_blend.py -- <출력.blend> [--old]
"""

import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.join(HERE, 'deoksugung')):
    if p not in sys.path:
        sys.path.insert(0, p)

ARGV = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = ARGV[0] if ARGV else os.path.join(HERE, 'palaces.blend')
OLD = '--old' in ARGV

bpy.ops.wm.read_factory_settings(use_empty=True)

import hanok            # noqa: E402
import roof             # noqa: E402
import build            # noqa: E402

# build.py 가 importlib.reload(roof) 를 하므로 **import 뒤에** 켠다
roof.USE_MULMAE = not OLD
build.roof.USE_MULMAE = not OLD
print("USE_MULMAE = %s" % roof.USE_MULMAE)

hanok.setup_materials()

# 어느 사이트를 세울지. 기본은 **화성만** 이다.
#
# 경복궁·덕수궁은 화성에서 내려다보면 회색 판때기 위에 얹힌 장난감처럼
# 보인다 — 규모가 작고(각각 90×186 m, 300×160 m) 화성 사이트(590×590 m)와
# 나란히 서면 스케일이 안 맞는다. 오버데어 익스포트는 --groups 로 이미
# 화성 그룹만 뽑으므로 반입에는 영향이 없고, 블렌더 화면만 정리된다.
#
# 되살리려면 --all 을 붙이거나 아래 기본값을 바꾼다.
#   blender -b -noaudio -P make_blend.py -- palaces.blend --all
WITH_PALACES = '--all' in ARGV

if WITH_PALACES:
    build.build_all()
    try:
        from deoksugung import build_dsg
        build_dsg.build_all()
    except Exception as e:
        print("덕수궁 건너뜀: %s" % e)
else:
    print("경복궁·덕수궁 건너뜀 (--all 로 켠다)")

# 화성은 절차 생성이 아니라 KCISA 실측 모델을 가져다 쓴다.
# janganmun.blend 가 있어야 한다 — 만드는 법은 hwaseong/heritage.py 주석 참조.
try:
    from hwaseong import build_hs
    build_hs.build_all()
except Exception as e:
    print("화성 건너뜀: %s" % e)

sc = bpy.context.scene

# --- 빛과 하늘
w = bpy.data.worlds.new('sky')
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes['Background']
bg.inputs[0].default_value = (0.42, 0.55, 0.78, 1.0)
bg.inputs[1].default_value = 0.55

sun = bpy.data.lights.new('sun', 'SUN')
sun.energy = 4.0
sun.angle = math.radians(2.0)
so = bpy.data.objects.new("해", sun)
sc.collection.objects.link(so)
so.rotation_euler = (math.radians(52), 0.0, math.radians(-125))

avail = [i.identifier for i in sc.render.bl_rna.properties['engine'].enum_items]
for cand in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
    if cand in avail:
        sc.render.engine = cand
        break
try:
    sc.view_settings.view_transform = 'AgX'
except Exception:
    pass

# --- 미리 앉혀 둔 카메라들. GUI 에서 숫자패드 0 으로 골라 본다.
import mathutils                                          # noqa: E402
SJY = build.SAJEONGJEON_Y
CAMS = [
    ("카메라_사정전", (26.0, SJY - 30.0, 11.0), (0.0, SJY, 7.0), 42.0),
    ("카메라_처마밑", (3.0, SJY - 12.5, 1.5), (0.0, SJY - 4.0, 8.4), 30.0),
    ("카메라_근정전", (44.0, -52.0, 20.0), (0.0, 0.0, 13.0), 42.0),
    ("카메라_덕수궁", (606.0, 18.0, 22.0), (602.0, 50.0, 6.0), 38.0),
    # 화성 장안문 — 성 바깥(-Y)에서 옹성 너머로 문루를 본다. 사이트 원점 x=1200.
    ("카메라_장안문", (1232.0, -58.0, 28.0), (1200.0, -4.0, 12.0), 40.0),
    # 팔달문은 남문이라 바깥이 +Y. 사이트 로컬 (0, 1200) 에 있다.
    ("카메라_팔달문", (1232.0, 1258.0, 28.0), (1200.0, 1204.0, 12.0), 40.0),
    ("카메라_우화관", (1112.0, 570.0, 16.0), (1080.0, 600.0, 5.0), 42.0),
    # 의궤로 세운 것들. 사이트 로컬 uv × DIST_SCALE(0.35) + 원점 1200.
    #   화서문 (990, 122)  공심돈 (984, 88)  방화수류정 (1382, 63)
    ("카메라_화서문", (938.0, 96.0, 26.0), (988.0, 116.0, 9.0), 34.0),
    ("카메라_공심돈", (958.0, 66.0, 15.0), (984.0, 88.0, 7.0), 40.0),
    ("카메라_방화수류정", (1414.0, 18.0, 22.0), (1380.0, 62.0, 8.0), 36.0),
    # OSM 실측 도시. 장안문(사이트 원점)을 중심으로 반경 100 m 를 내려다본다.
    ("카메라_도시", (1310.0, -150.0, 105.0), (1198.0, -6.0, 6.0), 30.0),
    ("카메라_도시_가로", (1246.0, -44.0, 6.5), (1200.0, -12.0, 9.0), 34.0),
]
for nm, loc, look, lens in CAMS:
    cd = bpy.data.cameras.new(nm)
    cd.lens = lens
    # 기본 far clip 이 100 m 라 도시·전경 샷이 통째로 잘린다. 실제로 당했다.
    cd.clip_start, cd.clip_end = 0.5, 20000.0
    cam = bpy.data.objects.new(nm, cd)
    sc.collection.objects.link(cam)
    cam.location = loc
    d = mathutils.Vector(look) - mathutils.Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
sc.camera = bpy.data.objects["카메라_사정전"]

# --- 지형 마감. 씬·조명을 다 세운 **뒤에** 부른다 (월드와 태양을 갈아끼운다).
try:
    from hwaseong import terrain
    terrain.apply()
except Exception as e:
    print("지형 마감 건너뜀: %s" % e)

tris = sum(sum(max(0, len(p.vertices) - 2) for p in o.data.polygons)
           for o in bpy.data.objects if o.type == 'MESH')
print("SCENE %d 메시 / %d 삼각형" % (
    len([o for o in bpy.data.objects if o.type == 'MESH']), tris))

bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("SAVED %s (%.1f MB)" % (OUT, os.path.getsize(OUT) / 1e6))
