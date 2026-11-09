# -*- coding: utf-8 -*-
"""Namhansanseong heritage kit -> game modules (1 texture each).
Run inside the GUI Blender:  exec(open(r"...\kit_namhan.py", encoding="utf-8").read())
Per module: import FBX -> clear parents / apply transforms / join -> relink textures
-> align (min x=0, center y=0, min z=0) -> decimate -> smart UV -> bake albedo(+normal shade)
via rebuild.bake_class (no voxel remesh: these are clean modelled meshes, not scan soup).
Sources are deleted after baking; prototypes live in collection KIT_NH at origin+offset."""
import bpy, os, glob, sys, re
from mathutils import Vector

RB = r"C:\Users\HSP\Desktop\blender\hwaseong_rebuild"
if RB not in sys.path:
    sys.path.append(RB)
import importlib, rebuild
importlib.reload(rebuild)

BASE = r"C:\Users\HSP\Desktop\국가유산_3D\남한산성"
KIT = "KIT_NH"
# key, dir keyword, target faces, cage extrusion, max ray dist
MODULES = [
    ("WALL",       "성벽",   3000, 0.06, 0.20),
    ("PARAPET",    "여장",    600, 0.04, 0.12),
    ("GUNPOST",    "포좌",   2500, 0.05, 0.15),
    ("SECRETGATE", "암문",   4000, 0.06, 0.20),
    ("STAIR",      "돌계단",  400, 0.04, 0.12),
]


def find_dir(kw):
    for d in sorted(os.listdir(BASE)):
        if kw in d:
            return os.path.join(BASE, d)
    raise FileNotFoundError(kw)


def find_fbx(d):
    fs = [p for p in glob.glob(os.path.join(d, "**", "*.*"), recursive=True) if p.lower().endswith(".fbx")]
    return fs[0]


def tex_files(d):
    return {os.path.basename(p).lower(): p for p in glob.glob(os.path.join(d, "**", "*.*"), recursive=True)
            if p.lower().endswith((".png", ".jpg", ".jpeg", ".tga"))}


def relink_textures(objs, texmap):
    fixed = 0; missing = []
    bcs = [p for n, p in texmap.items() if re.search(r'(_bc|basecolor|albedo|_d)\.', n)]
    for o in objs:
        for m in o.data.materials:
            if not m or not m.use_nodes:
                continue
            nt = m.node_tree
            bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            for n in [n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image]:
                p = bpy.path.abspath(n.image.filepath)
                if not os.path.exists(p):
                    cand = texmap.get(os.path.basename(p).lower())
                    if cand:
                        n.image.filepath = cand; n.image.reload(); fixed += 1
                    else:
                        missing.append(os.path.basename(p))
            if bsdf and not bsdf.inputs['Base Color'].is_linked:
                key = re.sub(r'[^a-z0-9]', '', m.name.lower())[:8]
                pick = next((p for p in bcs if key and key in re.sub(r'[^a-z0-9]', '', os.path.basename(p).lower())), None)
                if not pick and len(bcs) == 1:
                    pick = bcs[0]
                if pick:
                    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(pick, check_existing=True)
                    nt.links.new(t.outputs['Color'], bsdf.inputs['Base Color']); fixed += 1
                else:
                    missing.append("nobase:" + m.name)
    return fixed, missing


def import_module(key, kw):
    d = find_dir(kw); fbx = find_fbx(d)
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
    src = meshes[0]; src.name = "NH_%s_SRC" % key; src.data.name = src.name
    return src, d


def align(o):
    me = o.data
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    off = Vector((min(xs), (min(ys) + max(ys)) / 2.0, min(zs)))
    for v in me.vertices:
        v.co -= off
    me.update()
    return [round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2), round(max(zs) - min(zs), 2)]


def build_module(src, key, target, extr, dist):
    lp = rebuild.join_copy([src], "NH_" + key)
    rebuild.decimate(lp, target)
    rebuild.unwrap(lp, margin=0.006)
    path, cov, mean = rebuild.bake_class(lp, [src], "NH_" + key, size=1024, extr=extr, dist=dist)
    return lp, path, cov


def main(only=None):
    kit = bpy.data.collections.get(KIT)
    if not kit:
        kit = bpy.data.collections.new(KIT); bpy.context.scene.collection.children.link(kit)
    for i, (key, kw, target, extr, dist) in enumerate(MODULES):
        if only and key not in only:
            continue
        old = bpy.data.objects.get("NH_" + key)
        if old:
            bpy.data.meshes.remove(old.data)
        src, d = import_module(key, kw)
        fixed, missing = relink_textures([src], tex_files(d))
        dims = align(src)
        tin = rebuild.mesh_tris(src.data) if hasattr(rebuild, "mesh_tris") else len(src.data.polygons)
        lp, path, cov = build_module(src, key, target, extr, dist)
        for c in list(lp.users_collection):
            c.objects.unlink(lp)
        kit.objects.link(lp)
        lp.location = (0.0, 12.0 * i, 0.0)
        bpy.data.objects.remove(src, do_unlink=True)
        print("@@KIT %-10s dims=%s faces_in=%d faces_out=%d cov=%.0f%% texfix=%d missing=%s" %
              (key, dims, tin, len(lp.data.polygons), cov, fixed, missing[:4]))
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for x in [x for x in blk if x.users == 0 and not x.name.startswith(("BC_", "MAT_"))]:
            blk.remove(x)


if __name__ == "__main__":
    main()
