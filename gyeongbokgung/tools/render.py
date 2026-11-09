# -*- coding: utf-8 -*-
"""조명 · 카메라 · 렌더 설정."""

import bpy
import math
from mathutils import Euler, Vector

DIR = r"C:\Users\HSP\Desktop\blender\gyeongbokgung"


def setup_world():
    """Nishita 하늘 + 부드러운 대기."""
    w = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    sky = nt.nodes.new("ShaderNodeTexSky")
    # Blender 5.x 에서 Nishita 는 MULTIPLE_SCATTERING 으로 이름이 바뀌었다
    types = [i.identifier for i in
             sky.bl_rna.properties['sky_type'].enum_items]
    sky.sky_type = ('MULTIPLE_SCATTERING' if 'MULTIPLE_SCATTERING' in types
                    else types[0])
    for attr, val in (("sun_elevation", math.radians(34)),
                      ("sun_rotation", math.radians(-42)),
                      ("altitude", 120),
                      ("air_density", 1.4),
                      ("dust_density", 2.2),
                      # 태양 램프를 따로 두므로 하늘의 태양 원반은 끈다
                      ("sun_disc", False)):
        if hasattr(sky, attr):
            setattr(sky, attr, val)
    bg = nt.nodes.new("ShaderNodeBackground")
    # 물리 하늘은 자체 휘도가 수십에 달해, 그대로 두면 앰비언트가 장면을
    # 덮어 음영이 사라진다. 하늘빛은 보조로만 쓴다.
    bg.inputs[1].default_value = 0.12
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(sky.outputs[0], bg.inputs[0])
    nt.links.new(bg.outputs[0], out.inputs[0])


def setup_sun():
    sun = bpy.data.objects.get("태양")
    if sun is None:
        sd = bpy.data.lights.new("태양", 'SUN')
        sun = bpy.data.objects.new("태양", sd)
        bpy.context.scene.collection.objects.link(sun)
    sun.data.energy = 3.0
    sun.data.angle = math.radians(1.5)
    sun.data.color = (1.0, 0.95, 0.86)
    sun.rotation_euler = Euler((math.radians(56), 0, math.radians(-42)), 'XYZ')
    for junk in ("TestSun",):
        o = bpy.data.objects.get(junk)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)
    return sun


def interior_lights(on):
    """내부 촬영용 보조광."""
    for name, loc in (("내부광_근정전", (0, 2.0, 6.5)),
                      ("내부광_사정전", (0, 76.5, 4.2))):
        lo = bpy.data.objects.get(name)
        if lo is None:
            ld = bpy.data.lights.new(name, 'AREA')
            ld.shape = 'RECTANGLE'
            ld.size, ld.size_y = 12.0, 8.0
            ld.energy = 700
            ld.color = (1.0, 0.88, 0.72)
            lo = bpy.data.objects.new(name, ld)
            bpy.context.scene.collection.objects.link(lo)
            lo.location = loc
        lo.data.energy = 700
        lo.hide_render = not on


def setup_render(res=(1400, 900), samples=48):
    sc = bpy.context.scene
    engines = [i.identifier for i in
               bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    sc.render.engine = ('BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in engines
                        else 'BLENDER_EEVEE')
    ee = getattr(sc, 'eevee', None)
    if ee:
        for attr, val in (("taa_render_samples", samples),
                          ("use_shadows", True),
                          ("use_raytracing", True)):
            if hasattr(ee, attr):
                setattr(ee, attr, val)
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    # view_transform 은 OCIO 가 채우는 동적 enum 이라 enum_items 로는
    # 확인되지 않는다(항상 NONE 하나만 보고됨). 실제로 넣어 보고 판단한다.
    chosen = None
    for want in ('AgX', 'Filmic', 'Standard'):
        try:
            sc.view_settings.view_transform = want
            chosen = want
            break
        except TypeError:
            continue
    sc.view_settings.exposure = -0.35 if chosen == 'AgX' else -0.7
    return chosen


def camera():
    cam = bpy.data.objects.get("카메라")
    if cam is None:
        cd = bpy.data.cameras.new("카메라")
        cam = bpy.data.objects.new("카메라", cd)
        bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    old = bpy.data.objects.get("TestCam")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    return cam


# 오일러 각을 손으로 넣으면 방향을 틀리기 쉬워, 바라볼 지점으로 지정한다.
SHOTS = {
    "01_근정전_정면":  dict(loc=(0, -62, 22),    at=(0, 0, 12),    lens=50, inside=False),
    "02_근정전_사각":  dict(loc=(46, -56, 34),   at=(0, 0, 12),    lens=45, inside=False),
    "03_조정_어도":    dict(loc=(0, -84, 5.0),   at=(0, -6, 13),   lens=38, inside=False),
    "04_근정전_처마":  dict(loc=(24, -34, 13),   at=(4, -12, 16),  lens=70, inside=False),
    "05_근정전_어좌":  dict(loc=(0, -7.5, 5.2),  at=(0, 4.0, 4.2), lens=30, inside=True),
    "06_사정전":       dict(loc=(24, 50, 15),    at=(0, 75, 6),    lens=48, inside=False),
    "07_사정전_어좌":  dict(loc=(0, 69.5, 3.4),  at=(0, 77, 2.6),  lens=30, inside=True),
    "08_전경":         dict(loc=(105, -108, 96), at=(0, 20, 10),   lens=42, inside=False),
}


def aim(cam, loc, at):
    """카메라를 loc 에 두고 at 을 바라보게 한다."""
    cam.location = Vector(loc)
    d = Vector(at) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def render_all(only=None):
    setup_world()
    setup_sun()
    setup_render()
    cam = camera()
    done = []
    for name, s in SHOTS.items():
        if only and name not in only:
            continue
        interior_lights(s["inside"])
        aim(cam, s["loc"], s["at"])
        cam.data.lens = s["lens"]
        bpy.context.scene.render.filepath = "%s\\%s.png" % (DIR, name)
        bpy.ops.render.render(write_still=True)
        done.append(name)
    return done
