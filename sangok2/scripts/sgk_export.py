# -*- coding: utf-8 -*-
r"""
sgk_export.py — Phase 3 FBX 익스포트 (헤드리스).

  "C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe" -b 00_Source_Blender\SGK_Master.blend --python _scripts\sgk_export.py -- all
  옵션: masters | terrain | statics | all

규칙 (overdare-fbx-conversion 메모리):
  - 파일당 메시 1개, 메시 ≤27k tris (콜랩스 데시메이트; 알파 카드 메시는 감축 안 함)
  - 재질은 텍스처 1장(BC, 알파는 RGBA)만 남기고 같은 텍스처를 쓰는 슬롯은 병합 → 재질 수 = 임포트 유닛
  - 텍스처는 _texwork 의 디스크 PNG 를 path_mode COPY 로 임베드 (pack 이미지 절대 금지)
  - 마스터(인스턴스)는 바닥중심 피벗 로컬좌표, 정적(지형·산벽·석축·계단·물)은 월드좌표 그대로 → Studio 에서 (0,0,0)
  - 축 Y-up / -Z forward, FBX_SCALE_NONE
결과: 06_OVERDARE\{10_MASTERS,01_TERRAIN,02_STATIC}\*.fbx + manifest.json (tris/재질/bbox)
"""
import bpy, bmesh, os, sys, json, math, time
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sgk_layout as L
ROOT = os.path.dirname(HERE)
OVD = os.path.join(ROOT, "06_OVERDARE"); TEXWORK = os.path.join(OVD, "_texwork")
DIRS = {"masters": os.path.join(OVD, "10_MASTERS"), "terrain": os.path.join(OVD, "01_TERRAIN"), "statics": os.path.join(OVD, "02_STATIC")}
for d in DIRS.values(): os.makedirs(d, exist_ok=True)
TRI_CAP = 27000
MANIFEST = os.path.join(OVD, "manifest.json")

# 마스터 → {재질이름 접두 → 텍스처}
MASTERS = {}
for k in ("MST_PINE_L1", "MST_PINE_L2", "MST_PINE_L3", "MST_PINE_M1", "MST_PINE_M2", "MST_PINE_M3", "MST_PINE_XL1", "MST_PINE_XL2",
          "MST_PINE_S1", "MST_PINE_S2", "MST_SAPLING1", "MST_SAPLING2"):
    MASTERS[k] = {"Clusters_Mat": "PINE_CLUSTERS", "Bark_Mat": "PINE_BARK"}
MASTERS.update({
    "MST_BOULDER_A": {"*": "BOULDER_A"}, "MST_BOULDER_B": {"*": "BOULDER_B"}, "MST_FERN": {"*": "FERN"},
    "MST_STUMP": {"*": "STUMP"}, "MST_DEADTRUNK": {"*": "DEADTRUNK"},
    "MST_PAVILION": {"MI_Wood": "CJ_WOOD", "MI_CJ_Roof01a": "CJ_ROOF01", "MI_CJ_Roof02a": "CJ_ROOF02", "MI_Cornerstone": "CJ_CORNER", "MI_Fence01b": "CJ_FENCE"},
    "MST_BRIDGE": {"MI_Bridge01b": "BRIDGE01", "MI_Bridge02b": "BRIDGE02"},
    "MST_WALL_9M": {"StoneWall": "STONEWALL", "Trim_roof": "WALLROOF"}, "MST_WALL_L": {"StoneWall": "STONEWALL", "Trim_roof": "WALLROOF"},
})
NO_DECIMATE = {k for k in MASTERS if k.startswith(("MST_PINE", "MST_SAPLING"))} | {"MST_FERN"}
# 정적 (월드좌표): 이름 → (텍스처, 박스UV 타일 m or None)
STATICS = {"STA_Terrace_N": ("STONEWALL", 2.4), "STA_Terrace_S": ("STONEWALL", 2.4), "STA_Cairn": ("BASALT", 0.9), "STA_STEPS": ("BASALT", 0.9), "SGK_StreamWater": ("SGK_WATER", 8.0)}

def _tris(me): return sum(len(p.vertices) - 2 for p in me.polygons)

def _flat_material(tex):
    name = "OVD_" + tex
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    b.inputs["Roughness"].default_value = 0.85
    p = os.path.join(TEXWORK, tex + ".png")
    im = bpy.data.images.load(p, check_existing=True)
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = im; nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    if im.channels == 4 and (tex in ("PINE_CLUSTERS", "FERN", "CJ_ROOF01", "CJ_FENCE") or tex.endswith("_ATL")):
        nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"]); m.blend_method = "HASHED"
    return m

def _copy_object(src, name):
    me = src.data.copy(); me.name = "EX_" + name
    ob = bpy.data.objects.new("EX_" + name, me); bpy.context.scene.collection.objects.link(ob)
    ob.matrix_world = src.matrix_world.copy()
    return ob

def _analytic_normal(x, y, e=0.25):
    """height_at 의 유한차분 기울기 → 단위 노멀 (Blender Z-up)."""
    hx = (L.height_at(x + e, y) - L.height_at(x - e, y)) / (2 * e)
    hy = (L.height_at(x, y + e) - L.height_at(x, y - e)) / (2 * e)
    return Vector((-hx, -hy, 1.0)).normalized()

def _bake_world(ob):
    ob.data.transform(ob.matrix_world); ob.matrix_world = Matrix.Identity(4)

def _decimate(ob, cap):
    n = _tris(ob.data)
    if n <= cap: return n
    mod = ob.modifiers.new("dec", "DECIMATE"); mod.decimate_type = "COLLAPSE"; mod.ratio = cap / n * 0.97; mod.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.remove(mod); old = ob.data; ob.data = me; me.name = old.name + "_dec"; bpy.data.meshes.remove(old)
    return _tris(me)

def _remap_materials(ob, mapping):
    """슬롯 → 텍스처 매핑으로 재질을 병합. mapping {"prefix": tex} 또는 {"*": tex}."""
    me = ob.data
    def tex_for(mat):
        if "*" in mapping: return mapping["*"]
        nm = (mat.name if mat else "")
        for pre, tex in mapping.items():
            if nm.startswith(pre): return tex
        # 폴백: 첫 텍스처
        return list(mapping.values())[0]
    slot_tex = [tex_for(m) for m in me.materials] or [list(mapping.values())[0]]
    uniq = []
    for t in slot_tex:
        if t not in uniq: uniq.append(t)
    newidx = [uniq.index(t) for t in slot_tex]
    for p in me.polygons:
        p.material_index = newidx[p.material_index] if p.material_index < len(newidx) else 0
    me.materials.clear()
    for t in uniq: me.materials.append(_flat_material(t))
    return uniq

def _keep_first_uv(me):
    while len(me.uv_layers) > 1:
        me.uv_layers.remove(me.uv_layers[-1])

def _box_uv(ob, tile):
    """UV 없는 절차 메시: 면 법선 지배축으로 평면 투영 (BOX 근사). 월드좌표 기준."""
    me = ob.data
    if me.uv_layers: me.uv_layers.remove(me.uv_layers[0])
    uv = me.uv_layers.new(name="UVMap")
    mw = ob.matrix_world
    for p in me.polygons:
        n = (mw.to_3x3() @ p.normal); a = [abs(n.x), abs(n.y), abs(n.z)]; ax = a.index(max(a))
        for li in p.loop_indices:
            co = mw @ me.vertices[me.loops[li].vertex_index].co
            if ax == 2: u, v = co.x, co.y
            elif ax == 0: u, v = co.y, co.z
            else: u, v = co.x, co.z
            uv.data[li].uv = (u / tile, v / tile)

FILE_PREFIX = {"terrain": "SGK_", "statics": "SGK_"}   # 파일명(=Studio 에셋 이름) 접두. 산옥(JSN)의 STA_TER_xy_overdare 등 14개와 이름이 겹쳐서 (2026-09-06)

def _export(ob, folder, stem):
    for o in bpy.context.view_layer.objects: o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    pre = next((v for k, v in FILE_PREFIX.items() if DIRS[k] == folder), "")
    path = os.path.join(folder, pre + stem + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"MESH"}, axis_up="Y", axis_forward="-Z",
                             apply_scale_options="FBX_SCALE_NONE", global_scale=1.0, apply_unit_scale=True, path_mode="COPY", embed_textures=True,
                             mesh_smooth_type="FACE", use_mesh_modifiers=True, add_leaf_bones=False, bake_anim=False, use_custom_props=False)
    me = ob.data
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    rec = {"file": os.path.relpath(path, OVD), "tris": _tris(me), "verts": len(me.vertices), "mats": [m.name[4:] for m in me.materials],
           "bbox_min": [round(min(xs), 3), round(min(ys), 3), round(min(zs), 3)], "bbox_max": [round(max(xs), 3), round(max(ys), 3), round(max(zs), 3)],
           "size_mb": round(os.path.getsize(path) / 1e6, 2)}
    return rec

ATLAS_PLAN = os.path.join(TEXWORK, "_atlas_plan.json")
# 알파 아틀라스 마스터 (재익스포트·재임포트 대상). 파일·텍스처 이름에 SGK_ 접두 → 이미 발행된 1024×2048 판과 이름 충돌 없이 새 에셋으로 임포트
ALPHA_MASTERS = {k for k in MASTERS if k.startswith(("MST_PINE", "MST_SAPLING"))} | {"MST_PAVILION", "MST_FERN"}
ALPHA_TEX = {"PINE_CLUSTERS", "FERN", "CJ_ROOF01", "CJ_FENCE"}
# 알파 마스터 에셋 이름 접두. 라운드마다 올려야 한다 (SGK_ = 2차, 알파 안 자른 판 / SGK3_ = 3차, 실루엣 컷 + 인필 아틀라스, 2026-09-06). Studio 는 같은 이름을 새 에셋으로 안 받는다
ALPHA_PREFIX = "SGK3_"

def _slot_groups(ob, mapping):
    """슬롯 → 텍스처 키, 키별 (vmin, vmax, loops)."""
    me = ob.data; uv = me.uv_layers.active
    def tex_for(mat):
        if "*" in mapping: return mapping["*"]
        nm = mat.name if mat else ""
        for pre, tex in mapping.items():
            if nm.startswith(pre): return tex
        return list(mapping.values())[0]
    slot_tex = [tex_for(m) for m in me.materials] or [list(mapping.values())[0]]
    rng = {}
    for p in me.polygons:
        t = slot_tex[p.material_index] if p.material_index < len(slot_tex) else slot_tex[0]
        r = rng.setdefault(t, [1e9, -1e9, 0])
        for li in p.loop_indices:
            v = uv.data[li].uv.y; r[0] = min(r[0], v); r[1] = max(r[1], v); r[2] += 1
    return slot_tex, rng

def _make_plan(name, rng):
    """밴드 아틀라스 계획: 각 텍스처가 가로 전폭 밴드(세로 v 반복 N 스택). 알파 텍스처 밴드는 2배 가중."""
    keys = list(rng)
    w = {k: (2.0 if k in ALPHA_TEX else 1.0) for k in keys}
    tot = sum(w.values()); y = 0.0; bands = []
    for k in keys:
        vmin, vmax, _ = rng[k]; v0 = math.floor(vmin - 1e-4); N = max(1, min(48, math.ceil(vmax + 1e-4) - v0))
        h = w[k] / tot
        bands.append({"tex": k, "v0": v0, "N": N, "y0": round(y, 5), "y1": round(y + h, 5)}); y += h
    # 시트는 반드시 정방형 1024×1024: Studio 는 1024×2048 텍스처의 알파를 버린다 (2026-09-06 실측 — 소나무 잎·정자 지붕이 검은 판, FERN 1024² 은 정상)
    return {"name": (ALPHA_PREFIX + name if name in ALPHA_MASTERS else name), "sheet": [1024, 1024], "bands": bands}

def _apply_plan(ob, slot_tex, plan):
    me = ob.data; uv = me.uv_layers.active
    band = {b["tex"]: b for b in plan["bands"]}
    for p in me.polygons:
        t = slot_tex[p.material_index] if p.material_index < len(slot_tex) else slot_tex[0]
        b = band[t]
        for li in p.loop_indices:
            u, v = uv.data[li].uv
            uv.data[li].uv = (u, b["y0"] + (b["y1"] - b["y0"]) * (v - b["v0"]) / b["N"])
        p.material_index = 0
    me.materials.clear(); me.materials.append(_flat_material(plan["name"] + "_ATL"))

def _cut_alpha_faces(ob, slot_tex, atlas_png, max_verts=5, thr=100):
    """OVERDARE MeshPart 는 텍스처 알파를 안 쓴다(2026-09-06 실측, 산옥도 동일). 잎 삼각형을 알파>thr 영역의 볼록 껍질로 잘라
    검은 배경을 지오메트리에서 제거한다. UV 는 이미 아틀라스 좌표. 삼각형당 최대 max_verts 각형(= max_verts-2 tris)."""
    from PIL import Image
    import numpy as np
    A = np.asarray(Image.open(atlas_png).convert("RGBA"))[:, :, 3]; H, W = A.shape
    me = ob.data; uvl = me.uv_layers.active.data
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table(); uv = bm.loops.layers.uv.active
    alpha_faces = [f for f in bm.faces if slot_tex[f.material_index] in ALPHA_TEX and len(f.verts) == 3] if slot_tex else []
    # 샘플 격자 (무게중심 좌표)
    n = 14; samp = [(i / n, j / n) for i in range(n + 1) for j in range(n + 1 - i)]
    def hull(pts):
        pts = sorted(set(pts))
        if len(pts) <= 2: return pts
        def cross(o, a, b): return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
        lo = []
        for p in pts:
            while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
            lo.append(p)
        up = []
        for p in reversed(pts):
            while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0: up.pop()
            up.append(p)
        return lo[:-1] + up[:-1]
    def simplify(h, k):
        while len(h) > k:   # 제거 시 면적 손실이 가장 작은 꼭짓점 제거
            best = None
            for i in range(len(h)):
                a, b, c = h[i-1], h[i], h[(i+1) % len(h)]
                area = abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
                if best is None or area < best[0]: best = (area, i)
            h.pop(best[1])
        return h
    removed = kept = cut = 0; new_faces = []
    for f in alpha_faces:
        L = list(f.loops); P = [l.vert.co.copy() for l in L]; U = [l[uv].uv.copy() for l in L]
        op = []
        for (s, t) in samp:
            w0, w1, w2 = 1 - s - t, s, t
            u = w0*U[0].x + w1*U[1].x + w2*U[2].x; v = w0*U[0].y + w1*U[1].y + w2*U[2].y
            px = min(W-1, max(0, int(u * W))); py = min(H-1, max(0, int((1 - v) * H)))
            if A[py, px] > thr: op.append((round(s, 4), round(t, 4)))
        if not op: bmesh.ops.delete(bm, geom=[f], context="FACES_ONLY"); removed += 1; continue
        if len(op) >= len(samp) - 2: kept += 1; continue
        h = simplify(hull(op), max_verts)
        if len(h) < 3: bmesh.ops.delete(bm, geom=[f], context="FACES_ONLY"); removed += 1; continue
        # 껍질을 한 샘플 간격만큼 바깥으로 살짝 팽창 (실루엣 잘림 방지)
        cs = sum(p[0] for p in h) / len(h); ct = sum(p[1] for p in h) / len(h)
        h = [(cs + (p[0]-cs) * 1.12, ct + (p[1]-ct) * 1.12) for p in h]
        verts = []; uvs = []
        for (s, t) in h:
            s = max(0.0, s); t = max(0.0, t)
            if s + t > 1: k = 1.0 / (s + t); s *= k; t *= k
            w0, w1, w2 = 1 - s - t, s, t
            verts.append(bm.verts.new(P[0]*w0 + P[1]*w1 + P[2]*w2)); uvs.append(U[0]*w0 + U[1]*w1 + U[2]*w2)
        try:
            nf = bm.faces.new(verts); nf.material_index = f.material_index; nf.smooth = f.smooth
            for l, u in zip(nf.loops, uvs): l[uv].uv = u
            new_faces.append(nf); bmesh.ops.delete(bm, geom=[f], context="FACES_ONLY"); cut += 1
        except ValueError:
            for v in verts: bm.verts.remove(v)
            kept += 1
    bmesh.ops.triangulate(bm, faces=new_faces)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(me); bm.free(); me.update()
    print(f"    alpha-cut: kept {kept} cut {cut} removed {removed} -> tris {_tris(me)}")

def export_masters(manifest, plan_only=False):
    plans = json.load(open(ATLAS_PLAN, encoding="utf-8")) if os.path.exists(ATLAS_PLAN) else {}
    for name, mapping in MASTERS.items():
        src = bpy.data.objects.get(name)
        if not src:
            stem0 = name if name.startswith("STA_") else "STA_" + name.replace("SGK_", "")
            if manifest.pop(stem0, None) is not None: print("REMOVED from manifest:", stem0)   # 사용자가 씬에서 지운 정적 (예: STA_Terrace_S, 2026-09-06)
            fp = os.path.join(DIRS["statics"], stem0 + ".fbx")
            if os.path.exists(fp): os.remove(fp)
            print("MISSING", name); continue
        ob = _copy_object(src, name); _bake_world(ob)
        _keep_first_uv(ob.data)
        n = _decimate(ob, TRI_CAP) if name not in NO_DECIMATE else _tris(ob.data)
        slot_tex, rng = _slot_groups(ob, mapping)
        if len(rng) > 1 or name in ALPHA_MASTERS:   # 알파 마스터는 1장짜리(FERN)도 아틀라스 경로: 텍스처 에셋 이름에 접두가 붙어야 새 에셋으로 올라간다
            if plan_only or name not in plans:
                plans[name] = _make_plan(name, rng); print("plan", name, [(b["tex"], b["N"], round(b["y1"] - b["y0"], 2)) for b in plans[name]["bands"]])
                bpy.data.objects.remove(ob, do_unlink=True); continue
            _apply_plan(ob, slot_tex, plans[name]); mats = [plans[name]["name"] + "_ATL"]
            if name in ALPHA_MASTERS and not plan_only: _cut_alpha_faces(ob, slot_tex, os.path.join(TEXWORK, mats[0] + ".png"))
        else:
            mats = _remap_materials(ob, mapping)
            if name in ALPHA_MASTERS and not plan_only: _cut_alpha_faces(ob, [mats[0]] * max(1, len(ob.data.materials)), os.path.join(TEXWORK, mats[0] + ".png"))
        if plan_only:
            bpy.data.objects.remove(ob, do_unlink=True); continue
        rec = _export(ob, DIRS["masters"], (ALPHA_PREFIX + name if name in ALPHA_MASTERS else name)); rec["kind"] = "master"; manifest[name] = rec
        print(f"{name:16s} tris={rec['tris']:6d} mats={mats} {rec['size_mb']} MB")
        bpy.data.objects.remove(ob, do_unlink=True)
    json.dump(plans, open(ATLAS_PLAN, "w", encoding="utf-8"), indent=1)

def export_terrain(manifest):
    src = bpy.data.objects["SGK_Terrain"]; me0 = src.data; T = L.TILE
    # 이음선 방지 1: 노멀은 height_at 해석 기울기로 (타일·산벽 공통). 타일 안 면만으로 재계산하면 경계 음영이 끊기고,
    # 산벽(1.25 m 격자)과 지형(0.5 m 격자)은 정점 수가 달라 메시 노멀로는 맞출 수 없다. 메시 z == height_at 확인됨(2026-09-05).
    for ty in range(L.TILES_Y):
        for tx in range(L.TILES_X):
            x0 = -L.PLAY_X + tx * T; y0 = -L.PLAY_Y + ty * T
            bm = bmesh.new(); vmap = {}; vsrc = {}
            for p in me0.polygons:
                c = p.center
                if x0 - 1e-6 <= c.x < x0 + T - 1e-6 and y0 - 1e-6 <= c.y < y0 + T - 1e-6:
                    vs = []
                    for vi in p.vertices:
                        if vi not in vmap: vmap[vi] = bm.verts.new(me0.vertices[vi].co); vsrc[vmap[vi]] = vi
                        vs.append(vmap[vi])
                    try: bm.faces.new(vs)
                    except ValueError: pass
            # 이음선 방지 2: UV 를 패딩 안쪽으로 (텍스처 바깥 TEX_PAD px 는 이웃 타일 월드를 이어 구웠다)
            uv = bm.loops.layers.uv.new("UVMap")
            for f in bm.faces:
                for l in f.loops:
                    l[uv].uv = (L.uv_pad((l.vert.co.x - x0) / T, 1024), L.uv_pad((l.vert.co.y - y0) / T, 1024))
            bm.verts.index_update()
            vn = [_analytic_normal(v.co.x, v.co.y) for v in bm.verts]
            name = f"TER_{tx}{ty}"; me = bpy.data.meshes.new("EX_" + name); bm.to_mesh(me); bm.free()
            for p in me.polygons: p.use_smooth = True
            me.normals_split_custom_set_from_vertices(vn)
            me.materials.append(_flat_material("SGK_" + name))
            ob = bpy.data.objects.new("EX_" + name, me); bpy.context.scene.collection.objects.link(ob)
            rec = _export(ob, DIRS["terrain"], "STA_" + name); rec["kind"] = "static"; manifest["STA_" + name] = rec
            print(f"STA_{name} tris={rec['tris']} {rec['size_mb']} MB"); bpy.data.objects.remove(ob, do_unlink=True)
    for name, (x0, y0, w, h, pw, ph) in L.wall_slabs().items():
        k = name.split("_")[-1]                       # N1 / N2 / S1 / S2 / E / W
        src = bpy.data.objects[f"SGK_Wall_{k[0]}"]; ob = _copy_object(src, "WALL_" + k); _bake_world(ob)
        me = ob.data
        if k[0] in "NS":                              # N/S 벽은 x=0 에서 반으로 (면 중심 기준, 정점은 공유 좌표 그대로)
            bm = bmesh.new(); bm.from_mesh(me)
            drop = [f for f in bm.faces if (f.calc_center_median().x >= 0.0) != (k[1] == "2")]
            bmesh.ops.delete(bm, geom=drop, context="FACES"); bm.to_mesh(me); bm.free()
        if me.uv_layers:
            while me.uv_layers: me.uv_layers.remove(me.uv_layers[0])
        uv = me.uv_layers.new(name="UVMap")
        for p in me.polygons:
            for li in p.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                uv.data[li].uv = (L.uv_pad(max(0.0, min(1.0, (co.x - x0) / w)), pw), L.uv_pad(max(0.0, min(1.0, (co.y - y0) / h)), ph))
        for p in me.polygons: p.use_smooth = True
        me.normals_split_custom_set_from_vertices([_analytic_normal(v.co.x, v.co.y) for v in me.vertices])
        me.materials.clear(); me.materials.append(_flat_material(name))
        stem = "STA_WALL_" + k
        rec = _export(ob, DIRS["terrain"], stem); rec["kind"] = "static"; manifest[stem] = rec
        print(f"{stem} tris={rec['tris']} {rec['size_mb']} MB"); bpy.data.objects.remove(ob, do_unlink=True)
    for old in ("STA_WALL_N", "STA_WALL_S"):            # 구 1장짜리 항목·파일 제거
        manifest.pop(old, None)
        fp = os.path.join(DIRS["terrain"], old + ".fbx")
        if os.path.exists(fp): os.remove(fp)

def export_statics(manifest):
    for name, (tex, tile) in STATICS.items():
        src = bpy.data.objects.get(name)
        if not src:
            stem0 = name if name.startswith("STA_") else "STA_" + name.replace("SGK_", "")
            if manifest.pop(stem0, None) is not None: print("REMOVED from manifest:", stem0)   # 사용자가 씬에서 지운 정적 (예: STA_Terrace_S, 2026-09-06)
            fp = os.path.join(DIRS["statics"], stem0 + ".fbx")
            if os.path.exists(fp): os.remove(fp)
            print("MISSING", name); continue
        ob = _copy_object(src, name)
        _box_uv(ob, tile)          # 월드좌표 기준 투영 후
        _bake_world(ob)
        n = _decimate(ob, TRI_CAP)
        ob.data.materials.clear(); ob.data.materials.append(_flat_material(tex))
        stem = name if name.startswith("STA_") else "STA_" + name.replace("SGK_", "")
        rec = _export(ob, DIRS["statics"], stem); rec["kind"] = "static"; manifest[stem] = rec
        print(f"{stem:18s} tris={rec['tris']} {rec['size_mb']} MB"); bpy.data.objects.remove(ob, do_unlink=True)

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["all"]
    manifest = json.load(open(MANIFEST, encoding="utf-8")) if os.path.exists(MANIFEST) else {}
    t = time.time()
    if "plan" in args: export_masters(manifest, plan_only=True)
    if "all" in args or "masters" in args: export_masters(manifest)
    if "all" in args or "terrain" in args: export_terrain(manifest)
    if "all" in args or "statics" in args: export_statics(manifest)
    json.dump(manifest, open(MANIFEST, "w", encoding="utf-8"), indent=1)
    bad = {k: v["tris"] for k, v in manifest.items() if v["tris"] > 30000}
    print(f"manifest {len(manifest)} files, over 30k: {bad}, {time.time()-t:.0f}s")
