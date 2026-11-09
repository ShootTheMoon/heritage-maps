# -*- coding: utf-8 -*-
"""CP-2 시각 게이트 — 사정전 지붕을 옛 곡선/새 물매 두 벌로 만들어 비교한다.

    blender -b -noaudio -P compare_profile.py -- <출력폴더>

지붕 종단면 오류는 **셰이딩 렌더에서 안 보이고 실루엣에서 대번 보인다.**
그래서 건물만 검정, 배경 흰색으로 정투영 측면을 찍는다.
숫자 비교도 같이 찍어 눈과 수치가 어긋나지 않는지 본다.
"""

import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.join(HERE, 'deoksugung')):
    if p not in sys.path:
        sys.path.insert(0, p)

import hanok                                            # noqa: E402
import roof                                             # noqa: E402
from roofprofile import RoofProfile                      # noqa: E402

OUT = (sys.argv[sys.argv.index('--') + 1:] or ['.'])[0] if '--' in sys.argv else '.'
os.makedirs(OUT, exist_ok=True)

# --- 사정전 제원. **build.py 에서 직접 읽는다.**
# 손으로 옮겨 적었다가 값을 잘못 지어내는 바람에 멀쩡한 치수표를 틀렸다고
# 보고한 적이 있다. 표를 두 벌 두지 않는다.
import re
_src = open(os.path.join(HERE, 'build.py'), encoding='utf-8').read()
_m = re.search(r'^SJ\s*=\s*dict\((.*?)^\)', _src, re.S | re.M)
SJ = eval("dict(%s)" % re.sub(r'#.*', '', _m.group(1)), {'dict': dict})
W, D = sum(SJ['bays_x']), sum(SJ['bays_y'])
EO = SJ['eave_out']
EAVE, RIDGE = SJ['eave'], SJ['ridge']
RW, RD = W + 2 * EO, D + 2 * EO
print("사정전  정면 %.1f  측면 %.1f  처마 %.2f  처마고 %.2f  용마루 %.2f"
      % (W, D, EO, EAVE, RIDGE))

# 부연 내밀기 — 실측 비 0.383~0.45 의 중앙 0.40 → b = E·f/(1+f)
F = 0.40
B = EO * F / (1.0 + F)

# 표값 그대로 쓴다. audit_roofs.py 로 확인했듯 사정전은 지름 5.9치 / a/R 0.15 로
# 정상 범위 안이다 (걸리는 건 석어당 상층뿐이었고, 그건 실측으로 고쳤다).
prof = RoofProfile(R=RD / 2.0, h0=EAVE, h1=RIDGE, b=B, jouro=0.03, name='사정전')
print("PROFILE  " + prof.describe())
for m in prof.assert_sane(strict=False):
    print("  경고: " + m)
RIDGE_NEW = RIDGE

print("\n  r(m)    옛 z      새 z     옛기울기  새기울기")
import math
hd = RD / 2.0
for i in range(11):
    r = hd * i / 10.0
    old = EAVE + (RIDGE - EAVE) * ((1.0 - r / hd) ** 1.42)
    e = 1e-3
    o0 = EAVE + (RIDGE - EAVE) * ((1.0 - max(0, r - e) / hd) ** 1.42)
    o1 = EAVE + (RIDGE - EAVE) * ((1.0 - min(hd, r + e) / hd) ** 1.42)
    os_ = math.degrees(math.atan((o0 - o1) / (min(hd, r + e) - max(0, r - e))))
    print("  %5.2f  %7.3f  %7.3f   %6.1f°   %6.1f°"
          % (r, old, prof.z(r), os_, prof.slope_deg(r)))


def build_one(name, profile, x_off, ridge):
    coll = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)
    # 합각 높이 h2 와 마루 스윕이 아직 h1 을 직접 쓰므로 반드시 일치시켜 넘긴다
    roof.build_hip_gable_roof(name, coll, RW, RD, EAVE, ridge,
                              ridge_ratio=0.54, gable_ratio=0.50,
                              lift=0.95, out=0.52, profile=profile,
                              eave_out=EO, rafter_pitch=0.31)
    for o in coll.objects:
        o.location.x += x_off
    return coll


def silhouette(coll_names, path, ortho_scale, loc, rot):
    """건물만 검정 / 배경 흰색인 정투영 샷."""
    sc = bpy.context.scene
    for o in list(bpy.data.objects):
        if o.type == 'CAMERA':
            bpy.data.objects.remove(o, do_unlink=True)
    cam_d = bpy.data.cameras.new('c')
    cam_d.type = 'ORTHO'
    cam_d.ortho_scale = ortho_scale
    cam = bpy.data.objects.new('c', cam_d)
    sc.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = rot
    sc.camera = cam

    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light = 'FLAT'
    sh.color_type = 'SINGLE'
    sh.single_color = (0.0, 0.0, 0.0)
    sh.show_shadows = False
    sh.show_cavity = False
    sc.world = sc.world or bpy.data.worlds.new('w')
    sc.world.color = (1.0, 1.0, 1.0)
    sc.render.film_transparent = False
    sc.render.resolution_x, sc.render.resolution_y = 1600, 700
    sc.render.filepath = path
    sc.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)
    print("SHOT %s" % path)


bpy.ops.wm.read_factory_settings(use_empty=True)
hanok.setup_materials()

c_old = build_one("옛곡선", None, 0.0, RIDGE)
c_new = build_one("새물매", prof, 0.0, RIDGE_NEW)

# 측면(YZ) 정투영 — 종단면 형상이 그대로 실루엣이 된다.
# 정면(XZ)에서는 용마루가 수평선이라 물매가 아예 안 보인다.
# 두 벌을 같은 자리에 겹쳐 두고 번갈아 숨긴다 — 크기 비교가 정확해진다.
HALF = math.pi / 2.0
for tag, keep in (('old', c_old), ('new', c_new)):
    for c in (c_old, c_new):
        for o in c.objects:
            o.hide_render = (c is not keep)
    silhouette(None, os.path.join(OUT, 'cp2_side_%s.png' % tag),
               ortho_scale=24.0, loc=(-70.0, 0.0, 7.0),
               rot=(HALF, 0.0, -HALF))

# --- CP-2 게이트 ② : 처마 밑에서 올려다본 샷.
# 서까래 마구리가 **두 줄로 층져** 보여야 한다. 실루엣으로는 판정할 수 없고
# 셰이딩이 필요하다.
def underside(keep, path):
    for c in (c_old, c_new):
        for o in c.objects:
            o.hide_render = (c is not keep)
    sc = bpy.context.scene
    for o in list(bpy.data.objects):
        if o.type in ('CAMERA', 'LIGHT'):
            bpy.data.objects.remove(o, do_unlink=True)
    cd = bpy.data.cameras.new('u')
    cd.lens = 30.0
    cam = bpy.data.objects.new('u', cd)
    sc.collection.objects.link(cam)
    # 처마 바깥 아래쪽에서 처마선을 향해
    cam.location = (2.0, -(RD / 2.0 + 5.5), 1.4)
    cam.rotation_euler = (1.22, 0.0, 0.10)
    sc.camera = cam
    sun = bpy.data.lights.new('s', 'SUN')
    sun.energy = 3.0
    so = bpy.data.objects.new('s', sun)
    sc.collection.objects.link(so)
    so.rotation_euler = (1.05, 0.0, -0.7)
    # 엔진 이름은 빌드마다 다르다 (EEVEE / EEVEE_NEXT). 열거값에서 고른다.
    avail = [i.identifier for i in
             sc.render.bl_rna.properties['engine'].enum_items]
    for cand in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
        if cand in avail:
            sc.render.engine = cand
            break
    if sc.render.engine == 'CYCLES':
        sc.cycles.samples = 16
    sc.world = sc.world or bpy.data.worlds.new('w')
    sc.world.color = (0.55, 0.62, 0.75)
    sc.render.resolution_x, sc.render.resolution_y = 1500, 900
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("SHOT %s" % path)


for tag, keep in (('old', c_old), ('new', c_new)):
    try:
        underside(keep, os.path.join(OUT, 'cp2_under_%s.png' % tag))
    except Exception as e:
        print("처마밑 샷 실패(%s): %s" % (tag, e))

tris = sum(sum(max(0, len(p.vertices) - 2) for p in o.data.polygons)
           for o in bpy.data.objects if o.type == 'MESH')
print("TRIS %d (두 벌 합계)" % tris)
