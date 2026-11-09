# -*- coding: utf-8 -*-
"""BlenderKit props (downloaded async by start_download into their own collections at y>=500):
collapse each asset to ONE prototype mesh in KIT_PROPS, then scatter copies into the village
and join per type into 화성_소품 (HPR). Run in GUI after the downloads landed."""
import bpy, math, sys, os
from mathutils import Vector, Matrix
V25 = r"C:\Users\HSP\Desktop\blender\hwaseong_rebuild\v25"
if V25 not in sys.path:
    sys.path.append(V25)
import importlib, assemble_v25 as asm
importlib.reload(asm)

ASSETS = {  # collection name (as BlenderKit made it) -> (proto key, target height m)
    "Korea Ceremonial flag on stand": ("BK_FLAG", 3.2),
    "Mud Pots 11": ("BK_POT", 0.85),
    "Japanese Temple - Stone Lantern": ("BK_LANTERN", 2.0),
    "Old Wooden Barrel": ("BK_BARREL", 1.0),
    "Hay Bale": ("BK_HAY", 0.9),
}
PLACES = {  # key -> list of (x, y, rot_deg)
    "BK_FLAG": [(-7, 21, 0), (7, 21, 0), (-3, 58, 0), (3, 58, 0)],
    "BK_POT": [(-57, 23, 0), (-56, 23.9, 30), (-55, 23.2, 60), (-52, 46.5, 0), (-51, 47.3, 45), (-50, 46.6, 90), (-49, 47.2, 20)],
    "BK_LANTERN": [(-5, 31, 0), (5, 31, 0), (-14, 52, 0), (14, 52, 0)],
    "BK_BARREL": [(-20, 14, 0), (-19, 15.2, 30), (-20.8, 15.4, 70), (22, 15, 0), (30, 40, 15), (-30, 44, 50), (12, 61, 0), (13, 61.9, 40)],
    "BK_HAY": [(52, 26, 0), (53.6, 26, 90), (52.8, 26.9, 0), (50, 57, 20), (58, 52, 70), (-58, 10, 0)],
}


def collapse(colname, key, height):
    col = bpy.data.collections.get(colname)
    proto = bpy.data.objects.get("P_" + key)
    if col:
        objs = [o for o in col.all_objects]
        meshes = [o for o in objs if o.type == 'MESH']
        others = [o.name for o in objs if o.type != 'MESH']      # capture BEFORE join removes objects
        if meshes and not proto:
            for o in meshes:
                if o.data.users > 1:
                    o.data = o.data.copy()
                o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4); o.parent = None
            proto = asm._join(meshes, "P_" + key)
        for n in others:
            o = bpy.data.objects.get(n)
            if o:
                bpy.data.objects.remove(o, do_unlink=True)
    if proto and not proto.get("bk_done"):
        dims = asm.bake_and_ground(proto)
        s = height / max(dims[2], 1e-3)
        proto.data.transform(Matrix.Scale(s, 4))
        for c in list(proto.users_collection):
            c.objects.unlink(proto)
        bpy.data.collections["KIT_PROPS"].objects.link(proto)
        proto.location = (90.0, 500.0 + 15.0 * list(ASSETS).index(colname), 0.0)
        proto["bk_done"] = True
    if col and col.name in bpy.data.collections and not col.all_objects:
        bpy.data.collections.remove(col)
    return proto


def main():
    hpr = asm.coll("화성_소품")
    for o in [o for o in bpy.data.objects if o.name.startswith("소품_BK_")]:
        bpy.data.objects.remove(o, do_unlink=True)
    made = []
    for colname, (key, h) in ASSETS.items():
        proto = bpy.data.objects.get("P_" + key) or collapse(colname, key, h)
        if not proto:
            continue
        copies = []
        for i, (x, y, r) in enumerate(PLACES[key]):
            copies.append(asm.place(proto, "소품_%s_%d" % (key, i), (x, y, 0.0), r, hpr))
        asm._join(copies, "소품_" + key)
        made.append((key, len(copies), sum(len(p.vertices) - 2 for p in proto.data.polygons), len(proto.data.materials)))
    for lt in [o for o in bpy.data.objects if o.type == 'LIGHT' and o.matrix_world.translation.y > 480]:
        bpy.data.objects.remove(lt, do_unlink=True)
    print("@@BK_PROPS", made)


if __name__ == "__main__":
    main()
