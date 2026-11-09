# -*- coding: utf-8 -*-
r"""
sgk_collision.py — 콜리전 Part 생성 (bpy 없음). UCX 는 OVERDARE 에서 불가하므로 엔진 Part 로.

  python sgk_collision.py            → 06_OVERDARE\_collision\items_col_NNN.json (200개/청크) + collision_cov.json

지형: rect 안을 쿼드트리(16→8→4→2→1 m)로 나누고 셀마다 높이를 최소자승 평면으로 피팅.
  잔차 ≤ tol 이면 그 평면에 맞춘 **기울어진 슬랩**(두께 1 m, 상면 = 평면) 1개. tol: 보행 가능(≤45°) 0.25 m, 절벽 0.9 m.
  Part 방향: Roblox/OVERDARE Orientation (rx, ry, rz) = YXZ 오일러. yaw 0 으로 두고 법선 n(엔진 좌표)에 대해
  rz = -asin(nx), rx = atan2(nz, ny) 이면 R·(0,1,0) = n. → **Studio 프로브로 반드시 확인** (부호가 틀리면 rz 부호 반전).
프롭: placements_master.json 의 바위(높이 ≥1.2)·담장·석축·돌탑 → yaw 오리엔티드 박스. 다리는 데크 슬랩만. 정자는 통 박스(Phase 3 메모).
좌표: Blender m Z-up → 엔진 cm Y-up: X = x·100 + ENGINE_X0, Y = z·100, Z = −y·100 (L.to_engine).
"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sgk_layout as L

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "06_OVERDARE", "_collision"); os.makedirs(OUT, exist_ok=True)
DOC = os.path.join(ROOT, "05_Documentation")
THICK = 1.0; SKIN = 0.15; BATCH = 200
TOL_WALK, TOL_CLIFF = 0.4, 1.5
MIN_CELL, MAX_CELL = 2.0, 16.0
TOL_OUT, MIN_CELL_OUT = 1.5, 8.0   # 플레이 rect 밖 산벽 띠: 오차 1.5 m·최소 8 m 셀 (걷는 곳이 아니라 떨어지지만 않으면 된다)
SAMPLE = 0.5

def eng(x, y, z):
    return [round(v, 1) for v in L.to_engine(x, y, z)]   # 맵 회전(L.MAP_YAW_DEG) 포함

def part(name, pos_m, size_m, orient=(0.0, 0.0, 0.0), extra=None):
    # Material 은 반드시 Unlit: 산옥에서 투명 콜리전 1,669장이 "Basic" 인 채로 나가 핸드폰(안드로이드)에서 화면이 깨졌다 (MapService_1.lua 2026-08-30 기록)
    raw = {"Transparency": 1.0, "CanCollide": True, "CastShadow": False, "CanTouch": False, "Material": "Unlit"}
    props = {"position": eng(*pos_m), "size": [round(size_m[0] * 100, 1), round(size_m[2] * 100, 1), round(size_m[1] * 100, 1)],
             "orientation": [round(orient[0], 3), L.eng_yaw(orient[1]), round(orient[2], 3)], "anchored": True, "mobility": "Static", "raw": raw}   # YXZ 오일러: yaw 에 맵 회전만 더하면 pitch/roll 은 그대로
    if extra: props.update(extra)
    return {"className": "Part", "name": name, "props": props}

# ------------------------------------------------------------------ 지형 평면 슬랩
def _fit_plane(pts):
    """z = a x + b y + c 최소자승. 반환 (a,b,c,max_residual)."""
    n = len(pts); sx = sy = sz = sxx = syy = sxy = sxz = syz = 0.0
    for x, y, z in pts:
        sx += x; sy += y; sz += z; sxx += x * x; syy += y * y; sxy += x * y; sxz += x * z; syz += y * z
    # 정규방정식 3×3
    A = [[sxx, sxy, sx], [sxy, syy, sy], [sx, sy, n]]; B = [sxz, syz, sz]
    # 가우스 소거
    M = [A[i] + [B[i]] for i in range(3)]
    for i in range(3):
        p = max(range(i, 3), key=lambda r: abs(M[r][i])); M[i], M[p] = M[p], M[i]
        if abs(M[i][i]) < 1e-12: return None
        for r in range(3):
            if r != i:
                f = M[r][i] / M[i][i]
                for c in range(4): M[r][c] -= f * M[i][c]
    a, b, c = (M[i][3] / M[i][i] for i in range(3))
    above = max(z - (a * x + b * y + c) for x, y, z in pts)      # 지형이 평면 위로 솟은 최대
    below = max((a * x + b * y + c) - z for x, y, z in pts)      # 평면이 지형 위로 뜬 최대
    c += above                                                     # 상면을 올려 가라앉기 0 → 뜸 = above+below
    return a, b, c, above + below

def _cell_pts(x0, y0, w, h):
    pts = []; nx = max(2, int(round(w / SAMPLE)) + 1); ny = max(2, int(round(h / SAMPLE)) + 1)
    for i in range(nx):
        for j in range(ny):
            x = x0 + w * i / (nx - 1); y = y0 + h * j / (ny - 1); pts.append((x, y, L.height_at(x, y)))
    return pts

def _slab(name, x0, y0, w, h, a, b, c):
    """평면 z=ax+by+c 위 셀 → 기울어진 Part. 상면 중심 = 셀 중심의 평면점, 두께 아래로."""
    cx, cy = x0 + w / 2, y0 + h / 2; cz = a * cx + b * cy + c
    # 법선 (Blender): (-a, -b, 1) 정규화 → 엔진 (X=x, Y=z, Z=y)
    nl = math.sqrt(a * a + b * b + 1.0); nbx, nby, nbz = -a / nl, -b / nl, 1.0 / nl
    nx, ny, nz = nbx, nbz, -nby           # 엔진 축 (Z = −y, L.to_engine 과 동일 부호)
    rz = -math.degrees(math.asin(max(-1.0, min(1.0, nx))))
    rx = math.degrees(math.atan2(nz, ny))
    # 슬랩 치수: 사면 길이로 확대 + skin. 중심을 법선 반대방향으로 두께/2 내림
    sx = w * math.sqrt(1 + a * a) + SKIN; sy = h * math.sqrt(1 + b * b) + SKIN
    px, py, pz = cx - nbx * THICK / 2, cy - nby * THICK / 2, cz - nbz * THICK / 2
    return part(name, (px, py, pz), (sx, sy, THICK), (rx, 0.0, rz))

def terrain_parts():
    parts = []; stats = {"cells": 0, "by_size": {}}
    def rec(x0, y0, w, h):
        pts = _cell_pts(x0, y0, w, h)
        fit = _fit_plane(pts)
        smax = max(L.slope_deg(x, y) for x, y, _ in pts[:: max(1, len(pts) // 25)])
        tol = TOL_WALK if smax <= L.ENGINE_MAX_DEG else TOL_CLIFF
        outside = (x0 >= L.PLAY_X or x0 + w <= -L.PLAY_X or y0 >= L.PLAY_Y or y0 + h <= -L.PLAY_Y)   # 플레이 rect 밖(산벽 띠): 인스턴스 수가 fps 레버라 느슨하게
        if outside: tol = TOL_OUT
        if fit and (fit[3] <= tol or w <= (MIN_CELL_OUT if outside else MIN_CELL)):
            a, b, c, r = fit
            parts.append(_slab(f"COL_TER_{len(parts):04d}", x0, y0, w, h, a, b, c))
            stats["cells"] += 1; stats["by_size"][str(w)] = stats["by_size"].get(str(w), 0) + 1
            return
        hw, hh = w / 2, h / 2
        for dx in (0, hw):
            for dy in (0, hh):
                rec(x0 + dx, y0 + dy, hw, hh)
    # 커버 범위 = 산벽 포함 지형 메시 전체(±MESH_X × ±MESH_Y). 예전엔 플레이 rect(±80×±60)만 깔아서
    # 경계(장벽)를 넘으면 산벽 메시(콜리전 없음)를 뚫고 떨어졌다 (2026-09-07 사용자 보고). 산벽 사면은 완만해 큰 셀로 끝난다.
    CX, CY = L.MESH_X, L.MESH_Y
    nx, ny = math.ceil(2 * CX / MAX_CELL), math.ceil(2 * CY / MAX_CELL)
    for i in range(nx):
        for j in range(ny):
            rec(-CX + i * MAX_CELL, -CY + j * MAX_CELL, MAX_CELL, MAX_CELL)
    # (세계 끝 차단벽 4장은 뺐다: 260 m × 45 m 투명 Part 가 모바일 미리보기에서 흰 리본으로 그려지고 길을 막았다, 2026-09-07. 산벽 띠 슬랩만으로 떨어지진 않는다)
    return parts, stats

# ------------------------------------------------------------------ 프롭 박스
def prop_parts():
    pm = json.load(open(os.path.join(DOC, "placements_master.json"), encoding="utf-8"))
    parts = []
    for r in pm["instances"]:
        nm = r["name"]; d = r["dims"]
        if nm.startswith("SGK_Rock") and d[2] >= 0.5:      # 모든 바위·너럭돌 (1.2 m 이상만 막던 것을 0.5 m 로, 2026-09-07 "물체 전부 못 지나가게")
            parts.append(part(f"COL_{nm}", (r["x"], r["y"], r["z"] + d[2] / 2), (d[0] * 0.85, d[1] * 0.85, d[2] * 0.95), (0.0, r["yaw"], 0.0)))
        elif nm.startswith(("SGK_Pine", "SGK_Und_SmallPine", "SGK_Sapling")) or r["master"].startswith(("MST_PINE", "MST_SAPLING")):
            # 나무 줄기: 밑동 기준 4 m 높이 기둥 박스 (수관은 통과). 반지름은 수종별 (XL 0.55, L 0.45, M 0.35, S 0.25, 묘목 0.12 m)
            m = r["master"]; rad = 0.55 if "XL" in m else 0.45 if "_L" in m else 0.35 if "_M" in m else 0.25 if "_S" in m else 0.12
            rad *= r.get("scale", 1.0); hgt = min(4.0, d[2] * 0.4)
            parts.append(part(f"COL_{nm}", (r["x"], r["y"], r["z"] + hgt / 2), (2 * rad, 2 * rad, hgt), (0.0, 0.0, 0.0)))
        elif r["master"] in ("MST_BOULDER_A", "MST_BOULDER_B", "MST_STUMP"):
            parts.append(part(f"COL_{nm}", (r["x"], r["y"], r["z"] + d[2] / 2), (d[0] * 0.8, d[1] * 0.8, d[2] * 0.95), (0.0, r["yaw"], 0.0)))
        elif r["master"] == "MST_DEADTRUNK":
            parts.append(part(f"COL_{nm}", (r["x"], r["y"], r["z"] + d[2] / 2), (d[0] * 0.7, d[1] * 0.7, d[2]), (0.0, r["yaw"], 0.0)))
        elif nm.startswith("SGK_Wall"):
            parts.append(part(f"COL_{nm}", (r["x"], r["y"], r["z"] + d[2] / 2), (d[0], max(d[1], 0.5), d[2]), (0.0, r["yaw"], 0.0)))
        elif nm == "SGK_Pavilion":
            parts.append(part("COL_Pavilion", (r["x"], r["y"], r["z"] + d[2] / 2), (d[0], d[1], d[2]), (0.0, r["yaw"], 0.0)))
        elif nm == "SGK_Bridge":
            parts.append(part("COL_BridgeDeck", (r["x"], r["y"], r["z"] + L.BRIDGE_DECK_TOP - 0.15), (1.6, 5.4, 0.3), (0.0, 0.0, 0.0)))   # 슬랩 상면 = 데크 상면
    # 석축 2 + 돌탑
    man = json.load(open(os.path.join(ROOT, "06_OVERDARE", "manifest.json"), encoding="utf-8"))
    for kind, (x, y), yaw, (sx, sy, sz) in L.structures():
        zg = L.height_at(x, y)
        tname = f"STA_Terrace_{'N' if y > 0 else 'S'}"
        if kind in ("PAVILION", "TERRACE") and tname in man:      # 씬에서 지운 석축(STA_Terrace_S)은 콜리전도 없음
            parts.append(part(f"COL_Terrace_{'N' if y > 0 else 'S'}", (x, y, zg - 0.3 + 0.75), (sx, sy, 1.5)))
        if kind == "TERRACE":
            cz = zg + 1.2 if tname in man else zg                   # 석축이 없으면 돌탑은 지면에
            parts.append(part("COL_Cairn", (x, y, cz + 0.8), (0.9, 0.9, 1.6)))
    return parts

# ------------------------------------------------------------------ 커버리지 검증 (슬랩 상면 vs 지형)
def coverage(parts):
    """1 m 격자에서 평면 슬랩 상면 높이 − height_at ∈ [−0.05, +0.35] 비율."""
    slabs = []
    for p in parts:
        if not p["name"].startswith("COL_TER_"): continue
        slabs.append(p)
    # 슬랩 → 다시 평면으로 (위치·방향에서 복원하지 않고 생성 시 저장한 평면 사용이 정확하므로 재계산 대신 셀 재피팅)
    return None

def main():
    tp, stats = terrain_parts(); pp = prop_parts()
    allp = tp + pp
    for f in os.listdir(OUT):
        if f.startswith("items_col_"): os.remove(os.path.join(OUT, f))
    for k, i in enumerate(range(0, len(allp), BATCH)):
        json.dump(allp[i:i + BATCH], open(os.path.join(OUT, f"items_col_{k:03d}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    rep = {"terrain_parts": len(tp), "prop_parts": len(pp), "total": len(allp), "cells_by_size": stats["by_size"], "chunks": k + 1,
           "tol": [TOL_WALK, TOL_CLIFF], "thick": THICK}
    json.dump(rep, open(os.path.join(DOC, "collision_report.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1))

if __name__ == "__main__":
    main()
