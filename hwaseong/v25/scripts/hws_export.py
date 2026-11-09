# -*- coding: utf-8 -*-
"""화성 v25 → OVERDARE 익스포트 (산곡 sgk_export 규약 그대로).
규약: FBX 1개 = 메시 1개, ≤27k tris(collapse), 재질 1개 = 텍스처 1장(≤1024², 디스크 PNG, path_mode COPY, pack 금지),
      axis_up Y / forward -Z / FBX_SCALE_NONE. 정적물은 월드좌표 그대로 → Studio 원점 배치 + 컨테이너 오프셋.
      마스터(담장 모듈·소품)는 바닥중심 피벗 로컬좌표, 인스턴스는 placements.json.
Usage (headless):  blender -b hwaseong_v25.blend --python hws_export.py -- jam|doors|masters|terrain|all
Outputs: ovdr_export\hwaseong_v25\{01_JAM,02_DOORS,10_MASTERS,03_TERRAIN}\*.fbx, manifest_v25.json"""
import bpy, bmesh, os, sys, json, math, shutil
from mathutils import Vector, Matrix

OUT = r"C:\Users\HSP\Desktop\blender\ovdr_export\hwaseong_v25"
TEXOUT = os.path.join(OUT, "_tex")
CAP = 27000
FBX = dict(axis_up='Y', axis_forward='-Z', apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', use_selection=True,
           object_types={'MESH'}, use_mesh_modifiers=True, mesh_smooth_type='FACE', path_mode='COPY', embed_textures=True,
           add_leaf_bones=False, bake_anim=False, use_triangles=True)
MANIFEST = {"schema": "hwaseong-v25/sgk-rules", "files": []}


def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def family(o):
    yield o
    for c in o.children:
        yield from family(c)


def ensure_dirs():
    for d in ("01_JAM", "02_DOORS", "10_MASTERS", "03_TERRAIN", "_tex"):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)


# ------------------------------------------------------------------ texture: one ≤1024 PNG on disk per material
def fix_material(m):
    """Keep only Base Color image, resize >1024 to 1024, save as PNG in _tex, unpack. Returns image name or None."""
    if not m or not m.use_nodes:
        return None
    nt = m.node_tree; bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not bsdf:
        return None
    src = None
    if bsdf.inputs['Base Color'].is_linked:
        n = bsdf.inputs['Base Color'].links[0].from_node
        # walk back through mix nodes to the first image
        seen = 0
        while n and n.type != 'TEX_IMAGE' and seen < 6:
            inp = next((i for i in n.inputs if i.is_linked), None); n = inp.links[0].from_node if inp else None; seen += 1
        src = n.image if (n and n.type == 'TEX_IMAGE') else None
    for l in list(bsdf.inputs['Alpha'].links) + list(bsdf.inputs['Normal'].links):
        nt.links.remove(l)
    m.blend_method = 'OPAQUE'
    if src is None:
        return None
    key = "".join(ch if ch.isalnum() else "_" for ch in src.name.split(".")[0])[:40]
    path = os.path.join(TEXOUT, key + ".png")
    if not os.path.exists(path):
        img = src.copy(); w, h = img.size
        if max(w, h) > 1024:
            s = 1024.0 / max(w, h); img.scale(max(1, int(w * s)), max(1, int(h * s)))
        img.filepath_raw = path; img.file_format = 'PNG'; img.save(); bpy.data.images.remove(img)
    disk = bpy.data.images.get(key + "_disk") or bpy.data.images.load(path); disk.name = key + "_disk"
    for n in [n for n in nt.nodes if n.type == 'TEX_IMAGE']:      # drop normal/roughness/2048 maps: FBX embeds every image node
        nt.nodes.remove(n)
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = disk
    for l in list(bsdf.inputs['Base Color'].links):
        nt.links.remove(l)
    nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    return key


def decimate_to_cap(o, cap=CAP):
    me = o.data; n = tris(me)
    if n <= cap:
        return n
    m = o.modifiers.new("dec", 'DECIMATE'); m.decimate_type = 'COLLAPSE'; m.ratio = (cap * 0.96) / n; m.use_collapse_triangulate = True
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(o.evaluated_get(dg)); o.modifiers.remove(m)
    old = o.data; o.data = new; new.name = old.name + "_dec"; bpy.data.meshes.remove(old)
    return tris(new)


def export_one(o, folder, name, world=True, centre=False):
    """Export a single mesh object. world=True bakes matrix_world into the FBX (static); else local (master)."""
    for x in bpy.data.objects:
        x.select_set(False)
    saved = o.matrix_world.copy()
    # Studio's importer ignores the FBX object transform and reads raw vertices, so a parented/rotated object
    # comes in un-rotated (2026-09-09: KCISA walls appeared turned 90 deg). Bake matrix_world into a temp copy.
    tmp = o.copy(); tmp.data = o.data.copy(); tmp.parent = None; tmp.animation_data_clear()
    bpy.context.scene.collection.objects.link(tmp)
    tmp.matrix_world = Matrix.Identity(4)
    tmp.name = name; tmp.data.name = name          # ASCII node names inside the FBX (Hangul node names broke door import)
    if world:
        tmp.data.transform(saved)
    if centre:   # doors: Studio drew world-baked small meshes off-pivot; put the bbox centre at the origin (master-style)
        vs = [v.co.copy() for v in tmp.data.vertices]
        c = Vector([(min(v[i] for v in vs) + max(v[i] for v in vs)) / 2 for i in range(3)])
        tmp.data.transform(Matrix.Translation(-c))
    tmp.hide_set(False); tmp.select_set(True); bpy.context.view_layer.objects.active = tmp
    path = os.path.join(OUT, folder, name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, **FBX)
    bpy.data.meshes.remove(tmp.data)
    pts = [saved @ Vector(c) for c in o.bound_box] if world else [Vector(c) for c in o.bound_box]
    mn = [min(p[i] for p in pts) for i in range(3)]; mx = [max(p[i] for p in pts) for i in range(3)]
    MANIFEST["files"].append({"file": folder + "/" + name + ".fbx", "tris": tris(o.data), "material": o.data.materials[0].name if o.data.materials else None,
                              "bbox_min_m": [round(v, 3) for v in mn], "bbox_max_m": [round(v, 3) for v in mx], "world": world})
    return path


# ------------------------------------------------------------------ JAM: KCISA original, per-material meshes
def do_jam():
    root = bpy.data.objects["장안문_KCISA"]
    meshes = [o for o in family(root) if o.type == 'MESH' and not o.name.startswith("장안문_문_")]
    for i, o in enumerate(sorted(meshes, key=lambda x: x.name)):
        if len(o.data.materials) > 1:            # KCISA is single-material per object; guard anyway
            o.data.materials[:] = [o.data.materials[0]]
        fix_material(o.data.materials[0] if o.data.materials else None)
        o.data = o.data.copy() if o.data.users > 1 else o.data
        decimate_to_cap(o)
        export_one(o, "01_JAM", "HWS_JAM_%02d_%s" % (i, "".join(ch if ch.isalnum() else "_" for ch in (o.data.materials[0].name if o.data.materials else "nomat"))[:28]))
    print("@@JAM", len(meshes))


def do_doors():
    hinges = {}
    for o in [o for o in bpy.data.objects if o.name.startswith("장안문_문_") and o.type == 'MESH']:
        fix_material(o.data.materials[0])
        decimate_to_cap(o)
        export_one(o, "02_DOORS", "HWS_DOOR_" + o.name.replace("장안문_문_", "").replace("Object_", "P"), centre=True)
        piv = o.parent
        if piv and piv.name not in hinges:
            hinges[piv.name] = {"pivot_world_m": [round(v, 3) for v in piv.matrix_world.translation], "open_deg": 88.0 * (1 if "_좌_" in piv.name else -1),
                                "leaves": []}
        if piv:
            hinges[piv.name]["leaves"].append("HWS_DOOR_" + o.name.replace("장안문_문_", "").replace("Object_", "P"))
    MANIFEST["doors"] = hinges
    print("@@DOORS", len(hinges))


def main():
    ensure_dirs()
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["all"]
    what = args[0]
    bpy.context.scene.frame_set(1)
    if what in ("jam", "all"):
        do_jam()
    if what in ("doors", "all"):
        do_doors()
    over = [f for f in MANIFEST["files"] if f["tris"] > 30000]
    json.dump(MANIFEST, open(os.path.join(OUT, "manifest_v25_%s.json" % what), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("@@TOTAL files=%d tris=%d over30k=%d" % (len(MANIFEST["files"]), sum(f["tris"] for f in MANIFEST["files"]), len(over)))


if __name__ == "__main__":
    main()
