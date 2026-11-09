# -*- coding: utf-8 -*-
"""
sgk_dress.py — Phase 2 드레싱. sgk_live.py 를 exec 한 같은 네임스페이스에서 exec 한다.

    exec(open(LIVE).read()); exec(open(DRESS).read())
    terrain_material(); water_material(); import_assets(); scatter_all(); place_structures(); make_steps(); save()

모든 배치는 결정적(_h01 해시)이고 `05_Documentation\placements_master.json` 으로 내보낸다 (Phase 3 placements.csv 의 원천).
재질 규칙: Object 좌표 + BOX 투영(UV 없는 절차 메시), 이미지 pack 금지, 텍스처는 절대경로 참조.
"""
import bpy, bmesh, math, os, json, re, time
from mathutils import Vector, Matrix

TEXROOT = os.path.join(ROOT, "_TexLib")
PH = os.path.join(TEXROOT, "polyhaven")
JSN = r"C:\Users\29\Desktop\blender\JSN_Sangok"
JSN_ROCKTEX = os.path.join(JSN, "_extracted", "ROCK_ColumnarA", "Texture")
JSN_OVD = os.path.join(JSN, "00_Source_Blender", "JSN_Master_OVD.blend")
SSW = r"C:\Users\29\Desktop\blender\SSW_Soswaewon\_extracted"
PINE_LIB = os.path.join(TEXROOT, "sketchfab", "pine_pack_lib.blend")
COLL["KIT"] = "SGK_KIT"          # 마스터 원본 (숨김)
PLACEMENTS = os.path.join(ROOT, "05_Documentation", "placements_master.json")

# ------------------------------------------------------------------ 이미지 / PBR 도우미
def _img(path, non_color=False):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    name = os.path.basename(path)
    im = bpy.data.images.get(name)
    if im is None or bpy.path.abspath(im.filepath) != path:
        im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    return im

def _ph_set(asset):
    d = os.path.join(PH, asset)
    def f(suffix):
        for fn in os.listdir(d):
            if fn.endswith(f"_{suffix}_1k.png") or fn.endswith(f"_{suffix}_1k.jpg"):
                return os.path.join(d, fn)
        return None
    return {"bc": f("diff"), "nm": f("nor_gl"), "rn": f("rough"), "ao": f("ao")}

def _pbr(nt, name, s, x, tile=4.0, ao_mix=0.6):
    """Object+BOX 삼중평면 PBR 한 벌. 반환 (color, normal, rough) 소켓."""
    tc = nt.nodes.new("ShaderNodeTexCoord"); tc.location = (x - 620, 0)
    mp = nt.nodes.new("ShaderNodeMapping"); mp.location = (x - 430, 0)
    k = 1.0 / max(0.001, tile); mp.inputs["Scale"].default_value = (k, k, k)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    def tex(path, non, dy):
        n = nt.nodes.new("ShaderNodeTexImage"); n.location = (x, dy); n.label = f"{name}_{dy}"
        n.image = _img(path, non); n.extension = "REPEAT"; n.projection = "BOX"; n.projection_blend = 0.5
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"]); return n
    col = tex(s["bc"], False, 260).outputs["Color"]
    if s.get("ao") and ao_mix > 0:
        ao = tex(s["ao"], True, 480)
        m = nt.nodes.new("ShaderNodeMixRGB"); m.blend_type = "MULTIPLY"; m.location = (x + 260, 360)
        m.inputs["Fac"].default_value = ao_mix
        nt.links.new(col, m.inputs["Color1"]); nt.links.new(ao.outputs["Color"], m.inputs["Color2"]); col = m.outputs["Color"]
    nrm = tex(s["nm"], True, 0).outputs["Color"]
    rgh = tex(s["rn"], True, -260).outputs["Color"]
    return col, nrm, rgh

def _mix(nt, loc, fac, a, b, label=""):
    n = nt.nodes.new("ShaderNodeMix"); n.data_type = "RGBA"; n.location = loc; n.label = label
    nt.links.new(fac, n.inputs["Factor"]); nt.links.new(a, n.inputs[6]); nt.links.new(b, n.inputs[7])
    return n.outputs[2]

def _tint(nt, loc, col, rgb, fac=1.0):
    m = nt.nodes.new("ShaderNodeMixRGB"); m.blend_type = "MULTIPLY"; m.location = loc
    m.inputs["Fac"].default_value = fac; nt.links.new(col, m.inputs["Color1"]); m.inputs["Color2"].default_value = (*rgb, 1.0)
    return m.outputs["Color"]

# ------------------------------------------------------------------ 지형 재질 6-way
def terrain_material():
    """풀 → (A) 솔잎 낙엽 → (R) 마사토 길 → (B) 젖은 자갈 → (G) 암반(주상절리 × aerial_rocks 노이즈 믹스)."""
    sets = {
        "grass": (_ph_set("aerial_grass_rock"), 4.0, (0.80, 0.86, 0.66)),
        "litter": (_ph_set("brown_mud_leaves_01"), 3.5, (0.92, 0.84, 0.72)),
        "dirt": (_ph_set("brown_mud_dry"), 3.0, (0.86, 0.78, 0.66)),
        "wet": (_ph_set("brown_mud_rocks_01"), 3.0, (0.70, 0.72, 0.72)),
        "rock2": (_ph_set("aerial_rocks_02"), 6.0, (0.95, 0.93, 0.90)),
        "rock": ({"bc": os.path.join(JSN_ROCKTEX, "T_MDS_UnitA_BC.png"), "nm": os.path.join(JSN_ROCKTEX, "T_MDS_UnitA_N.png"),
                  "rn": os.path.join(JSN_ROCKTEX, "T_MDS_UnitA_R.png")}, 3.5, (1.05, 1.00, 0.94)),
    }
    mat = bpy.data.materials.get("M_SGK_Terrain") or bpy.data.materials.new("M_SGK_Terrain")
    mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (1700, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (1400, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    vc = nt.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "Blend"; vc.location = (-900, -700)
    sep = nt.nodes.new("ShaderNodeSeparateColor"); sep.location = (-700, -700)
    nt.links.new(vc.outputs["Color"], sep.inputs["Color"])
    fr, fg, fb, fa = sep.outputs[0], sep.outputs[1], sep.outputs[2], vc.outputs["Alpha"]
    ch = {}
    xs = {"grass": -1500, "litter": -1100, "dirt": -700, "wet": -300, "rock": 100, "rock2": 100}
    for k, (s, tile, tint) in sets.items():
        c, n, r = _pbr(nt, k, s, xs[k], tile, ao_mix=0.5 if k != "rock" else 0.0)
        if k == "rock2":
            for nd in nt.nodes:
                if nd.label.startswith("rock2_"): nd.location.y -= 900
        c = _tint(nt, (xs[k] + 300, 200), c, tint)
        ch[k] = (c, n, r)
    # 암반 두 벌을 대형 노이즈로 (0.08~0.42) — 타일 반복 깨기
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.location = (300, -900); nz.inputs["Scale"].default_value = 0.09; nz.inputs["Detail"].default_value = 3.0
    nzc = nt.nodes.new("ShaderNodeTexCoord"); nzc.location = (120, -900); nt.links.new(nzc.outputs["Object"], nz.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.location = (480, -900); mr.inputs["To Min"].default_value = 0.08; mr.inputs["To Max"].default_value = 0.42
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"]); f = mr.outputs["Result"]
    rock = tuple(_mix(nt, (660, -700 - i * 160), f, ch["rock"][i], ch["rock2"][i], f"rockmix{i}") for i in range(3))
    # 채널 순서: grass → litter(A) → dirt(R) → wet(B) → rock(G)
    def chain(i, y):
        v = _mix(nt, (700, y), fa, ch["grass"][i], ch["litter"][i], "litter")
        v = _mix(nt, (860, y), fr, v, ch["dirt"][i], "dirt")
        v = _mix(nt, (1020, y), fb, v, ch["wet"][i], "wet")
        v = _mix(nt, (1180, y), fg, v, rock[i], "rock")
        return v
    col, nrm, rgh = chain(0, 300), chain(1, 40), chain(2, -220)
    # 근거리 디테일 + 색 얼룩
    dtc = nt.nodes.new("ShaderNodeTexCoord"); dtc.location = (600, -1300)
    dmp = nt.nodes.new("ShaderNodeMapping"); dmp.location = (760, -1300); dmp.inputs["Scale"].default_value = (1.7, 1.7, 1.7)
    nt.links.new(dtc.outputs["Object"], dmp.inputs["Vector"])
    dn = nt.nodes.new("ShaderNodeTexNoise"); dn.location = (940, -1300); dn.inputs["Scale"].default_value = 2.2; dn.inputs["Detail"].default_value = 8.0; dn.inputs["Roughness"].default_value = 0.62
    nt.links.new(dmp.outputs["Vector"], dn.inputs["Vector"])
    cb = nt.nodes.new("ShaderNodeMapRange"); cb.location = (1120, -1200); cb.inputs["To Min"].default_value = 0.82; cb.inputs["To Max"].default_value = 1.16
    nt.links.new(dn.outputs["Fac"], cb.inputs["Value"])
    cmul = nt.nodes.new("ShaderNodeMixRGB"); cmul.blend_type = "MULTIPLY"; cmul.location = (1260, 300); cmul.inputs["Fac"].default_value = 1.0
    nt.links.new(col, cmul.inputs["Color1"]); nt.links.new(cb.outputs["Result"], cmul.inputs["Color2"])
    nt.links.new(cmul.outputs["Color"], bsdf.inputs["Base Color"])
    nmap = nt.nodes.new("ShaderNodeNormalMap"); nmap.location = (1260, 40); nmap.inputs["Strength"].default_value = 0.8
    nt.links.new(nrm, nmap.inputs["Color"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.location = (1260, -120); bump.inputs["Strength"].default_value = 0.18; bump.inputs["Distance"].default_value = 0.05
    nt.links.new(dn.outputs["Fac"], bump.inputs["Height"]); nt.links.new(nmap.outputs["Normal"], bump.inputs["Normal"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(rgh, bsdf.inputs["Roughness"])
    for o in _coll(COLL["TER"]).objects:
        o.data.materials.clear(); o.data.materials.append(mat)
    print("terrain material ok")
    return mat

# ------------------------------------------------------------------ 물
def water_material():
    mat = bpy.data.materials.get("M_SGK_Water") or bpy.data.materials.new("M_SGK_Water")
    mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (860, 0)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled"); b.location = (600, 0)
    b.inputs["Transmission Weight"].default_value = 0.62; b.inputs["IOR"].default_value = 1.333
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    vc = nt.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "Flow"; vc.location = (-820, -260)
    sep = nt.nodes.new("ShaderNodeSeparateColor"); sep.location = (-640, -260); nt.links.new(vc.outputs["Color"], sep.inputs["Color"])
    bank = nt.nodes.new("ShaderNodeMapRange"); bank.location = (-460, -360); bank.inputs["To Min"].default_value = 0.45; bank.inputs["To Max"].default_value = 1.5
    nt.links.new(sep.outputs[1], bank.inputs["Value"])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.use_clamp = True; mul.location = (-280, -260)
    nt.links.new(sep.outputs[0], mul.inputs[0]); nt.links.new(bank.outputs["Result"], mul.inputs[1])
    tc = nt.nodes.new("ShaderNodeTexCoord"); tc.location = (-1000, 240)
    mp = nt.nodes.new("ShaderNodeMapping"); mp.location = (-820, 240); mp.inputs["Scale"].default_value = (0.55, 0.55, 0.55)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    fn = nt.nodes.new("ShaderNodeTexNoise"); fn.location = (-640, 240); fn.inputs["Scale"].default_value = 3.5; fn.inputs["Detail"].default_value = 4.0
    nt.links.new(mp.outputs["Vector"], fn.inputs["Vector"])
    fm = nt.nodes.new("ShaderNodeMath"); fm.operation = "MULTIPLY"; fm.use_clamp = True; fm.location = (-260, -120)
    nt.links.new(mul.outputs[0], fm.inputs[0]); nt.links.new(fn.outputs["Fac"], fm.inputs[1])
    bo = nt.nodes.new("ShaderNodeMath"); bo.operation = "MULTIPLY"; bo.use_clamp = True; bo.inputs[1].default_value = 1.4; bo.location = (-80, -120)
    nt.links.new(fm.outputs[0], bo.inputs[0]); foam = bo.outputs[0]
    col = nt.nodes.new("ShaderNodeMixRGB"); col.location = (300, 180)
    col.inputs["Color1"].default_value = (0.055, 0.115, 0.125, 1.0); col.inputs["Color2"].default_value = (0.86, 0.90, 0.90, 1.0)
    nt.links.new(foam, col.inputs["Fac"]); nt.links.new(col.outputs["Color"], b.inputs["Base Color"])
    rg = nt.nodes.new("ShaderNodeMapRange"); rg.location = (300, -60); rg.inputs["To Min"].default_value = 0.045; rg.inputs["To Max"].default_value = 0.62
    nt.links.new(foam, rg.inputs["Value"]); nt.links.new(rg.outputs["Result"], b.inputs["Roughness"])
    tr = nt.nodes.new("ShaderNodeMapRange"); tr.location = (300, -240); tr.inputs["To Min"].default_value = 0.62; tr.inputs["To Max"].default_value = 0.0
    nt.links.new(foam, tr.inputs["Value"]); nt.links.new(tr.outputs["Result"], b.inputs["Transmission Weight"])
    wtc = nt.nodes.new("ShaderNodeTexCoord"); wtc.location = (-1000, -520)
    wmp = nt.nodes.new("ShaderNodeMapping"); wmp.location = (-820, -520); wmp.inputs["Scale"].default_value = (1.1, 7.0, 7.0)   # 흐름축 = X
    nt.links.new(wtc.outputs["Object"], wmp.inputs["Vector"])
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.location = (-620, -520); n1.inputs["Scale"].default_value = 5.5; n1.inputs["Detail"].default_value = 6.0
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.location = (-620, -720); n2.inputs["Scale"].default_value = 22.0; n2.inputs["Detail"].default_value = 3.0
    nt.links.new(wmp.outputs["Vector"], n1.inputs["Vector"]); nt.links.new(wmp.outputs["Vector"], n2.inputs["Vector"])
    nm = nt.nodes.new("ShaderNodeMixRGB"); nm.location = (-380, -600); nm.inputs["Fac"].default_value = 0.42
    nt.links.new(n1.outputs["Fac"], nm.inputs["Color1"]); nt.links.new(n2.outputs["Fac"], nm.inputs["Color2"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.location = (300, -440); bump.inputs["Strength"].default_value = 0.22; bump.inputs["Distance"].default_value = 0.035
    nt.links.new(nm.outputs["Color"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    ob = bpy.data.objects.get("SGK_StreamWater")
    if ob:
        ob.data.materials.clear(); ob.data.materials.append(mat); _paint_flow(ob)
    print("water material ok"); return mat

def _paint_flow(ob):
    """Flow 정점색: R = 유속(하상 종단 경사 + 도섭 가속), G = 물가 근접."""
    me = ob.data
    ca = me.color_attributes.get("Flow") or me.color_attributes.new("Flow", "FLOAT_COLOR", "POINT")
    for v in me.vertices:
        x, y = v.co.x, v.co.y
        yc = L.stream_center(x); half = max(0.3, abs(y - yc))
        # 물가 근접: 이 x 의 수면 폭 추정 = 2.2 (도섭 2.3)
        w = 2.2 - 1.0 * L.ford_amt(x)
        edge = min(1.0, half / w) ** 2.2
        bed = L.height_at(x, yc); bed2 = L.height_at(x + 1.0, L.stream_center(x + 1.0))
        spd = min(1.0, max(0.0, abs(bed2 - bed) - 0.017) * 2.5 + L.ford_amt(x) * 0.30 + 0.03)   # 바닥 기울기(0.017/m)는 기본 흐름, 포말 아님
        ca.data[v.index].color = (spd, edge, 0.0, 1.0)

# ------------------------------------------------------------------ 에셋 임포트
def _hide(o):
    o.hide_set(True); o.hide_render = True

def _append_objects(lib, names):
    with bpy.data.libraries.load(lib, link=False) as (src, dst):
        dst.objects = [n for n in names if n in src.objects]
    out = []
    for o in dst.objects:
        if o is None: continue
        _link(o, COLL["KIT"]); out.append(o)
    return out

def _bake_world(o):
    o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4); o.data.update()

def _bottom_center_pivot(o):
    me = o.data
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zmin = min(v.co.z for v in me.vertices)
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    me.transform(Matrix.Translation((-cx, -cy, -zmin))); me.update()

def _join_into(name, objs, cname):
    """여러 메시 오브젝트를 월드좌표로 하나의 새 메시에 합친다 (재질 슬롯 유지)."""
    bm = bmesh.new(); mats = []
    for o in objs:
        me_src = o.data.copy(); me_src.transform(o.matrix_world)
        base = len(mats)
        for m in me_src.materials:
            mats.append(m)
        nf0 = len(bm.faces)
        bm.from_mesh(me_src)
        bm.faces.ensure_lookup_table()
        for idx in range(nf0, len(bm.faces)):          # 새로 들어온 면만 재질 인덱스 오프셋
            bm.faces[idx].material_index += base
        bpy.data.meshes.remove(me_src)
    me = bpy.data.meshes.new("MD_" + name); bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    me.update()
    ob = bpy.data.objects.new(name, me); _link(ob, cname)
    return ob

def _stats(o):
    return {"tris": sum(len(p.vertices) - 2 for p in o.data.polygons), "dims": [round(v, 2) for v in o.dimensions], "mats": len(o.data.materials)}

PINE_MASTERS = {  # 마스터명 → 팩 트리명
    "MST_PINE_L1": "Pine_big_1", "MST_PINE_L2": "Pine_big_2", "MST_PINE_L3": "Pine_big_3",
    "MST_PINE_M1": "Pine_medium_1", "MST_PINE_M2": "Pine_medium_2", "MST_PINE_M3": "Pine_medium_3",
    "MST_PINE_XL1": "Pine_large_1", "MST_PINE_XL2": "Pine_large_3",
    "MST_PINE_S1": "Pine_small_1", "MST_PINE_S2": "Pine_small_3",
    "MST_SAPLING1": "Pine_sapling_1", "MST_SAPLING2": "Pine_sapling_2",
}

def import_pines():
    made = {}
    with bpy.data.libraries.load(PINE_LIB, link=False) as (src, dst):
        dst.objects = list(src.objects)
    objs = [o for o in dst.objects if o]
    tmp = _coll("SGK_TMP")
    for o in objs:
        for c in o.users_collection: c.objects.unlink(o)
        tmp.objects.link(o)
    bpy.context.view_layer.update()
    for mst, tree in PINE_MASTERS.items():
        parts = [o for o in objs if o.type == "MESH" and o.name.startswith(f"{tree}_LOD0_")]
        ob = _join_into(mst, parts, COLL["KIT"])
        _bottom_center_pivot(ob)
        for p in ob.data.polygons: p.use_smooth = True
        _hide(ob); made[mst] = _stats(ob)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(tmp)
    tune_pine_bark()
    print("pines:", {k: (v["tris"], v["dims"][2]) for k, v in made.items()})
    return made

def tune_pine_bark():
    """Bark_Mat: 기부 흑갈 → 상부 적갈 그라디언트(적송). Clusters_Mat: 채도 살짝 내림."""
    for m in bpy.data.materials:
        if not m.use_nodes or m.name.split(".")[0] not in ("Bark_Mat", "Clusters_Mat"):
            continue
        nt = m.node_tree
        bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if not bsdf or any(n.label == "sgk_tuned" for n in nt.nodes):
            continue
        link = next((l for l in nt.links if l.to_node == bsdf and l.to_socket.name == "Base Color"), None)
        if not link: continue
        src = link.from_socket
        if m.name.startswith("Bark"):
            tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); mr = nt.nodes.new("ShaderNodeMapRange")
            nt.links.new(tc.outputs["Object"], sep.inputs[0]); nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
            mr.inputs["From Min"].default_value = 1.5; mr.inputs["From Max"].default_value = 11.0
            grad = nt.nodes.new("ShaderNodeMixRGB"); grad.inputs["Color1"].default_value = (0.40, 0.32, 0.26, 1); grad.inputs["Color2"].default_value = (0.98, 0.56, 0.34, 1)
            nt.links.new(mr.outputs["Result"], grad.inputs["Fac"])
            mul = nt.nodes.new("ShaderNodeMixRGB"); mul.blend_type = "MULTIPLY"; mul.inputs["Fac"].default_value = 0.85; mul.label = "sgk_tuned"
            nt.links.new(src, mul.inputs["Color1"]); nt.links.new(grad.outputs["Color"], mul.inputs["Color2"]); nt.links.new(mul.outputs["Color"], bsdf.inputs["Base Color"])
        else:
            hs = nt.nodes.new("ShaderNodeHueSaturation"); hs.label = "sgk_tuned"; hs.inputs["Saturation"].default_value = 0.88; hs.inputs["Value"].default_value = 0.96
            nt.links.new(src, hs.inputs["Color"]); nt.links.new(hs.outputs["Color"], bsdf.inputs["Base Color"])
            m.blend_method = "HASHED"

def import_jsn_masters():
    objs = _append_objects(JSN_OVD, ["MST_ROCK_A", "MST_ROCK_D", "MST_ROCK_E", "MST_EULALIA", "MST_ARTEMISIA"])
    made = {}
    for o in objs:
        _bake_world(o); _bottom_center_pivot(o); _hide(o); made[o.name] = _stats(o)
    # 텍스처 경로 확인 (JSN _texwork 절대경로)
    bad = [im.name for im in bpy.data.images if im.filepath and not os.path.exists(bpy.path.abspath(im.filepath))]
    print("jsn masters:", made, "missing images:", bad)
    return made

GLTF_MODELS = {"MST_BOULDER_A": "boulder_01", "MST_BOULDER_B": "namaqualand_boulder_02", "MST_FERN": "fern_02",
               "MST_STUMP": "tree_stump_01", "MST_DEADTRUNK": "dead_tree_trunk"}

def import_gltf_models():
    made = {}
    for mst, asset in GLTF_MODELS.items():
        d = os.path.join(PH, "models", asset)
        gl = next((os.path.join(d, f) for f in os.listdir(d) if f.endswith(".gltf")), None)
        before = set(bpy.data.objects.keys())
        bpy.ops.import_scene.gltf(filepath=gl)
        new = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]
        meshes = [o for o in new if o.type == "MESH"]
        bpy.context.view_layer.update()
        ob = _join_into(mst, meshes, COLL["KIT"]) if len(meshes) > 1 else meshes[0]
        if len(meshes) == 1:
            ob.name = mst; ob.data.name = "MD_" + mst; _bake_world(ob); _link(ob, COLL["KIT"])
        for o in new:
            if o not in (ob,) and o.name in bpy.data.objects: bpy.data.objects.remove(o, do_unlink=True)
        _bottom_center_pivot(ob); _hide(ob); made[mst] = _stats(ob)
    print("gltf:", made); return made

def _find_maps(d):
    maps = {}
    for fn in os.listdir(d):
        m = re.match(r"(.+)_(BC|NM|RN|N|R|OP|AO|MT)\.png$", fn, re.I)
        if m: maps.setdefault(m.group(1), {})[m.group(2).upper()] = os.path.join(d, fn)
    return maps

def _wire_kit_material(mat, maps):
    """재질 이름을 텍스처 스템에 퍼지 매칭해 BC/NM/RN/OP 배선."""
    key = re.sub(r"\.\d+$", "", mat.name); key = re.sub(r"^(MI_|M_|T_|SM_)", "", key)
    best = None
    for stem in maps:
        s = re.sub(r"^T_", "", stem)
        if s.lower() in key.lower() or key.lower() in s.lower():
            if best is None or len(s) > len(best): best = stem
    if best is None:
        # 이미 배선된 이미지 노드에서 스템 추정
        for n in mat.node_tree.nodes if mat.use_nodes else []:
            if n.type == "TEX_IMAGE" and n.image:
                st = re.sub(r"_(BC|NM|RN|N|R|OP|AO)\.png$", "", n.image.name, flags=re.I)
                if st in maps: best = st; break
    if best is None: return None
    t = maps[best]
    mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (500, 0)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled"); b.location = (200, 0); nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    def tex(p, non, loc):
        n = nt.nodes.new("ShaderNodeTexImage"); n.location = loc; n.image = _img(p, non); return n
    if "BC" in t: nt.links.new(tex(t["BC"], False, (-400, 250)).outputs["Color"], b.inputs["Base Color"])
    if "OP" in t:
        nt.links.new(tex(t["OP"], True, (-400, 50)).outputs["Color"], b.inputs["Alpha"]); mat.blend_method = "HASHED"
    nm = t.get("NM") or t.get("N")
    if nm:
        n = tex(nm, True, (-400, -180)); nmap = nt.nodes.new("ShaderNodeNormalMap"); nmap.location = (-100, -180)
        nt.links.new(n.outputs["Color"], nmap.inputs["Color"]); nt.links.new(nmap.outputs["Normal"], b.inputs["Normal"])
    rn = t.get("RN") or t.get("R")
    if rn: nt.links.new(tex(rn, True, (-400, -400)).outputs["Color"], b.inputs["Roughness"])
    return best

def _import_fbx(path, name, scale=1.0):
    before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.fbx("EXEC_DEFAULT", filepath=path, use_custom_normals=True, use_image_search=False, global_scale=1.0, axis_forward="-Z", axis_up="Y")
    new = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]
    meshes = [o for o in new if o.type == "MESH"]
    bpy.context.view_layer.update()
    if scale != 1.0:
        for o in meshes: o.matrix_world = Matrix.Scale(scale, 4) @ o.matrix_world
    ob = _join_into(name, meshes, COLL["KIT"]) if len(meshes) > 1 else meshes[0]
    if len(meshes) == 1:
        ob.name = name; ob.data.name = "MD_" + name; _bake_world(ob); _link(ob, COLL["KIT"])
    for o in new:
        if o is not ob and o.name in bpy.data.objects: bpy.data.objects.remove(o, do_unlink=True)
    maps = _find_maps(os.path.dirname(path))
    wired = [(_wire_kit_material(m, maps)) for m in ob.data.materials if m]
    return ob, wired

def _planar_decimate(ob, angle_deg=4.0):
    mod = ob.modifiers.new("dec", "DECIMATE"); mod.decimate_type = "DISSOLVE"; mod.angle_limit = math.radians(angle_deg); mod.delimit = {"UV"}
    dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data; ob.modifiers.remove(mod); ob.data = me; me.name = old.name; bpy.data.meshes.remove(old)

def import_kit():
    made = {}
    ob, w = _import_fbx(os.path.join(SSW, "Chojeong_Pavilion", "Chojeong_Pavilion.fbx"), "MST_PAVILION"); _bottom_center_pivot(ob); _hide(ob); made["MST_PAVILION"] = (_stats(ob), w)
    ob, w = _import_fbx(os.path.join(SSW, "Tujugwigyo", "Tujugwigyo.fbx"), "MST_BRIDGE"); _bottom_center_pivot(ob); _hide(ob); made["MST_BRIDGE"] = (_stats(ob), w)
    # 담장: 원본 3.0×0.79×3.3 → 0.6 배 → 1.8×0.47×2.0; 5장 이어 9 m, 3장 3+2 L
    seg, w = _import_fbx(os.path.join(SSW, "Stonewall", "Stonewall.fbx"), "KIT_WALLSEG", scale=0.6)
    _bottom_center_pivot(seg); _planar_decimate(seg, 5.0)
    dims = seg.dimensions; L_ = max(dims.x, dims.y); along = 0 if dims.x >= dims.y else 1
    def run(name, n, extra=None):
        parts = []
        for i in range(n):
            c = seg.copy(); c.data = seg.data; off = (i - (n - 1) / 2) * L_
            c.location = (off, 0, 0) if along == 0 else (0, off, 0); parts.append(c); _link(c, COLL["KIT"])
        if extra:
            for e in extra:
                c = seg.copy(); c.data = seg.data; c.location = e[0]; c.rotation_euler = (0, 0, e[1]); parts.append(c); _link(c, COLL["KIT"])
        bpy.context.view_layer.update()
        ob = _join_into(name, parts, COLL["KIT"])
        for p in parts: bpy.data.objects.remove(p, do_unlink=True)
        _bottom_center_pivot(ob); _hide(ob); return ob
    w9 = run("MST_WALL_9M", 5)
    # L: 3장 직선 + 2장 직각 (끝에서 꺾임)
    if along == 0:
        wl = run("MST_WALL_L", 3, extra=[((1.5 * L_ + dims.y / 2, L_ * 0.5 + 0.0, 0), math.radians(90)), ((1.5 * L_ + dims.y / 2, L_ * 1.5, 0), math.radians(90))])
    else:
        wl = run("MST_WALL_L", 3, extra=[((L_ * 0.5, 1.5 * L_ + dims.x / 2, 0), math.radians(90)), ((L_ * 1.5, 1.5 * L_ + dims.x / 2, 0), math.radians(90))])
    made["MST_WALL_9M"] = _stats(w9); made["MST_WALL_L"] = _stats(wl); made["wall_wired"] = w
    bpy.data.objects.remove(seg, do_unlink=True)
    print("kit:", made); return made

def import_assets():
    _clear_coll(COLL["KIT"])
    import_pines(); import_jsn_masters(); import_gltf_models(); import_kit()
    packed = [im.name for im in bpy.data.images if im.packed_file]
    if packed:
        for im in bpy.data.images:
            if im.packed_file:
                p = os.path.join(TEXROOT, "unpacked", im.name if im.name.lower().endswith(".png") else im.name + ".png")
                os.makedirs(os.path.dirname(p), exist_ok=True); im.filepath_raw = p; im.file_format = "PNG"; im.save(); im.unpack(method="REMOVE"); im.filepath = p
        print("unpacked:", packed)

# ------------------------------------------------------------------ 스캐터
def _h01(i, j, salt=0.0):
    v = math.sin(i * 127.1 + j * 311.7 + salt * 74.7) * 43758.5453
    return v - math.floor(v)

_PLACED = []      # (master, x, y, z, yaw_deg, scale)
# 발자국 반경(m)·묻기(m): 뿌리·밑동이 지면 위로 드러나지 않게 발자국 안 최저 지면 기준으로 놓는다.
# 소나무 팩은 노출 뿌리가 r 0.9~1.5 m, 높이 0.5~0.7 m 라 0.7 묻는다 (2026-09-05 트레일러에서 "뿌리째 뽑힌" 모습으로 보였다).
FOOT = {"MST_PINE_XL2": (1.5, 1.0), "MST_PINE_L2": (1.4, 1.0), "MST_PINE_XL": (1.5, 0.7), "MST_PINE_L": (0.9, 0.7), "MST_PINE_M": (1.0, 0.7), "MST_PINE_S": (0.7, 0.35), "MST_SAPLING": (0.6, 0.12),
        "MST_STUMP": (0.9, 0.12), "MST_DEADTRUNK": (1.5, 0.08), "MST_FERN": (0.9, 0.08), "MST_EULALIA": (0.4, 0.05), "MST_ARTEMISIA": (0.4, 0.05)}
def _ground_min(x, y, r):
    pts = [(x + r * math.cos(a), y + r * math.sin(a)) for a in [i * math.pi / 4 for i in range(8)]] + [(x, y)]
    return min(L.height_at(px, py) for px, py in pts)

def _instance(src, name, cname, x, y, yaw, scale=1.0, sink=0.05, z=None):
    inst = src.copy(); inst.data = src.data; inst.name = name
    inst.hide_set(False); inst.hide_render = False
    foot = next((v for k, v in FOOT.items() if src.name.startswith(k)), None)
    if z is None and foot: zz = _ground_min(x, y, foot[0] * scale) - foot[1]
    else: zz = (L.height_at(x, y) - sink) if z is None else z
    inst.location = (x, y, zz); inst.rotation_euler = (0, 0, math.radians(yaw)); inst.scale = (scale, scale, scale)
    _link(inst, cname)
    _PLACED.append((src.name, round(x, 3), round(y, 3), round(zz, 3), round(yaw, 2), round(scale, 3)))
    return inst

def _cam_keepout(x, y, r=6.0):
    for c in _coll(COLL["CAM"]).objects:
        if c.data.type == "PERSP" and c.location.z < L.height_at(c.location.x, c.location.y) + 3.0:
            if math.hypot(c.location.x - x, c.location.y - y) < r: return True
    return False

def _struct_keepout(x, y, pad=1.5):
    for kind, (sx, sy), yaw, (a, b, c) in L.structures():
        if math.hypot(x - sx, y - sy) < max(a, b) * 0.5 + pad: return True
    return False

def _off_limits(x, y):
    lm = L.lane_mask(x, y)
    if lm["stream"] > 0.15 or lm["path"] > 0.25 or lm["ramp"] > 0.15 or lm["crest"] > 0.1 or lm["cliff"] > 0.5: return True
    if lm["spawn"] > 0.02: return True
    if math.hypot(x, y) < 6.0: return True
    if _struct_keepout(x, y) or _cam_keepout(x, y): return True
    return False

def pine_density(x, y):
    lm = L.lane_mask(x, y)
    if _off_limits(x, y) or L.slope_deg(x, y) > 36.0: return 0.0
    d = max(lm["forest"] * 0.9, lm["strip"] * 1.0, lm["knoll"] * 0.35, lm["glade"] * 0.12, lm["wall"] * 1.0)
    d *= 1.0 - lm["bowl"] * 0.8
    return d

def _pick(keys, i, j, salt):
    return keys[int(_h01(i, j, salt) * len(keys)) % len(keys)]

def scatter_pines(seed_step=12.0, cap_play=280, cap_wall=160):
    for o in list(_coll(COLL["VEG"]).objects):
        if o.name.startswith("SGK_Pine"): bpy.data.objects.remove(o, do_unlink=True)
    src = {k: bpy.data.objects[k] for k in PINE_MASTERS}
    n_play = n_wall = 0; k = 0
    pad = 44.0
    xs = int(2 * (L.PLAY_X + pad) / seed_step); ys = int(2 * (L.PLAY_Y + pad) / seed_step)
    for i in range(xs + 1):
        for j in range(ys + 1):
            cx = -L.PLAY_X - pad + i * seed_step + (_h01(i, j, 1) - 0.5) * seed_step * 0.8
            cy = -L.PLAY_Y - pad + j * seed_step + (_h01(i, j, 2) - 0.5) * seed_step * 0.8
            d = pine_density(cx, cy)
            if d <= 0.05 or _h01(i, j, 3) > d: continue
            wall = L.lane_mask(cx, cy)["wall"] > 0.3
            cnt = (2 + int(_h01(i, j, 4) * 2)) if wall else (3 + int(_h01(i, j, 4) * 3 * d))
            rad = 3.0 + 2.5 * _h01(i, j, 5)
            for t in range(cnt):
                a = _h01(i, j, 10 + t) * 6.283; r = rad * math.sqrt(_h01(i, j, 20 + t))
                x, y = cx + r * math.cos(a), cy + r * math.sin(a)
                if pine_density(x, y) <= 0.05: continue
                if abs(x) > L.MESH_X - 4 or abs(y) > L.MESH_Y - 4: continue
                lm = L.lane_mask(x, y)
                if lm["wall"] > 0.3:
                    if n_wall >= cap_wall: continue
                    key = _pick(["MST_PINE_XL1", "MST_PINE_XL2", "MST_PINE_L1", "MST_PINE_L3"], i, j, 30 + t); n_wall += 1
                else:
                    if n_play >= cap_play: continue
                    near_lane = max(lm["path"], lm["glade"], lm["stream"], lm["bowl"]) > 0.05
                    keys = ["MST_PINE_M1", "MST_PINE_M2", "MST_PINE_M3"] if (near_lane or _h01(i, j, 40 + t) < 0.4) else ["MST_PINE_L1", "MST_PINE_L2", "MST_PINE_L3"]
                    key = _pick(keys, i, j, 30 + t); n_play += 1
                k += 1
                _instance(src[key], f"SGK_Pine_{k:04d}", COLL["VEG"], x, y, _h01(i, j, 50 + t) * 360, 0.9 + 0.2 * _h01(i, j, 60 + t), sink=0.12)
    print(f"pines play={n_play} wall={n_wall}")
    return n_play, n_wall

UNDERSTORY = [  # (마스터, 이름, step, 조건 함수 키, 크기범위, cap, salt)
    ("MST_FERN", "Fern", 4.0, "verge", (0.8, 1.4), 60, 7),
    ("MST_EULALIA", "Eulalia", 5.0, "glade_stream", (0.9, 1.6), 40, 8),
    ("MST_ARTEMISIA", "Artemisia", 4.5, "bank", (0.8, 1.4), 30, 9),
    ("MST_PINE_S1", "SmallPine", 7.0, "forest", (0.9, 1.3), 30, 10),
    ("MST_SAPLING1", "Sapling", 7.0, "forest", (0.9, 1.5), 20, 11),
    ("MST_STUMP", "Stump", 14.0, "forest", (0.9, 1.3), 8, 12),
    ("MST_DEADTRUNK", "DeadTrunk", 18.0, "forest", (0.9, 1.2), 4, 13),
]

def _under_ok(kind, x, y, lm):
    ds = L._stream_normal_dist(x, y) if L.stream_len(x) > 0.5 else 99.0
    if kind == "verge":   # 길·개활지 가장자리, 분지 림
        return (0.02 < lm["path"] < 0.7) or (0.03 < lm["glade"] < 0.7) or (0.15 < lm["bowl"] < 0.75)
    if kind == "glade_stream":
        return lm["glade"] > 0.5 or (4.5 < ds < 9.0 and L.ford_amt(x) < 0.3)
    if kind == "bank":
        return 2.4 < ds < 5.0 and L.ford_amt(x) < 0.4
    if kind == "forest":
        return lm["forest"] > 0.6 or lm["strip"] > 0.6
    return False

def scatter_understory():
    for o in list(_coll(COLL["VEG"]).objects):
        if o.name.startswith("SGK_Und"): bpy.data.objects.remove(o, do_unlink=True)
    counts = {}
    for mst, nm, step, kind, (s0, s1), cap, salt in UNDERSTORY:
        src = bpy.data.objects.get(mst)
        if not src: continue
        n = 0
        xs = int(2 * L.PLAY_X / step); ys = int(2 * L.PLAY_Y / step)
        for i in range(xs + 1):
            for j in range(ys + 1):
                if n >= cap: break
                x = -L.PLAY_X + i * step + (_h01(i, j, salt) - 0.5) * step
                y = -L.PLAY_Y + j * step + (_h01(i, j, salt + 1) - 0.5) * step
                lm = L.lane_mask(x, y)
                if not _under_ok(kind, x, y, lm): continue
                if lm["ramp"] > 0.1 or lm["crest"] > 0.1 or lm["cliff"] > 0.4 or lm["spawn"] > 0.02: continue
                if lm["stream"] > 0.15: continue
                if _struct_keepout(x, y, 1.0) or _cam_keepout(x, y, 4.0) or L.slope_deg(x, y) > 38: continue
                if _h01(i, j, salt + 2) > 0.7: continue
                n += 1
                _instance(src, f"SGK_Und_{nm}_{n:03d}", COLL["VEG"], x, y, _h01(i, j, salt + 3) * 360, s0 + (s1 - s0) * _h01(i, j, salt + 4), sink=0.08)
        counts[nm] = n
    print("understory:", counts); return counts

def scatter_rocks():
    _clear_coll(COLL["ROCK"])
    A, B = bpy.data.objects["MST_BOULDER_A"], bpy.data.objects["MST_BOULDER_B"]
    cols = [bpy.data.objects[k] for k in ("MST_ROCK_A", "MST_ROCK_D", "MST_ROCK_E")]
    n = 0
    def put(src, x, y, yaw, scale, sink=0.25):
        nonlocal n
        if _cam_keepout(x, y, 4.0): return
        n += 1; _instance(src, f"SGK_Rock_{n:03d}", COLL["ROCK"], x, y, yaw, scale, sink=sink)
    # 분지 림 6 (개활지 축 ±y 와 T 착지점 피함)
    for k, ang in enumerate((25, 65, 115, 205, 245, 295)):
        r = 10.5 + 3.0 * _h01(k, 1); x, y = r * math.cos(math.radians(ang)), r * math.sin(math.radians(ang))
        put(A if k % 2 else B, x, y, _h01(k, 2) * 360, 0.9 + 0.7 * _h01(k, 3))
    # 계류변 6 (양안, 점대칭)
    for k, x in enumerate((-36.0, -13.0, -25.0)):
        yc = L.stream_center(x); off = 3.6 if k % 2 == 0 else -3.6
        for sgn in (1, -1):
            put(B if k % 2 else A, sgn * x, sgn * (yc + off), _h01(k, 4 + sgn) * 360, 1.1 + 0.6 * _h01(k, 6 + sgn))
    # 숲길 가장자리 10 (15 m 마다 지그재그, 점대칭)
    pts = L.FOREST_PATH_W; acc = 0.0; side = 1; k = 0
    for a, b in zip(pts, pts[1:]):
        seg = math.hypot(b[0] - a[0], b[1] - a[1]); t = 0.0
        while acc + (seg - t) >= 15.0:
            adv = 15.0 - acc; t += adv; acc = 0.0
            u = t / seg; x, y = L.lerp(a[0], b[0], u), L.lerp(a[1], b[1], u)
            nx, ny = -(b[1] - a[1]) / seg, (b[0] - a[0]) / seg
            px, py = x + nx * 4.2 * side, y + ny * 4.2 * side; side = -side; k += 1
            if k > 5: break
            for sgn in (1, -1):
                if not _struct_keepout(sgn * px, sgn * py, 1.0):
                    put(A if k % 2 else B, sgn * px, sgn * py, _h01(k, 7 + sgn) * 360, 0.8 + 0.5 * _h01(k, 9 + sgn))
        else:
            acc += seg - t
        if k > 5: break
    # 마루 난간 (주상절리, 절벽쪽 가장자리, 착지점 회피) 8/지릉
    crest = [(c[0], c[1]) for c in L.CREST]
    lens = [math.hypot(crest[i + 1][0] - crest[i][0], crest[i + 1][1] - crest[i][1]) for i in range(len(crest) - 1)]; tot = sum(lens)
    land = [(L.RAMPS[k][1][0], L.RAMPS[k][1][1]) for k in ("R1", "R2", "R3")] + [(L.RAMPS["T"][0][0], L.RAMPS["T"][0][1])]
    for q in range(8):
        s = 0.06 + q * 0.125; d = s * tot; acc2 = 0.0
        for i, ln in enumerate(lens):
            if d <= acc2 + ln or i == len(lens) - 1:
                u = (d - acc2) / ln; x, y = L.lerp(crest[i][0], crest[i + 1][0], u), L.lerp(crest[i][1], crest[i + 1][1], u)
                dx, dy = (crest[i + 1][0] - crest[i][0]) / ln, (crest[i + 1][1] - crest[i][1]) / ln
                nx, ny = dy, -dx     # 오른쪽 = 남서(절벽 앞면)
                break
            acc2 += ln
        px, py = x + nx * 2.2, y + ny * 2.2
        if any(math.hypot(px - lx, py - ly) < 4.5 for lx, ly in land): continue
        src = cols[q % 3]; h = src.dimensions.z; sc = (3.2 + 1.4 * _h01(q, 20)) / max(0.1, h)
        for sgn in (1, -1):
            put(src, sgn * px, sgn * py, (math.degrees(math.atan2(dy, dx)) + 90 + (_h01(q, 21 + sgn) - 0.5) * 30) * sgn, sc, sink=0.6)
    # 둔덕 위 5 + 북측 띠 너덜 6 (점대칭)
    for k, (cx, cy, r, dz, soft) in enumerate(L.KNOLLS_W):
        if k >= 5: break
        x, y = cx + (_h01(k, 30) - 0.5) * 3, cy + (_h01(k, 31) - 0.5) * 3
        for sgn in (1, -1):
            put(A if k % 2 else B, sgn * x, sgn * y, _h01(k, 32 + sgn) * 360, 0.8 + 0.5 * _h01(k, 34 + sgn))
    for k in range(3):
        x = -52 + k * 14 + (_h01(k, 40) - 0.5) * 6; y = 50 + (_h01(k, 41) - 0.5) * 6
        for sgn in (1, -1):
            if not _off_limits(sgn * x, sgn * y):
                put(B, sgn * x, sgn * y, _h01(k, 42 + sgn) * 360, 0.7 + 0.5 * _h01(k, 44 + sgn))
    print("rocks", n); return n

# ------------------------------------------------------------------ 구조물 / 계단 / 석축 / 돌탑
def _stone_mat(name="M_SGK_Stone", tile=1.6):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (600, 0)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled"); b.location = (300, 0); nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    if name == "M_SGK_Terrace":   # 석축 = 담장 석재 (쌓은 돌)
        sw = os.path.join(SSW, "Stonewall")
        s = {"bc": os.path.join(sw, "T_Stonewall_BC.png"), "nm": os.path.join(sw, "T_Stonewall_NM.png"), "rn": os.path.join(sw, "T_Stonewall_RN.png")}
    else:
        s = {"bc": os.path.join(JSN_ROCKTEX, "T_MDS_UnitA_BC.png"), "nm": os.path.join(JSN_ROCKTEX, "T_MDS_UnitA_N.png"), "rn": os.path.join(JSN_ROCKTEX, "T_MDS_UnitA_R.png")}
    c, n, r = _pbr(nt, "stone", s, -400, tile, ao_mix=0)
    lift = nt.nodes.new("ShaderNodeMixRGB"); lift.blend_type = "SCREEN"; lift.inputs["Fac"].default_value = 0.10; lift.location = (0, 300)
    nt.links.new(c, lift.inputs["Color1"]); lift.inputs["Color2"].default_value = (0.5, 0.5, 0.5, 1)
    nt.links.new(lift.outputs["Color"], b.inputs["Base Color"])
    nmap = nt.nodes.new("ShaderNodeNormalMap"); nmap.location = (0, -100); nt.links.new(n, nmap.inputs["Color"]); nt.links.new(nmap.outputs["Normal"], b.inputs["Normal"])
    nt.links.new(r, b.inputs["Roughness"])
    return m

def _box_mesh(name, cx, cy, z0, sx, sy, sz, yaw_deg, cname, mat):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz + sz * 0.5))
    me = bpy.data.meshes.new("MD_" + name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); ob.location = (cx, cy, z0); ob.rotation_euler = (0, 0, math.radians(yaw_deg)); _link(ob, cname)
    return ob

def place_structures():
    _clear_coll(COLL["STRUCT"]); _clear_coll(COLL["BLOCK"])
    stone = _stone_mat()
    pav, brg, w9, wl = (bpy.data.objects[k] for k in ("MST_PAVILION", "MST_BRIDGE", "MST_WALL_9M", "MST_WALL_L"))
    for kind, (x, y), yaw, (sx, sy, sz) in L.structures():
        zg = L.height_at(x, y)
        if kind == "PAVILION":
            _box_mesh("STA_Terrace_N", x, y, zg - 0.3, sx, sy, 1.5, 0, COLL["STRUCT"], _stone_mat("M_SGK_Terrace", 2.4))
            _instance(pav, "SGK_Pavilion", COLL["STRUCT"], x, y, yaw, 1.0, z=zg + 1.2)
        elif kind == "TERRACE":
            _box_mesh("STA_Terrace_S", x, y, zg - 0.3, sx, sy, 1.5, 0, COLL["STRUCT"], _stone_mat("M_SGK_Terrace", 2.4))
            make_cairn(x, y, zg + 1.2)
        elif kind == "BRIDGE":
            # 다리 장축을 남북(Y)으로: 원본 장축이 X 이면 90° 회전
            yaw_b = 90.0 if brg.dimensions.x > brg.dimensions.y else 0.0
            # 피벗은 바닥중심, 데크 상면은 로컬 z≈1.75 (BRIDGE_DECK_TOP). 데크가 양 둑 높이 +0.15 에 오도록 (수면 기준 +0.55 는 1.9 m 떠 있었다, 2026-09-05)
            # 데크 상면 = 수면 +0.35 (2026-09-05 '중간 다리 내려달라'. 둑 기준이면 어깨 사면 위로 아치처럼 떠 보였다)
            _instance(brg, "SGK_Bridge", COLL["STRUCT"], x, y, yaw_b, 1.0, z=L.water_z(x) + 0.35 - L.BRIDGE_DECK_TOP)
        elif kind == "WALL9":
            _instance(w9, f"SGK_Wall9_{int(x)}_{int(y)}", COLL["STRUCT"], x, y, yaw, 1.0, sink=0.35)
        elif kind == "WALL_L":
            _instance(wl, f"SGK_WallL_{int(x)}_{int(y)}", COLL["STRUCT"], x, y, yaw, 1.0, sink=0.35)
    print("structures placed:", len(_coll(COLL["STRUCT"]).objects))

def make_cairn(x, y, z0, name="STA_Cairn"):
    """돌탑: 납작한 돌 7~9개 스택, 1.6 m."""
    bm = bmesh.new(); h = 0.0; k = 0
    while h < 1.55:
        r = 0.42 * (1.0 - h / 2.4) * (0.85 + 0.3 * _h01(k, 77)); t = 0.14 + 0.08 * _h01(k, 78)
        m = Matrix.Translation((0.03 * (_h01(k, 79) - 0.5), 0.03 * (_h01(k, 80) - 0.5), h + t / 2)) @ Matrix.Rotation(_h01(k, 81) * 6.28, 4, "Z") @ Matrix.Diagonal((r, r * 0.8, t / 2, 1))
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0, matrix=m)
        h += t * 0.92; k += 1
    me = bpy.data.meshes.new("MD_" + name); bm.to_mesh(me); bm.free(); me.materials.append(_stone_mat("M_SGK_StoneSmall", 0.9))
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, me); ob.location = (x, y, z0); _link(ob, COLL["STRUCT"]); return ob

def make_steps():
    """자연석계단: T 계단·R2 선반에 슬랩(1.2×0.55×0.16) 0.9 m 간격, 한 메시 STA_STEPS."""
    for o in list(_coll(COLL["STRUCT"]).objects):
        if o.name == "STA_STEPS": bpy.data.objects.remove(o, do_unlink=True)
    bm = bmesh.new(); n = 0
    for key in ("T", "R2"):
        (ax, ay, z0), (bx, by, z1), hw, bl = L.RAMPS[key]
        for sgn in (1, -1):
            Lr = math.hypot(bx - ax, by - ay); yaw = math.atan2(by - ay, bx - ax)
            d = 1.0
            while d < Lr - 0.8:
                u = d / Lr; x, y = sgn * L.lerp(ax, bx, u), sgn * L.lerp(ay, by, u)
                z = L.height_at(x, y) - 0.06
                jitter = (_h01(n, 5) - 0.5) * 0.4
                m = Matrix.Translation((x + jitter * math.sin(yaw), y - jitter * math.cos(yaw), z)) @ Matrix.Rotation(yaw + (_h01(n, 6) - 0.5) * 0.35, 4, "Z") @ Matrix.Diagonal((0.62 * (0.9 + 0.2 * _h01(n, 7)), 0.28 * (0.9 + 0.3 * _h01(n, 8)), 0.08, 1))
                bmesh.ops.create_cube(bm, size=2.0, matrix=m)
                d += 0.9 + 0.2 * _h01(n, 9); n += 1
    me = bpy.data.meshes.new("MD_STA_STEPS"); bm.to_mesh(me); bm.free(); me.materials.append(_stone_mat("M_SGK_StoneSmall", 0.9))
    ob = bpy.data.objects.new("STA_STEPS", me); _link(ob, COLL["STRUCT"])
    print("steps slabs", n); return ob

# ------------------------------------------------------------------ 전체
def scatter_all():
    _PLACED.clear()
    scatter_pines(); scatter_understory(); scatter_rocks()

def _mesh_dims(me):
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    return Vector((max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)))

def export_placements():
    rows = []
    for o in bpy.data.objects:
        if o.name.startswith(("SGK_Pine", "SGK_Und", "SGK_Rock", "SGK_Pavilion", "SGK_Bridge", "SGK_Wall9", "SGK_WallL")):
            master = o.data.name[3:] if o.data.name.startswith("MD_") else o.data.name
            src = next((s.name for s in _coll(COLL["KIT"]).objects if s.data == o.data), master)
            rows.append({"master": src, "name": o.name, "x": round(o.location.x, 3), "y": round(o.location.y, 3), "z": round(o.location.z, 3),
                         "yaw": round(math.degrees(o.rotation_euler.z), 2), "scale": round(o.scale.x, 3),
                         "dims": [round(v * o.scale.x, 2) for v in _mesh_dims(o.data)]})   # 마스터 로컬 bbox × 인스턴스 스케일 (o.dimensions 는 depsgraph 갱신 전엔 스케일 미반영)
    statics = [o.name for c in ("SGK_TERRAIN", "SGK_WATER", "SGK_STRUCT") for o in _coll(c).objects if o.name.startswith(("SGK_Terrain", "SGK_Wall_", "SGK_StreamWater", "STA_"))]
    json.dump({"instances": rows, "statics": statics}, open(PLACEMENTS, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("placements", len(rows), "statics", len(statics), "->", PLACEMENTS)
    return rows

def dress_report():
    rows = scene_report()
    uniq = {o.data.name for o in bpy.data.objects if o.type == "MESH" and o.visible_get()}
    inst = sum(r[1] for r in rows if r[0] in ("SGK_VEG", "SGK_ROCK", "SGK_STRUCT", "SGK_TERRAIN", "SGK_WATER"))
    packed = [im.name for im in bpy.data.images if im.packed_file]
    print("visible unique meshes:", len(uniq), "| render instances:", inst, "| packed images:", packed)
    return {"unique_meshes": len(uniq), "instances": inst, "packed": packed}
