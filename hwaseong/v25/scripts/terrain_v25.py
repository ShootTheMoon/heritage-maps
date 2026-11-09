# -*- coding: utf-8 -*-
"""지면 고퀄리티 + 나무 랜덤 산포 (산곡 방식). 2026-09-09 v2.
Ground : 200x150 m, 1 m cells (30k faces). fBm relief outside the structures (fades to flat within 12 m of
         KCISA 일곽 / 담장 / 길), micro-bumps, vertex colour "Blend" (POINT):
             R = 마사토(길·광장·맨땅 패치)  G = 암반(둔덕 정상)  B = 젖은 흙(저지)  A = 솔잎 낙엽(나무·고사리 아래)
         Material = Sangok sgk_dress.terrain_material() 6-way minus the T_MDS cliff set, plus a 13 m macro
         grass sample mixed by low-frequency noise to kill tiling. Poly Haven 1k sets from JSN_Sangok2\_TexLib.
Trees  : Sangok masters MST_PINE_* (SGK_Master.blend; Sketchfab pine pack, CC BY 4.0) scattered by Poisson dart
         throwing with zone density, keep-outs, per-type root burial (Sangok FOOT table).
Clutter: MST_FERN / EULALIA / ARTEMISIA / BOULDER_A,B / ROCK_A,D / STUMP / DEADTRUNK (Sangok masters) scattered.
Run in GUI: ns={}; exec(open(p,encoding='utf-8').read(), ns); ns['main']()"""
import bpy, bmesh, os, glob, math, random
from mathutils import Vector, noise

SGK = r"C:\Users\HSP\Desktop\blender\JSN_Sangok2"
PH = os.path.join(SGK, "_TexLib", "polyhaven")
MASTER = os.path.join(SGK, "00_Source_Blender", "SGK_Master.blend")
GROUND = "지면_지형"; C_GND, C_VEG, C_CLT, KIT = "화성_지면", "화성_수목", "화성_지면소품", "KIT_SGK"
SX, SY, CELL, CY = 200.0, 150.0, 1.0, 5.0
BOUNDS = (-98.0, 98.0, -68.0, 78.0)
FLAT = [(-88.0, 84.0, -33.0, 35.5), (-42.0, 42.0, 18.0, 62.0)]            # KCISA 일곽 + 4 m, 담장 + 6 m
ROADS = [(-3.5, 3.5, -72.0, 24.0), (-70.0, 70.0, 11.0, 16.0), (-2.5, 2.5, 24.0, 56.0)]
PLAZAS = [((0.0, -38.0), 8.0), ((0.0, 20.0), 6.0), ((0.0, 60.0), 6.0)]
SEED = 25

PINES = {"XL": ["MST_PINE_XL1", "MST_PINE_XL2"], "L": ["MST_PINE_L1", "MST_PINE_L2", "MST_PINE_L3"],
         "M": ["MST_PINE_M1", "MST_PINE_M2", "MST_PINE_M3"], "S": ["MST_PINE_S1", "MST_PINE_S2"]}
# Sangok FOOT: footprint radius (m), burial (m)
FOOT = {"MST_PINE_XL2": (1.5, 1.0), "MST_PINE_L2": (1.4, 1.0), "MST_PINE_XL": (1.5, 0.7), "MST_PINE_L": (0.9, 0.7),
        "MST_PINE_M": (1.0, 0.7), "MST_PINE_S": (0.7, 0.35), "MST_STUMP": (0.9, 0.12), "MST_DEADTRUNK": (1.5, 0.08),
        "MST_FERN": (0.9, 0.08), "MST_EULALIA": (0.4, 0.05), "MST_ARTEMISIA": (0.4, 0.05),
        "MST_BOULDER": (1.2, 0.25), "MST_ROCK": (0.6, 0.15)}
CLUTTER = [  # master, count, scale range, zone
    ("MST_FERN", 70, (0.8, 1.4), "forest"), ("MST_EULALIA", 55, (0.9, 1.6), "open"), ("MST_ARTEMISIA", 45, (0.8, 1.4), "verge"),
    ("MST_BOULDER_A", 4, (0.5, 0.9), "open"), ("MST_BOULDER_B", 4, (0.5, 0.9), "open"),
    # MST_ROCK_A/D are Sangok's 10 m 주상절리 cliff pillars — wrong scale for a field, not used here
    ("MST_STUMP", 6, (0.9, 1.3), "forest"), ("MST_DEADTRUNK", 3, (0.9, 1.2), "forest")]
MASTERS = sorted({n for v in PINES.values() for n in v} | {c[0] for c in CLUTTER})

_TREES = []      # (x, y, r_litter) filled by scatter, read by ground colours
_FERNS = []


# ------------------------------------------------------------------ helpers
def coll(name, exclude=None):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
    if exclude is not None:
        lc = bpy.context.view_layer.layer_collection.children.get(name)
        if lc:
            lc.exclude = exclude
    return c


def smooth(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def dist_rect(x, y, r):
    dx = max(r[0] - x, 0.0, x - r[1]); dy = max(r[2] - y, 0.0, y - r[3]); return math.hypot(dx, dy)


def dist_struct(x, y):
    return min([dist_rect(x, y, r) for r in FLAT + ROADS] + [max(0.0, math.hypot(x - c[0], y - c[1]) - rad) for c, rad in PLAZAS])


def fbm(x, y, f=0.012, octaves=4, z=0.0):
    v, a = 0.0, 1.0
    for o in range(octaves):
        v += a * noise.noise(Vector((x * f, y * f, z + 0.37 * o))); a *= 0.5; f *= 2.1
    return v


def relief(x, y):
    fade = smooth(dist_struct(x, y) / 12.0)
    z = 0.9 * fbm(x, y) + 0.05 * noise.noise(Vector((x * 0.9, y * 0.9, 4.2))) * smooth(min(dist_rect(x, y, r) for r in ROADS) / 3.0)
    return fade * z


def dirt(x, y):
    v = 0.0
    for r in ROADS:
        v = max(v, 1.0 - smooth(dist_rect(x, y, r) / 2.5))
    for c, rad in PLAZAS:
        v = max(v, 1.0 - smooth(max(0.0, math.hypot(x - c[0], y - c[1]) - rad) / 3.0))
    p = fbm(x, y, 0.035, 3, 9.0)                       # bare patches outside
    v = max(v, 0.55 * smooth((p - 0.35) / 0.25) * smooth(dist_struct(x, y) / 6.0))
    return v


def wet(x, y, z):
    return smooth((-0.22 - z) / 0.25)


def rock(x, y, z):
    return 0.8 * smooth((fbm(x, y, 0.03, 3, 17.0) - 0.42) / 0.2) * smooth((z - 0.35) / 0.3)


def litter(x, y):
    v = 0.0
    for tx, ty, r in _TREES:
        d = math.hypot(x - tx, y - ty)
        if d < r + 4.5:
            v = max(v, 0.85 * (1.0 - smooth((d - r) / 4.5)))
    for tx, ty in _FERNS:
        d = math.hypot(x - tx, y - ty)
        if d < 3.0:
            v = max(v, 0.6 * (1.0 - smooth(d / 3.0)))
    return v


# ------------------------------------------------------------------ Sangok masters
def load_masters():
    kit = coll(KIT)
    have = {o.name for o in kit.objects}
    need = [n for n in MASTERS if n not in have]
    if need:
        with bpy.data.libraries.load(MASTER, link=False) as (df, dt):
            dt.objects = [n for n in df.objects if n in need]
        for o in dt.objects:
            if o:
                kit.objects.link(o); o.hide_set(False)
    # path fix only: masters may point at the other PC's absolute texture paths
    texs = {os.path.basename(p).lower(): p for p in glob.glob(os.path.join(SGK, "_TexLib", "**", "*.*"), recursive=True)
            if p.lower().endswith((".png", ".jpg", ".jpeg", ".tga", ".exr"))}
    fixed, missing = 0, []
    for o in kit.objects:
        for m in o.data.materials:
            if not m or not m.use_nodes:
                continue
            for n in [n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]:
                p = bpy.path.abspath(n.image.filepath)
                if not os.path.exists(p) and not n.image.packed_file:
                    cand = texs.get(os.path.basename(p).lower())
                    if cand:
                        n.image.filepath = cand; n.image.reload(); fixed += 1
                    else:
                        missing.append(os.path.basename(p))
    coll(KIT, exclude=True)
    print("@@MASTERS", len(kit.objects), "texfix", fixed, "missing", sorted(set(missing))[:6])
    return {o.name: o for o in kit.objects}


def foot(name):
    return next((v for k, v in sorted(FOOT.items(), key=lambda kv: -len(kv[0])) if name.startswith(k)), (0.5, 0.05))


def instance(src, name, col, x, y, yaw, scale):
    inst = src.copy(); inst.data = src.data; inst.name = name
    r, sink = foot(src.name)
    pts = [(x + r * scale * math.cos(a), y + r * scale * math.sin(a)) for a in [i * math.pi / 4 for i in range(8)]] + [(x, y)]
    z = min(relief(px, py) for px, py in pts) - sink
    inst.location = (x, y, z); inst.rotation_euler = (0.0, 0.0, math.radians(yaw)); inst.scale = (scale, scale, scale)
    inst.hide_set(False); inst.hide_render = False
    col.objects.link(inst)
    return inst


# ------------------------------------------------------------------ scatter
def zone(x, y):
    if y < -36.0:
        return "forest"
    if x < -52.0 or x > 52.0 or y > 64.0:
        return "edge"
    return "inner"


def allowed(x, y, pad):
    if not (BOUNDS[0] < x < BOUNDS[1] and BOUNDS[2] < y < BOUNDS[3]):
        return False
    return dist_struct(x, y) > pad


def poisson(rng, spacing_fn, pad, attempts, existing=None):
    pts = list(existing or [])
    for _ in range(attempts):
        x = rng.uniform(BOUNDS[0], BOUNDS[1]); y = rng.uniform(BOUNDS[2], BOUNDS[3])
        if not allowed(x, y, pad):
            continue
        s = spacing_fn(x, y)
        if s is None:
            continue
        if all(math.hypot(x - px, y - py) >= max(s, ps) for px, py, ps in pts):
            pts.append((x, y, s))
    return pts[len(existing or []):]


def scatter_trees(masters, rng):
    vc = coll(C_VEG)
    for o in [o for o in bpy.data.objects if o.name.startswith("수목_")]:
        bpy.data.objects.remove(o, do_unlink=True)
    def spacing(x, y):
        return {"forest": 7.5, "edge": 10.0, "inner": 17.0}[zone(x, y)]
    pts = poisson(rng, spacing, 3.0, 9000)
    weights = {"forest": (("XL", 1), ("L", 5), ("M", 3), ("S", 1)), "edge": (("L", 3), ("M", 4), ("S", 2)), "inner": (("L", 2), ("M", 4), ("S", 3))}
    _TREES.clear(); n = 0
    for i, (x, y, s) in enumerate(pts):
        z = zone(x, y)
        kinds = [k for k, w in weights[z] for _ in range(w)]
        k = rng.choice(kinds); src = masters.get(rng.choice(PINES[k]))
        if not src:
            continue
        sc = rng.uniform(0.9, 1.15) if k != "XL" else rng.uniform(0.75, 0.9)
        instance(src, "수목_소나무_%03d" % i, vc, x, y, rng.uniform(0, 360), sc)
        _TREES.append((x, y, {"XL": 3.0, "L": 2.2, "M": 1.6, "S": 1.0}[k] * sc)); n += 1
    print("@@TREES", n, {z: sum(1 for x, y, _ in pts if zone(x, y) == z) for z in ("forest", "edge", "inner")})
    return pts


def scatter_clutter(masters, rng, tree_pts):
    cc = coll(C_CLT)
    for o in [o for o in bpy.data.objects if o.name.startswith("지면소품_")]:
        bpy.data.objects.remove(o, do_unlink=True)
    _FERNS.clear(); made = {}
    near_tree = lambda x, y, d: any(math.hypot(x - tx, y - ty) < d for tx, ty, _ in tree_pts)
    for mname, count, (s0, s1), zn in CLUTTER:
        src = masters.get(mname)
        if not src:
            continue
        got, tries = 0, 0
        while got < count and tries < count * 60:
            tries += 1
            x = rng.uniform(BOUNDS[0], BOUNDS[1]); y = rng.uniform(BOUNDS[2], BOUNDS[3])
            if not allowed(x, y, 1.5):
                continue
            z = zone(x, y)
            if zn == "forest" and not (z == "forest" or near_tree(x, y, 6.0)):
                continue
            if zn == "verge" and not (2.5 < min(dist_rect(x, y, r) for r in ROADS) < 6.0):
                continue
            if zn == "open" and near_tree(x, y, 2.5):
                continue
            if mname.startswith(("MST_BOULDER", "MST_ROCK")) and dist_struct(x, y) < 4.0:
                continue
            instance(src, "지면소품_%s_%03d" % (mname[4:], got), cc, x, y, rng.uniform(0, 360), rng.uniform(s0, s1)); got += 1
            if mname == "MST_FERN":
                _FERNS.append((x, y))
        made[mname[4:]] = got
    print("@@CLUTTER", made)


# ------------------------------------------------------------------ ground
def build_ground():
    for n in (GROUND, "지면_잔디", "지면_아레나"):
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.meshes.remove(o.data)
    nx, ny = int(SX / CELL) + 1, int(SY / CELL) + 1
    bm = bmesh.new()
    grid = [[bm.verts.new((-SX / 2 + i * CELL, CY - SY / 2 + j * CELL, 0.0)) for j in range(ny)] for i in range(nx)]
    for row in grid:
        for v in row:
            v.co.z = relief(v.co.x, v.co.y)
    for i in range(nx - 1):
        for j in range(ny - 1):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    me = bpy.data.meshes.new(GROUND); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ca = me.color_attributes.new("Blend", 'FLOAT_COLOR', 'POINT')
    cols = []
    for v in me.vertices:
        x, y, z = v.co
        cols += [dirt(x, y), rock(x, y, z), wet(x, y, z), litter(x, y)]
    ca.data.foreach_set("color", cols)
    me.materials.append(terrain_material())
    o = bpy.data.objects.new(GROUND, me); coll(C_GND).objects.link(o)
    print("@@GROUND verts=%d faces=%d" % (len(me.vertices), len(me.polygons)))
    return o


# ------------------------------------------------------------------ material (Sangok 6-way recipe)
def _ph_set(asset):
    d = os.path.join(PH, asset)
    def f(suffix):
        for fn in os.listdir(d):
            if fn.endswith("_%s_1k.png" % suffix) or fn.endswith("_%s_1k.jpg" % suffix):
                return os.path.join(d, fn)
    return {"bc": f("diff"), "nm": f("nor_gl"), "rn": f("rough"), "ao": f("ao")}


def _img(path, non_color=False):
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    return im


def _pbr(nt, name, s, x, tile, ao_mix=0.5):
    tc = nt.nodes.new("ShaderNodeTexCoord"); tc.location = (x - 620, 0)
    mp = nt.nodes.new("ShaderNodeMapping"); mp.location = (x - 430, 0)
    k = 1.0 / tile; mp.inputs["Scale"].default_value = (k, k, k)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    def tex(path, non, dy):
        n = nt.nodes.new("ShaderNodeTexImage"); n.location = (x, dy); n.label = "%s_%d" % (name, dy)
        n.image = _img(path, non); n.extension = "REPEAT"; n.projection = "BOX"; n.projection_blend = 0.5
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"]); return n
    col = tex(s["bc"], False, 260).outputs["Color"]
    if s.get("ao") and ao_mix > 0:
        ao = tex(s["ao"], True, 480)
        m = nt.nodes.new("ShaderNodeMixRGB"); m.blend_type = "MULTIPLY"; m.location = (x + 260, 360); m.inputs["Fac"].default_value = ao_mix
        nt.links.new(col, m.inputs["Color1"]); nt.links.new(ao.outputs["Color"], m.inputs["Color2"]); col = m.outputs["Color"]
    nrm = tex(s["nm"], True, 0).outputs["Color"]
    rgh = tex(s["rn"], True, -260).outputs["Color"]
    return col, nrm, rgh


def _mix(nt, loc, fac, a, b, label=""):
    n = nt.nodes.new("ShaderNodeMix"); n.data_type = "RGBA"; n.location = loc; n.label = label
    nt.links.new(fac, n.inputs["Factor"]); nt.links.new(a, n.inputs[6]); nt.links.new(b, n.inputs[7])
    return n.outputs[2]


def _tint(nt, loc, col, rgb):
    m = nt.nodes.new("ShaderNodeMixRGB"); m.blend_type = "MULTIPLY"; m.location = loc; m.inputs["Fac"].default_value = 1.0
    nt.links.new(col, m.inputs["Color1"]); m.inputs["Color2"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    return m.outputs["Color"]


def terrain_material():
    sets = {"grass": (_ph_set("aerial_grass_rock"), 4.0, (0.80, 0.86, 0.66)),
            "grass2": (_ph_set("aerial_grass_rock"), 13.0, (0.74, 0.82, 0.60)),
            "litter": (_ph_set("brown_mud_leaves_01"), 3.5, (0.92, 0.84, 0.72)),
            "dirt": (_ph_set("brown_mud_dry"), 3.0, (0.86, 0.78, 0.66)),
            "wet": (_ph_set("brown_mud_rocks_01"), 3.0, (0.70, 0.72, 0.72)),
            "rock": (_ph_set("aerial_rocks_02"), 6.0, (0.95, 0.93, 0.90))}
    mat = bpy.data.materials.get("M_HWS_Terrain") or bpy.data.materials.new("M_HWS_Terrain")
    mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (2000, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (1700, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    vc = nt.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "Blend"; vc.location = (-900, -900)
    sep = nt.nodes.new("ShaderNodeSeparateColor"); sep.location = (-700, -900)
    nt.links.new(vc.outputs["Color"], sep.inputs["Color"])
    fr, fg, fb, fa = sep.outputs[0], sep.outputs[1], sep.outputs[2], vc.outputs["Alpha"]
    ch = {}; xs = {"grass": -2300, "grass2": -1900, "litter": -1500, "dirt": -1100, "wet": -700, "rock": -300}
    for k, (s, tile, tint) in sets.items():
        c, n, r = _pbr(nt, k, s, xs[k], tile)
        ch[k] = (_tint(nt, (xs[k] + 300, 200), c, tint), n, r)
    # macro grass variation: 4 m grass vs 13 m grass by 60 m noise -> kills tiling
    mz = nt.nodes.new("ShaderNodeTexNoise"); mz.location = (300, -1300); mz.inputs["Scale"].default_value = 0.016; mz.inputs["Detail"].default_value = 2.0
    mzc = nt.nodes.new("ShaderNodeTexCoord"); mzc.location = (120, -1300); nt.links.new(mzc.outputs["Object"], mz.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.location = (480, -1300); mr.inputs["From Min"].default_value = 0.35; mr.inputs["From Max"].default_value = 0.65
    nt.links.new(mz.outputs["Fac"], mr.inputs["Value"]); fmacro = mr.outputs["Result"]
    grass = tuple(_mix(nt, (560, -700 - i * 160), fmacro, ch["grass"][i], ch["grass2"][i], "grassmacro%d" % i) for i in range(3))
    def chain(i, y):
        v = _mix(nt, (800, y), fa, grass[i], ch["litter"][i], "litter")
        v = _mix(nt, (960, y), fr, v, ch["dirt"][i], "dirt")
        v = _mix(nt, (1120, y), fb, v, ch["wet"][i], "wet")
        return _mix(nt, (1280, y), fg, v, ch["rock"][i], "rock")
    col, nrm, rgh = chain(0, 300), chain(1, 40), chain(2, -220)
    dtc = nt.nodes.new("ShaderNodeTexCoord"); dtc.location = (800, -1600)
    dmp = nt.nodes.new("ShaderNodeMapping"); dmp.location = (960, -1600); dmp.inputs["Scale"].default_value = (1.7, 1.7, 1.7)
    nt.links.new(dtc.outputs["Object"], dmp.inputs["Vector"])
    dn = nt.nodes.new("ShaderNodeTexNoise"); dn.location = (1140, -1600)
    dn.inputs["Scale"].default_value = 2.2; dn.inputs["Detail"].default_value = 8.0; dn.inputs["Roughness"].default_value = 0.62
    nt.links.new(dmp.outputs["Vector"], dn.inputs["Vector"])
    cb = nt.nodes.new("ShaderNodeMapRange"); cb.location = (1320, -1500); cb.inputs["To Min"].default_value = 0.82; cb.inputs["To Max"].default_value = 1.16
    nt.links.new(dn.outputs["Fac"], cb.inputs["Value"])
    cmul = nt.nodes.new("ShaderNodeMixRGB"); cmul.blend_type = "MULTIPLY"; cmul.location = (1500, 300); cmul.inputs["Fac"].default_value = 1.0
    nt.links.new(col, cmul.inputs["Color1"]); nt.links.new(cb.outputs["Result"], cmul.inputs["Color2"])
    nt.links.new(cmul.outputs["Color"], bsdf.inputs["Base Color"])
    nmap = nt.nodes.new("ShaderNodeNormalMap"); nmap.location = (1500, 40); nmap.inputs["Strength"].default_value = 0.8
    nt.links.new(nrm, nmap.inputs["Color"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.location = (1500, -120); bump.inputs["Strength"].default_value = 0.18; bump.inputs["Distance"].default_value = 0.05
    nt.links.new(dn.outputs["Fac"], bump.inputs["Height"]); nt.links.new(nmap.outputs["Normal"], bump.inputs["Normal"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(rgh, bsdf.inputs["Roughness"])
    mat.diffuse_color = (0.30, 0.42, 0.20, 1.0)
    return mat


def main():
    rng = random.Random(SEED)
    masters = load_masters()
    # NOTE: never delete by collection here — only 수목_/지면소품_/지면_ prefixed objects are ours to replace.
    pts = scatter_trees(masters, rng)
    scatter_clutter(masters, rng, pts)
    build_ground()
    bpy.ops.wm.save_mainfile(); print("@@SAVED")


# ------------------------------------------------------------------ outer ring (horizon filler, Sangok style)
OUTER = (400.0, 300.0, 4.0)      # size x, size y, cell — around the same centre (0, CY)
BERM_H, BERM_W = 3.5, 60.0        # berm height (m) and ramp width from the inner edge


def berm(x, y):
    dx = max(0.0, abs(x) - SX / 2); dy = max(0.0, abs(y - CY) - SY / 2); d = math.hypot(dx, dy)
    return smooth(d / BERM_W) * BERM_H + 0.6 * smooth(d / 20.0) * fbm(x, y, 0.02, 3, 31.0) + relief(x, y) * (1 - smooth(d / 8.0))


def build_outer():
    old = bpy.data.objects.get("지면_외곽")
    if old:
        bpy.data.meshes.remove(old.data)
    ox, oy, cell = OUTER; nx, ny = int(ox / cell) + 1, int(oy / cell) + 1
    bm = bmesh.new()
    grid = [[bm.verts.new((-ox / 2 + i * cell, CY - oy / 2 + j * cell, 0.0)) for j in range(ny)] for i in range(nx)]
    def inner(v):
        return abs(v.co.x) < SX / 2 - 0.01 and abs(v.co.y - CY) < SY / 2 - 0.01
    for row in grid:
        for v in row:
            v.co.z = berm(v.co.x, v.co.y)
    for i in range(nx - 1):
        for j in range(ny - 1):
            q = (grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1])
            if not all(inner(v) for v in q):
                bm.faces.new(q)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    me = bpy.data.meshes.new("지면_외곽"); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ca = me.color_attributes.new("Blend", 'FLOAT_COLOR', 'POINT'); cols = []
    for v in me.vertices:
        x, y, z = v.co
        cols += [0.0, 0.6 * smooth((fbm(x, y, 0.03, 3, 17.0) - 0.45) / 0.2) * smooth((z - 2.0) / 1.5), 0.0, 0.5 * smooth((fbm(x, y, 0.04, 2, 23.0) - 0.3) / 0.3)]
    ca.data.foreach_set("color", cols)
    me.materials.append(bpy.data.materials.get("M_HWS_Terrain") or terrain_material())
    o = bpy.data.objects.new("지면_외곽", me); coll(C_GND).objects.link(o)
    print("@@OUTER faces=%d" % len(me.polygons))
    return o


def ring_trees(masters, rng, spacing=9.0, pad=6.0):
    """pine belt on the outer ring (uses berm heights)."""
    vc = coll(C_VEG); ox, oy, _ = OUTER; pts = []; n = 0
    for _ in range(6000):
        x = rng.uniform(-ox / 2 + pad, ox / 2 - pad); y = rng.uniform(CY - oy / 2 + pad, CY + oy / 2 - pad)
        if abs(x) < SX / 2 + 2 and abs(y - CY) < SY / 2 + 2:
            continue
        if all(math.hypot(x - px, y - py) >= spacing for px, py in pts):
            pts.append((x, y))
    for i, (x, y) in enumerate(pts):
        k = rng.choice(["L", "L", "M", "M", "XL", "S"]); src = masters.get(rng.choice(PINES[k]))
        if not src:
            continue
        inst = src.copy(); inst.data = src.data; inst.name = "수목_외곽소나무_%03d" % i
        r, sink = foot(src.name); sc = rng.uniform(0.9, 1.15) if k != "XL" else rng.uniform(0.75, 0.9)
        inst.location = (x, y, berm(x, y) - sink); inst.rotation_euler = (0, 0, math.radians(rng.uniform(0, 360))); inst.scale = (sc, sc, sc)
        vc.objects.link(inst); n += 1
    print("@@RING_TREES", n)
