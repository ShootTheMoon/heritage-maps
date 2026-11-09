# -*- coding: utf-8 -*-
"""Village props -> ONE texture each (MeshPart budget), a procedural pine (solid, no alpha —
OVERDARE ignores texture alpha) and the 낙안읍성 연자방아 (millstone) as a cover prop.
Run in GUI after assemble.main(): ns={}; exec(...); ns['main']()   then re-run assemble village/consolidate."""
import bpy, bmesh, sys, os, glob
from mathutils import Vector
RB = r"C:\Users\HSP\Desktop\blender\hwaseong_rebuild"; V25 = os.path.join(RB, "v25")
for p in (RB, V25):
    if p not in sys.path:
        sys.path.append(p)
import importlib, rebuild, jam_reduce, kit_namhan
for m in (rebuild, jam_reduce, kit_namhan):
    importlib.reload(m)

PROTO = "KIT_PROPS"
BAKE = {"P_초가집": (0.03, 0.08, None), "P_사랑채": (0.03, 0.08, 15000),
        "P_대문": (0.03, 0.08, None), "P_상가": (0.03, 0.08, None)}


def _mat(name, rgb):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (rgb[0], rgb[1], rgb[2], 1.0); m.use_nodes = True
    b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if b:
        b.inputs['Base Color'].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    return m


def bake_prop(name, extr, dist, tri_target):
    src = bpy.data.objects[name]; key = "PB_" + name[2:]
    old = bpy.data.objects.get(key)
    if old:
        bpy.data.meshes.remove(old.data)
    lp = rebuild.join_copy([src], key)
    if tri_target:
        jam_reduce.tri_dec(lp, tri_target)
    rebuild.unwrap(lp, margin=0.005)
    path, cov, mean = rebuild.bake_class(lp, [src], key, size=1024, extr=extr, dist=dist)
    pc = bpy.data.collections[PROTO]
    for c in list(lp.users_collection):
        c.objects.unlink(lp)
    pc.objects.link(lp); lp.location = src.location + Vector((30.0, 0.0, 0.0))
    print("@@BAKE %s tris=%d cov=%.0f%%" % (key, sum(len(p.vertices) - 2 for p in lp.data.polygons), cov))
    return lp


def pine(name="P_소나무2", h=7.5):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.meshes.remove(old.data)
    bm = bmesh.new()
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=7, radius1=0.38, radius2=0.16, depth=h * 0.6)
    for v in r['verts']:
        v.co.z += h * 0.3
    for z, rad, d in ((h * 0.42, 2.6, 2.8), (h * 0.62, 2.0, 2.4), (h * 0.82, 1.3, 2.0)):
        r = bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=rad, radius2=0.04, depth=d)
        for v in r['verts']:
            v.co.z += z + d * 0.15
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(_mat("소나무_수피", (0.30, 0.20, 0.12)))
    me.materials.append(_mat("소나무_잎", (0.15, 0.30, 0.13)))
    for p in me.polygons:
        p.material_index = 0 if (p.center.xy.length < 0.45 and p.center.z < h * 0.6) else 1
        p.use_smooth = False
    o = bpy.data.objects.new(name, me); bpy.data.collections[PROTO].objects.link(o)
    o.location = (60.0, 300.0, 0.0)
    print("@@PINE tris", sum(len(p.vertices) - 2 for p in me.polygons))
    return o


def millstone(name="P_연자방아", tri_target=4000):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.meshes.remove(old.data)
    d = glob.glob(os.path.join(r"C:\Users\HSP\Desktop\국가유산_3D\순천_낙안읍성", "*연자방아*"))[0]
    fbx = kit_namhan.find_fbx(d)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=fbx)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    ov = rebuild._sel(meshes, meshes[0])
    with bpy.context.temp_override(**ov):
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        if len(meshes) > 1:
            bpy.ops.object.join()
    for o in new:
        if o.type != 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)
    o = meshes[0]; o.name = name; o.data.name = name
    fixed, missing = kit_namhan.relink_textures([o], kit_namhan.tex_files(d))
    me = o.data
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    off = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)))
    for v in me.vertices:
        v.co -= off
    jam_reduce.tri_dec(o, tri_target)
    for c in list(o.users_collection):
        c.objects.unlink(o)
    bpy.data.collections[PROTO].objects.link(o); o.location = (60.0, 320.0, 0.0)
    print("@@MILL tris", len(o.data.polygons), "texfix", fixed, "missing", missing[:3], "mats", len(o.data.materials))
    return o


def main():
    for n, (e, d, t) in BAKE.items():
        if bpy.data.objects.get(n):
            bake_prop(n, e, d, t)
    pine(); millstone()


if __name__ == "__main__":
    main()
