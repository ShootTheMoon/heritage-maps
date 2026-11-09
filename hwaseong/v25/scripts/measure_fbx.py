# -*- coding: utf-8 -*-
"""Headless: measure heritage FBX under given dirs (tris, dims, materials)."""
import bpy, os, glob, mathutils
BASE = r"C:\Users\HSP\Desktop\국가유산_3D"
DIRS = glob.glob(os.path.join(BASE, "순천_낙안읍성", "*")) + glob.glob(os.path.join(BASE, "기타", "*"))
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
for d in DIRS:
    fs = [p for p in glob.glob(os.path.join(d, "**", "*.*"), recursive=True) if p.lower().endswith(".fbx")]
    if not fs: print("@@NOFBX", d); continue
    before = set(bpy.data.objects)
    try: bpy.ops.import_scene.fbx(filepath=fs[0])
    except Exception as e: print("@@ERR", d, e); continue
    new = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    tris = sum(sum(len(pg.vertices) - 2 for pg in o.data.polygons) for o in new)
    pts = [o.matrix_world @ mathutils.Vector(v) for o in new for v in o.bound_box]
    dims = [round(max(p[i] for p in pts) - min(p[i] for p in pts), 1) for i in range(3)] if pts else None
    mats = set(m.name for o in new for m in o.data.materials if m)
    print("@@FBX", os.path.basename(d), "meshes=", len(new), "tris=", tris, "dims=", dims, "mats=", len(mats))
