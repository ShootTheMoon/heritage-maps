# -*- coding: utf-8 -*-
"""장면을 세우고 보여줄 샷을 찍는다.

    blender -b -noaudio -P show.py -- <출력폴더> [--old]

--old 를 주면 물매 스위치를 꺼서 예전 지붕으로 찍는다. 같은 카메라·같은 빛으로
두 벌을 찍어야 비교가 된다.
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
OUT = ARGV[0] if ARGV else '.'
OLD = '--old' in ARGV
TAG = 'old' if OLD else 'new'
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)

import hanok            # noqa: E402
import roof             # noqa: E402
import build            # noqa: E402

# **build 를 import 한 뒤에 켠다.** build.py 가 importlib.reload(roof) 를 하므로
# 그 전에 켜면 모듈이 다시 실행되면서 플래그가 False 로 되돌아간다.
roof.USE_MULMAE = not OLD
build.roof.USE_MULMAE = not OLD          # reload 로 갈린 참조까지 맞춘다
print("USE_MULMAE = %s" % roof.USE_MULMAE)

hanok.setup_materials()
build.build_all()
try:
    from deoksugung import build_dsg
    build_dsg.build_all()
except Exception as e:
    print("덕수궁 건너뜀: %s" % e)

tris = sum(sum(max(0, len(p.vertices) - 2) for p in o.data.polygons)
           for o in bpy.data.objects if o.type == 'MESH')
print("SCENE %s : %d 오브젝트 / %d 삼각형"
      % (TAG, len([o for o in bpy.data.objects if o.type == 'MESH']), tris))


# ------------------------------------------------------------------ 렌더 설정
sc = bpy.context.scene
avail = [i.identifier for i in sc.render.bl_rna.properties['engine'].enum_items]
for cand in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
    if cand in avail:
        sc.render.engine = cand
        break
if sc.render.engine == 'CYCLES':
    sc.cycles.samples = 24

# 하늘. 노드가 켜져 있으면 world.color 는 무시되므로 노드를 쓴다.
w = bpy.data.worlds.new('sky')
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes['Background']
bg.inputs[0].default_value = (0.42, 0.55, 0.78, 1.0)
bg.inputs[1].default_value = 0.55

sun = bpy.data.lights.new('sun', 'SUN')
sun.energy = 4.0
sun.angle = math.radians(2.0)
so = bpy.data.objects.new('sun', sun)
sc.collection.objects.link(so)
so.rotation_euler = (math.radians(52), 0.0, math.radians(-125))

vs = sc.view_settings
try:
    vs.view_transform = 'AgX'          # 동적 OCIO 열거라 enum_items 로는 안 보인다
except Exception:
    pass
vs.look = 'None'
vs.exposure = 0.0

sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.render.image_settings.file_format = 'PNG'


def shot(name, loc, look_at, lens=42.0, res=(1600, 900)):
    import mathutils
    for o in list(bpy.data.objects):
        if o.type == 'CAMERA':
            bpy.data.objects.remove(o, do_unlink=True)
    cd = bpy.data.cameras.new('c')
    cd.lens = lens
    cam = bpy.data.objects.new('c', cd)
    sc.collection.objects.link(cam)
    cam.location = loc
    d = mathutils.Vector(look_at) - mathutils.Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    path = os.path.join(OUT, '%s_%s.png' % (name, TAG))
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("SHOT %s" % path)


# 사정전 — 물매 꺾임이 가장 잘 보이는 단층 팔작
SJY = build.SAJEONGJEON_Y
shot('01_사정전', (26.0, SJY - 30.0, 11.0), (0.0, SJY, 7.0))
# 처마 밑 — 서까래 마구리가 두 줄로 층져 보여야 한다 (CP-2 게이트 ②)
shot('02_처마밑', (3.0, SJY - 12.5, 1.5), (0.0, SJY - 4.0, 8.4), lens=30.0)
# 근정전 — 중층
shot('03_근정전', (44.0, -52.0, 20.0), (0.0, 0.0, 13.0))
# 덕수궁 세 채
shot('04_덕수궁', (600.0 + 6.0, 18.0, 22.0), (600.0 + 2.0, 50.0, 6.0), lens=38.0)
