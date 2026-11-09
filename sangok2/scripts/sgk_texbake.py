# -*- coding: utf-8 -*-
r"""
sgk_texbake.py — Phase 3 텍스처 (시스템 파이썬 + PIL/numpy, Blender 불필요).

  python sgk_texbake.py props     # 프롭 텍스처 → 06_OVERDARE\_texwork\*.png (BC + OP→alpha, 크기 캡)
  python sgk_texbake.py terrain   # 지형 타일 12장 (1024) + 산벽 슬랩 4장 → _texwork\TER_xy.png / WALL_x.png
  python sgk_texbake.py           # 둘 다

지형 타일은 sgk_layout.blend_at(x,y)->(R 흙, G 암반, B 젖은, A 낙엽) 을 성글게(128²) 평가해 업샘플하고
6개 소스(풀·낙엽·마사토·젖은·주상절리·aerial_rocks)를 sgk_dress.terrain_material 과 같은 타일 거리·틴트로 합성한다.
"""
import os, sys, json, math
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sgk_layout as L

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "06_OVERDARE", "_texwork"); os.makedirs(OUT, exist_ok=True)
TEX = os.path.join(ROOT, "_TexLib")
PH = os.path.join(TEX, "polyhaven")
SSW = os.path.join(os.path.dirname(ROOT), "SSW_Soswaewon", "_extracted")   # 이 PC(HSP)엔 없음 — props 베이크(초정·담장)에만 필요
JSN_ROCK = os.path.join(os.path.dirname(ROOT), "JSN_Sangok", "_extracted", "ROCK_ColumnarA", "Texture")
PINE = os.path.join(TEX, "sketchfab", "pine_pack")
UNP = os.path.join(TEX, "unpacked")

def _ph(asset, ch):
    d = os.path.join(PH, asset)
    for f in os.listdir(d):
        if f"_{ch}_1k" in f: return os.path.join(d, f)
    raise FileNotFoundError(asset + ch)

# 프롭: 출력명 → (BC 경로, OP 경로 or None, (w,h), 틴트 RGB or None)
PROPS = {
    "PINE_BARK":     (os.path.join(PINE, "Bark_Mat_baseColor.png"), None, (512, 1024), (0.98, 0.80, 0.66)),   # 적송 온색 틴트
    "PINE_CLUSTERS": (os.path.join(PINE, "Clusters_Mat_baseColor.png"), "SELF", (1024, 1024), (0.96, 1.0, 0.92)),
    "BOULDER_A":     (os.path.join(UNP, "boulder_01_diff.png"), None, (512, 512), None),
    "BOULDER_B":     (os.path.join(UNP, "boulder_02_diff.png"), None, (512, 512), None),
    "FERN":          (os.path.join(PH, "models", "fern_02", "textures", "fern_02_diff_1k.jpg"), os.path.join(PH, "models", "fern_02", "textures", "fern_02_alpha_1k.jpg"), (1024, 1024), None),
    "STUMP":         (os.path.join(UNP, "tree_stump_01_diff.png"), None, (512, 512), None),
    "DEADTRUNK":     (os.path.join(UNP, "dead_tree_trunk_diff.png"), None, (512, 512), None),
    "CJ_WOOD":       (os.path.join(SSW, "Chojeong_Pavilion", "T_Wood_BC.png"), None, (512, 512), None),
    "CJ_ROOF01":     (os.path.join(SSW, "Chojeong_Pavilion", "T_CJ_Roof01a_BC.png"), os.path.join(SSW, "Chojeong_Pavilion", "T_CJ_Roof01a_OP.png"), (512, 512), None),
    "CJ_ROOF02":     (os.path.join(SSW, "Chojeong_Pavilion", "T_CJ_Roof02a_BC.png"), None, (512, 512), None),
    "CJ_CORNER":     (os.path.join(SSW, "Chojeong_Pavilion", "T_Cornerstone_BC.png"), None, (512, 512), None),
    "CJ_FENCE":      (os.path.join(SSW, "Chojeong_Pavilion", "T_Fence01b_BC.png"), os.path.join(SSW, "Chojeong_Pavilion", "T_Fence01b_OP.png"), (512, 512), None),
    "BRIDGE01":      (os.path.join(SSW, "Tujugwigyo", "T_Bridge01b_BC.png"), None, (512, 512), None),
    "BRIDGE02":      (os.path.join(SSW, "Tujugwigyo", "T_Bridge02b_BC.png"), None, (512, 512), None),
    "STONEWALL":     (os.path.join(SSW, "Stonewall", "T_Stonewall_BC.png"), None, (512, 512), None),
    "WALLROOF":      (os.path.join(SSW, "Stonewall", "T_GPG_Roof_BC.png"), None, (512, 512), None),
    "BASALT":        (os.path.join(JSN_ROCK, "T_MDS_UnitA_BC.png"), None, (512, 512), (1.12, 1.10, 1.06)),   # 계단·돌탑 (SCREEN 0.1 근사)
    "SGK_WATER":     (None, None, (16, 16), (0.16, 0.30, 0.32)),   # 엔진에서 Transparency 0.45 와 함께 (검은 불투명 슬랩이었다)
}

def bake_props():
    made = {}
    for name, (bc, op, size, tint) in PROPS.items():
        if bc is None:
            im = Image.new("RGB", size, tuple(int(c * 255) for c in tint))
        else:
            im = Image.open(bc)
            alpha = None
            if op == "SELF":
                alpha = im.split()[-1] if im.mode in ("RGBA", "LA") else None
            elif op:
                alpha = Image.open(op).convert("L")
            im = im.convert("RGB")
            if tint:
                a = np.asarray(im, dtype=np.float32) * np.array(tint, dtype=np.float32)
                im = Image.fromarray(np.clip(a, 0, 255).astype("uint8"), "RGB")
            im = im.resize(size, Image.LANCZOS)
            if alpha is not None:
                im.putalpha(alpha.resize(size, Image.LANCZOS))
        p = os.path.join(OUT, name + ".png"); im.save(p, optimize=True)
        made[name] = {"size": im.size, "mode": im.mode, "bytes": os.path.getsize(p)}
        print(f"{name:14s} {im.size} {im.mode} {os.path.getsize(p)/1e3:7.0f} KB")
    json.dump(made, open(os.path.join(OUT, "_props.json"), "w"), indent=1)
    return made

# ------------------------------------------------------------------ 지형
TILE_M = {"grass": 4.0, "litter": 3.5, "dirt": 3.0, "wet": 3.0, "rock": 3.5, "rock2": 6.0}
TINT = {"grass": (0.80, 0.86, 0.66), "litter": (0.92, 0.84, 0.72), "dirt": (0.86, 0.78, 0.66),
        "wet": (0.70, 0.72, 0.72), "rock": (1.05, 1.00, 0.94), "rock2": (0.95, 0.93, 0.90)}
SRC = {"grass": ("aerial_grass_rock", True), "litter": ("brown_mud_leaves_01", True), "dirt": ("brown_mud_dry", True),
       "wet": ("brown_mud_rocks_01", True), "rock2": ("aerial_rocks_02", True)}

def _load_sources(n=1024):
    src = {}
    for k, (asset, ao) in SRC.items():
        im = np.asarray(Image.open(_ph(asset, "diff")).convert("RGB").resize((n, n), Image.LANCZOS), dtype=np.float32) / 255.0
        if ao:
            a = np.asarray(Image.open(_ph(asset, "ao")).convert("L").resize((n, n), Image.LANCZOS), dtype=np.float32) / 255.0
            im = im * (1.0 - 0.5 + 0.5 * a[:, :, None])
        src[k] = np.clip(im * np.array(TINT[k], dtype=np.float32), 0, 1)
    im = np.asarray(Image.open(os.path.join(JSN_ROCK, "T_MDS_UnitA_BC.png")).convert("RGB").resize((n, n), Image.LANCZOS), dtype=np.float32) / 255.0
    src["rock"] = np.clip(im * np.array(TINT["rock"], dtype=np.float32), 0, 1)
    return src

# ------------------------------------------------------------------ 월드 연속 필드 (이음선 방지)
# 이전 버전은 타일마다 다른 시드로 노이즈를 만들고 마스크도 타일별로 클램프해 업샘플했다 → 타일 경계에서 색조가 직선으로 끊김
# (산옥 OVERDARE_맵이식_명세서 §4 의 "밝은 올리브 vs 어두운 녹색"). 이제 노이즈·마스크는 지형 전체 rect 위에 한 번만 만들고
# 모든 타일·산벽이 월드 좌표로 같은 필드를 샘플한다. 텍스처 가장자리 TEX_PAD 픽셀은 rect 밖 월드를 이어서 굽는다.
_FX0, _FY0 = -L.MESH_X - 6.0, -L.MESH_Y - 6.0
_FW, _FH = 2 * (L.MESH_X + 6.0), 2 * (L.MESH_Y + 6.0)
_FIELDS = {}

def _world_noise(cell_m, seed, res_m=4.0):
    """값 노이즈. 격자 간격 cell_m(m), 출력 래스터 res_m px/m, 지형 rect 전체. 행 0 = 북(+y)."""
    key = ("nz", cell_m, seed)
    if key in _FIELDS: return _FIELDS[key]
    rng = np.random.RandomState(seed)
    nx, ny = int(math.ceil(_FW / cell_m)) + 2, int(math.ceil(_FH / cell_m)) + 2
    g = rng.rand(ny, nx).astype(np.float32)
    # 격자 (nx-1)*cell_m 폭이 rect 를 덮도록 래스터 크기를 격자 실제 폭 기준으로 잡는다
    W, H = (nx - 1) * cell_m, (ny - 1) * cell_m
    img = Image.fromarray((g * 255).astype("uint8"), "L").resize((int(W * res_m), int(H * res_m)), Image.BICUBIC)
    fld = {"x0": _FX0, "y0": _FY0, "w": W, "h": H, "arr": np.asarray(img, dtype=np.float32) / 255.0}
    _FIELDS[key] = fld; return fld

def _world_mask(res_m=4.0):
    """blend_at 을 rect 전체에서 res_m px/m 로 한 번 평가 (RGBA float)."""
    key = ("mask", res_m)
    if key in _FIELDS: return _FIELDS[key]
    C, R = int(_FW * res_m), int(_FH * res_m)
    m = np.zeros((R, C, 4), dtype=np.float32)
    for j in range(R):
        wy = _FY0 + _FH - (j + 0.5) / res_m
        for i in range(C):
            m[j, i] = L.blend_at(_FX0 + (i + 0.5) / res_m, wy)
    fld = {"x0": _FX0, "y0": _FY0, "w": _FW, "h": _FH, "arr": np.clip(m, 0, 1)}
    _FIELDS[key] = fld; return fld

def _field_sample(fld, wx, wy):
    """월드 좌표 열벡터 wx(1,W)·행벡터 wy(H,1) 에서 바이리니어 샘플 → (H,W[,ch])."""
    arr = fld["arr"]; R, C = arr.shape[:2]
    cf = np.clip((wx[0] - fld["x0"]) / fld["w"] * C - 0.5, 0, C - 1)
    rf = np.clip((fld["y0"] + fld["h"] - wy[:, 0]) / fld["h"] * R - 0.5, 0, R - 1)
    c0 = np.floor(cf).astype(np.int32); c1 = np.minimum(c0 + 1, C - 1); tc = (cf - c0).astype(np.float32)
    r0 = np.floor(rf).astype(np.int32); r1 = np.minimum(r0 + 1, R - 1); tr = (rf - r0).astype(np.float32)
    if arr.ndim == 3: tc = tc[None, :, None]; tr = tr[:, None, None]
    else: tc = tc[None, :]; tr = tr[:, None]
    top = arr[np.ix_(r0, c0)] * (1 - tc) + arr[np.ix_(r0, c1)] * tc
    bot = arr[np.ix_(r1, c0)] * (1 - tc) + arr[np.ix_(r1, c1)] * tc
    return top * (1 - tr) + bot * tr

def bake_rect(name, x0, y0, w, h, px_w, px_h, src, mask_res=None):
    """월드 rect (x0,y0,w,h) → px_w×px_h 텍스처. v 위 = +y (Blender UV 규약, 아래행 = y0).
    바깥 TEX_PAD 픽셀은 rect 밖 월드(연속). UV 는 sgk_layout.uv_pad 로 [PAD, N-PAD] 안에 넣는다."""
    P = L.TEX_PAD
    ii = (np.arange(px_w, dtype=np.float32) + 0.5 - P) / (px_w - 2 * P)
    jj = (np.arange(px_h, dtype=np.float32) + 0.5 - P) / (px_h - 2 * P)
    wx = x0 + w * ii[None, :]; wy = y0 + h * (1.0 - jj)[:, None]
    masks = _field_sample(_world_mask(), wx, wy)
    def sample(k):
        s = src[k]; n = s.shape[0]
        u = (((wx / TILE_M[k]) % 1.0) * n).astype(np.int32) % n
        v = (((wy / TILE_M[k]) % 1.0) * n).astype(np.int32) % n
        return s[n - 1 - np.broadcast_to(v, (px_h, px_w)), np.broadcast_to(u, (px_h, px_w))]
    nz = _field_sample(_world_noise(L.TILE / 6.0, 7001), wx, wy)
    f = (0.08 + nz * 0.34)[:, :, None]
    rock = sample("rock") * (1 - f) + sample("rock2") * f
    out = sample("grass")
    for c, wgt in ((sample("litter"), masks[:, :, 3]), (sample("dirt"), masks[:, :, 0]), (sample("wet"), masks[:, :, 2]), (rock, masks[:, :, 1])):
        a = wgt[:, :, None]; out = out * (1 - a) + c * a
    out = out * (0.86 + _field_sample(_world_noise(L.TILE / 22.0, 7002), wx, wy) * 0.28)[:, :, None]
    img = Image.fromarray((np.clip(out, 0, 1) * 255).astype("uint8"), "RGB")
    p = os.path.join(OUT, name + ".png"); img.save(p, optimize=True)
    return {"name": name, "x0": x0, "y0": y0, "w": w, "h": h, "px": [px_w, px_h], "bytes": os.path.getsize(p)}

def bake_terrain():
    src = _load_sources()
    made = []
    T = L.TILE
    for ty in range(L.TILES_Y):
        for tx in range(L.TILES_X):
            x0 = -L.PLAY_X + tx * T; y0 = -L.PLAY_Y + ty * T
            r = bake_rect(f"SGK_TER_{tx}{ty}", x0, y0, T, T, 1024, 1024, src); made.append(r); print(r["name"], round(r["bytes"] / 1e6, 2), "MB")
    X, Y, MX, MY = L.PLAY_X, L.PLAY_Y, L.MESH_X, L.MESH_Y
    slabs = L.wall_slabs()   # N/S 는 2장씩(2048×1024), E/W 1024×2048 → 16~20 px/m (구 2048×512 은 7.9 px/m 라 뿌옇게 늘어났다)
    for name, (x0, y0, w, h, pw, ph) in slabs.items():
        r = bake_rect(name, x0, y0, w, h, pw, ph, src, mask_res=(160, 48) if pw > ph else (48, 160)); made.append(r); print(name, round(r["bytes"] / 1e6, 2), "MB")
    json.dump({"tiles": made, "tile_m": L.TILE, "play": [L.PLAY_X, L.PLAY_Y], "mesh": [L.MESH_X, L.MESH_Y]}, open(os.path.join(OUT, "_tiles.json"), "w"), indent=1)
    return made

# ------------------------------------------------------------------ 밴드 아틀라스 (sgk_export.py plan 패스 결과)
def _infill_transparent(im, radius=(3, 9, 27)):
    """알파<128 픽셀의 RGB 를 근처 불투명 색으로 채운다 (알파 가중 블러를 반경별로 겹쳐 먼 곳까지)."""
    from PIL import ImageFilter
    a = np.asarray(im.convert("RGBA")).astype(np.float32); rgb = a[:, :, :3]; al = a[:, :, 3:4] / 255.0
    fill = rgb.copy(); have = (al[:, :, 0] >= 0.5)
    for r in radius:
        pm = Image.fromarray(np.clip(rgb * al, 0, 255).astype("uint8"), "RGB").filter(ImageFilter.GaussianBlur(r))
        am = Image.fromarray((al[:, :, 0] * 255).astype("uint8"), "L").filter(ImageFilter.GaussianBlur(r))
        pmv = np.asarray(pm).astype(np.float32); amv = np.asarray(am).astype(np.float32)[:, :, None] / 255.0
        est = pmv / np.maximum(amv, 1e-3)
        m = (~have) & (amv[:, :, 0] > 0.02)
        fill[m] = est[m]; have = have | m
    fill[~have] = fill[have].mean(axis=0) if have.any() else 0
    # 알파 블렌딩을 텍스처에 미리 굽는다: rgb·a + fill·(1−a). 엔진이 알파를 무시해도 반투명 가장자리가 검게 뜨지 않는다
    out = a.copy(); out[:, :, :3] = rgb * al + fill * (1.0 - al)
    return Image.fromarray(np.clip(out, 0, 255).astype("uint8"), "RGBA")

def bake_atlas():
    """_atlas_plan.json: 재질별 가로 전폭 밴드, 밴드 안에 소스를 세로 N회 스택. v=0 이 이미지 아래줄."""
    plan = json.load(open(os.path.join(OUT, "_atlas_plan.json"), encoding="utf-8"))
    for name, pl in plan.items():
        W, H = pl["sheet"]; sheet = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        for b in pl["bands"]:
            src = Image.open(os.path.join(OUT, b["tex"] + ".png")).convert("RGBA")
            if src.getextrema()[3][0] < 255: src = _infill_transparent(src)   # 알파 텍스처: 밴드 자기 색으로만 투명 영역을 채우고 알파를 미리 합성 (엔진이 알파를 안 씀, 2026-09-06)
            row1 = int(round(H * (1 - b["y0"]))); row0 = int(round(H * (1 - b["y1"])))   # 이미지 행 (위→아래)
            bh = row1 - row0; rep_h = max(1, bh // b["N"])
            # RGBA 를 한 번에 resize 하면 PIL 이 알파를 프리멀티플라이해 투명 영역 RGB 가 검정이 된다 → RGB/알파 따로
            tile = src.convert("RGB").resize((W, rep_h), Image.LANCZOS).convert("RGBA"); tile.putalpha(src.getchannel("A").resize((W, rep_h), Image.LANCZOS))
            y = row1 - rep_h                                   # v 증가 = 위로: 첫 반복이 밴드 아래
            k = 0
            while y >= row0 - rep_h + 1 and k < b["N"] + 1:
                sheet.paste(tile, (0, max(row0, y)) if y >= row0 else (0, row0), None) if y >= row0 else sheet.paste(tile.crop((0, row0 - y, W, rep_h)), (0, row0))
                y -= rep_h; k += 1
        p = os.path.join(OUT, pl["name"] + "_ATL.png"); sheet.save(p, optimize=True)   # pl["name"] (알파 마스터는 SGK_ 접두)
        print(f"{pl['name']}_ATL {sheet.size} {os.path.getsize(p)/1e6:.2f} MB bands={[(b['tex'], b['N']) for b in pl['bands']]}")

if __name__ == "__main__":
    what = sys.argv[1:] or ["props", "terrain"]
    if "props" in what: bake_props()
    if "terrain" in what: bake_terrain()
    if "atlas" in what: bake_atlas()
