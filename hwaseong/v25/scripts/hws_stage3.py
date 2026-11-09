# -*- coding: utf-8 -*-
"""화성 v25 이관 3~5단계 (GUI 세션에서 실행 — 베이크는 Cycles, 씬 에셋은 건드리지 않고 사본만 굽는다).
  masters : 담장 모듈 3 + BlenderKit 소품 3 → 1텍스처 베이크 사본 → 10_MASTERS\*.fbx (바닥중심 피벗, 로컬좌표)
  terrain : relief()/berm() 로 40 m 안쪽 타일 20 + 100 m 외곽 타일 12 → M_HWS_Terrain 을 1024² 로 베이크 → 03_TERRAIN\*.fbx
  dump    : 모든 인스턴스(담장·소품·나무·지면소품·정적)의 월드 변환 → scene_dump.json (hws_place.py 입력)
  collision: 쿼드트리 슬랩 → _collision\slabs.json (Part 사양, 산곡 sgk_collision 공식)
Run: ns={}; exec(open(p,encoding='utf-8').read(), ns); ns['main']()"""
import bpy, bmesh, os, sys, json, math
from mathutils import Vector, Matrix
V25 = r"C:\Users\HSP\Desktop\blender\hwaseong_rebuild\v25"; RB = os.path.dirname(V25)
for p in (V25, RB):
    if p not in sys.path:
        sys.path.append(p)
import importlib, rebuild, hws_export as HX
importlib.reload(rebuild); importlib.reload(HX)
tv = {"__name__": "tv"}; exec(compile(open(os.path.join(V25, "terrain_v25.py"), encoding="utf-8").read(), "terrain_v25.py", "exec"), tv)
relief, berm, dirt, wet, rock, litter = tv['relief'], tv['berm'], tv['dirt'], tv['wet'], tv['rock'], tv['litter']

OUT = HX.OUT; CAP = HX.CAP
X0 = -58000.0                   # 컨테이너 X 오프셋 (hwaseong-handover-spec)
YAW_FIX = 180.0                 # 산곡 MESH_YAW_FIX
DUMP = {"x0_cm": X0, "yaw_fix": YAW_FIX, "masters": {}, "instances": [], "statics": []}


def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def family(o):
    yield o
    for c in o.children:
        yield from family(c)


def wbbox(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type == 'MESH' for c in o.bound_box]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


def eng_pos(v):
    return [round(v.x * 100 + X0, 1), round(v.z * 100, 1), round(-v.y * 100, 1)]


def eng_yaw(rot_z_deg):
    return round(((rot_z_deg + YAW_FIX + 180) % 360) - 180, 2)


# ------------------------------------------------------------------ masters
def bake_master(src_objs, key, size=1024):
    """Join a COPY of src_objs (world space), unwrap, bake base colour into one PNG, return baked object (world coords)."""
    lp = rebuild.join_copy(src_objs, "BAKE_" + key)
    lp.data.transform(lp.matrix_world); lp.matrix_world = Matrix.Identity(4)
    srcs = []
    for o in src_objs:                                        # world-space copies as bake sources
        c = o.copy(); c.data = o.data.copy(); bpy.context.scene.collection.objects.link(c)
        c.data.transform(c.matrix_world); c.matrix_world = Matrix.Identity(4); srcs.append(c)
    rebuild.unwrap(lp, margin=0.006)
    rebuild.OUT = HX.TEXOUT
    path, cov, mean = rebuild.bake_class(lp, srcs, key, size=size, extr=0.04, dist=0.12)
    for c in srcs:
        bpy.data.objects.remove(c, do_unlink=True)
    # material -> single disk PNG (bake_class already saved <key>_BC.png in TEXOUT and wired it)
    return lp, path, cov


def copy_master(src_objs, key):
    """Joined COPY in world space with original UVs; every material slot -> one <=1024 disk PNG (no bake)."""
    lp = rebuild.join_copy(src_objs, "EXP_" + key)
    lp.data.transform(lp.matrix_world); lp.matrix_world = Matrix.Identity(4)
    for i, m in enumerate(list(lp.data.materials)):
        if m:
            mc = m.copy(); mc.name = "EXP_%s_%d" % (key, i); lp.data.materials[i] = mc; HX.fix_material(mc)
    return lp, None, 100.0


def export_master(lp, key):
    """pivot = bottom centre; export in local coords; record local bbox."""
    mn, mx = wbbox([lp]); off = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    lp.data.transform(Matrix.Translation(-off))
    HX.decimate_to_cap(lp)
    HX.export_one(lp, "10_MASTERS", "HWS_" + key, world=False)
    mn2, mx2 = wbbox([lp])
    DUMP["masters"][key] = {"file": "10_MASTERS/HWS_%s.fbx" % key, "size_cm": [round((mx2.x - mn2.x) * 100, 1), round((mx2.z - mn2.z) * 100, 1), round((mx2.y - mn2.y) * 100, 1)],
                            "centre_offset_m": [round(v, 3) for v in ((mn2 + mx2) / 2)], "tris": tris(lp.data), "materials": len(lp.data.materials)}
    bpy.data.meshes.remove(lp.data)
    return off


def do_masters():
    # 1) compound modules: prototypes NH_* (KIT_RAW), instances = copies sharing the mesh
    kit = bpy.data.collections["KIT_RAW"]
    for key in ("NH_WALL", "NH_PARAPET", "NH_SECRETGATE"):
        # the placed copies share the mesh of whichever NH_* import they were made from (may be NH_WALL.001)
        cands = [o for o in kit.objects if o.name.startswith(key)]
        used = {o.data for o in bpy.data.objects if o.name.startswith("담장_") and o.type == 'MESH'}
        proto = next((c for c in cands if c.data in used), cands[0])
        lp, path, cov = copy_master([proto], key)
        off = export_master(lp, key)                          # off = bottom centre in proto-world coords
        n = 0
        for o in bpy.data.objects:
            if o.type == 'MESH' and o.data == proto.data and o is not proto:
                rel = o.matrix_world @ proto.matrix_world.inverted()          # rigid: copy frame vs proto frame
                pos = rel @ off; yaw = math.degrees(rel.to_euler('XYZ').z)
                DUMP["instances"].append({"master": key, "name": o.name, "pos_m": [round(v, 3) for v in pos], "yaw_deg": round(yaw, 2), "scale": 1.0}); n += 1
        print("@@MASTER", key, "cov %.0f%%" % cov, "instances", n)
    # 2) BlenderKit props: roots with asset_data (Pots / Barrel / Hay) — first root per asset is the master
    groups = {}
    for r in [o for o in bpy.data.objects if o.get("asset_data") is not None]:
        groups.setdefault(r["asset_data"]["name"], []).append(r)
    for aname, roots in groups.items():
        if "Pine" in aname:
            continue
        key = "BK_" + "".join(ch for ch in aname.title() if ch.isalnum())[:16]
        r0 = roots[0]; meshes0 = [o for o in family(r0) if o.type == 'MESH']
        has_img = all(any(n.type == 'TEX_IMAGE' and n.image for n in m.node_tree.nodes) for o in meshes0 for m in o.data.materials if m and m.use_nodes)
        lp, path, cov = copy_master(meshes0, key) if has_img else bake_master(meshes0, key)   # procedural (noise/ramp) materials must be baked
        # bring baked copy into r0-local frame so the pivot maths below is per-root
        lp.data.transform(r0.matrix_world.inverted())
        off = export_master(lp, key)                          # bottom centre in r0-local coords
        for r in roots:
            pos = r.matrix_world @ off; yaw = math.degrees(r.matrix_world.to_euler('XYZ').z); sc = r.matrix_world.to_scale().x / r0.matrix_world.to_scale().x
            DUMP["instances"].append({"master": key, "name": r.name, "pos_m": [round(v, 3) for v in pos], "yaw_deg": round(yaw, 2), "scale": round(sc, 3)})
        print("@@MASTER", key, "cov %.0f%%" % cov, "instances", len(roots))


# ------------------------------------------------------------------ vegetation / clutter instances (Sangok masters, no FBX)
def do_veg():
    kit = bpy.data.collections.get("KIT_SGK")
    by_mesh = {o.data: o.name for o in kit.objects if o.type == 'MESH'} if kit else {}
    n = 0
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.data in by_mesh and (o.name.startswith("수목_") or o.name.startswith("지면소품_")):
            m = o.matrix_world; mn, mx = wbbox([o])
            DUMP["instances"].append({"master": by_mesh[o.data], "sangok_asset": True, "name": o.name, "pos_m": [round(v, 3) for v in m.translation],
                                      "yaw_deg": round(math.degrees(m.to_euler('XYZ').z), 2), "scale": round(m.to_scale().x, 3),
                                      "bbox_min_m": [round(v, 2) for v in mn], "bbox_max_m": [round(v, 2) for v in mx]}); n += 1
    print("@@VEG instances", n)


# ------------------------------------------------------------------ terrain tiles (bake M_HWS_Terrain → 1024 PNG per tile)
def tile_mesh(name, x0, x1, y0, y1, cell, hfun, hole=None):
    nx, ny = int(round((x1 - x0) / cell)) + 1, int(round((y1 - y0) / cell)) + 1
    bm = bmesh.new()
    grid = [[bm.verts.new((x0 + i * cell, y0 + j * cell, 0.0)) for j in range(ny)] for i in range(nx)]
    for row in grid:
        for v in row:
            v.co.z = hfun(v.co.x, v.co.y)
    for i in range(nx - 1):
        for j in range(ny - 1):
            q = (grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1])
            if hole and all(hole[0] < v.co.x < hole[1] and hole[2] < v.co.y < hole[3] for v in q):
                continue
            bm.faces.new(q)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    if not bm.faces:
        bm.free(); return None
    uv = bm.loops.layers.uv.new("UVMap"); pad = 8.0 / 1024.0
    for f in bm.faces:
        for l in f.loops:
            l[uv].uv = (pad + (1 - 2 * pad) * (l.vert.co.x - x0) / (x1 - x0), pad + (1 - 2 * pad) * (l.vert.co.y - y0) / (y1 - y0))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ca = me.color_attributes.new("Blend", 'FLOAT_COLOR', 'POINT'); cols = []
    for v in me.vertices:
        x, y, z = v.co
        cols += [dirt(x, y), rock(x, y, z), wet(x, y, z), litter(x, y)]
    ca.data.foreach_set("color", cols)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    return o


def bake_tile(o, key, size=1024):
    """Diffuse colour of M_HWS_Terrain baked to the tile's own UVs (Cycles, 1 sample)."""
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 1
    src = bpy.data.materials["M_HWS_Terrain"]; mat = src.copy(); mat.name = "BAKE_" + key
    o.data.materials.append(mat); nt = mat.node_tree
    img = bpy.data.images.new("_bake_" + key, size, size, alpha=False)
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img; nt.nodes.active = t
    for n in nt.nodes:
        n.select = (n == t)
    ov = rebuild._sel([o], o)
    with bpy.context.temp_override(**ov):
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, margin=8, use_clear=True)
    # texture file name must differ from the mesh name: Studio makes Texture2D <stem> and then the mesh <stem> collides ("object is in use", Code 1315)
    path = os.path.join(HX.TEXOUT, "T_" + key + ".png"); img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img); bpy.data.materials.remove(mat)
    final = bpy.data.materials.new("M_" + key); final.use_nodes = True
    b = final.node_tree.nodes["Principled BSDF"]; b.inputs['Roughness'].default_value = 0.95
    ti = final.node_tree.nodes.new('ShaderNodeTexImage'); ti.image = bpy.data.images.load(path)
    final.node_tree.links.new(ti.outputs['Color'], b.inputs['Base Color'])
    o.data.materials.clear(); o.data.materials.append(final)
    return path


def do_terrain():
    SX, SY, CY = tv['SX'], tv['SY'], tv['CY']; ox, oy, _ = tv['OUTER']
    tiles = []
    xs = [-SX / 2 + 40.0 * i for i in range(5)]; ys = [CY - SY / 2 + 40.0 * j for j in range(4)]
    for i, x0 in enumerate(xs):
        for j, y0 in enumerate(ys):
            tiles.append(("HWS_TER_%d%d" % (i, j), x0, min(x0 + 40.0, SX / 2), y0, min(y0 + 40.0, CY + SY / 2), 1.0, relief, None))
    hole = (-SX / 2 - 0.01, SX / 2 + 0.01, CY - SY / 2 - 0.01, CY + SY / 2 + 0.01)
    oxs = [-ox / 2 + 100.0 * i for i in range(4)]; oys = [CY - oy / 2 + 100.0 * j for j in range(3)]
    for i, x0 in enumerate(oxs):
        for j, y0 in enumerate(oys):
            tiles.append(("HWS_OUT_%d%d" % (i, j), x0, x0 + 100.0, y0, y0 + 100.0, 4.0, berm, hole))
    n = 0
    for name, x0, x1, y0, y1, cell, hf, hl in tiles:
        o = tile_mesh(name, x0, x1, y0, y1, cell, hf, hl)
        if not o:
            continue
        bake_tile(o, name)
        HX.decimate_to_cap(o)
        HX.export_one(o, "03_TERRAIN", name, world=True)
        mn, mx = wbbox([o])
        DUMP["statics"].append({"file": "03_TERRAIN/%s.fbx" % name, "bbox_min_m": [round(v, 3) for v in mn], "bbox_max_m": [round(v, 3) for v in mx], "tris": tris(o.data), "collide": False})
        bpy.data.meshes.remove(o.data); n += 1
    json.dump({"files": [f for f in HX.MANIFEST["files"] if f["file"].startswith("03_TERRAIN/")]}, open(os.path.join(OUT, "manifest_v25_terrain.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("@@TERRAIN tiles", n)


# ------------------------------------------------------------------ collision slabs (quadtree + plane fit, Sangok formula)
THICK = 0.4   # 2026-09-10: 1.0 이면 윗면(중심+0.5)이 잔디 기복 위로 튀어나와 슬랩 격자가 보였다. 0.4 → 윗면 -0.3 m


def slab(x0, x1, y0, y1, hf, out, tol=0.25, minsz=4.01):
    xs = [x0 + (x1 - x0) * k / 4 for k in range(5)]; ys = [y0 + (y1 - y0) * k / 4 for k in range(5)]
    pts = [(x, y, hf(x, y)) for x in xs for y in ys]
    zs = [p[2] for p in pts]
    if (max(zs) - min(zs) > tol) and (x1 - x0) > minsz:
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        for a, b, c, d in ((x0, mx, y0, my), (mx, x1, y0, my), (x0, mx, my, y1), (mx, x1, my, y1)):
            slab(a, b, c, d, hf, out, tol, minsz)
        return
    # least-squares plane z = ax + by + c
    n = len(pts); sx = sum(p[0] for p in pts); sy = sum(p[1] for p in pts); sz = sum(p[2] for p in pts)
    cx, cy, cz = sx / n, sy / n, sz / n
    sxx = sum((p[0] - cx) ** 2 for p in pts); syy = sum((p[1] - cy) ** 2 for p in pts); sxy = sum((p[0] - cx) * (p[1] - cy) for p in pts)
    sxz = sum((p[0] - cx) * (p[2] - cz) for p in pts); syz = sum((p[1] - cy) * (p[2] - cz) for p in pts)
    det = sxx * syy - sxy * sxy
    a, b = ((sxz * syy - syz * sxy) / det, (syz * sxx - sxz * sxy) / det) if abs(det) > 1e-9 else (0.0, 0.0)
    nrm = Vector((-a, -b, 1.0)).normalized()
    nx, ny, nz = nrm.x, nrm.z, -nrm.y                       # blender → engine axes
    rz = -math.degrees(math.asin(max(-1.0, min(1.0, nx)))); rx = math.degrees(math.atan2(nz, ny))
    top = Vector((cx, cy, cz)); centre = top - nrm * (THICK / 2)
    out.append({"className": "Part", "name": "COL_HWS_%04d" % len(out),
                "props": {"position": eng_pos(centre), "size": [round((x1 - x0) * 100, 1), THICK * 100, round((y1 - y0) * 100, 1)],
                          "orientation": [round(rx, 3), 0.0, round(rz, 3)], "anchored": True, "mobility": "Static",
                          "shape": "Block", "mobility": "Movable",   # MCP default shape is Cylinder -> no walkable slab (2026-09-10)
                          "raw": {"Transparency": 1.0, "CanCollide": True, "CastShadow": False, "CanTouch": False, "Material": "Unlit"}}})


def do_collision():
    SX, SY, CY = tv['SX'], tv['SY'], tv['CY']; ox, oy, _ = tv['OUTER']
    out = []
    for i in range(int(SX / 16)):
        for j in range(int(math.ceil(SY / 16))):
            x0 = -SX / 2 + 16 * i; y0 = CY - SY / 2 + 16 * j
            slab(x0, x0 + 16, y0, min(y0 + 16, CY + SY / 2), relief, out)
    inner = len(out)
    for i in range(int(ox / 32)):
        for j in range(int(oy / 32)):
            x0 = -ox / 2 + 32 * i; y0 = CY - oy / 2 + 32 * j
            if -SX / 2 <= x0 and x0 + 32 <= SX / 2 and CY - SY / 2 <= y0 and y0 + 32 <= CY + SY / 2:
                continue
            slab(x0, x0 + 32, y0, y0 + 32, berm, out, tol=2.5, minsz=16.01)   # unreachable ring: coarse
    os.makedirs(os.path.join(OUT, "_collision"), exist_ok=True)
    for k in range(0, len(out), 200):
        json.dump(out[k:k + 200], open(os.path.join(OUT, "_collision", "items_col_%03d.json" % (k // 200)), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("@@COLLISION slabs", len(out), "inner", inner)
    return len(out)


def do_statics_from_manifests():
    for name in ("manifest_v25_jam.json", "manifest_v25_doors.json", "manifest_v25_terrain.json"):
        p = os.path.join(OUT, name)
        if os.path.exists(p):
            m = json.load(open(p, encoding="utf-8"))
            for f in m["files"]:
                if any(x["file"] == f["file"] for x in DUMP["statics"]):
                    continue
                DUMP["statics"].append({"file": f["file"], "bbox_min_m": f["bbox_min_m"], "bbox_max_m": f["bbox_max_m"], "tris": f["tris"], "collide": not f["file"].startswith("03_TERRAIN/")})
            if "doors" in m:
                DUMP["doors"] = m["doors"]


def main(parts=("masters", "veg", "terrain", "collision")):
    HX.ensure_dirs(); bpy.context.scene.frame_set(1)
    if "masters" in parts:
        do_masters()
    if "veg" in parts:
        do_veg()
    if "terrain" in parts:
        do_terrain()
    if "collision" in parts:
        do_collision()
    do_statics_from_manifests()
    json.dump(DUMP, open(os.path.join(OUT, "scene_dump.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(HX.MANIFEST, open(os.path.join(OUT, "manifest_v25_stage3.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("@@DUMP masters=%d instances=%d statics=%d" % (len(DUMP["masters"]), len(DUMP["instances"]), len(DUMP["statics"])))
