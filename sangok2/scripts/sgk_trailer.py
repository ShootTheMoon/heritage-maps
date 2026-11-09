# -*- coding: utf-8 -*-
r"""
sgk_trailer.py — SGK(산곡 II) 트레일러. 익스포트 FBX(06_OVERDARE) 만으로 조립(sgk_engine_view.build) → 새벽 분위기 → 카메라 5샷 → MP4.

  blender.exe -b --python _scripts\sgk_trailer.py -- [preview]      # preview: 절반 해상도·스텝 4
결과: 04_Previews\trailer\SGK_trailer.mp4 (+ 샷별 스틸 trailer_shotN.png)
"""
import bpy, os, sys, math
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sgk_layout as L
import sgk_engine_view as EV

PREVIEW = "preview" in sys.argv
FPS = 24
OUT = os.path.join(EV.OUT, "trailer"); os.makedirs(OUT, exist_ok=True)

sc = EV.build()
h = L.height_at

# ------------------------------------------------------------------ 분위기: 새벽 역광 + 안개 + 볼륨
sun = bpy.data.objects["EV_S"]; sun.data.energy = 7.0; sun.data.angle = 0.6; sun.data.color = (1.0, 0.78, 0.55)
sun.rotation_euler = (math.radians(72), 0, math.radians(35))       # 낮은 해(고도 18°), 동북동에서
w = sc.world; nt = w.node_tree; nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputWorld"); bg = nt.nodes.new("ShaderNodeBackground")
sky = nt.nodes.new("ShaderNodeTexSky"); sky.sky_type = "MULTIPLE_SCATTERING"; sky.sun_elevation = math.radians(12); sky.sun_rotation = math.radians(215)
for k, v in (("sun_intensity", 0.6), ("sun_size", math.radians(1.5)), ("altitude", 300), ("air_density", 1.4), ("dust_density", 2.5), ("aerosol_density", 2.5), ("ozone_density", 1.5)):
    if hasattr(sky, k): setattr(sky, k, v)
nt.links.new(sky.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = 0.3; nt.links.new(bg.outputs[0], out.inputs["Surface"])
vol = nt.nodes.new("ShaderNodeVolumePrincipled"); vol.inputs["Density"].default_value = 0.0022; vol.inputs["Anisotropy"].default_value = 0.6
vol.inputs["Color"].default_value = (0.75, 0.78, 0.8, 1)
# (월드 볼륨은 Blender 5.2 헤드리스 EEVEE 에서 화면 전체가 검게 나온다 → 대신 맵 전체 볼륨 박스 사용)
ee = sc.eevee
ee.volumetric_start = 1.0; ee.volumetric_end = 400.0; ee.volumetric_tile_size = "8" if not PREVIEW else "16"; ee.volumetric_samples = 96
ee.use_volumetric_shadows = True; ee.use_shadows = True; ee.shadow_ray_count = 2; ee.shadow_step_count = 4
ee.use_raytracing = True; ee.taa_render_samples = 24 if not PREVIEW else 8
HQ = "hq" in sys.argv   # 최고 품질 (2026-09-07 사용자 요청): 샘플 160, 볼륨 타일 4·샘플 128, 그림자 레이 4·스텝 8, 인코딩 BEST
if HQ:
    ee.taa_render_samples = 160; ee.volumetric_tile_size = "4"; ee.volumetric_samples = 128; ee.shadow_ray_count = 4; ee.shadow_step_count = 8
    ee.use_volumetric_shadows = True; ee.use_raytracing = True
    sc.render.use_high_quality_normals = True; sc.render.film_transparent = False
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"; sc.view_settings.exposure = -0.1
# 지면 안개층(월드 볼륨과 별개로 저지대에 깔리는 안개): 얇은 큐브 볼륨
fog = bpy.data.objects.new("EV_FOG", bpy.data.meshes.new("EV_FOG")); sc.collection.objects.link(fog)
import bmesh; bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bm.to_mesh(fog.data); bm.free()
fog.location = (0, 0, 0.5); fog.scale = (170, 130, 3.0)
fm = bpy.data.materials.new("EV_FOG"); fm.use_nodes = True; fnt = fm.node_tree; fnt.nodes.clear()
fo = fnt.nodes.new("ShaderNodeOutputMaterial"); fv = fnt.nodes.new("ShaderNodeVolumePrincipled")
fv.inputs["Density"].default_value = 0.006; fv.inputs["Anisotropy"].default_value = 0.4; fv.inputs["Color"].default_value = (0.8, 0.82, 0.85, 1)
fnt.links.new(fv.outputs[0], fo.inputs["Volume"]); fog.data.materials.append(fm)
# 대기 안개: 맵 전체(카메라 포함)를 덮는 큰 박스, 옅게
haze = bpy.data.objects.new("EV_HAZE", fog.data.copy()); sc.collection.objects.link(haze)
haze.location = (0, 0, 40); haze.scale = (420, 380, 90)
hm = bpy.data.materials.new("EV_HAZE"); hm.use_nodes = True; hnt = hm.node_tree; hnt.nodes.clear()
ho = hnt.nodes.new("ShaderNodeOutputMaterial"); hv = hnt.nodes.new("ShaderNodeVolumePrincipled")
hv.inputs["Density"].default_value = 0.0006; hv.inputs["Anisotropy"].default_value = 0.65; hv.inputs["Color"].default_value = (0.78, 0.80, 0.84, 1)
hnt.links.new(hv.outputs[0], ho.inputs["Volume"]); haze.data.materials.clear(); haze.data.materials.append(hm)
# 물: 반투명 + 반사
wo = bpy.data.objects["EV_STA_StreamWater"]
for s in wo.material_slots:
    m = s.material; m.blend_method = "BLEND"
    for n in m.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            n.inputs["Alpha"].default_value = 0.6; n.inputs["Roughness"].default_value = 0.28; n.inputs["Specular IOR Level"].default_value = 0.5

# ------------------------------------------------------------------ 컴포지터 (Blender 5.x: scene.compositing_node_group + NodeGroupOutput)
ct = bpy.data.node_groups.new("EV_COMP", "CompositorNodeTree"); sc.compositing_node_group = ct; sc.use_nodes = True
ct.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
rl = ct.nodes.new("CompositorNodeRLayers"); rl.scene = sc; gout = ct.nodes.new("NodeGroupOutput")
glare = ct.nodes.new("CompositorNodeGlare"); glare.inputs["Type"].default_value = "Fog Glow"
for k, v in (("Threshold", 1.1), ("Strength", 0.35), ("Size", 7)):
    try: glare.inputs[k].default_value = v
    except Exception as e: print("glare", k, e)
ct.links.new(rl.outputs["Image"], glare.inputs["Image"]); last = glare.outputs["Image"]
def _sock(node, ident):
    return next(s for s in node.inputs if s.identifier == ident)
def _mix(fac, a_sock, b_val=None, b_sock=None, blend="MULTIPLY"):
    m = ct.nodes.new("ShaderNodeMix"); m.data_type = "RGBA"; m.blend_type = blend
    _sock(m, "Factor_Float").default_value = fac; ct.links.new(a_sock, _sock(m, "A_Color"))
    if b_sock is not None: ct.links.new(b_sock, _sock(m, "B_Color"))
    else: _sock(m, "B_Color").default_value = b_val
    return m
try:   # 비네트
    ell = ct.nodes.new("CompositorNodeEllipseMask"); ell.inputs["Size"].default_value = (1.3, 1.1)
    blur = ct.nodes.new("CompositorNodeBlur"); blur.inputs["Size"].default_value = (0.35, 0.35) if hasattr(blur.inputs["Size"].default_value, "__len__") else 300
    ct.links.new(ell.outputs[0], blur.inputs["Image"])
    mv = _mix(0.5, last, b_sock=blur.outputs["Image"]); last = next(o for o in mv.outputs if o.identifier == "Result_Color")
except Exception as e:
    print("vignette skipped", e)
fadeN = _mix(0.0, last, b_val=(0, 0, 0, 1)); fade = _sock(fadeN, "Factor_Float")
ct.links.new(next(o for o in fadeN.outputs if o.identifier == "Result_Color"), gout.inputs["Image"])

# ------------------------------------------------------------------ 카메라 샷
cam = sc.camera; cam.data.lens = 30; cam.data.sensor_width = 36
cam.data.dof.use_dof = False
sw, se = L.spawn_points()["Red"], L.spawn_points()["Blue"]; tip = (L.CREST[-1][0], L.CREST[-1][1])
SHOTS = [   # (초, [(t, 위치, 목표점, lens)], 보간)
    ("aerial",  7.0, [(0.0, (-100, -92, 88), (0, 0, 5), 30), (1.0, (-15, -98, 78), (0, 0, 5), 30)]),   # 메시(|y|≤110) 안에서 — 밖이면 스커트가 보인다
    ("stream",  7.0, [(t, (x, L.stream_center(x) - 5.0, max(h(x, L.stream_center(x) - 5.0) + 2.2, L.water_z(x) + 3.2)),
                           (x + 12, L.stream_center(x + 12), L.water_z(x + 12) + 0.3), 28)
                      for t, x in ((0.0, -18.0), (0.25, -13.0), (0.5, -8.0), (0.75, -3.0), (1.0, 2.0))]),   # 분지 구간, 남쪽 어깨 위 지면 +2.2 (둔덕·능선 구간은 카메라가 땅속으로 들어간다)
    ("crest",   6.0, [(0.0, (tip[0] - 3, tip[1] + 2, h(tip[0] - 3, tip[1] + 2) + 1.7), (14, -13, 2), 24),
                      (1.0, (tip[0] + 4, tip[1] - 2, h(tip[0] + 4, tip[1] - 2) + 9.0), (10, -10, 1), 24)]),
    ("forest",  6.0, [(0.0, (-48, -30, h(-48, -30) + 1.6), (-20, -40, 1.5), 28), (1.0, (-30, -35, h(-30, -35) + 1.6), (-5, -38, 1.5), 28)]),
    ("spawn",   7.0, [(0.0, (sw[0], sw[1], h(*sw) + 1.7), (0, 0, 2), 22), (0.5, (sw[0] + 3, sw[1], h(sw[0] + 3, sw[1]) + 2.0), (0, 0, 2), 22),
                      (1.0, (sw[0] + 3, sw[1], h(sw[0] + 3, sw[1]) + 45), (0, 0, 2), 22)]),   # 스폰 디스크(r 12, 나무 없음) 위에서 수직 상승 — 수관을 뚫지 않게
]
FADE = 0.6  # 초
def aim(loc, tgt):
    d = Vector(tgt) - Vector(loc); return d.to_track_quat("-Z", "Y").to_euler()

frame = 1; ranges = []
for name, secs, keys in SHOTS:
    n = int(secs * FPS); f0 = frame
    for t, loc, tgt, lens in keys:
        f = f0 + int(round(t * (n - 1)))
        cam.location = Vector(loc); cam.rotation_euler = aim(loc, tgt); cam.data.lens = lens
        cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_euler", frame=f); cam.data.keyframe_insert("lens", frame=f)
    # 페이드 인/아웃 (샷 경계 컷 대신 짧은 디졸브 느낌)
    fi = int(FADE * FPS)
    for f, v in ((f0, 1.0), (f0 + fi, 0.0), (f0 + n - 1 - fi, 0.0), (f0 + n - 1, 1.0)):
        fade.default_value = v; fade.keyframe_insert("default_value", frame=f)
    ranges.append((name, f0, f0 + n - 1)); frame = f0 + n
# 카메라 보간을 부드럽게(EASE) + 샷 경계에서 튀지 않게 CONSTANT 가 아니라 각 샷 첫 키를 이전 샷 마지막 프레임 다음에 둔다(이미 그렇다)
def _fcurves(idb):
    act = idb.animation_data.action
    if hasattr(act, "fcurves") and len(act.fcurves): return list(act.fcurves)
    out = []
    for layer in act.layers:                       # Blender 5.x 슬롯 액션
        for strip in layer.strips:
            for cb in strip.channelbags: out += list(cb.fcurves)
    return out
for fc in _fcurves(cam):
    for kp in fc.keyframe_points: kp.interpolation = "BEZIER"; kp.easing = "EASE_IN_OUT"
for fc in _fcurves(cam.data) + _fcurves(ct):
    for kp in fc.keyframe_points: kp.interpolation = "LINEAR"

# 타이틀 (마지막 샷 끝 2.5 초): 카메라 앞 텍스트
title = bpy.data.objects.new("EV_TITLE", bpy.data.curves.new("EV_TITLE", "FONT")); sc.collection.objects.link(title)
title.data.body = "SANGOK II"; title.data.align_x = "CENTER"; title.data.size = 1.0; title.data.extrude = 0.0
tm = bpy.data.materials.new("EV_TITLE"); tm.use_nodes = True
e = tm.node_tree.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (1.0, 0.92, 0.8, 1); e.inputs[1].default_value = 6.0
tm.node_tree.links.new(e.outputs[0], tm.node_tree.nodes["Material Output"].inputs["Surface"]); title.data.materials.append(tm)
title.parent = cam; title.location = (0, 0.35, -6.0); title.rotation_euler = (0, 0, 0); title.scale = (0.9, 0.9, 0.9)
sub = bpy.data.objects.new("EV_SUB", bpy.data.curves.new("EV_SUB", "FONT")); sc.collection.objects.link(sub)
sub.data.body = "VALLEY  3-LANE  /  ONLY ONE SHOT"; sub.data.align_x = "CENTER"; sub.data.size = 0.28; sub.data.materials.append(tm)
sub.parent = cam; sub.location = (0, -0.45, -6.0)
last_f = ranges[-1][2]; t_on = last_f - int(2.5 * FPS)
for ob in (title, sub):
    ob.hide_render = True; ob.keyframe_insert("hide_render", frame=1)
    ob.hide_render = False; ob.keyframe_insert("hide_render", frame=t_on)

# ------------------------------------------------------------------ 출력
sc.frame_start = 1; sc.frame_end = last_f; sc.render.fps = FPS
sc.render.resolution_x, sc.render.resolution_y = (1920, 1080) if not PREVIEW else (960, 540)
sc.render.resolution_percentage = 100
sc.render.image_settings.media_type = "VIDEO"; sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.ffmpeg.constant_rate_factor = "PERC_LOSSLESS" if HQ else "HIGH"; sc.render.ffmpeg.ffmpeg_preset = "BEST" if HQ else "GOOD"
sc.render.filepath = os.path.join(OUT, "SGK_trailer_preview" if PREVIEW else ("SGK_trailer_HQ" if HQ else "SGK_trailer"))
sc.frame_step = 4 if PREVIEW else 1
print("shots", ranges, "frames", last_f)
# 샷별 스틸 (중간 프레임)
sc.render.image_settings.media_type = "IMAGE"; sc.render.image_settings.file_format = "PNG"
if "nocomp" in sys.argv: sc.use_nodes = False
if "nofog" in sys.argv: fog.hide_render = True
if "noworldvol" in sys.argv: nt.links.remove(next(l for l in nt.links if l.to_socket.name == "Volume"))
if "novolset" in sys.argv:
    ee.volumetric_tile_size = "8"; ee.volumetric_samples = 64; ee.use_volumetric_shadows = False
if "novol" in sys.argv:
    nt.links.remove(next(l for l in nt.links if l.to_socket.name == "Volume")); fog.hide_render = True
if "frames" in sys.argv:
    for f in (190, 230, 300, 330):
        sc.frame_set(f); sc.render.filepath = os.path.join(OUT, f"frame_{f:04d}.png"); bpy.ops.render.render(write_still=True)
    print("FRAMES ONLY"); sys.exit(0)
if "stills" in sys.argv:
    for name, a, b in ranges:
        sc.frame_set((a + b) // 2); sc.render.filepath = os.path.join(OUT, f"trailer_{name}.png"); bpy.ops.render.render(write_still=True)
    print("STILLS ONLY"); sys.exit(0)
for name, a, b in ranges:
    sc.frame_set((a + b) // 2); sc.render.filepath = os.path.join(OUT, f"trailer_{name}.png"); bpy.ops.render.render(write_still=True)
sc.render.image_settings.media_type = "VIDEO"; sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"; sc.render.filepath = os.path.join(OUT, "SGK_trailer_preview" if PREVIEW else ("SGK_trailer_HQ" if HQ else "SGK_trailer"))
bpy.ops.render.render(animation=True)
print("DONE", sc.render.filepath)
