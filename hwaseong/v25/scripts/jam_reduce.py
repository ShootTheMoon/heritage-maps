# -*- coding: utf-8 -*-
"""Reduce the KCISA Janganmun v24 set for the arena (idempotent: reloads from v24 each run).
Per mesh: drop custom normals, keep ONE uv layer named UVMap (the 10 roofs carried differently
named layers -> a join produced 6 UV maps and broke both texturing and collapse), delete loose
verts, weld 2 mm. Then join per material (per collection), triangulate, collapse to TRI_TARGETS.
Run in GUI: ns={}; exec(open(p,encoding='utf-8').read(), ns); ns['main']()"""
import bpy, bmesh, sys
RB = r"C:\Users\HSP\Desktop\blender\hwaseong_rebuild"
if RB not in sys.path:
    sys.path.append(RB)
import importlib, rebuild
importlib.reload(rebuild)

V24 = r"C:\Users\HSP\Desktop\blender\hwaseong_rebuild\janganmun_v24.blend"
COLS = ["화성_장안문", "화성_성벽", "화성_소품"]
WELD = 0.002
TRI_TARGETS = {"Roof": 28000, "ComplexBracket": 16000, "B_GateHouse_001": 5000, "Flag_01": 3000,
               "SideDoor": 2500, "G_Stair_001": 2500, "CW_003": 3500, "WoodStair": 2000, "RoofStatue": 2000,
               "RoofBoard": 1500, "Cannon": 1500, "Rafter": 6000, "B_Parapet_001": 3500, "Column": 3000}


def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def reload_v24():
    for o in [o for o in bpy.data.objects if o.name.startswith("장안문_")]:
        bpy.data.objects.remove(o, do_unlink=True)
    with bpy.data.libraries.load(V24, link=False) as (df, dt):
        dt.collections = [n for n in df.collections if n in COLS]
    for c in dt.collections:
        base = c.name.split(".")[0]
        tgt = bpy.data.collections.get(base)
        if tgt is None or tgt is c:
            if c.name not in bpy.context.scene.collection.children:
                bpy.context.scene.collection.children.link(c)
            continue
        for o in list(c.objects):
            tgt.objects.link(o); c.objects.unlink(o)
        bpy.data.collections.remove(c)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for x in [x for x in blk if x.users == 0]:
            blk.remove(x)


def clean(me):
    a = me.attributes.get("custom_normal")
    if a:
        me.attributes.remove(a)
    while len(me.uv_layers) > 1:
        me.uv_layers.remove(me.uv_layers[-1])
    if me.uv_layers:
        me.uv_layers[0].name = "UVMap"
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=WELD)
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(me); bm.free(); me.update()


def tri_dec(o, target_tris):
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.to_mesh(me); bm.free(); me.update()
    n = len(me.polygons)
    if n <= target_tris:
        return n
    m = o.modifiers.new("dec", 'DECIMATE'); m.decimate_type = 'COLLAPSE'
    m.ratio = target_tris / float(n); m.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get(); new = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    o.modifiers.remove(m); old = o.data; nm = old.name; o.data = new; bpy.data.meshes.remove(old); new.name = nm
    return len(new.polygons)


def main():
    reload_v24()
    objs = [o for c in COLS for o in bpy.data.collections[c].objects if o.type == 'MESH']
    t0 = sum(tris(o.data) for o in objs)
    for o in objs:
        clean(o.data)
    for cn in COLS:
        col = bpy.data.collections[cn]
        groups = {}
        for o in list(col.objects):
            if o.type == 'MESH' and o.name.startswith("장안문_"):
                groups.setdefault(o.data.materials[0].name if o.data.materials else "_nomat", []).append(o)
        for mname, group in groups.items():
            if len(group) > 1:
                ov = rebuild._sel(group, group[0])
                with bpy.context.temp_override(**ov):
                    bpy.ops.object.join()
            o = group[0]
            base = mname.replace("MI_T_", "").replace("MI_", "").replace(".001", "")
            o.name = "장안문_" + base; o.data.name = o.name
            tgt = TRI_TARGETS.get(base)
            if tgt:
                tri_dec(o, tgt)
    rows = sorted([(o.name, tris(o.data), len(o.data.uv_layers)) for c in COLS for o in bpy.data.collections[c].objects
                   if o.type == 'MESH' and o.name.startswith("장안문_")], key=lambda r: -r[1])
    print("@@JAM tris %d -> %d, meshes=%d" % (t0, sum(r[1] for r in rows), len(rows)))
    for r in rows[:10]:
        print("@@  %s %d uv=%d" % r)
    return rows
