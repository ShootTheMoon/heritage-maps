# -*- coding: utf-8 -*-
"""sgk_engine_view.py — 익스포트된 FBX(06_OVERDARE) 만으로 맵을 조립해 렌더 (엔진이 보는 그대로). 라이브 Blender MCP 에서 exec.
   build() → 임시 씬 ENGINE_VIEW ; shots(names) → 04_Previews/ev_<name>.png ; teardown()"""
import bpy, os, json, math, sys
from mathutils import Vector
ROOT = r"C:\Users\HSP\Desktop\blender\JSN_Sangok2"; OVD = os.path.join(ROOT, "06_OVERDARE"); OUT = os.path.join(ROOT, "04_Previews")
JSNM = r"C:\Users\HSP\Desktop\blender\JSN_Sangok\06_OVERDARE\10_MASTERS"
sys.path.insert(0, os.path.join(ROOT, "_scripts")); import sgk_layout as L

def _imp(path):
    before = set(bpy.data.objects); bpy.ops.import_scene.fbx(filepath=path, use_image_search=False)
    o = [x for x in set(bpy.data.objects) - before if x.type == 'MESH'][0]
    for s in o.material_slots:
        if s.material: s.material.blend_method = 'HASHED'
    return o

def build():
    if bpy.context.window is None:          # 헤드리스(-b): 새 씬으로 못 바꾸므로 현재 씬을 비워 쓴다
        sc = bpy.context.scene
        for o in list(sc.objects): bpy.data.objects.remove(o, do_unlink=True)
    else:
        sc = bpy.data.scenes.new("ENGINE_VIEW"); bpy.context.window.scene = sc
    man = json.load(open(os.path.join(OVD, "manifest.json"), encoding="utf-8"))
    for k, r in man.items():
        if r.get("kind") == "static" and r.get("file"): _imp(os.path.join(OVD, r["file"])).name = "EV_" + k
    pl = json.load(open(os.path.join(ROOT, "05_Documentation", "placements_master.json"), encoding="utf-8"))["instances"]
    masters = {}
    for it in pl:
        m = it["master"]
        if m in masters: continue
        r = man.get(m)
        p = os.path.join(OVD, r["file"]) if r and r.get("file") else os.path.join(JSNM, m + "_overdare.fbx")
        o = _imp(p); o.name = "EVM_" + m; o.hide_render = True; o.hide_viewport = True; masters[m] = o
    for it in pl:
        o = bpy.data.objects.new("EV_" + it["name"], masters[it["master"]].data); sc.collection.objects.link(o)
        o.location = (it["x"], it["y"], it["z"]); o.rotation_euler = (0, 0, math.radians(it["yaw"])); s = it.get("scale", 1.0); o.scale = (s, s, s)
    sun = bpy.data.lights.new("EV_S", 'SUN'); sun.energy = 3.5; sun.angle = 0.15
    so = bpy.data.objects.new("EV_S", sun); sc.collection.objects.link(so); so.rotation_euler = (math.radians(52), 0, math.radians(-40))
    w = bpy.data.worlds.new("EV_W"); w.use_nodes = True; bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.55, 0.65, 0.8, 1); bg.inputs[1].default_value = 0.7; sc.world = w
    cam = bpy.data.objects.new("EV_C", bpy.data.cameras.new("EV_C")); sc.collection.objects.link(cam); sc.camera = cam
    sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x, sc.render.resolution_y = 1600, 900; sc.eevee.taa_render_samples = 16
    return sc

EYE = 1.7
def _h(x, y): return L.height_at(x, y)
def SHOTS():
    sw, se = L.spawn_points()["Red"], L.spawn_points()["Blue"]; tip = (L.CREST[-1][0], L.CREST[-1][1])
    return {
        "Survey": ((-40, -150, 120), (0, 0, 2), 32), "Top": ((0, 0, 400), (0, 0, 0), "ortho185"),
        "SpawnW_POV": ((sw[0], sw[1], _h(*sw) + EYE), (0, 0, 2), 16), "SpawnE_POV": ((se[0], se[1], _h(*se) + EYE), (0, 0, 2), 16),
        "Bowl": ((0, -12, _h(0, -12) + EYE), (0, 9, 2.5), 18), "CrestNW": ((tip[0], tip[1], _h(*tip) + EYE), (14, -13, 2), 18),
        "ForestMid": ((-20, -36, _h(-20, -36) + EYE), (20, -44, 1), 18), "StripN": ((-35, 50, _h(-35, 50) + EYE), (-10, 40, 1), 18),
        "RidgeW": ((-70, 40, 30), (-30, 22, 8), 35),
        "Bridge": ((-8, -6, _h(-8, -6) + EYE), (0, 0, 0.5), 24), "Pavilion": ((6, 16, _h(6, 16) + EYE), (0, 9, 2), 24),
        "FordW": ((-42, -8, _h(-42, -8) + EYE), (-42, 4, -0.5), 20), "StreamE": ((30, 8, _h(30, 8) + EYE), (10, -2, -0.5), 20),
        "R1_foot": ((-70, 20, _h(-70, 20) + EYE), (-52, 32, 8), 20), "WallE_POV": ((60, 0, _h(60, 0) + EYE), (95, 5, 10), 20),
        "Glade_S": ((0, -46, _h(0, -46) + EYE), (0, -20, 1), 20), "Terrace": ((-30, 12, _h(-30, 12) + EYE), (-22, 22, 8), 22),
    }

def shots(names=None, prefix="ev_"):
    sc = bpy.data.scenes["ENGINE_VIEW"]; cam = sc.camera; done = []
    for k, (loc, tgt, lens) in SHOTS().items():
        if names and k not in names: continue
        cam.location = Vector(loc); d = Vector(tgt) - cam.location; cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        if isinstance(lens, str): cam.data.type = 'ORTHO'; cam.data.ortho_scale = float(lens[5:])
        else: cam.data.type = 'PERSP'; cam.data.lens = lens
        sc.render.filepath = os.path.join(OUT, prefix + k + ".png"); bpy.ops.render.render(write_still=True); done.append(k)
    return done

def teardown():
    sc = bpy.data.scenes.get("ENGINE_VIEW")
    if not sc: return
    bpy.context.window.scene = [s for s in bpy.data.scenes if s != sc][0]
    for o in [o for o in bpy.data.objects if o.name.startswith(("EV_", "EVM_"))]:
        d = o.data; bpy.data.objects.remove(o, do_unlink=True)
        if d and d.users == 0:
            for c in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights):
                if d.name in c: c.remove(d); break
    bpy.data.scenes.remove(sc)
    for c in (bpy.data.worlds, bpy.data.materials, bpy.data.images):
        for d in list(c):
            if d.users == 0 and not d.use_fake_user and (d.name.startswith(("EV_", "OVD_", "SGK_", "MST_", "STA_")) or c is bpy.data.worlds): c.remove(d)
