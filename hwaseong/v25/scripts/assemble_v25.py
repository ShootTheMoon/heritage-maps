# -*- coding: utf-8 -*-
"""Assemble the Janganmun arena (v25). Run in GUI after jam_reduce + kit_namhan.
Frame: origin = gate centre, +X along the wall, -Y = outside (north), +Y = inside (south). Metres.
Everything placed here is a *copy* (shared mesh) of a prototype; the exporter bakes matrix_world."""
import bpy, math
from mathutils import Vector, Matrix

PROPS = r"C:\Users\HSP\Desktop\blender\gyeongbokgung\hwaseong_props.blend"
PROP_NAMES = ["초가집", "대문", "상가", "소나무", "바위무리", "사랑채"]
KIT = "KIT_NH"; PROTO = "KIT_PROPS"
C_WALL, C_BLD, C_VEG, C_GND, C_PROP = "화성_성벽", "화성_도시_건물", "화성_수목", "화성_지면", "화성_소품"
WALL_L, WALL_H, WALL_T = 8.0, 3.98, 6.33     # NH_WALL module
PARA_L, PARA_T = 4.0, 1.01                   # NH_PARAPET module
# inner compound rectangle (metres): x -36..36 (9 modules), y 24..56 (4 modules)
CX0, CX1, CY0, CY1 = -36.0, 36.0, 24.0, 56.0
FACE = +1   # which local-Y side of NH_WALL is the outer face; flip to -1 after the first snap if wrong
USE_STALLS = False   # Sketchfab shop stalls look modern; off unless the snap says otherwise


def coll(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
    return c


def wipe(prefix):
    for o in [o for o in bpy.data.objects if o.name.startswith(prefix)]:
        bpy.data.objects.remove(o, do_unlink=True)


def place(proto, name, loc, rot_z=0.0, col=None, scale=1.0):
    o = proto.copy(); o.name = name
    o.location = Vector(loc); o.rotation_mode = 'XYZ'
    o.rotation_euler = (0.0, 0.0, math.radians(rot_z)); o.scale = (scale, scale, scale)
    o.hide_set(False); o.hide_viewport = False
    col.objects.link(o)
    return o


def bake_and_ground(o):
    """Bake world matrix into the mesh, then move the mesh so bbox bottom-centre = origin."""
    me = o.data
    me.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    off = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)))
    me.transform(Matrix.Translation(-off)); me.update()
    return [round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1), round(max(zs) - min(zs), 1)]


def load_props():
    pc = coll(PROTO)
    have = {o.name for o in pc.objects}
    need = [n for n in PROP_NAMES if "P_" + n not in have]
    if need:
        with bpy.data.libraries.load(PROPS, link=False) as (df, dt):
            dt.objects = [n for n in df.objects if n in need]
        for o in dt.objects:
            if not o:
                continue
            o.name = "P_" + o.name; pc.objects.link(o)
            dims = bake_and_ground(o)
            o.location = (0.0, 300.0 + 20.0 * PROP_NAMES.index(o.name[2:]), 0.0)
            print("@@PROP", o.name, dims, sum(len(p.vertices) - 2 for p in o.data.polygons), [m.name for m in o.data.materials][:3])
    return {o.name[2:]: o for o in pc.objects}


def compound(kit, wc):
    """Inner compound: NH_WALL modules + parapets, 암문 north-centre, gap south-centre, 포좌 at N corners."""
    W, P, G, S = kit["NH_WALL"], kit["NH_PARAPET"], kit["NH_SECRETGATE"], kit["NH_GUNPOST"]
    n = 0
    def run(x, y, rot, mod, tag):
        nonlocal n
        n += 1
        place(mod, "CMP_%s_%02d" % (tag, n), (x, y, 0.0), rot, wc)
        # parapets on top along the module's local +X, offset to the outer face
        for k in range(2):
            lx = k * PARA_L
            ly = FACE * (WALL_T / 2 - PARA_T / 2)
            r = math.radians(rot)
            gx = x + lx * math.cos(r) - ly * math.sin(r); gy = y + lx * math.sin(r) + ly * math.cos(r)
            place(P, "CMP_PAR_%02d_%d" % (n, k), (gx, gy, WALL_H), rot, wc)
    # north side (y=CY0, outer face = -Y): rot 180 puts local +Y toward -Y
    for x in [-36, -28, -20, -12, 4, 12, 20, 28]:
        run(x + WALL_L, CY0, 180, W, "N")
    place(G, "CMP_GATE_N", (4.0, CY0, 0.0), 180, wc)           # 암문 spans x -4..4
    # south side (y=CY1, outer face = +Y): rot 0; opening closed to the 대문 width (x -1.4..1.4) with two stubs
    for x in [-36, -28, -20, -12, 4, 12, 20, 28]:
        run(x, CY1, 0, W, "S")
    for i, x in enumerate([-4.0, 1.4]):
        o = place(W, "CMP_S_STUB_%d" % i, (x, CY1, 0.0), 0, wc); o.scale = (2.6 / WALL_L, 1.0, 1.0)
    # west side (x=CX0, outer face = -X): rot -90 -> local +Y = -X ... use 270
    for y in [24, 32, 40, 48]:
        run(CX0, y + WALL_L, 270, W, "W")
    # east side (x=CX1, outer face = +X): rot 90
    for y in [24, 32, 40, 48]:
        run(CX1, y, 90, W, "E")
    # corner bastions 6.4 x 5.9 m centred on the four corners (they also hide the 3.2 m corner notches)
    for i, (cx, cy) in enumerate([(CX0, CY0), (CX1, CY0), (CX0, CY1), (CX1, CY1)]):
        o = place(S, "CMP_GUNPOST_%d" % i, (cx - 3.2, cy, 0.0), 0, wc); o.scale = (1.6, 1.6, 1.0)
    bpy.context.view_layer.update()


def ground(gc):
    wipe("지면_")
    me = bpy.data.meshes.new("지면_아레나"); bm = __import__("bmesh").new()
    __import__("bmesh").ops.create_cube(bm, size=1.0); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("지면_아레나", me); gc.objects.link(o)
    o.location = (0.0, 5.0, -0.5); o.scale = (200.0, 150.0, 1.0)
    m = bpy.data.materials.get("흙바닥") or bpy.data.materials.new("흙바닥")
    m.diffuse_color = (0.42, 0.36, 0.28, 1.0); me.materials.append(m)
    return o


def village(props, bc, vc):
    P = dict(props)
    for k in list(P):
        b = bpy.data.objects.get("PB_" + k)
        if b:
            P[k] = b
    if bpy.data.objects.get("P_소나무2"):
        P["소나무"] = bpy.data.objects["P_소나무2"]
    ms = bpy.data.objects.get("P_연자방아")
    if ms:
        for i, (x, y, r) in enumerate([(-14, 34, 0), (16, 48, 40), (-42, 30, 75), (44, 34, 15)]):
            place(ms, "소품_연자방아_%d" % i, (x, y, 0.0), r, bc)
    main_house = bpy.data.objects.get("P_동아시아집") or P["사랑채"]   # Sketchfab CC-BY placeholder (stage 1)
    place(main_house, "민가_본채", (0.0, 42.0, 0.0), 180, bc)
    place(P["대문"], "민가_대문", (0.0, CY1, 0.0), 0, bc)
    place(P["초가집"], "민가_초가_1", (-56.0, 16.0, 0.0), 90, bc)
    place(P["초가집"], "민가_초가_2", (52.0, 20.0, 0.0), -90, bc)
    place(P["초가집"], "민가_초가_3", (-50.0, 52.0, 0.0), 0, bc)
    place(P["초가집"], "민가_초가_4", (52.0, 50.0, 0.0), 180, bc)
    if USE_STALLS:
        place(P["상가"], "민가_상가_1", (-16.0, 12.0, 0.0), 0, bc)
        place(P["상가"], "민가_상가_2", (16.0, 12.0, 0.0), 0, bc)
    trees = [(-40, -46, 0), (38, -50, 20), (-22, -62, 45), (25, -66, 70), (-62, -30, 110), (60, -28, 160),
             (-64, 62, 0), (64, 64, 90)]
    for i, (x, y, r) in enumerate(trees):
        place(P["소나무"], "수목_소나무_%d" % i, (x, y, 0.0), r, vc, scale=1.0 + 0.15 * (i % 3))
    for i, (x, y, r) in enumerate([(-30, -55, 0), (45, -40, 60), (-70, 45, 120)]):
        place(P["바위무리"], "수목_바위_%d" % i, (x, y, 0.0), r, vc)


def main():
    kit = {o.name: o for o in bpy.data.collections[KIT].objects}
    props = load_props()
    for pre in ("CMP_", "담장_", "민가_", "수목_", "소품_연자"):
        wipe(pre)
    wc, bc, vc, gc = coll(C_WALL), coll(C_BLD), coll(C_VEG), coll(C_GND)
    compound(kit, wc)
    village(props, bc, vc)
    ground(gc)
    n = {c: len(bpy.data.collections[c].objects) for c in (C_WALL, C_BLD, C_VEG, C_GND, C_PROP, "화성_장안문")}
    print("@@ASSEMBLED", n)


if __name__ == "__main__":
    main()


def _join(objs, name):
    """Join copies into one real mesh (make single-user first: they share prototype meshes)."""
    objs = [o for o in objs if o]
    if not objs:
        return None
    for o in objs:
        if o.data.users > 1:
            o.data = o.data.copy()
    bpy.context.view_layer.update()
    vl = bpy.context.view_layer
    for o in vl.objects:
        o.select_set(False)
    for o in objs:
        o.hide_set(False); o.select_set(True)
    vl.objects.active = objs[0]
    area = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D')
    region = next(r for r in area.regions if r.type == 'WINDOW')
    with bpy.context.temp_override(window=bpy.context.window, area=area, region=region,
                                   active_object=objs[0], selected_objects=objs, selected_editable_objects=objs):
        bpy.ops.object.join()
    o = objs[0]; o.name = name; o.data.name = name
    return o


def consolidate():
    """Instance count is the fps lever: merge the compound per side, trees, rocks, houses, stalls.
    Material splits happen later in the exporter (1 texture per MeshPart)."""
    objs = bpy.data.objects
    for side in "NSEW":
        _join([o for o in objs if o.name.startswith("CMP_%s_" % side) or
               (o.name.startswith("CMP_PAR_") and o.get("side") == side)], "담장_" + side)
    _join([o for o in objs if o.name.startswith("CMP_PAR_")], "담장_여장")   # leftovers (no side tag)
    _join([o for o in objs if o.name.startswith("CMP_GUNPOST_")], "담장_포좌")
    g = objs.get("CMP_GATE_N")
    if g:
        g.name = "담장_암문"
    _join([o for o in objs if o.name.startswith("수목_소나무_")], "수목_소나무")
    _join([o for o in objs if o.name.startswith("수목_바위_")], "수목_바위")
    _join([o for o in objs if o.name.startswith("민가_초가_")], "민가_초가")
    _join([o for o in objs if o.name.startswith("민가_상가_")], "민가_상가")
    _join([o for o in objs if o.name.startswith("소품_연자방아_")], "소품_연자방아")
    print("@@CONSOLIDATED", {c.name: len(c.objects) for c in bpy.data.collections if c.name.startswith("화성_")})


def roads():
    """Dirt-road decals (CTR): thin quads at z=0.03, non-walkable; the Part slab below carries collision."""
    import bmesh
    rc = coll("화성_도시_도로")
    for o in [o for o in bpy.data.objects if o.name.startswith("도로_")]:
        bpy.data.objects.remove(o, do_unlink=True)
    mat = bpy.data.materials.get("흙길") or bpy.data.materials.new("흙길"); mat.diffuse_color = (0.36, 0.30, 0.22, 1)

    def strip(name, cx, cy, sx, sy):
        me = bpy.data.meshes.new(name); bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5); bm.to_mesh(me); bm.free()
        me.materials.append(mat); o = bpy.data.objects.new(name, me); rc.objects.link(o)
        o.location = (cx, cy, 0.03); o.scale = (sx, sy, 1)
    strip("도로_남북", 0, 14, 6, 20); strip("도로_동서", 0, 14, 120, 5); strip("도로_북", 0, -18, 6, 24)


def split_multi():
    """export_overdare.material_key() reads only slot 0 -> every export object must be single-material.
    Separate multi-material objects by material (pine trunk/needles etc.)."""
    done = []
    for c in [c for c in bpy.data.collections if c.name.startswith("화성_")]:
        for o in list(c.objects):
            if o.type == 'MESH' and len(o.data.materials) > 1:
                if o.data.users > 1:
                    o.data = o.data.copy()
                vl = bpy.context.view_layer
                for x in vl.objects:
                    x.select_set(False)
                o.hide_set(False); o.select_set(True); vl.objects.active = o
                area = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D')
                region = next(r for r in area.regions if r.type == 'WINDOW')
                with bpy.context.temp_override(window=bpy.context.window, area=area, region=region,
                                               active_object=o, selected_objects=[o], selected_editable_objects=[o]):
                    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.mesh.separate(type='MATERIAL'); bpy.ops.object.mode_set(mode='OBJECT')
                done.append(o.name)
    # drop now-unused material slots
    for c in [c for c in bpy.data.collections if c.name.startswith("화성_")]:
        for o in c.objects:
            if o.type == 'MESH' and len(o.data.materials) > 1:
                used = {p.material_index for p in o.data.polygons}
                for i in reversed(range(len(o.data.materials))):
                    if i not in used:
                        o.data.materials.pop(index=i)
    print("@@SPLIT", done)
