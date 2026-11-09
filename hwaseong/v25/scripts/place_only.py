# -*- coding: utf-8 -*-
"""PLACE-ONLY (user 2026-09-09: "그냥 에셋 배치만 해라. 생성하지 말고 바꾸지 말고").
Nothing is generated (no gate house, no ground, no roads, no procedural trees) and no asset is edited.
Assets used exactly as delivered:
  * 장안문 일곽  — KCISA original from Sketchfab (kcisameta, CC BY 4.0), imported by the Sketchfab tool
                  BEFORE running this; this script only moves its root object.
  * inner compound — 남한산성 성벽/여장/암문 FBX (국가유산청), copies share the imported mesh, matrix only.
  * 본채 — PaperMouse house imported by the Sketchfab tool BEFORE running this; root moved only.
  * trees/props — BlenderKit downloader appends (bk_props() from rebuild_raw.py), real scale.
Run in GUI after the two Sketchfab downloads: ns={}; exec(open(p,encoding='utf-8').read(), ns); ns['main']()"""
import bpy, os, sys, math
from mathutils import Vector, Matrix
V25 = r"C:\Users\HSP\Desktop\blender\hwaseong_rebuild\v25"
if V25 not in sys.path:
    sys.path.append(V25)
import importlib, rebuild_raw as rr
importlib.reload(rr)

C_WALL, C_BLD, C_JAM = "화성_성벽", "화성_도시_건물", "화성_장안문"


def family(root):
    yield root
    for c in root.children:
        yield from family(c)


def move_root(root, name, loc, rot_deg, col):
    """Only the root's matrix changes; children ride along untouched."""
    root.name = name
    for o in family(root):
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    root.matrix_world = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(math.radians(rot_deg), 4, 'Z') @ root.matrix_world
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in family(root) if o.type == 'MESH' for c in o.bound_box]
    return [round(min(p[i] for p in pts), 1) for i in range(3)], [round(max(p[i] for p in pts), 1) for i in range(3)]


def sketchfab_root(exclude=()):
    roots = [o for o in bpy.data.objects if o.name.startswith("Sketchfab_model") and o.name not in exclude]
    return roots[0] if roots else None


def main(house_root=None, gate_root=None):
    for lc in bpy.context.view_layer.layer_collection.children:
        lc.exclude = False
    # 1) heritage modules (raw) -> compound, placement only
    W = rr.import_heritage("성벽", "NH_WALL"); P = rr.import_heritage("여장", "NH_PARAPET"); Gt = rr.import_heritage("암문", "NH_SECRETGATE")
    rr.compound(W, P, Gt, rr.coll(C_WALL))
    bpy.context.view_layer.layer_collection.children[rr.KIT].exclude = True
    # 2) roots imported by the Sketchfab tool: move only
    out = {}
    if house_root and bpy.data.objects.get(house_root):
        out["house"] = move_root(bpy.data.objects[house_root], "본채_PaperMouse", (0.0, 42.0, 0.606), 180, rr.coll(C_BLD))
    if gate_root and bpy.data.objects.get(gate_root):
        out["gate"] = move_root(bpy.data.objects[gate_root], "장안문_KCISA", (0.0, 0.0, 0.0), 0, rr.coll(C_JAM))
    print("@@PLACED", out, {c.name: len(c.objects) for c in bpy.data.collections if c.name.startswith("화성_")})
    return out
