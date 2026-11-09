# -*- coding: utf-8 -*-
"""
sgk_live.py — JSN_Sangok2 씬 빌더 (Blender 안에서 실행).  지형 정의는 전부 sgk_layout 에서 읽는다.

사용 (blender-mcp execute_blender_code 또는 headless):
    exec(open(r"C:\\Users\\29\\Desktop\\blender\\JSN_Sangok2\\_scripts\\sgk_live.py", encoding="utf-8").read())
    boot(); make_terrain(); make_walls(); make_water(); make_blockouts(); make_lighting(); make_cameras(); save(); render("p1")

Phase 1 = 블록아웃: 지형(레인 디버그 색) + 산벽 + 물 + 구조물 그레이박스 + 스폰/경계 마커 + 카메라.
"""
import bpy, bmesh, math, os, sys, time, importlib
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"C:\Users\29\Desktop\blender\JSN_Sangok2\_scripts"
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import sgk_layout as L
importlib.reload(L)

MASTER = os.path.join(ROOT, "00_Source_Blender", "SGK_Master.blend")
PREVIEWS = os.path.join(ROOT, "04_Previews")
COLL = {"TER": "SGK_TERRAIN", "WATER": "SGK_WATER", "BLOCK": "SGK_BLOCKOUT", "MARK": "SGK_MARKERS",
        "CAM": "SGK_CAMS", "LIGHT": "SGK_LIGHT", "VEG": "SGK_VEG", "ROCK": "SGK_ROCK", "STRUCT": "SGK_STRUCT"}

# ------------------------------------------------------------------ 공용
def _coll(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c

def _clear_coll(name):
    c = bpy.data.collections.get(name)
    if not c:
        return
    for o in list(c.objects):
        bpy.data.objects.remove(o, do_unlink=True)

def _link(obj, cname):
    for c in obj.users_collection:
        c.objects.unlink(obj)
    _coll(cname).objects.link(obj)
    return obj

def _flat_mat(name, rgb, alpha=1.0, emit=0.0):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.85
        if alpha < 1.0:
            bsdf.inputs["Alpha"].default_value = alpha
            m.blend_method = "BLEND"
        if emit > 0:
            bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
            bsdf.inputs["Emission Strength"].default_value = emit
    return m

def boot(fresh=True):
    """씬 비우고 컬렉션 준비. fresh=False 면 기존 오브젝트 유지."""
    if fresh:
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        for c in list(bpy.data.collections):
            if c.name.startswith("SGK_") or c.users == 0:
                bpy.data.collections.remove(c)
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    for n in COLL.values():
        _coll(n)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    print("boot ok")

# ------------------------------------------------------------------ 지형
LANE_COLORS = {   # 디버그 표시색 (Phase 1)
    "spawn": (0.85, 0.20, 0.20), "crest": (0.95, 0.85, 0.25), "cliff": (0.45, 0.42, 0.40),
    "ramp": (0.95, 0.55, 0.15), "stream": (0.15, 0.40, 0.85), "ford": (0.35, 0.70, 0.90),
    "path": (0.55, 0.38, 0.22), "glade": (0.70, 0.85, 0.40), "bowl": (0.85, 0.75, 0.55),
    "strip": (0.20, 0.45, 0.25), "wall": (0.60, 0.62, 0.60), "forest": (0.25, 0.55, 0.28), "knoll": (0.55, 0.62, 0.30),
}
LANE_ORDER = ("stream", "ford", "ramp", "spawn", "crest", "cliff", "path", "glade", "bowl", "knoll", "strip", "wall", "forest")

def _lane_rgb(lm):
    best, bw = (0.35, 0.60, 0.30), 0.0
    for k in LANE_ORDER:
        w = lm.get(k, 0.0)
        if k == "ford":
            w = lm["ford"] * 1.2
        if w > 0.35 and w > bw:
            best, bw = LANE_COLORS[k], w
    return best

def _grid_mesh(name, x0, x1, y0, y1, step, cname, skirt=0.0, colors=True):
    nx = int(round((x1 - x0) / step)); ny = int(round((y1 - y0) / step))
    bm = bmesh.new()
    verts = [[None] * (ny + 1) for _ in range(nx + 1)]
    blend = {}; lane = {}
    t0 = time.time()
    for i in range(nx + 1):
        x = x0 + i * step
        for j in range(ny + 1):
            y = y0 + j * step
            v = bm.verts.new((x, y, L.height_at(x, y)))
            verts[i][j] = v
            if colors:
                blend[v] = L.blend_at(x, y)
                lane[v] = _lane_rgb(L.lane_mask(x, y))
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((verts[i][j], verts[i + 1][j], verts[i + 1][j + 1], verts[i][j + 1]))
    if skirt > 0.0:
        edges = [e for e in bm.edges if e.is_boundary]
        r = bmesh.ops.extrude_edge_only(bm, edges=edges)
        for el in r["geom"]:
            if isinstance(el, bmesh.types.BMVert):
                el.co.z -= skirt
    bm.verts.index_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    if colors:
        ca = me.color_attributes.new("Blend", "FLOAT_COLOR", "POINT")
        cb = me.color_attributes.new("Lane", "FLOAT_COLOR", "POINT")
        for v in bm.verts:
            if v in blend:
                r, g, b, a = blend[v]
                ca.data[v.index].color = (r, g, b, a)
                cb.data[v.index].color = (*lane[v], 1.0)
            else:
                ca.data[v.index].color = (0, 0.6, 0, 0); cb.data[v.index].color = (0.4, 0.4, 0.4, 1)
    bm.free()
    me.validate(); me.update()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    _link(ob, cname)
    print(f"{name}: {nx}x{ny} quads, {len(me.polygons)*2} tris, {time.time()-t0:.1f}s")
    return ob

def _lane_debug_material():
    m = bpy.data.materials.get("M_SGK_LaneDebug")
    if m:
        return m
    m = bpy.data.materials.new("M_SGK_LaneDebug"); m.use_nodes = True
    nt = m.node_tree
    attr = nt.nodes.new("ShaderNodeVertexColor"); attr.layer_name = "Lane"; attr.location = (-400, 0)
    bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = 0.9
    nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    return m

def make_terrain():
    _clear_coll(COLL["TER"])
    ob = _grid_mesh("SGK_Terrain", -L.PLAY_X, L.PLAY_X, -L.PLAY_Y, L.PLAY_Y, L.GRID, COLL["TER"])
    ob.data.materials.append(_lane_debug_material())
    return ob

def make_walls(step=1.25):
    """외곽 산벽 4장 (1.25 m 격자, 스커트 −40). N/S 260×50 m → 8.3k quads."""
    for o in list(_coll(COLL["TER"]).objects):
        if o.name.startswith("SGK_Wall_"):
            bpy.data.objects.remove(o, do_unlink=True)
    X, Y, MX, MY = L.PLAY_X, L.PLAY_Y, L.MESH_X, L.MESH_Y
    specs = {"N": (-MX, MX, Y, MY), "S": (-MX, MX, -MY, -Y), "E": (X, MX, -Y, Y), "W": (-MX, -X, -Y, Y)}
    for k, (x0, x1, y0, y1) in specs.items():
        ob = _grid_mesh(f"SGK_Wall_{k}", x0, x1, y0, y1, step, COLL["TER"], skirt=40.0)
        ob.data.materials.append(_lane_debug_material())

# ------------------------------------------------------------------ 물
def _waterline(x, yc, wz, direction, span=4.5):
    """수면 wz 가 지면과 만나는 y 를 이분법으로 (direction ±1)."""
    lo, hi = 0.0, span
    if L.height_at(x, yc + direction * hi) < wz:   # 스팬 끝도 물속이면 스팬 끝
        return yc + direction * hi
    for _ in range(24):
        mid = (lo + hi) * 0.5
        if L.height_at(x, yc + direction * mid) < wz:
            lo = mid
        else:
            hi = mid
    return yc + direction * hi

def make_water(step=1.0, cols=9):
    _clear_coll(COLL["WATER"])
    xs = []
    x = -L.STREAM_FADE_END + 2.0
    while x <= L.STREAM_FADE_END - 2.0:
        xs.append(x); x += step
    bm = bmesh.new()
    rows = []
    for x in xs:
        if L.stream_len(x) <= 0.7:   # 소멸 구간은 도랑이 얕아 수면이 번져 보인다 → 메시를 먼저 끝낸다 (2026-09-05)
            continue
        yc = L.stream_center(x); wz = L.water_z(x)
        yl = _waterline(x, yc, wz, -1.0); yr = _waterline(x, yc, wz, +1.0)
        if yr - yl < 0.3:
            continue
        row = [bm.verts.new((x, L.lerp(yl, yr, c / (cols - 1)), wz)) for c in range(cols)]
        rows.append(row)
    for a, b in zip(rows, rows[1:]):
        for c in range(cols - 1):
            try:
                bm.faces.new((a[c], a[c + 1], b[c + 1], b[c]))
            except ValueError:
                pass
    me = bpy.data.meshes.new("SGK_StreamWater"); bm.to_mesh(me); bm.free(); me.update()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new("SGK_StreamWater", me); _link(ob, COLL["WATER"])
    ob.data.materials.append(_flat_mat("M_SGK_WaterDebug", (0.10, 0.35, 0.75), alpha=0.75))
    print("water rows", len(rows), "tris", len(me.polygons) * 2)
    return ob

# ------------------------------------------------------------------ 블록아웃 / 마커
def _box(name, cx, cy, yaw_deg, sx, sy, sz, cname, mat, z=None, sink=0.0):
    zb = L.height_at(cx, cy) if z is None else z
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, zb - sink + sz * 0.5))
    ob = bpy.context.active_object; ob.name = name
    ob.scale = (sx, sy, sz); ob.rotation_euler = (0, 0, math.radians(yaw_deg))
    _link(ob, cname); ob.data.materials.append(mat)
    return ob

def _cyl(name, cx, cy, r, h, cname, mat, z=None):
    zb = L.height_at(cx, cy) if z is None else z
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=(cx, cy, zb + h * 0.5), vertices=48)
    ob = bpy.context.active_object; ob.name = name; _link(ob, cname); ob.data.materials.append(mat)
    return ob

def make_blockouts():
    _clear_coll(COLL["BLOCK"]); _clear_coll(COLL["MARK"])
    grey = _flat_mat("M_SGK_Graybox", (0.62, 0.60, 0.55))
    red = _flat_mat("M_SGK_Red", (0.85, 0.15, 0.15), alpha=0.55)
    blue = _flat_mat("M_SGK_Blue", (0.15, 0.30, 0.85), alpha=0.55)
    fence = _flat_mat("M_SGK_Fence", (0.9, 0.2, 0.2), alpha=0.25)
    zone = _flat_mat("M_SGK_Zone", (0.95, 0.85, 0.2), alpha=0.35)
    # 구조물 그레이박스
    n = 0
    for kind, (x, y), yaw, (sx, sy, sz) in L.structures():
        n += 1
        if kind == "PAVILION":
            _box(f"BLK_{kind}_{n:02d}_terrace", x, y, yaw, sx, sy, 1.2, COLL["BLOCK"], grey)
            _box(f"BLK_{kind}_{n:02d}", x, y, yaw, sx * 0.9, sy * 0.9, sz, COLL["BLOCK"], grey, z=L.height_at(x, y) + 1.2)
        elif kind == "TERRACE":
            _box(f"BLK_{kind}_{n:02d}", x, y, yaw, sx, sy, sz, COLL["BLOCK"], grey)
            _cyl(f"BLK_CAIRN_{n:02d}", x, y, 0.45, 1.6, COLL["BLOCK"], grey, z=L.height_at(x, y) + sz)
        elif kind == "BRIDGE":
            _box(f"BLK_{kind}_{n:02d}", x, y, yaw, sx, sy, 0.25, COLL["BLOCK"], grey, z=L.water_z(x) + 0.55)
        else:
            _box(f"BLK_{kind}_{n:02d}", x, y, yaw, sx, sy, sz, COLL["BLOCK"], grey, sink=0.3)
    # 스폰 디스크 + 방향
    for team, (x, y) in L.spawn_points().items():
        _cyl(f"MK_Spawn_{team}", x, y, L.SPAWN_R, 0.15, COLL["MARK"], red if team == "Red" else blue)
        _cyl(f"MK_SpawnCore_{team}", x, y, 3.0, 0.5, COLL["MARK"], red if team == "Red" else blue)
    # 경계 (16 m 담장 판) — 엔진 Bound Part 자리
    X, Y = L.PLAY_X, L.PLAY_Y
    _box("MK_Bound_North", 0, Y, 0, 2 * X, 0.3, 16, COLL["MARK"], fence, z=0.0)
    _box("MK_Bound_South", 0, -Y, 0, 2 * X, 0.3, 16, COLL["MARK"], fence, z=0.0)
    _box("MK_Bound_East", X, 0, 0, 0.3, 2 * Y, 16, COLL["MARK"], fence, z=0.0)
    _box("MK_Bound_West", -X, 0, 0, 0.3, 2 * Y, 16, COLL["MARK"], fence, z=0.0)
    # 점령 구역 크기 표시 (반경 9 m) 중앙
    _cyl("MK_Zone_R9", 0, 0, L.ZONE_RADIUS_CM / 100.0, 0.2, COLL["MARK"], zone)
    # 키포인트 표지
    for name, (x, y) in L.key_points().items():
        bpy.ops.mesh.primitive_cone_add(radius1=0.6, depth=2.0, location=(x, y, L.height_at(x, y) + 1.0))
        ob = bpy.context.active_object; ob.name = f"KP_{name}"; _link(ob, COLL["MARK"]); ob.data.materials.append(zone)
    print("blockouts", n)

# ------------------------------------------------------------------ 라이팅 / 카메라 / 렌더
def make_lighting():
    _clear_coll(COLL["LIGHT"])
    sun = bpy.data.lights.new("SGK_Sun", "SUN"); sun.energy = 4.5; sun.angle = math.radians(2.0)
    sun.color = (1.0, 0.965, 0.90)
    ob = bpy.data.objects.new("SGK_Sun", sun); _link(ob, COLL["LIGHT"])
    ob.rotation_euler = (math.radians(48), 0, math.radians(-125))
    w = bpy.context.scene.world or bpy.data.worlds.new("SGK_World")
    bpy.context.scene.world = w; w.use_nodes = True
    nt = w.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputWorld"); bg = nt.nodes.new("ShaderNodeBackground")
    ramp = nt.nodes.new("ShaderNodeValToRGB"); mr = nt.nodes.new("ShaderNodeMapRange"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0]); nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    mr.inputs["From Min"].default_value = -0.3; mr.inputs["From Max"].default_value = 0.55
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].color = (0.42, 0.44, 0.44, 1); ramp.color_ramp.elements[1].color = (0.36, 0.50, 0.78, 1)
    e = ramp.color_ramp.elements.new(0.45); e.color = (0.58, 0.66, 0.74, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 0.65
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    print("lighting ok")

def _look_at(cam, target):
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

def _cam(name, loc, target, lens=28.0, ortho=None):
    cd = bpy.data.cameras.new(name); cd.clip_end = 2000.0
    if ortho:
        cd.type = "ORTHO"; cd.ortho_scale = ortho
    else:
        cd.lens = lens
    ob = bpy.data.objects.new(name, cd); _link(ob, COLL["CAM"]); ob.location = loc; _look_at(ob, target)
    return ob

def make_cameras():
    _clear_coll(COLL["CAM"])
    eye = 1.7
    sw, se = L.spawn_points()["Red"], L.spawn_points()["Blue"]
    _cam("CAM_Top", (0, 0, 400), (0, 0, 0), ortho=185.0)
    _cam("CAM_Survey", (-40, -150, 120), (0, 0, 2), lens=32)
    _cam("CAM_SpawnW_POV", (sw[0], sw[1], L.height_at(*sw) + eye), (0, 0, 2), lens=16)
    _cam("CAM_SpawnE_POV", (se[0], se[1], L.height_at(*se) + eye), (0, 0, 2), lens=16)
    _cam("CAM_Bowl", (0, -12, L.height_at(0, -12) + eye), (0, 9, 2.5), lens=18)
    tip = (L.CREST[-1][0], L.CREST[-1][1])
    _cam("CAM_CrestNW", (tip[0], tip[1], L.height_at(*tip) + eye), (14, -13, 2), lens=18)
    pm = (-20.0, -36.0)
    _cam("CAM_ForestMid", (pm[0], pm[1], L.height_at(*pm) + eye), (20, -44, 1), lens=18)
    _cam("CAM_StripN", (-35, 50, L.height_at(-35, 50) + eye), (-10, 40, 1), lens=18)
    _cam("CAM_RidgeW", (-70, 40, 30), (-30, 22, 8), lens=35)
    bpy.context.scene.camera = bpy.data.objects["CAM_Survey"]
    print("cameras", len(_coll(COLL["CAM"]).objects))

def render(tag, cams=None, size=1400, samples=32):
    os.makedirs(PREVIEWS, exist_ok=True)
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = eng; break
        except TypeError:
            continue
    try:
        sc.eevee.taa_render_samples = samples
        sc.eevee.use_raytracing = True
        sc.eevee.use_shadows = True
    except Exception:
        pass
    sc.render.image_settings.file_format = "PNG"; sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    done = []
    for ob in _coll(COLL["CAM"]).objects:
        if cams and ob.name not in cams:
            continue
        sc.camera = ob
        if ob.data.type == "ORTHO":
            sc.render.resolution_x, sc.render.resolution_y = size, int(size * 0.75)
        else:
            sc.render.resolution_x, sc.render.resolution_y = size, int(size * 9 / 16)
        sc.render.resolution_percentage = 100
        path = os.path.join(PREVIEWS, f"{tag}_{ob.name.replace('CAM_', '')}.png")
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        done.append(path)
    print("rendered", done)
    return done

def save(path=None):
    p = path or MASTER
    os.makedirs(os.path.dirname(p), exist_ok=True)
    packed = [im.name for im in bpy.data.images if im.packed_file]
    if packed:
        raise RuntimeError(f"packed images present, refuse to save: {packed}")
    bpy.ops.wm.save_as_mainfile(filepath=p, relative_remap=True)
    print("saved", p, round(os.path.getsize(p) / 1e6, 1), "MB")

def stage1():
    boot(); make_terrain(); make_walls(); make_water(); make_blockouts(); make_lighting(); make_cameras(); save()

def scene_report():
    rows = []
    for c in bpy.data.collections:
        if not c.name.startswith("SGK_"):
            continue
        tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in c.objects if o.type == "MESH")
        rows.append((c.name, len(c.objects), tris))
    for r in rows:
        print(f"{r[0]:14s} objs={r[1]:5d} tris={r[2]:9d}")
    return rows

if __name__ == "__main__" and "--stage1" in sys.argv:
    stage1()
