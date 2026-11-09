# -*- coding: utf-8 -*-
r"""
sgk_verify.py — 레이아웃 수치 검증 (bpy 없음, 시스템 파이썬).  결과 → 05_Documentation\.

    python sgk_verify.py            # 전부
    python sgk_verify.py walk       # 보행성 + 연결성분 + 히트맵
    python sgk_verify.py travel     # 레인별 이동시간 (Dijkstra)
    python sgk_verify.py sight      # 시야선
    python sgk_verify.py spawn      # 스폰 디스크 평탄도
    python sgk_verify.py zone       # 점령 구역 몬테카를로 (CaptureServer.pickSpot 재현)

판정 기준은 sgk_layout 상수(WALK_DEG 38 / ENGINE_MAX_DEG 45)와 계획서 §검증.
"""
import os, sys, json, math, heapq, random, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sgk_layout as L

DOC = os.path.join(os.path.dirname(HERE), "05_Documentation")
os.makedirs(DOC, exist_ok=True)
CELL = 0.5
X0, X1, Y0, Y1 = -L.PLAY_X, L.PLAY_X, -L.PLAY_Y, L.PLAY_Y
NX = int(round((X1 - X0) / CELL)) + 1
NY = int(round((Y1 - Y0) / CELL)) + 1

_H = None
def heights():
    """0.5 m 격자 높이 (캐시)."""
    global _H
    if _H is None:
        t = time.time()
        _H = [[L.height_at(X0 + i * CELL, Y0 + j * CELL) for j in range(NY)] for i in range(NX)]
        print(f"heights {NX}x{NY} in {time.time()-t:.1f}s")
    return _H

def ij(x, y):
    return int(round((x - X0) / CELL)), int(round((y - Y0) / CELL))

def xy(i, j):
    return X0 + i * CELL, Y0 + j * CELL

def cell_slope_deg(i, j):
    """4방향 이웃(0.5 m) 높이차의 최대 경사 — 캡슐이 느끼는 국소 경사."""
    H = heights(); h = H[i][j]; best = 0.0
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        a, b = i + di, j + dj
        if 0 <= a < NX and 0 <= b < NY:
            best = max(best, abs(H[a][b] - h) / CELL)
    return math.degrees(math.atan(best))

_S = None
def slopes():
    global _S
    if _S is None:
        heights()
        _S = [[cell_slope_deg(i, j) for j in range(NY)] for i in range(NX)]
    return _S

def blockers(with_props=True):
    """구조물(+ 배치된 바위 1.2 m 이상)을 XY 사각형 장애물로 (kind, cx, cy, yaw, sx, sy, sz)."""
    out = []
    for kind, (x, y), yaw, (sx, sy, sz) in L.structures():
        if kind == "BRIDGE":
            continue
        out.append((kind, x, y, yaw, sx, sy, sz))
    pm = os.path.join(DOC, "placements_master.json")
    if with_props and os.path.exists(pm):
        for r in json.load(open(pm, encoding="utf-8"))["instances"]:
            if r["name"].startswith("SGK_Rock") and r["dims"][2] >= 1.2:
                out.append(("ROCK", r["x"], r["y"], r["yaw"], r["dims"][0] * 0.8, r["dims"][1] * 0.8, r["dims"][2]))
    return out

def in_blocker(x, y, bl):
    kind, cx, cy, yaw, sx, sy, sz = bl
    c, s = math.cos(-math.radians(yaw)), math.sin(-math.radians(yaw))
    dx, dy = x - cx, y - cy
    lx, ly = dx * c - dy * s, dx * s + dy * c
    return abs(lx) <= sx * 0.5 + 0.3 and abs(ly) <= sy * 0.5 + 0.3

# ------------------------------------------------------------------ 1. 보행성
def walk_grid():
    S = slopes(); H = heights(); bls = blockers()
    W = [[0] * NY for _ in range(NX)]     # 0 blocked, 1 scramble(38-45), 2 walk
    for i in range(NX):
        for j in range(NY):
            s = S[i][j]
            x, y = xy(i, j)
            if any(in_blocker(x, y, b) for b in bls):
                W[i][j] = 0; continue
            # 수면 아래(깊이 >1.2)도 통행 가능 취급 (계류 깊이 1.8 → 걷기+점프)
            W[i][j] = 2 if s <= L.WALK_DEG else (1 if s <= L.ENGINE_MAX_DEG else 0)
    return W

def components(W):
    comp = [[-1] * NY for _ in range(NX)]; sizes = []
    for i in range(NX):
        for j in range(NY):
            if W[i][j] == 0 or comp[i][j] >= 0:
                continue
            cid = len(sizes); stack = [(i, j)]; comp[i][j] = cid; n = 0
            while stack:
                a, b = stack.pop(); n += 1
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    c, d = a + da, b + db
                    if 0 <= c < NX and 0 <= d < NY and W[c][d] > 0 and comp[c][d] < 0:
                        comp[c][d] = cid; stack.append((c, d))
            sizes.append(n)
    return comp, sizes

def snap_walkable(W, x, y, rmax=6.0):
    i0, j0 = ij(x, y); best = None
    r = int(rmax / CELL)
    for di in range(-r, r + 1):
        for dj in range(-r, r + 1):
            a, b = i0 + di, j0 + dj
            if 0 <= a < NX and 0 <= b < NY and W[a][b] > 0:
                d = math.hypot(di, dj) * CELL
                if best is None or d < best[0]:
                    best = (d, a, b)
    return best

def run_walk(png=True):
    t = time.time()
    W = walk_grid(); comp, sizes = components(W)
    total = NX * NY
    cnt = {0: 0, 1: 0, 2: 0}
    for i in range(NX):
        for j in range(NY):
            cnt[W[i][j]] += 1
    big = max(range(len(sizes)), key=lambda k: sizes[k]) if sizes else -1
    kp = {}
    ok = True
    for name, (x, y) in L.key_points().items():
        sn = snap_walkable(W, x, y)
        if sn is None:
            kp[name] = {"reach": False}; ok = False; continue
        d, a, b = sn
        kp[name] = {"comp": comp[a][b], "snap_m": round(d, 2), "in_main": comp[a][b] == big}
        ok &= comp[a][b] == big
    # 경사 분포
    S = slopes(); bands = {}
    for i in range(NX):
        for j in range(NY):
            b = int(S[i][j] // 10) * 10; bands[b] = bands.get(b, 0) + 1
    band42_48 = sum(1 for i in range(NX) for j in range(NY) if 42.0 <= S[i][j] <= 48.0)
    rep = {
        "cells": total, "walk_pct": round(100 * cnt[2] / total, 1), "scramble_pct": round(100 * cnt[1] / total, 1),
        "blocked_pct": round(100 * cnt[0] / total, 1), "components": len(sizes),
        "main_component_pct": round(100 * sizes[big] / max(1, cnt[1] + cnt[2]), 1) if sizes else 0,
        "band_42_48_pct": round(100 * band42_48 / total, 2),
        "slope_bands_pct": {f"{k}-{k+10}": round(100 * v / total, 1) for k, v in sorted(bands.items())},
        "key_points": kp, "PASS": ok and len(sizes) >= 1 and (sizes[big] / max(1, cnt[1] + cnt[2])) >= 0.95,
        "seconds": round(time.time() - t, 1),
    }
    json.dump(rep, open(os.path.join(DOC, "walkability.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != "key_points"}, ensure_ascii=False, indent=1))
    bad = [k for k, v in kp.items() if not v.get("in_main")]
    print("key points NOT in main component:", bad or "none")
    if png:
        heatmap(W, comp, big)
    return rep

def heatmap(W, comp, big):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("PIL 없음 — 히트맵 생략"); return
    sc = 4
    im = Image.new("RGB", (NX * sc, NY * sc), (20, 20, 20)); px = im.load()
    for i in range(NX):
        for j in range(NY):
            w = W[i][j]
            lm = L.lane_mask(*xy(i, j)) if (i % 2 == 0 and j % 2 == 0) else None
            if w == 0:
                c = (60, 60, 60)
            elif w == 1:
                c = (230, 140, 40)
            else:
                c = (70, 160, 70) if comp[i][j] == big else (200, 60, 200)
            if lm and w == 2:
                if lm["stream"] > 0.5: c = (60, 110, 200)
                elif lm["ramp"] > 0.5: c = (240, 200, 90)
                elif lm["crest"] > 0.5: c = (230, 230, 120)
                elif lm["path"] > 0.5: c = (150, 110, 70)
                elif lm["spawn"] > 0.5: c = (200, 90, 90)
            for a in range(sc):
                for b in range(sc):
                    px[i * sc + a, (NY - 1 - j) * sc + b] = c
    d = ImageDraw.Draw(im)
    for name, (x, y) in L.key_points().items():
        i, j = ij(x, y); d.ellipse([i * sc - 5, (NY - 1 - j) * sc - 5, i * sc + 5, (NY - 1 - j) * sc + 5], outline=(255, 255, 255), width=2)
    p = os.path.join(os.path.dirname(HERE), "04_Previews", "p1_walkability.png"); im.save(p); print("heatmap", p)

# ------------------------------------------------------------------ 2. 이동시간
def dijkstra(W, S, src, speed):
    INF = float("inf"); dist = [[INF] * NY for _ in range(NX)]
    si, sj = src; dist[si][sj] = 0.0; pq = [(0.0, si, sj)]
    nbrs = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
    while pq:
        d, i, j = heapq.heappop(pq)
        if d > dist[i][j]:
            continue
        for di, dj, m in nbrs:
            a, b = i + di, j + dj
            if not (0 <= a < NX and 0 <= b < NY) or W[a][b] == 0:
                continue
            f = max(0.5, 1.0 - S[a][b] / 90.0) * (0.75 if W[a][b] == 1 else 1.0)
            nd = d + (m * CELL) / (speed * f)
            if nd < dist[a][b]:
                dist[a][b] = nd; heapq.heappush(pq, (nd, a, b))
    return dist

def run_travel():
    W = walk_grid(); S = slopes(); kp = L.key_points()
    pairs = [("spawn_W", "bowl"), ("spawn_W", "spawn_E"), ("spawn_W", "crest_tip_NW"), ("spawn_W", "crest_tip_SE"),
             ("spawn_W", "ford_W"), ("spawn_W", "R1_top_W"), ("spawn_W", "strip_S"), ("spawn_W", "glade_S"),
             ("crest_tip_NW", "bowl"), ("spawn_E", "bowl"), ("spawn_E", "spawn_W"),
             ("R1_top_W", "crest_tip_NW"), ("R1_top_W", "R2_top_W"), ("R2_top_W", "R3_top_W"), ("R3_top_W", "crest_tip_NW")]
    out = {}
    for spd_name, spd in (("walk", 7.0 * L.MOVE_SCALE), ("sprint", 11.9 * L.MOVE_SCALE)):
        cache = {}
        for a, b in pairs:
            if a not in cache:
                sn = snap_walkable(W, *kp[a]); cache[a] = dijkstra(W, S, (sn[1], sn[2]), spd)
            sb = snap_walkable(W, *kp[b])
            d = cache[a][sb[1]][sb[2]]
            out.setdefault(f"{a}->{b}", {})[spd_name] = round(d, 1) if d != float("inf") else None
    json.dump({"moveScale": L.MOVE_SCALE, "seconds": out}, open(os.path.join(DOC, "travel.json"), "w"), indent=1)
    for k, v in out.items():
        print(f"{k:28s} walk {v['walk']!s:>6}s  sprint {v['sprint']!s:>6}s")
    return out

# ------------------------------------------------------------------ 3. 시야선
def los_clear(ax, ay, az, bx, by, bz, bls, step=0.5):
    d = math.hypot(bx - ax, by - ay); n = max(2, int(d / step))
    for k in range(1, n):
        t = k / n; x, y, z = L.lerp(ax, bx, t), L.lerp(ay, by, t), L.lerp(az, bz, t)
        if L.height_at(x, y) + 0.25 > z:
            return False
        for b in bls:
            if in_blocker(x, y, b) and z < L.height_at(b[1], b[2]) + b[6]:
                return False
    return True

def run_sight(limit=55.0):
    bls = blockers(); kp = L.key_points(); lanes = L.lanes()
    sources = {"spawn_W": kp["spawn_W"], "spawn_W_N": (kp["spawn_W"][0], kp["spawn_W"][1] + 10), "spawn_W_S": (kp["spawn_W"][0], kp["spawn_W"][1] - 10),
               "crest_tip_NW": kp["crest_tip_NW"], "crest_mid_NW": kp["crest_mid_NW"], "R2_top_W": kp["R2_top_W"],
               "path_W_mid": kp["path_W_mid"], "strip_N": kp["strip_N"], "bowl": kp["bowl"], "ford_W": kp["ford_W"], "glade_S": kp["glade_S"]}
    targets = []
    for name, pts in lanes.items():
        for a, b in zip(pts, pts[1:]):
            n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 5.0))
            for k in range(n):
                t = k / n; targets.append((name, L.lerp(a[0], b[0], t), L.lerp(a[1], b[1], t)))
    rep = {}; worst = []
    lane_names = sorted(set(t[0] for t in targets))
    for sname, (sx, sy) in sources.items():
        sz = L.height_at(sx, sy) + 1.7; per = {ln: 0.0 for ln in lane_names}; n_long = 0
        for lname, tx, ty in targets:
            d = math.hypot(tx - sx, ty - sy)
            if d < 3.0:
                continue
            tz = L.height_at(tx, ty) + 1.0
            if los_clear(sx, sy, sz, tx, ty, tz, bls):
                per[lname] = max(per[lname], d)
                if d > limit:
                    n_long += 1
        maxd = max(per.values())
        rep[sname] = {"max_clear_m": round(maxd, 1), "per_lane": {k: round(v, 0) for k, v in per.items()}, "targets_over_limit": n_long}
        if maxd > limit:
            worst.append(sname)
    md = ["# 시야선 (지형 + 구조물 그레이박스만, 나무 없음)", "", f"기준: 하드 차폐 없는 직선 > {limit} m 이면 FAIL 후보. 표는 시점→표적 레인별 최장 개방거리(m)", ""]
    md += ["| 시점 | " + " | ".join(lane_names) + " | 55 m 초과 표적 수 |", "|---|" + "---|" * len(lane_names) + "---|"]
    for k, v in rep.items():
        md.append(f"| {k} | " + " | ".join(f"{int(v['per_lane'][ln])}" for ln in lane_names) + f" | {v['targets_over_limit']} |")
    open(os.path.join(DOC, "sightlines.md"), "w", encoding="utf-8").write("\n".join(md))
    print(f"{'source':14s} " + " ".join(f"{ln:>9s}" for ln in lane_names) + "  over55")
    for k, v in rep.items():
        print(f"{k:14s} " + " ".join(f"{int(v['per_lane'][ln]):9d}" for ln in lane_names) + f"  {v['targets_over_limit']}")
    print("SOURCES OVER LIMIT:", worst or "none")
    return rep

# ------------------------------------------------------------------ 4. 스폰 디스크
def run_spawn():
    rep = {}
    for team, (cx, cy) in L.spawn_points().items():
        zs = []; smax = 0.0
        for dx in range(-11, 12):
            for dy in range(-11, 12):
                if dx * dx + dy * dy <= 121:          # r ≤ 11 (스폰 산개 최대 11 m)
                    x, y = cx + dx, cy + dy
                    zs.append(L.height_rel(x, y)); smax = max(smax, L.slope_deg(x, y, e=0.5))
        rep[team] = {"rel_z_range": round(max(zs) - min(zs), 2), "slope_max_deg": round(smax, 1),
                     "PASS": (max(zs) - min(zs)) <= 0.6 and smax <= 5.0}
    print(json.dumps(rep, indent=1)); return rep

# ------------------------------------------------------------------ 5. 점령 구역 MC (CaptureServer.pickSpot 재현)
def run_zone(n=400, seed=7):
    random.seed(seed)
    minX, maxX = -L.PLAY_X * 100, L.PLAY_X * 100; minZ, maxZ = -L.PLAY_Y * 100, L.PLAY_Y * 100
    mx = min(L.EDGE_MARGIN_CM, (maxX - minX) * 0.25); mz = min(L.EDGE_MARGIN_CM, (maxZ - minZ) * 0.25)
    sp = [(p[0] * 100, p[1] * 100) for p in L.spawn_points().values()]
    S = slopes()
    stats = {"draws": n, "pass": 0, "fail_spawn": 0, "slope_gt40": 0, "in_stream": 0, "on_crest": 0, "cliff_edge_near": 0, "twenty_fail_runs": 0}
    r_cells = int(L.ZONE_RADIUS_CM / 100 / CELL)
    consecutive = 0
    for _ in range(n):
        X = random.uniform(minX + mx, maxX - mx); Z = random.uniform(minZ + mz, maxZ - mz)
        if any(math.hypot(X - a, Z - b) < L.MIN_SPAWN_DIST_CM for a, b in sp):
            stats["fail_spawn"] += 1; consecutive += 1
            if consecutive >= 20:
                stats["twenty_fail_runs"] += 1; consecutive = 0
            continue
        consecutive = 0; stats["pass"] += 1
        x, y = X / 100, Z / 100; lm = L.lane_mask(x, y)
        steep = L.slope_deg(x, y) > 40
        if steep: stats["slope_gt40"] += 1
        if lm["stream"] > 0.5: stats["in_stream"] += 1
        if steep and lm["stream"] <= 0.5 and lm["ford"] <= 0.5: stats["steep_dry"] = stats.get("steep_dry", 0) + 1   # 절벽/사면 위 (진짜 문제)
        if lm["crest"] > 0.5: stats["on_crest"] += 1
        # 반경 9 m 안에 5 m 넘는 낙차가 있는가 (|Δy|≤10 판정과 층 분리 위험)
        i0, j0 = ij(x, y); zc = L.height_at(x, y); near = False
        for di in range(-r_cells, r_cells + 1, 2):
            for dj in range(-r_cells, r_cells + 1, 2):
                a, b = i0 + di, j0 + dj
                if 0 <= a < NX and 0 <= b < NY and (di * di + dj * dj) * CELL * CELL <= 81 and abs(heights()[a][b] - zc) > 5.0:
                    near = True; break
            if near: break
        if near: stats["cliff_edge_near"] += 1
    p = stats["pass"]
    rep = {**stats, "pass_pct": round(100 * p / n, 1), "slope_gt40_pct_of_pass": round(100 * stats["slope_gt40"] / max(1, p), 1),
           "in_stream_pct": round(100 * stats["in_stream"] / max(1, p), 1), "on_crest_pct": round(100 * stats["on_crest"] / max(1, p), 1),
           "cliff_edge_near_pct": round(100 * stats["cliff_edge_near"] / max(1, p), 1),
           "params": {"zoneRadius": L.ZONE_RADIUS_CM, "minSpawnDist": L.MIN_SPAWN_DIST_CM, "edgeMargin": L.EDGE_MARGIN_CM, "margin_used": (mx, mz)}}
    rep["steep_dry_pct_of_pass"] = round(100 * stats.get("steep_dry", 0) / max(1, p), 1)
    rep["PASS"] = rep["pass_pct"] >= 60 and rep["steep_dry_pct_of_pass"] <= 8 and stats["twenty_fail_runs"] == 0
    json.dump(rep, open(os.path.join(DOC, "zone_mc.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1)); return rep

if __name__ == "__main__":
    what = sys.argv[1:] or ["walk", "travel", "sight", "spawn", "zone"]
    for w in what:
        print(f"\n===== {w}")
        {"walk": run_walk, "travel": run_travel, "sight": run_sight, "spawn": run_spawn, "zone": run_zone}[w]()
