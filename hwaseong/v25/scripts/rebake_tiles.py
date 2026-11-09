# -*- coding: utf-8 -*-
"""Re-bake the 30 terrain tiles with a wider UV inset + bake margin so the tile borders stop showing as bright lines.
Headless:  blender.exe -b hwaseong_v25.blend --python rebake_tiles.py
Output:    ovdr_export\hwaseong_v25\_rebatch_tiles2\HWS_TER2_rc.fbx / HWS_OUT2_rc.fbx  (+ _tex\T_HWS_TER2_rc.png)
Why:       T_HWS_TER_*.png rows 0..9 are ~8 % brighter than the interior (bake margin 8 == UV pad 8, bilinear
           sampling reaches the margin) -> a thin bright line along every 40 m tile edge in Studio (2026-09-10)."""
import bpy, bmesh, os, sys, json, shutil
V25 = r"C:\Users\HSP\Desktop\blender\hwaseong_rebuild\v25"
sys.path.insert(0, V25)
import hws_stage3 as S3, hws_export as HX, rebuild

PAD_PX = 24          # UV inset in texels (was 8)
MARGIN = 48          # bake margin in texels (was 8)
DST = os.path.join(HX.OUT, "_rebatch_tiles2"); os.makedirs(DST, exist_ok=True)
S3.rebuild.OUT = HX.TEXOUT

def tile_mesh(name, x0, x1, y0, y1, cell, hfun, hole=None):
    o = S3.tile_mesh(name, x0, x1, y0, y1, cell, hfun, hole)
    if not o:
        return None
    me = o.data; uv = me.uv_layers["UVMap"]; pad = PAD_PX / 1024.0
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (pad + (1 - 2 * pad) * (v.x - x0) / (x1 - x0), pad + (1 - 2 * pad) * (v.y - y0) / (y1 - y0))
    return o

def bake_tile(o, key, size=1024):
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 1
    src = bpy.data.materials["M_HWS_Terrain"]; mat = src.copy(); mat.name = "BAKE_" + key
    o.data.materials.append(mat); nt = mat.node_tree
    img = bpy.data.images.new("_bake_" + key, size, size, alpha=False)
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img; nt.nodes.active = t
    for n in nt.nodes:
        n.select = (n == t)
    ov = rebuild._sel([o], o)
    sc.render.bake.margin_type = 'EXTEND'
    with bpy.context.temp_override(**ov):
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, margin=MARGIN, use_clear=True)
    path = os.path.join(HX.TEXOUT, "T_" + key + ".png"); img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img); bpy.data.materials.remove(mat)
    final = bpy.data.materials.new("M_" + key); final.use_nodes = True
    b = final.node_tree.nodes["Principled BSDF"]; b.inputs['Roughness'].default_value = 0.95
    ti = final.node_tree.nodes.new('ShaderNodeTexImage'); ti.image = bpy.data.images.load(path)
    final.node_tree.links.new(ti.outputs['Color'], b.inputs['Base Color'])
    o.data.materials.clear(); o.data.materials.append(final)
    return path

def main():
    tv = S3.tv; SX, SY, CY = tv['SX'], tv['SY'], tv['CY']; ox, oy, _ = tv['OUTER']
    tiles = []
    xs = [-SX / 2 + 40.0 * i for i in range(5)]; ys = [CY - SY / 2 + 40.0 * j for j in range(4)]
    for i, x0 in enumerate(xs):
        for j, y0 in enumerate(ys):
            tiles.append(("HWS_TER2_%d%d" % (i, j), x0, min(x0 + 40.0, SX / 2), y0, min(y0 + 40.0, CY + SY / 2), 1.0, S3.relief, None))
    hole = (-SX / 2 - 0.01, SX / 2 + 0.01, CY - SY / 2 - 0.01, CY + SY / 2 + 0.01)
    oxs = [-ox / 2 + 100.0 * i for i in range(4)]; oys = [CY - oy / 2 + 100.0 * j for j in range(3)]
    for i, x0 in enumerate(oxs):
        for j, y0 in enumerate(oys):
            tiles.append(("HWS_OUT2_%d%d" % (i, j), x0, x0 + 100.0, y0, y0 + 100.0, 4.0, S3.berm, hole))
    HX.ensure_dirs(); done = []
    for name, x0, x1, y0, y1, cell, hf, hl in tiles:
        o = tile_mesh(name, x0, x1, y0, y1, cell, hf, hl)
        if not o:
            continue
        bake_tile(o, name)
        HX.decimate_to_cap(o)
        p = HX.export_one(o, "03_TERRAIN", name, world=True)
        shutil.move(p, os.path.join(DST, os.path.basename(p)))
        done.append(name); print("@@TILE", name)
    json.dump(done, open(os.path.join(DST, "tiles.json"), "w"))
    print("@@REBAKE done", len(done), DST)

main()
