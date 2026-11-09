# -*- coding: utf-8 -*-
"""RAW-ONLY rebuild (user 2026-09-09: "무조건 수정 안 한 에셋만 사용해").
Every asset is used exactly as imported: no weld/join/decimate/bake/scale/material edits/mesh-origin shifts.
Placement = object matrix only (copies share the imported mesh). Assets whose import links texture alpha to
BSDF Alpha (연자방아, 돌계단) are NOT used instead of being edited. The gate house is procedural (user request).
Trees/props from BlenderKit are appended asynchronously by bk_props() (unmodified, real scale).
Run in GUI: ns={}; exec(open(p,encoding='utf-8').read(), ns); ns['main']()   then ns['bk_props']()"""
import bpy, os, sys, math, glob, json, urllib.request, urllib.parse
from mathutils import Vector, Matrix
RB = r"C:\Users\HSP\Desktop\blender\hwaseong_rebuild"; V25 = os.path.join(RB, "v25")
G = r"C:\Users\HSP\Desktop\blender\gyeongbokgung"
for p in (RB, V25, G):
    if p not in sys.path:
        sys.path.append(p)
import importlib, gate_house, snap
for m in (gate_house, snap):
    importlib.reload(m)

V24 = os.path.join(RB, "janganmun_v24.blend")
PROPS = os.path.join(G, "hwaseong_props.blend")
HERITAGE = r"C:\Users\HSP\Desktop\국가유산_3D\남한산성"
KIT = "KIT_RAW"
C_WALL, C_BLD, C_VEG, C_GND, C_ROAD = "화성_성벽", "화성_도시_건물", "화성_수목", "화성_지면", "화성_도시_도로"
CX0, CX1, CY0, CY1 = -36.0, 36.0, 24.0, 56.0          # inner compound: 9 modules x 4 modules
WALL_L = 8.0


def coll(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
    return c


def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.cameras, bpy.data.lights):
        for x in [x for x in blk if x.users == 0]:
            blk.remove(x)


def wbbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


def anchor(o, mode="minx"):
    """world-space anchor of the imported prototype: bottom, centre-y, and min-x (walls) or centre-x (props)."""
    mn, mx = wbbox(o)
    ax = mn.x if mode == "minx" else (mn.x + mx.x) / 2
    return Vector((ax, (mn.y + mx.y) / 2, mn.z)), mx - mn


def place(proto, name, loc, rot_deg, col, mode="minx"):
    """Copy sharing the imported mesh; ONLY the object matrix changes."""
    a, _ = anchor(proto, mode)
    c = proto.copy(); c.name = name
    c.matrix_world = (Matrix.Translation(Vector(loc)) @ Matrix.Rotation(math.radians(rot_deg), 4, 'Z')
                      @ Matrix.Translation(-a) @ proto.matrix_world)
    col.objects.link(c)
    return c


def append_v24():
    with bpy.data.libraries.load(V24, link=False) as (df, dt):
        dt.collections = [n for n in df.collections if n in ("화성_장안문", "화성_성벽", "화성_소품")]
    for c in dt.collections:
        if c.name not in bpy.context.scene.collection.children:
            bpy.context.scene.collection.children.link(c)


def import_heritage(kw, key):
    d = next(p for p in sorted(os.listdir(HERITAGE)) if kw in p)
    files = glob.glob(os.path.join(HERITAGE, d, "**", "*.*"), recursive=True)
    fbx = next(p for p in files if p.lower().endswith(".fbx"))
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=fbx)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    kit = coll(KIT)
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        kit.objects.link(o)
    o = meshes[0]; o.name = key
    # path fix only (importer could not find the texture); no material edit
    texs = {os.path.basename(p).lower(): p for p in files if p.lower().endswith((".png", ".jpg", ".jpeg", ".tga"))}
    for m in o.data.materials:
        if m and m.use_nodes:
            for n in [n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]:
                p = bpy.path.abspath(n.image.filepath)
                if not os.path.exists(p) and os.path.basename(p).lower() in texs:
                    n.image.filepath = texs[os.path.basename(p).lower()]; n.image.reload()
    return o


def load_props():
    kit = coll(KIT)
    with bpy.data.libraries.load(PROPS, link=False) as (df, dt):
        dt.objects = [n for n in df.objects if n in ("초가집", "바위무리")]
    for o in dt.objects:
        o.name = "P_" + o.name; kit.objects.link(o)


def compound(W, P, Gt, wc):
    """N/S: 9 modules x -36..36 (module 5 = gate). E/W: 4 modules y 24..56, centred so the outer face is
    flush with the N/S wall ends (no corner notch). Parapets 2 per module on the outer edge. No scaling."""
    _, wd = anchor(W); _, pd = anchor(P)
    half_t = wd.y / 2.0; wall_h = wd.z

    def run(x, y, rot, mod, tag, i):
        place(mod, "담장_%s_%02d" % (tag, i), (x, y, 0.0), rot, wc)
        r = math.radians(rot)
        for k in range(2):
            lx = k * pd.x; ly = half_t - pd.y / 2.0          # outer edge = local +Y
            gx = x + lx * math.cos(r) - ly * math.sin(r); gy = y + lx * math.sin(r) + ly * math.cos(r)
            place(P, "담장_여장_%s_%02d_%d" % (tag, i, k), (gx, gy, wall_h), rot, wc)

    xs = [CX0 + WALL_L * k for k in range(9)]
    for i, x in enumerate(xs):
        gate = (i == 4)
        run(x + WALL_L, CY0, 180, Gt if gate else W, "N", i)      # rot 180: local +Y -> -Y (outside)
        run(x, CY1, 0, Gt if gate else W, "S", i)                 # rot 0: local +Y -> +Y (outside)
    ex = CX1 - half_t; wx = CX0 + half_t
    for i, y in enumerate([CY0 + WALL_L * k for k in range(4)]):
        run(ex, y, 90, W, "E", i)
        run(wx, y + WALL_L, 270, W, "W", i)


def village(kit, bc, vc):
    ch, rk = kit["P_초가집"], kit["P_바위무리"]
    for i, (x, y, r) in enumerate([(-56, 16, 90), (52, 20, -90), (-50, 52, 0), (52, 50, 180)]):
        place(ch, "민가_초가_%d" % i, (x, y, 0.0), r, bc, mode="cx")
    for i, (x, y, r) in enumerate([(-30, -55, 0), (45, -40, 60), (-70, 45, 120)]):
        place(rk, "수목_바위_%d" % i, (x, y, 0.0), r, vc, mode="cx")


def ground_and_roads():
    import bmesh
    gc = coll(C_GND); rc = coll(C_ROAD)
    me = bpy.data.meshes.new("지면_아레나"); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bm.to_mesh(me); bm.free()
    m = bpy.data.materials.get("흙바닥") or bpy.data.materials.new("흙바닥"); m.diffuse_color = (0.42, 0.36, 0.28, 1); me.materials.append(m)
    o = bpy.data.objects.new("지면_아레나", me); gc.objects.link(o); o.location = (0, 5, -0.5); o.scale = (200, 150, 1)
    mr = bpy.data.materials.get("흙길") or bpy.data.materials.new("흙길"); mr.diffuse_color = (0.36, 0.30, 0.22, 1)
    for name, cx, cy, sx, sy in (("도로_남북", 0, 14, 6, 20), ("도로_동서", 0, 14, 120, 5), ("도로_북", 0, -18, 6, 24)):
        me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5); bm.to_mesh(me); bm.free()
        me.materials.append(mr); r = bpy.data.objects.new(name, me); rc.objects.link(r); r.location = (cx, cy, 0.03); r.scale = (sx, sy, 1)


TREES = [(-40, -46), (38, -50), (-22, -62), (25, -66), (-62, -30), (60, -28), (-64, 62), (64, 64)]
BK_PLAN = [  # (search, max faces, positions)
    ("pine tree low poly", 6000, TREES),
    ("clay pot old", 6000, [(-57, 23), (-56, 24.2), (-55, 23.4), (-52, 46.5), (-51, 47.3)]),
    ("wooden barrel old", 6000, [(-20, 14), (-19, 15.2), (22, 15), (30, 40), (-30, 44), (12, 61)]),
    ("hay bale", 3000, [(52, 26), (53.6, 26), (50, 57), (58, 52)]),
]


def bk_props():
    """BlenderKit assets appended UNMODIFIED at real scale via the addon's own downloader (async)."""
    prefs = bpy.context.preferences.addons['bl_ext.user_default.blenderkit'].preferences
    search = importlib.import_module('bl_ext.user_default.blenderkit.search')
    download = importlib.import_module('bl_ext.user_default.blenderkit.download')
    resolutions = importlib.import_module('bl_ext.user_default.blenderkit.resolutions')
    res = resolutions.resolution_props_to_server[prefs.resolution]
    started = []
    for q, maxf, poss in BK_PLAN:
        url = ("https://www.blenderkit.com/api/v1/search/?query=" + urllib.parse.quote(q + " asset_type:model")
               + "&page_size=12&dict_parameters=1")
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + prefs.api_key, "User-Agent": "blenderkit-script"})
        with urllib.request.urlopen(req, timeout=30) as r:
            results = json.load(r).get("results", [])
        ok = [a for a in results if a.get("isFree") and (a.get("dictParameters", {}).get("faceCount") or 10 ** 9) < maxf
              and a.get("license") in ("royalty_free", "cc_zero")]
        if not ok:
            started.append((q, "NONE")); continue
        ad = search.parse_result(ok[0])
        for (x, y) in poss:
            kw = dict(cast_parent="", target_object="", target_collection="", material_target_slot=0,
                      model_location=(float(x), float(y), 0.0), model_rotation=(0.0, 0.0, 0.0), replace=False,
                      replace_resolution=False, parent=None, resolution=res, node_x=0, node_y=0, nodegroup_mode="")
            download.start_download(ad, **kw)
        started.append((q, ad.get("name"), ok[0]["dictParameters"].get("faceCount"), len(poss)))
    print("@@BK_STARTED", started)
    return started


def main():
    clear_scene(); append_v24()
    W = import_heritage("성벽", "NH_WALL"); P = import_heritage("여장", "NH_PARAPET"); Gt = import_heritage("암문", "NH_SECRETGATE")
    load_props()
    kit = {o.name: o for o in bpy.data.collections[KIT].objects}
    wc, bc, vc = coll(C_WALL), coll(C_BLD), coll(C_VEG)
    compound(W, P, Gt, wc); village(kit, bc, vc); ground_and_roads()
    gate_house.main()
    bpy.context.view_layer.layer_collection.children[KIT].exclude = True
    a = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D'); sp = a.spaces.active
    sp.lens = 50; sp.clip_start = 0.1; sp.clip_end = 2000; sp.shading.type = 'MATERIAL'; sp.overlay.show_overlays = True
    cols = [c for c in bpy.data.collections if c.name.startswith("화성_")]
    print("@@RAW objs=%d tris=%d" % (sum(len(c.objects) for c in cols),
          sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for c in cols for o in c.objects if o.type == 'MESH')))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(V25, "hwaseong_v25.blend"))
