# -*- coding: utf-8 -*-
"""
sgk_layout.py — JSN_Sangok2 ("sgk") 지형 정의. **bpy 없음, 순수 수학.**

이 파일 하나가 지형의 진실이다. 재질(blend_at)·스캐터·콜리전·보행성·텍스처 베이크가
전부 여기의 height_at / lane_mask 를 읽는다. Blender 안(sgk_live)과 밖(PIL 베이크, 검증)
모두에서 그대로 import 한다.

좌표: Blender m, Z-up, +Y 북, 원점 = 맵 중심. 플레이 rect |x|≤80, |y|≤60. 메시 |x|≤110, |y|≤90.
180° 점대칭: 서쪽 절반에 정의한 모든 프리미티브 P(x,y) 는 P(-x,-y) 에도 적용된다 (sym()).

합성 순서 (height_rel):
  1) 가산   : 능선(ridge) + 북측 띠(strip) + 중앙 분지(bowl) + 미세 기복(noise × (1-flat))
  2) 절삭   : 스폰 디스크 / 램프 R1·R2·R3·T / 개활지 → lerp(h, target, mask)
  3) 계류   : h -= 도랑 단면 (도섭 구간은 얕고 완만)
  4) 산벽   : 외곽 +30 m
그 뒤 z_floor(x) (동쪽으로 2 m 기울기) 를 더해 절대 z 가 된다.

숫자를 바꿀 땐 이 파일의 상수/테이블만 건드린다. 검증(sgk_verify)이 PASS 를 찍기 전엔 렌더하지 않는다.
"""
import math

# ------------------------------------------------------------------ 프레임 상수
PLAY_X, PLAY_Y = 80.0, 60.0          # 플레이 rect 반폭
MESH_X, MESH_Y = 130.0, 110.0        # 지형 메시 반폭 (산벽 포함, rect 밖 50 m)
GRID = 0.5                           # 코어 격자 (m)
TILE = 40.0                          # 익스포트 타일 한 변 (m) → 4×3
TILES_X, TILES_Y = 4, 3
TEX_PAD = 8                          # 지형·산벽 텍스처 가장자리 패딩(px). 바깥 PAD 픽셀은 rect 밖 월드를 이어서 굽고, UV 는 [PAD, N-PAD] 안으로 넣는다 → 타일 이음선(wrap/밉맵 번짐) 방지
def uv_pad(t, n):
    """rect 내 정규화 좌표 t(0..1) → 패딩 안쪽 UV. n = 그 축 텍스처 px."""
    return (TEX_PAD + t * (n - 2 * TEX_PAD)) / n
def wall_slabs():
    """산벽 익스포트 슬랩: 이름 → (x0, y0, w, h, px_w, px_h). 텍스처(sgk_texbake)와 메시 UV(sgk_export)가 같은 표를 쓴다."""
    X, Y, MX, MY = PLAY_X, PLAY_Y, MESH_X, MESH_Y
    return {"SGK_WALL_N1": (-MX, Y, MX, MY - Y, 2048, 1024), "SGK_WALL_N2": (0.0, Y, MX, MY - Y, 2048, 1024),
            "SGK_WALL_S1": (-MX, -MY, MX, MY - Y, 2048, 1024), "SGK_WALL_S2": (0.0, -MY, MX, MY - Y, 2048, 1024),
            "SGK_WALL_E": (X, -Y, MX - X, 2 * Y, 1024, 2048), "SGK_WALL_W": (-MX, -Y, MX - X, 2 * Y, 1024, 2048)}
BRIDGE_DECK_TOP = 1.75               # MST_BRIDGE(투죽위교) 바닥피벗 기준 데크 상면 높이(m) — 배치·콜리전 공통
WALL_RISE = 20.0                    # 외곽 산벽 높이 (32 → 20, 2026-09-05. 9 까지 내려봤더니 물이 없어 보여 20 으로 복귀. 최대 30°, 평균 23°)
WALL_RUN = 48.0                      # rect 가장자리에서 이 거리(m) 동안 상승 → 최대 45°, 평균 34° (54° 돌담처럼 보이던 것 수정)
FLOOR_TILT = -0.017                  # z_floor = FLOOR_TILT * x  (서→동 2.7 m 하강)

# 엔진 변환 (cm, Y-up).  X = x*100 + ENGINE_X0, Y = z*100, Z = −y*100 (오른손 유지), yaw = +deg(rot_z)  [2026-09-06 부호 수정]
ENGINE_X0 = -30000.0    # 2026-09-07: −1000 m 자리는 모바일 렌더러가 ±1 km 밖을 안 그려 X<−1000 m 로 넘어가면 세상이 잘렸다 → 원래 X 로 복귀, 대신 Z 로 −400 m 이동
ENGINE_Z0 = -40000.0    # 산옥(Z −159~135 m)·로비와 남북 분리. SGK Z 범위 −512~−288 m

# 게임 파라미터 (MapService sgk 항목)
ZONE_RADIUS_CM = 1150   # 9 → 11.5 m (2026-09-07 "점령지 약간만 더 크게")
MIN_SPAWN_DIST_CM = 3500
EDGE_MARGIN_CM = 2500
MOVE_SCALE = 0.85

# 경사 규칙 (검증이 이 값으로 판정)
WALK_DEG, ENGINE_MAX_DEG, BLOCK_DEG = 38.0, 45.0, 50.0

# ------------------------------------------------------------------ 기본 수학
def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v

def lerp(a, b, t):
    return a + (b - a) * t

def smoothstep(t):
    t = clamp(t)
    return t * t * (3.0 - 2.0 * t)

def soft_edge(d, width):
    """d = 영역 경계까지의 부호거리(안쪽 음수). 안쪽 1 → 경계에서 width 만큼 바깥까지 **선형** 0.

    smoothstep 을 쓰면 블렌드가 곡면이 되어 콜리전 평면 슬랩이 2 m 셀로 쪼개진다(2,300개).
    선형이면 경사 = dz/width 로 단순해지고 4~8 m 셀 하나로 덮인다. (경사 계산식도 1.5배 없이 dz/width)"""
    if width <= 0.0:
        return 1.0 if d <= 0.0 else 0.0
    return 1.0 - clamp(d / width)

def seg_param(px, py, ax, ay, bx, by):
    """점 P 를 선분 AB 에 투영. (t 0..1, 수직거리, 부호: 좌+ 우-)"""
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy
    if L2 < 1e-9:
        return 0.0, math.hypot(px - ax, py - ay), 0.0
    t = ((px - ax) * vx + (py - ay) * vy) / L2
    tc = clamp(t)
    qx, qy = ax + vx * tc, ay + vy * tc
    d = math.hypot(px - qx, py - qy)
    side = vx * (py - ay) - vy * (px - ax)   # 외적: +면 진행방향 왼쪽
    return t, d, (1.0 if side >= 0 else -1.0)

def polyline_nearest(px, py, pts):
    """폴리라인에서 가장 가까운 점. (거리, 전체 파라미터 s 0..1, 좌우 부호, 세그먼트 index)"""
    best = None
    lens = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    total = sum(lens) or 1.0
    acc = 0.0
    for i in range(len(pts) - 1):
        t, d, side = seg_param(px, py, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
        s = (acc + clamp(t) * lens[i]) / total
        if best is None or d < best[0]:
            best = (d, s, side, i)
        acc += lens[i]
    return best

def rect_mask(px, py, ax, ay, bx, by, half_w, blend, cap=1.0):
    """A→B 축을 따르는 회전 직사각형(폭 2·half_w). 끝은 cap 만큼 연장. 반환 (mask 0..1, t 0..1)."""
    vx, vy = bx - ax, by - ay
    L = math.hypot(vx, vy)
    if L < 1e-9:
        return 0.0, 0.0
    ux, uy = vx / L, vy / L
    rx, ry = px - ax, py - ay
    along = rx * ux + ry * uy
    perp = abs(-rx * uy + ry * ux)
    over = max(0.0, -cap - along, along - L - cap)
    d_out = math.hypot(max(0.0, perp - half_w), over)
    return soft_edge(d_out, blend), clamp(along / L)

def disc_mask(px, py, cx, cy, r, blend):
    return soft_edge(math.hypot(px - cx, py - cy) - r, blend)

def box_mask(px, py, x0, x1, y0, y1, blend):
    dx = max(x0 - px, px - x1, 0.0)
    dy = max(y0 - py, py - y1, 0.0)
    inside = (x0 <= px <= x1) and (y0 <= py <= y1)
    d = -min(px - x0, x1 - px, py - y0, y1 - py) if inside else math.hypot(dx, dy)
    return soft_edge(d, blend)

def z_floor(x):
    return FLOOR_TILT * x

# ------------------------------------------------------------------ 레이아웃 테이블 (서쪽 절반)
# 능선 (북 지릉, 서팀). 마루 폴리라인과 마루 높이(바닥 기준)
CREST = [(-48.0, 34.0, 11.0), (-40.0, 30.0, 10.0), (-26.0, 21.5, 8.5), (-14.0, 16.0, 7.2)]
CREST_HALF_W = 3.0                   # 마루 평탄 반폭 (폭 6)
CLIFF_FRONT_DEG = 47.0               # 계류(남서) 쪽 사면 (60 → 47, 2026-09-05 '절벽 완만하게'. 45° 보행 한계보다 급해 등반은 여전히 차단)
CLIFF_BACK_DEG = 47.0                # 뒷면(북동) 사면 (56 → 47) (50°였을 때 구역 MC 절벽 착지 10.6% → 발자국 축소)
CREST_UNDULATION = (-36.0, 26.8, 1.2, 5.0)   # (x, y, +높이, 반경): 마루 직선 끊기 (R2·R3 착지점 사이, 최대 경사 ≈20°)

# 램프 = 절삭 (p0, z0) → (p1, z1), 반폭, 가장자리 블렌드
RAMPS = {
    "R1": ((-67.0, 25.0, 0.3), (-48.0, 34.0, 11.0), 4.0, 1.5),   # 자기편 진입 27° (길이 21, +10.7). 발치는 바닥 높이여야 한다
    # 램프 끝 = 마루 가장자리(폴리라인에서 3 m 바깥). 마루 평탄부 안으로 들어가면 마루를 깎아 노치가 생긴다.
    "R2": ((-27.0, 13.5, 1.0), (-42.8, 28.1, 10.0), 1.5, 1.0),   # 남서 사면을 비스듬히 오르는 선반 23° (길이 21.5, +9)
    "R3": ((-20.0, 33.0, 1.5), (-30.4, 27.7, 9.1), 2.5, 1.5),    # 뒷면을 비스듬히 오름 33° (길이 11.7, +7.6)
    "T":  ((-14.0, 16.0, 7.2), (-6.5, 6.5, 0.3), 2.0, 1.2),      # 끝단 계단 30° (길이 12.1, -6.9)
}

SPAWN_W = (-63.0, -4.0)              # 서 스폰 (동 = 점대칭)
SPAWN_R, SPAWN_Z, SPAWN_BLEND = 12.0, 0.5, 4.0    # smoothstep 최대 기울기 = 1.5·dz/blend → 24°. 높으면 둔덕 너머가 보인다

BOWL = (0.0, 0.0, 15.0, 0.0, 5.0)     # 높이차 0 (마스크만 사용; 콜리전 모서리 절감)   # 중앙 분지 (cx, cy, r, dz, soft)

# 둔덕 (가산 plateau, 서쪽 정의 + 점대칭). 바닥 레벨 장거리 시야를 끊는 지형 엄폐. (cx, cy, r, +h, soft) — 경사 = 1.5·h/soft
KNOLLS_W = [
    (-20.0, -4.0, 6.5, 4.0, 8.5),    # 계류 남안 중간: 스폰↔스폰 계류 회랑 차단 (미러 = 북안 (20,4)), 경사 ≤35°
    (-50.0, -34.0, 6.0, 2.8, 6.0),   # 스폰 남동: 스폰→개활지/숲길 직선 차단
    (-34.0, -18.0, 6.0, 2.8, 6.0),   # 숲길과 계류 사이
    (-9.0, -15.0, 5.5, 3.0, 6.5),    # 남 개활지 입구 서측: SW→SE 대각 회랑 + 숲길↔숲길 직선 차단 (미러 = 북 개활지 입구 동측)
    (-46.0, -11.0, 7.0, 3.5, 7.5),   # 스폰 정면 둔덕: 스폰→적 마당 남측 직선 차단 (스폰 캠핑 방지)
]

GLADE_S = ((0.0, -36.0, 0.3), (0.0, -14.0, 0.3), 6.0, 5.0)   # 평탄 +0.3 (2 m 경사는 콜리전 모서리만 늘림)   # 남 개활지 (p0,z0),(p1,z1),반폭,블렌드(≤31°)

STRIP_W = (-60.0, -10.0, 13.0, 56.0, 0.0, 6.0)   # 높이차 0 (마스크만 사용)               # 북측 띠 x0,x1, (마루선+offset)..y1, +dz, blend

FOREST_PATH_W = [(-55.0, -16.0), (-40.0, -30.0), (-20.0, -36.0), (0.0, -38.0),
                 (20.0, -44.0), (40.0, -46.0), (56.0, -40.0), (60.0, -24.0)]
PATH_HALF_W = 2.5

# 계류 (자기대칭: y_s(-x) = -y_s(x))
STREAM_AMP, STREAM_HALF_LEN, STREAM_FADE_END = 6.0, 44.0, 50.0   # 스폰 디스크(|x|≥51) 전에 소멸 = 발원지
STREAM_BED_HALF, STREAM_WALL_RUN, STREAM_DEPTH = 1.0, 1.2, 1.8    # (구) 벽 56° 단일 사면 — 아래 2단 단면으로 대체
# 2단 단면 (2026-09-05, "물쪽 경사가 너무 급하고 부자연스럽다"): 물가는 낮은 바위 턱(LIP: 1.0 m 를 0.7 m 에 = 55°, 등반 차단 유지),
# 그 위는 완만한 풀 어깨(SHOULDER: 나머지 0.8 m 를 2.4 m 에 = 18°), 상단 라운드 1.0 m. 상폭 ≈ 2×(1+0.7+2.4+1) = 10 m.
STREAM_LIP_DEPTH, STREAM_LIP_RUN, STREAM_SHOULDER_RUN, STREAM_ROUND = 1.0, 0.7, 2.4, 1.0
FORD_X = (-42.0, 0.0, 42.0)
FORD_HALF_LEN, FORD_DEPTH, FORD_WALL_RUN = 4.0, 0.6, 3.0          # 둔치 11° (1.3 → 3.0, 완만한 여울 둔치)
WATER_BELOW_RIM = 0.45               # 수면 = 낮은 둑 −0.45 (0.75 → 0.45, 2026-09-05 물이 너무 없어 보여서. 도섭 바닥 −0.6 이라 여울에 0.15 m 물이 흐른다)

# 구조물 자리 (서쪽/자기대칭). Phase 1 은 그레이박스, Phase 2 에 실제 에셋
STRUCTURES_W = [
    ("PAVILION", (0.0, 9.0), 0.0, (5.0, 5.0, 4.0)),        # 초정 + 석축 1.2 (자기대칭 아님: 미러는 CAIRN)
    ("TERRACE",  (0.0, -9.0), 0.0, (5.0, 5.0, 1.2)),        # 석축 + 돌탑
    ("BRIDGE",   (0.0, 0.0), 0.0, (1.4, 5.0, 0.9)),         # 투죽위교, 남북
    ("WALL9",    (-40.0, -30.0), 30.0, (9.0, 0.5, 2.0)),
    ("WALL_L",   (-6.0, -27.0), 0.0, (5.4, 0.5, 2.0)),
    ("WALL9",    (34.0, -46.0), -20.0, (9.0, 0.5, 2.0)),
]

# ------------------------------------------------------------------ 프리미티브
def _crest_z(s):
    """마루 파라미터 s(0..1) → 바닥 기준 마루 높이 (폴리라인 정점 z 를 구간 선형보간)."""
    lens = [math.hypot(CREST[i + 1][0] - CREST[i][0], CREST[i + 1][1] - CREST[i][1]) for i in range(len(CREST) - 1)]
    total = sum(lens)
    acc = 0.0
    for i, L in enumerate(lens):
        if s * total <= acc + L or i == len(lens) - 1:
            t = clamp((s * total - acc) / L) if L > 0 else 0.0
            return lerp(CREST[i][2], CREST[i + 1][2], t)
        acc += L
    return CREST[-1][2]

def ridge_h(x, y):
    """지릉 하나(서쪽 정의)의 가산 높이. 남서(앞) 58°, 북동(뒤) 50°. 0 이면 영향 없음."""
    pts = [(c[0], c[1]) for c in CREST]
    d, s, side, _ = polyline_nearest(x, y, pts)
    zc = _crest_z(s)
    ux, uy, amp, rad = CREST_UNDULATION
    zc += amp * soft_edge(math.hypot(x - ux, y - uy), rad)
    # 폴리라인 진행 방향은 NW→SE. 외적 + = 왼쫙 = 북동(뒷면).
    slope = CLIFF_BACK_DEG if side > 0 else CLIFF_FRONT_DEG
    over = max(0.0, d - CREST_HALF_W)
    h = zc - over * math.tan(math.radians(slope))
    # 끝단(s→1) 은 반원으로 마감: 폴리라인 끝을 지나면 d 가 커지며 자연히 떨어진다
    return max(0.0, h)

def crest_mask(x, y):
    pts = [(c[0], c[1]) for c in CREST]
    d, s, side, _ = polyline_nearest(x, y, pts)
    return soft_edge(d - CREST_HALF_W, 0.8)

def cliff_mask(x, y):
    """절벽 띠(마루 밖 ~ 사면 발치). 재질(암반)·콜리전용."""
    pts = [(c[0], c[1]) for c in CREST]
    d, s, side, _ = polyline_nearest(x, y, pts)
    zc = _crest_z(s)
    slope = CLIFF_BACK_DEG if side > 0 else CLIFF_FRONT_DEG
    run = zc / math.tan(math.radians(slope))
    inner = d - CREST_HALF_W
    if inner <= 0.0:
        return 0.0
    return soft_edge(inner - run, 1.0) * soft_edge(-inner, 0.5) if inner < run + 1.0 else 0.0

def crest_y_at_x(x):
    """마루선의 y (x 단조 구간 보간, 양 끝은 연장)."""
    pts = CREST
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for i in range(len(pts) - 1):
        if pts[i][0] <= x <= pts[i + 1][0]:
            t = (x - pts[i][0]) / (pts[i + 1][0] - pts[i][0])
            return lerp(pts[i][1], pts[i + 1][1], t)
    return pts[-1][1]

def strip_mask_w(x, y):
    x0, x1, off, y1, dz, blend = STRIP_W
    y0 = crest_y_at_x(x) + off
    return box_mask(x, y, x0, x1, y0, y1, blend)

def strip_h(x, y):
    return STRIP_W[4] * strip_mask_w(x, y)

def bowl_h(x, y):
    cx, cy, r, dz, soft = BOWL
    return dz * disc_mask(x, y, cx, cy, r, soft)

def knoll_h(x, y):
    h = 0.0
    for cx, cy, r, dz, soft in KNOLLS_W:
        h += dz * disc_mask(x, y, cx, cy, r, soft)
    return h

def knoll_mask_w(x, y):
    m = 0.0
    for cx, cy, r, dz, soft in KNOLLS_W:
        m = max(m, disc_mask(x, y, cx, cy, r, soft))
    return m

def stream_center(x):
    """계류 중심선 y_s(x). |x|>60 에서 진폭이 0 으로 감쇠."""
    a = STREAM_AMP
    ax = abs(x)
    if ax > STREAM_HALF_LEN:
        a *= clamp(1.0 - (ax - STREAM_HALF_LEN) / (STREAM_FADE_END - STREAM_HALF_LEN))
    return -a * math.sin(math.pi * x / 60.0) if ax <= STREAM_FADE_END else 0.0   # 사행 주기는 60 m 고정

def stream_len(x):
    """계류 존재 0..1 (끝은 산벽 전에 소멸)."""
    ax = abs(x)
    if ax <= STREAM_HALF_LEN:
        return 1.0
    return clamp(1.0 - (ax - STREAM_HALF_LEN) / (STREAM_FADE_END - STREAM_HALF_LEN))

def _stream_normal_dist(x, y):
    dydx = (stream_center(x + 0.25) - stream_center(x - 0.25)) / 0.5
    return abs(y - stream_center(x)) / math.sqrt(1.0 + dydx * dydx)

def ford_amt(x):
    a = 0.0
    for fx in FORD_X:
        a = max(a, soft_edge(abs(x - fx) - FORD_HALF_LEN, 2.5))
    return a

def _profile_piecewise(over, segs, rnd):
    """over = 바닥 가장자리 밖 거리. segs = [(깊이, 수평거리)] 아래→위 순. 반환 파인 깊이(양수)."""
    depth = sum(dz for dz, _ in segs); z = depth; run = 0.0
    for dz, dx in segs:
        if over <= run + dx:
            return z - dz * (over - run) / dx
        z -= dz; run += dx
    if over < run + rnd:                       # 상단 라운드: 남은 살짝을 부드럽게 0 으로
        t = (over - run) / rnd
        return 0.06 * depth * (1.0 - t) * (1.0 - t)
    return 0.0

def stream_profile(d, depth, wall_run):
    """법선거리 d → 파인 깊이(양수). depth==STREAM_DEPTH 면 2단(턱+어깨), 아니면(도섭) 단일 완사면."""
    if d <= STREAM_BED_HALF:
        return depth
    over = d - STREAM_BED_HALF
    if depth >= STREAM_DEPTH - 1e-6:
        return _profile_piecewise(over, [(STREAM_LIP_DEPTH, STREAM_LIP_RUN), (depth - STREAM_LIP_DEPTH, STREAM_SHOULDER_RUN)], STREAM_ROUND)
    return _profile_piecewise(over, [(depth, wall_run)], STREAM_ROUND)

def stream_top_half(x):
    """바닥 중심에서 상단 림까지의 반폭(라운드 제외)."""
    return STREAM_BED_HALF + lerp(STREAM_LIP_RUN + STREAM_SHOULDER_RUN, FORD_WALL_RUN, ford_amt(x))

def stream_cut(x, y):
    """계류가 파내는 깊이(양수). 도섭 구간은 얕고 완만한 단면으로 보간."""
    L = stream_len(x)
    if L <= 0.0:
        return 0.0
    d = _stream_normal_dist(x, y)
    f = ford_amt(x)
    deep = stream_profile(d, STREAM_DEPTH, STREAM_WALL_RUN)
    shallow = stream_profile(d, FORD_DEPTH, FORD_WALL_RUN)
    c = lerp(deep, shallow, f) * L
    if c > 0.0:
        # 바닥은 낮은 둑 기준으로 파야 물이 흐른다: 중심 림이 낮은 둑보다 높은 구간(둔덕 옆구리, x −30~−17)은 그만큼 더 깊게.
        # (이전엔 국소 림 기준 1.8 m 라 바닥이 둔덕을 따라 2 m 솟았고 수면이 낮은 둑으로 범람했다, 2026-09-05)
        yc = stream_center(x)
        d_nom = lerp(STREAM_DEPTH, FORD_DEPTH, f)
        ref = lerp(water_z(x) + WATER_BELOW_RIM, rim_low_s(x), f)     # 깊은 구간: 수면+0.75 를 림으로 → 바닥 = 수면−1.05 / 도섭: 낮은 둑 기준(마른 여울, 건널 수 있음)
        excess = (z_floor(x) + height_rel(x, yc, cut=False)) - ref
        if excess > 0.05:
            c *= (d_nom + excess) / d_nom
    return c

def stream_mask(x, y):
    """계류 도랑 안쪽(상단 림 포함) 0..1."""
    L = stream_len(x)
    if L <= 0.0:
        return 0.0
    d = _stream_normal_dist(x, y)
    top = STREAM_BED_HALF + lerp(STREAM_LIP_RUN + 0.9, FORD_WALL_RUN * 0.6, ford_amt(x))   # 젖은 자갈은 물가 근처만 (어깨는 풀)
    return soft_edge(d - top, 0.8) * L

def _wall_d(x, y):
    """rect 가장자리 밖 거리(m). 안쪽이면 0."""
    return max(abs(x) - PLAY_X, abs(y) - PLAY_Y, 0.0)

def wall_h(x, y):
    d = _wall_d(x, y)
    if d <= 0.0:
        return 0.0
    # 완만한 산지 사면 + 사면 위 기복(원경 실루엣)
    h = WALL_RISE * smoothstep(d / WALL_RUN)
    h += 2.5 * smoothstep(d / 12.0) * (math.sin(x * 0.07 + 1.3) * math.cos(y * 0.05) + 0.6 * math.sin(x * 0.19) * math.sin(y * 0.16 + 0.4))
    return h

def wall_mask(x, y):
    d = _wall_d(x, y)
    return smoothstep(d / WALL_RUN) if d > 0.0 else 0.0

def path_mask_w(x, y):
    d, s, side, _ = polyline_nearest(x, y, FOREST_PATH_W)
    return soft_edge(d - PATH_HALF_W, 2.0)

def noise(x, y):
    """3옥타브 사인 기복 (jsn_live :212 계열). 진폭 1 기준."""
    n = 0.95 * math.sin(x * 0.052) * math.cos(y * 0.041)
    n += 0.52 * math.sin(x * 0.11 + y * 0.07)
    n += 0.27 * math.sin(x * 0.24 + y * 0.17) * math.cos(x * 0.13)
    return n

# ------------------------------------------------------------------ 대칭 도우미
def sym2(fn, x, y):
    """서쪽 정의 fn 을 (x,y) 와 (-x,-y) 에서 평가한 합(가산형)."""
    return fn(x, y) + fn(-x, -y)

def sym_max(fn, x, y):
    return max(fn(x, y), fn(-x, -y))

# ------------------------------------------------------------------ 절삭(carve) 목록
def _carves(x, y):
    """(mask, target_rel_z) 목록. 서쪽 정의 + 점대칭 사본."""
    out = []
    for sx, sy in ((x, y), (-x, -y)):
        # 스폰 디스크
        m = disc_mask(sx, sy, SPAWN_W[0], SPAWN_W[1], SPAWN_R, SPAWN_BLEND)
        if m > 0.0:
            out.append((m, SPAWN_Z, "spawn"))
        # 램프
        for key, ((ax, ay, z0), (bx, by, z1), hw, bl) in RAMPS.items():
            m, t = rect_mask(sx, sy, ax, ay, bx, by, hw, bl, cap=0.8)
            if m > 0.0:
                out.append((m, lerp(z0, z1, t), "ramp"))
        # 개활지
        (ax, ay, z0), (bx, by, z1), hw, bl = GLADE_S
        m, t = rect_mask(sx, sy, ax, ay, bx, by, hw, bl, cap=2.0)
        if m > 0.0:
            out.append((m, lerp(z0, z1, t), "glade"))
    return out

# ------------------------------------------------------------------ 지형 높이
def lane_mask(x, y):
    """0..1 마스크 사전. 재질·스캐터·콜리전·검증이 공유."""
    m = {}
    m["spawn"] = sym_max(lambda a, b: disc_mask(a, b, SPAWN_W[0], SPAWN_W[1], SPAWN_R, SPAWN_BLEND), x, y)
    m["crest"] = sym_max(crest_mask, x, y)
    m["cliff"] = sym_max(cliff_mask, x, y)
    ramp = 0.0
    for sx, sy in ((x, y), (-x, -y)):
        for key, ((ax, ay, z0), (bx, by, z1), hw, bl) in RAMPS.items():
            ramp = max(ramp, rect_mask(sx, sy, ax, ay, bx, by, hw, bl, cap=0.8)[0])
    m["ramp"] = ramp
    (ax, ay, z0), (bx, by, z1), hw, bl = GLADE_S
    m["glade"] = max(rect_mask(x, y, ax, ay, bx, by, hw, bl, cap=2.0)[0],
                     rect_mask(-x, -y, ax, ay, bx, by, hw, bl, cap=2.0)[0])
    m["path"] = sym_max(path_mask_w, x, y)
    m["stream"] = stream_mask(x, y)
    m["ford"] = m["stream"] * ford_amt(x)
    m["bowl"] = disc_mask(x, y, BOWL[0], BOWL[1], BOWL[2], BOWL[4])
    m["strip"] = sym_max(strip_mask_w, x, y)
    m["wall"] = wall_mask(x, y)
    m["knoll"] = sym_max(knoll_mask_w, x, y)
    m["flat"] = max(m["spawn"], m["crest"], m["ramp"], m["glade"], m["path"], m["stream"], m["bowl"] * 0.6)
    # 숲 사분면 = 플레이 안쪽에서 위 마스크 어디에도 안 걸리는 곳
    inside = box_mask(x, y, -PLAY_X, PLAY_X, -PLAY_Y, PLAY_Y, 0.0)
    m["forest"] = inside * (1.0 - max(m["flat"], m["cliff"], m["strip"] * 0.4))
    return m

def height_rel(x, y, cut=True):
    """바닥 기준 높이 (기울기 제외)."""
    lm = lane_mask(x, y)
    # 1) 가산
    h = sym2(ridge_h, x, y)
    h += sym2(strip_h, x, y)
    h += sym2(knoll_h, x, y)
    h += bowl_h(x, y)
    amp = lerp(0.15, 0.3, lm["forest"])   # 최대 기복 ≈ ±0.25 / ±0.5 m (콜리전 슬랩 8 m 셀 허용치 안)
    h += amp * noise(x, y) * (1.0 - lm["flat"])
    # 2) 절삭 (마스크 큰 순으로 적용해 겹침 안정)
    for m, target, kind in sorted(_carves(x, y), key=lambda c: c[0]):
        h = lerp(h, target, m)
    # 3) 계류
    if cut: h -= stream_cut(x, y)
    # 4) 산벽
    h += wall_h(x, y)
    return h

def height_at(x, y, cut=True):
    return z_floor(x) + height_rel(x, y, cut)

def slope_deg(x, y, e=0.5):
    hx = (height_at(x + e, y) - height_at(x - e, y)) / (2 * e)
    hy = (height_at(x, y + e) - height_at(x, y - e)) / (2 * e)
    return math.degrees(math.atan(math.hypot(hx, hy)))

def _rim_low(x):
    """도랑 바로 바깥 양쪽 둑 높이 중 낮은 쪽. 둔덕 옆구리를 지나는 구간에서 높은 쪽 림을 기준으로 잡으면 낮은 둑 위로 물이 넘친다."""
    yc = stream_center(x)
    top = stream_top_half(x) + STREAM_ROUND + 0.6
    dydx = (stream_center(x + 0.25) - stream_center(x - 0.25)) / 0.5
    nx, ny = -dydx / math.sqrt(1 + dydx * dydx), 1.0 / math.sqrt(1 + dydx * dydx)   # 중심선 법선
    return min(height_at(x + nx * top, yc + ny * top, cut=False), height_at(x - nx * top, yc - ny * top, cut=False))

def water_z(x):
    """계류 수면 절대 z (x 단면) = 낮은 둑 − WATER_BELOW_RIM, x 방향 ±4 m 평균으로 평활. 도섭(바닥 = 림−0.6)에서는 자연히 바닥 아래 → 마른 여울.
    (이전: 중심선 림 기준 −1.4 / 도섭 −0.35 → 도섭에서 1 m 혹, 둔덕 구간에서 낮은 둑으로 범람. 2026-09-05)"""
    # 상류(서, x 작은 쪽)부터 running-min: 물은 동쪽(z_floor 낮은 쪽)으로만 내려간다. 둔덕 옆구리 구간은 그만큼 협곡이 깊어진다.
    key = round(x * 4.0) / 4.0
    v = _WATER_CACHE.get(key)
    if v is None:
        v = 1e9; xx = -STREAM_FADE_END
        while xx <= key + 1e-6:
            v = min(v, rim_low_s(xx) - WATER_BELOW_RIM); xx += 0.5
        _WATER_CACHE[key] = v
    return v

_WATER_CACHE = {}
_RIM_CACHE = {}
def rim_low_s(x):
    """낮은 둑 높이를 x ±4 m 로 평활 (0.25 m 캐시)."""
    key = round(x * 4.0) / 4.0
    v = _RIM_CACHE.get(key)
    if v is None:
        n = 9; acc = 0.0
        for k in range(n):
            acc += _rim_low(key - 4.0 + 8.0 * k / (n - 1))
        v = acc / n; _RIM_CACHE[key] = v
    return v

# ------------------------------------------------------------------ 재질 마스크
def blend_at(x, y):
    """(R 흙/길, G 암반, B 젖은 자갈, A 솔잎 낙엽) 0..1."""
    lm = lane_mask(x, y)
    s = slope_deg(x, y)
    r = max(lm["path"] * 0.85, lm["ramp"] * 0.7, lm["spawn"] * 0.55, lm["glade"] * 0.3)
    g = smoothstep((s - 30.0) / 25.0)
    g = max(g, lm["cliff"] * 0.9, lm["crest"] * 0.35)
    g *= 1.0 - 0.6 * lm["wall"]          # 산벽 사면은 대부분 풀·숲, 급한 곳만 암반
    b = max(lm["stream"], lm["ford"])
    a = lm["forest"] * 0.55 + lm["strip"] * 0.5 + lm["wall"] * 0.4
    return (clamp(r), clamp(g), clamp(b), clamp(a))

# ------------------------------------------------------------------ 엔진 변환 / 키포인트
MAP_YAW_DEG = 0.0                    # 맵 전체 회전 (안 씀, 0). 사용자 요청 "전부 180도" 는 맵이 아니라 지형 타일 각각의 자체 회전이었다 → sgk_placements.TILE_YAW_DEG
def rot_xy(x, y):
    """MAP_YAW_DEG 만큼 (x,y) 를 원점 기준 회전 (Blender m)."""
    th = math.radians(MAP_YAW_DEG); c, s_ = math.cos(th), math.sin(th)
    return (x * c - y * s_, x * s_ + y * c)
def eng_yaw(yaw_deg):
    """엔진 yaw(도) 에 맵 회전을 더한다 (−180..180)."""
    v = (yaw_deg + MAP_YAW_DEG + 180.0) % 360.0 - 180.0
    return round(v, 3)
def to_engine(x, y, z):
    """Blender (m, Z-up, 오른손) → 엔진 (cm, Y-up, 오른손).  X = x, Y = z, **Z = −y**.
    2026-09-06 까지 Z = +y 로 썼는데 그건 거울상(det −1)이라, FBX(정상 회전: Z_fbx = −y) 메시 내용과 배치 위치가 남북으로 뒤집혀
    타일·산벽마다 내용이 제자리에서 180° 뒤집힌 것처럼 보였다(사용자 지적 "바닥마다 180도 반대"). Z 부호를 바꾸면 전부 맞는다."""
    x, y = rot_xy(x, y)
    return (x * 100.0 + ENGINE_X0, z * 100.0, -y * 100.0 + ENGINE_Z0)

def mirror(p):
    return (-p[0], -p[1])

def spawn_points():
    return {"Red": SPAWN_W, "Blue": mirror(SPAWN_W)}

def key_points():
    """검증용 주요 지점 (이름 → (x,y))."""
    kp = {
        "spawn_W": SPAWN_W, "spawn_E": mirror(SPAWN_W),
        "crest_tip_NW": (CREST[-1][0], CREST[-1][1]), "crest_tip_SE": mirror((CREST[-1][0], CREST[-1][1])),
        "crest_mid_NW": (-33.0, 25.5), "crest_mid_SE": (33.0, -25.5),
        "R1_top_W": (RAMPS["R1"][1][0], RAMPS["R1"][1][1]), "R2_top_W": (RAMPS["R2"][1][0], RAMPS["R2"][1][1]),
        "R3_top_W": (RAMPS["R3"][1][0], RAMPS["R3"][1][1]),
        "R1_top_E": mirror((RAMPS["R1"][1][0], RAMPS["R1"][1][1])),
        "ford_W": (FORD_X[0], stream_center(FORD_X[0])), "ford_C": (0.0, 0.0), "ford_E": (FORD_X[2], stream_center(FORD_X[2])),
        "glade_S": (0.0, -25.0), "glade_N": (0.0, 25.0),
        "strip_N": (-35.0, 50.0), "strip_S": (35.0, -50.0),
        "bowl": (0.0, 0.0),
        "path_W_mid": (-20.0, -36.0), "path_E_mid": (20.0, 36.0),
    }
    return kp

def lanes():
    """레인 중심선 (서팀 기준 3개 + 동팀 대칭 3개). 이동시간/시야선 표본용."""
    ridge_W = [(SPAWN_W[0], SPAWN_W[1]), (-67.0, 25.0)] + [(c[0], c[1]) for c in CREST] + [(-6.5, 6.5), (0.0, 0.0)]
    stream_W = [(SPAWN_W[0], SPAWN_W[1]), (-52.0, 0.0)] + [(x, stream_center(x)) for x in range(-48, 1, 8)]
    forest_W = [(SPAWN_W[0], SPAWN_W[1])] + FOREST_PATH_W
    out = {"ridge_W": ridge_W, "stream_W": stream_W, "forest_W": forest_W}
    for k in list(out):
        out[k.replace("_W", "_E")] = [mirror(p) for p in out[k]]
    return out

def structures():
    """전체 구조물 목록 (서쪽 정의 + 점대칭). (kind, (x,y), yaw_deg, (sx,sy,sz))"""
    out = []
    for kind, (x, y), yaw, size in STRUCTURES_W:
        out.append((kind, (x, y), yaw, size))
        if kind in ("PAVILION", "TERRACE", "BRIDGE"):
            continue   # 자기대칭 쌍은 표에 이미 있음
        out.append((kind, (-x, -y), yaw, size))
    return out

def map_service_entry():
    """MapService_1.lua 에 넣을 sgk 항목 텍스트."""
    rx0, rx1 = ENGINE_X0 - PLAY_X * 100, ENGINE_X0 + PLAY_X * 100
    rz0, rz1 = ENGINE_Z0 - PLAY_Y * 100, ENGINE_Z0 + PLAY_Y * 100
    return f"""	sgk = {{
		id = "sgk",
		label = "SANGOK II",
		sub = "VALLEY 3-LANE / {int(PLAY_X*2)} x {int(PLAY_Y*2)}m",
		thumb = SQUARE,
		tint = Color3.fromRGB(92, 104, 66),
		containers = {{ "SGK_Sangok" }},
		spawnRed = "SGK_Spawn_Red",
		spawnBlue = "SGK_Spawn_Blue",
		bounds = {{ "SGK_Bound_North", "SGK_Bound_South", "SGK_Bound_East", "SGK_Bound_West" }},
		rect = {{ minX = {int(rx0)}, maxX = {int(rx1)}, minZ = {int(rz0)}, maxZ = {int(rz1)} }},
		center = {{ x = {int(ENGINE_X0)}, z = {int(ENGINE_Z0)} }},
		groundY = 250,
		snapRise = 3000,
		rayTop = 9000,
		rayLen = 22000,
		zoneRadius = {ZONE_RADIUS_CM},
		minSpawnDist = {MIN_SPAWN_DIST_CM},
		edgeMargin = {EDGE_MARGIN_CM},
		moveScale = {MOVE_SCALE},
		seam = {{ enabled = false }},
		light = {{ ClockTime = 9.5, SunBrightness = 3.0, AmbientSkyBrightness = 1.4,
			AmbientSkyColor = Color3.fromRGB(128, 126, 118), SunLightColor = Color3.fromRGB(230, 212, 184) }},
		atmo = {{ FogStart = 3000, FogDensity = 0.016, FogColor = Color3.fromRGB(150, 150, 140),
			AirColor = Color3.fromRGB(140, 136, 124), CloudAmount = 0.5 }},
	}},"""

if __name__ == "__main__":
    # 빠른 자가 점검: 몇 지점 높이/경사
    for name, (x, y) in key_points().items():
        print(f"{name:14s} ({x:6.1f},{y:6.1f}) z={height_at(x, y):6.2f} slope={slope_deg(x, y):5.1f}")
