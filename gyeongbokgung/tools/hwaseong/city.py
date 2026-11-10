# -*- coding: utf-8 -*-
"""장안문 주변 실측 도시 — OSM footprint 압출 + 도로.

건물 하나하나의 디테일이 아니라 **도시의 실제 형상**이 결과물이다.
좌표·투영은 geo.py 가 맡는다.

**건물 높이는 전부 추정이다.** 이 지역 OSM 에는 building:levels 도 height 도
하나도 없다(110채 전부). 도로 등급과 바닥면적으로 층수를 유도하고 derived 로
표시한다. VWorld 국토부 건물통합정보에 실제 층수가 있으니 API 키가 생기면
level_of() 만 갈아끼우면 된다.
"""

import math

import bmesh

from hanok import new_collection, bm_to_object, bm_box
from . import geo

COLL_BLD = "화성_도시_건물"
COLL_ROAD = "화성_도시_도로"

# 문마다 도시를 따로 만든다. 각 도시는 **자기 문을 원점으로** 세우므로
# layout.BUILDINGS 가 문을 옮기면 도시가 따라온다.
#   (앵커, 건물 컬렉션, 도로 컬렉션, 소품 컬렉션)
# 팔달문 도시는 **뺐다.** 장안문 도시와 나란히 놓으니 똑같은 것이 두 개로
# 보였다. 되살리려면 아래 줄의 주석을 풀면 된다 — geo.ANCHORS 와 sites.py 의
# PTB/PTR/PTP, layout.BUILDINGS['팔달도시'] 는 그대로 남겨 두었다.
CITY_SITES = [
    ("장안문", "화성_도시_건물", "화성_도시_도로", "화성_도시_소품"),
    # ("팔달문", "화성_팔달도시_건물", "화성_팔달도시_도로", "화성_팔달도시_소품"),
]

FLOOR_H = 3.1                  # 층고
PARAPET = 0.6                  # 옥상 난간

# 도시 지반 윗면 높이. 사이트 지면 슬래브(build_hs._build_ground)도 윗면이
# z=0 이라 겹치면 바닥이 깨진다. 3 cm 띄우고 그 위에 도로를 얹는다.
GROUND_Z = 0.03
# 여유가 2 cm 였을 때 원경(clip 0.5~20000)에서 도로가 지면과 깜빡였다.
# 지형 기복을 넣은 뒤로는 지면 격자와 정확히 같은 면을 보므로 잠기지는
# 않지만, 깊이 버퍼 정밀도를 위해 여유를 키운다. 보도는 연석처럼 더 높게.
ROAD_Z = GROUND_Z + 0.12       # 수레길
WALK_Z = GROUND_Z + 0.22       # 샛길이 살짝 높다

# 도로 폭(m). 실측이 아니라 등급별 통례다.
# **현대 도로 폭에서 줄였다.** 도시가 한옥 마을이 된 뒤로 12 m 짜리 2차선
# 도로는 시대가 안 맞는다. 조선 후기 읍성 안 대로가 대략 6~9 m 였다.
ROAD_W = {
    'secondary': 9.0, 'secondary_link': 6.0, 'tertiary': 7.0,
    'residential': 4.6, 'service': 3.2, 'unclassified': 4.6,
    'footway': 1.8, 'path': 1.5, 'steps': 1.5, 'pedestrian': 3.6,
}
# 재질도 아스팔트·보도블럭을 버린다 — 수레가 다니는 흙길과 사람만 다니는
# 좁은 샛길 둘로 간다. Poly Haven CC0.
ROAD_MAT = {'footway': 'dirt_path', 'path': 'dirt_path',
            'steps': 'dirt_path', 'pedestrian': 'dirt_path'}
ROAD_MAT_DEFAULT = 'dirt_road'
VERGE_MAT = 'dirt_verge'     # 갓길 — 밟힌 풀. 흙과 잔디 사이를 잇는다

# 띠를 만드는 규칙. 예전엔 구간마다 사각형을 따로 놓았는데, 꺾이는 곳마다
# V 자 틈과 겹침이 생기고 텍스처도 구간마다 끊겼다. 폴리라인을 한 줄로
# 잇고 이등분선으로 오프셋한다.
ROAD_STEP = 2.5          # 재표본 간격 m. 기복과 흔들림이 이 간격으로 실린다
# 흔들림을 두 번 고쳤다. 처음엔 좌표 해시를 0.16 m 격자로 뽑아 써서
# 2.5 m 간격 정점끼리 값이 **완전히 무상관**이었다 — 폭이 매 정점마다
# ±16% 로 튀어 가장자리가 톱니처럼 울퉁불퉁했다. 파장을 길게(22 m) 잡고
# 사이를 부드럽게 잇는다. 진폭도 7% 로 줄인다.
ROAD_WOBBLE = 0.07       # 폭 흔들림 비율
ROAD_WOBBLE_M = 22.0     # 흔들림 파장 m. 짧으면 톱니, 길면 자로 잰 띠
ROAD_SMOOTH = 2          # z 이동평균 반경(정점). 지면 격자 능선의 각을 뭉갠다
ROAD_CLEAR = 0.06        # 다듬은 뒤에도 지면에서 최소 이만큼은 떠 있어야 한다
ROAD_MITER_MAX = 2.2     # 급커브에서 이등분선이 폭발하지 않게 자른다
ROAD_TEX_M = 2.5         # 텍스처 한 장이 덮는 길이 m (폭·길이 같은 배율)
# 갓길 — 흙과 잔디가 칼로 자른 듯 맞닿지 않게 밟힌 풀 띠를 하나 더 깐다
ROAD_VERGE = 0.20        # 노면 폭 대비 한쪽 갓길 폭
ROAD_VERGE_MAX = 1.4     # 갓길 폭 상한 m
ROAD_SHOULDER = 0.055    # 갓길이 노면보다 이만큼 낮다 (완만한 어깨)

# 건물 외장. OSM id 해시로 골라 통색을 피한다.
FACADE = ('concrete', 'concrete_d', 'brick_city', 'panel_warm', 'glass')


def _z(dem, x, y):
    """그 자리 지형 높이. dem 이 없으면 평지(0).

    지형을 넣기 전에는 모든 것이 z=0 에 놓여 있었다. 지면만 기복을 주면
    집과 길이 공중에 뜨거나 땅에 묻힌다 — 놓는 시점에 같이 올려야 한다.
    """
    # height_at 이 아니라 surface_at 이다 — 지면 메시가 실제로 그리는
    # 삼각형 면. 연속 DEM 을 쓰면 격자 칸 안에서 도로가 땅에 잠긴다.
    return 0.0 if dem is None else dem.surface_at(x, y)


def _area(poly):
    """신발끈 공식. 부호로 감김 방향도 알 수 있다."""
    s = 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        s += x0 * y1 - x1 * y0
    return s / 2.0


def _dedup(poly, eps=1e-6):
    """닫힌 way 는 첫 점을 끝에 되풀이한다. 그대로 두면 faces.new 가 터진다."""
    out = []
    for p in poly:
        if not out or abs(p[0] - out[-1][0]) > eps or abs(p[1] - out[-1][1]) > eps:
            out.append(p)
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) < eps and abs(out[0][1] - out[-1][1]) < eps:
        out.pop()
    return out


def level_of(way, poly, near_major):
    """층수 추정. **전부 derived 다 — OSM 에 높이 태그가 0건이다.**

    간선로변은 상가라 높고, 바닥면적이 크면 상가·업무동이라 높고,
    이면도로 안쪽은 주택이라 낮다. 수원 장안문 일대의 실제 스카이라인을
    닮게 하려는 규칙이지 개별 건물의 실측이 아니다.
    """
    t = way["tags"]
    for k in ("building:levels", "levels", "height"):     # 혹시 생기면 우선
        v = t.get(k)
        if v:
            try:
                return max(1, int(round(float(str(v).split()[0]))))
            except ValueError:
                pass
    a = abs(_area(poly))
    if a > 400.0:
        return 5
    if near_major:
        return 4
    if a < 60.0:
        return 2
    return 3


def _extrude(bm, poly, h, z0=0.0):
    """평면 폴리곤을 h 만큼 세운다. 실패하면 False."""
    try:
        vs = [bm.verts.new((x, y, z0)) for x, y in poly]
        f = bm.faces.new(vs)
    except ValueError:
        return False            # 자기교차·중복점 등. 그런 footprint 는 버린다
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    nv = [e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=nv, vec=(0.0, 0.0, h))
    return True


# ------------------------------------------------------------------ 한옥
#
# 사용자 요청: "수원화성에 맞는 기와집(수원화성 작자랑 똑같음 공공제)".
# 장안문·팔달문과 **같은 제작처인 한국문화정보원(KCISA)** 의 CC-BY 공공저작물이다.
#   사랑채  095e7862fb91443ca2658b1e98066e53  창원의 집  8.8 × 14.0 m  기와
#   대문    f844d3c578614148af2677add0678c97  소슬대문    2.8 ×  5.2 m  기와
#   초가집  e78d2a2c80b646279e44e2ceaf6a1fd2  수내동가옥  8.6 ×  8.3 m  초가
# 셋 다 hwaseong_props.blend 에 5,000 삼각형으로 감축해 구워 두었다.
#
# 바닥면적으로 고른다. 원본 크기를 적어 두는 이유는 footprint 에 맞춰 등배
# 축소·확대할 때 기준이 필요해서다.
HANOK = [
    # (이름, 원본 폭 X, 원본 깊이 Y, 이 크기 이하 면적에 쓴다)
    ("대문",   2.8,  5.2,   45.0),
    ("초가집", 8.6,  8.3,  130.0),
    ("사랑채", 8.8, 14.0,  1e9),
]
# 처음엔 500 m² 를 넘으면 콘크리트 박스로 압출했는데, 한옥 72채 사이에
# 흰 박스 4개가 그대로 튀었다. 전부 한옥으로 간다 — 큰 필지는 사랑채가
# 스케일 상한(1.9배)까지 커져 큰 채로 앉는다.
HANOK_MAX_AREA = 1e9
HANOK_SCALE_LIMIT = (0.55, 1.9)


def _principal(poly):
    """폴리곤의 주방향(가장 긴 변의 각). 집을 대지 방향에 맞춰 앉히려고 쓴다."""
    best, ang = 0.0, 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        L = math.hypot(x1 - x0, y1 - y0)
        if L > best:
            best, ang = L, math.atan2(y1 - y0, x1 - x0)
    return ang


def _local_extent(poly, ang):
    """ang 만큼 되돌린 좌표계에서 폴리곤의 폭·깊이."""
    c, s = math.cos(-ang), math.sin(-ang)
    xs = [p[0] * c - p[1] * s for p in poly]
    ys = [p[0] * s + p[1] * c for p in poly]
    return max(xs) - min(xs), max(ys) - min(ys)


def build_buildings(osm, P, coll, dem=None):
    """반경 안 building way 를 압출한다. 외장별로 메시를 묶는다."""
    majors = []
    for w in osm.tagged("highway"):
        if w["tags"]["highway"] in ("secondary", "secondary_link", "tertiary"):
            majors += P.poly(osm.coords(w))

    def near_major(cx, cy, d=25.0):
        return any((cx - x) ** 2 + (cy - y) ** 2 < d * d for x, y in majors)

    from mathutils import Matrix, Vector

    bins = {k: bmesh.new() for k in FACADE}
    hbins, hmats = {}, {}
    hgeom = {}
    n_box = n_hanok = n_skip = 0
    for w in osm.tagged("building"):
        poly = _dedup(P.poly(osm.coords(w)))
        if len(poly) < 3:
            continue
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
        if math.hypot(cx, cy) > geo.RADIUS_M:
            continue
        if _area(poly) < 0:                 # 감김을 CCW 로 통일 — 법선이 뒤집히면
            poly.reverse()                  # 익스포터 preflight 가 미러로 잡는다
        a = abs(_area(poly))

        # --- 한옥이 들어갈 크기면 집을 앉힌다. 아니면 예전처럼 박스로 압출.
        pick = None
        for name, mw, md, amax in HANOK:
            if a <= amax:
                pick = (name, mw, md)
                break
        if pick and a <= HANOK_MAX_AREA:
            name, mw, md = pick
            if name not in hgeom:
                g, ms = _prop_mesh(name)
                if g is None:
                    pick = None
                else:
                    hgeom[name] = g
                    hmats[name] = ms
                    hbins[name] = bmesh.new()
        if pick and name in hgeom:
            ang = _principal(poly)
            ew, ed = _local_extent([(p[0] - cx, p[1] - cy) for p in poly], ang)
            s = min(ew / mw, ed / md)
            s = max(HANOK_SCALE_LIMIT[0], min(HANOK_SCALE_LIMIT[1], s))
            _stamp(hbins[name], hgeom[name],
                   Matrix.Translation(Vector((cx, cy, GROUND_Z + _z(dem, cx, cy))))
                   @ Matrix.Rotation(ang, 4, 'Z')
                   @ Matrix.Scale(s, 4))
            n_hanok += 1
            continue

        lv = level_of(w, poly, near_major(cx, cy))
        h = lv * FLOOR_H + PARAPET
        key = FACADE[int(w["id"]) % len(FACADE)]
        if _extrude(bins[key], poly, h, z0=_z(dem, cx, cy)):
            n_box += 1
        else:
            n_skip += 1

    for k, bm in bins.items():
        if bm.faces:
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
            bm_to_object(bm, "도시_건물_%s" % k, k, coll)
        else:
            bm.free()
    for k, bm in hbins.items():
        if bm.faces:
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
            _to_object_multi(bm, "도시_한옥_%s" % k, hmats[k], coll)
        else:
            bm.free()
    for k in list(hgeom):
        import bpy
        if k in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[k], do_unlink=True)
    return n_box, n_hanok, n_skip


def _wobble(x, y, salt=0):
    """좌표만으로 정해지는 -1..1 잡음.

    random 을 쓰면 빌드마다 도로 모양이 달라진다. 좌표 해시라 같은 자리는
    언제나 같은 값이다. 교차점 조각처럼 **한 점에서 한 번만** 쓸 때 쓴다.
    """
    h = (int(x * 6.1) * 73856093) ^ (int(y * 6.1) * 19349663) ^ (salt * 83492791)
    return ((h & 0x7fffffff) % 2003) / 1001.0 - 1.0


def _lattice(salt, i):
    """정수 격자점 i 의 -1..1 값."""
    h = (i * 374761393) ^ (salt * 668265263)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h & 0x7fffffff) % 2003) / 1001.0 - 1.0


def _smooth_noise(salt, s):
    """진행 거리 s(m) 를 따라 **부드럽게** 변하는 -1..1 잡음.

    _wobble 을 정점마다 부르면 2.5 m 간격 이웃끼리 값이 완전히 무상관이라
    가장자리가 톱니처럼 튄다(실제로 그렇게 보였다). ROAD_WOBBLE_M 마다
    격자값을 뽑고 사이를 smoothstep 으로 잇는다 — 값 잡음(value noise).
    """
    u = s / ROAD_WOBBLE_M
    i = int(math.floor(u))
    t = u - i
    t = t * t * (3.0 - 2.0 * t)
    return _lattice(salt, i) * (1.0 - t) + _lattice(salt, i + 1) * t


def _resample(pts, step):
    """폴리라인을 step 간격으로 다시 찍는다. 원래 꼭짓점은 그대로 남긴다."""
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 1e-6:
            continue
        k = max(1, int(L / step))
        for i in range(1, k + 1):
            t = i / float(k)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def _ribbon(slot, core_mat, verge_mat, pts, width, z, dem, salt):
    """폴리라인을 따라 **끊기지 않는** 길을 놓는다. 3줄로 깐다.

    예전에는 구간마다 사각형을 따로 놓았다. 꺾이는 곳마다 바깥쪽에 V 자
    틈이 벌어지고 안쪽은 겹쳐서, 텍스처를 아무리 좋은 걸 써도 자로 자른
    종잇조각처럼 보였다. 각 정점에서 **이등분선** 방향으로 오프셋하면
    한 줄로 이어진다.

    UV 는 **양쪽 다 미터 단위**다 — u = 폭 위치 / ROAD_TEX_M,
    v = 누적 거리 / ROAD_TEX_M. 이래야 흙길 텍스처의 바퀴 자국이 길을
    **따라** 흐르고, 결의 크기가 폭·길이 양방향으로 같다.

    처음엔 u 를 0..1 로 깔았는데, 9 m 짜리 대로에서는 텍스처 한 장이 폭
    9 m 를 덮고 길이는 4 m 마다 반복돼 결이 옆으로 찌그러졌다. Object
    좌표로 타일링하면 결이 도로와 무관한 방향으로 눕는 것도 같은 문제다.

    **가장자리를 3줄로 나눈다.** 한 줄짜리 띠는 흙과 잔디가 칼로 자른 듯
    맞닿아서, 텍스처가 아무리 좋아도 스티커를 붙인 것처럼 보였다. 실제
    흙길은 가운데가 다져져 맨흙이고 가장자리로 갈수록 풀이 비집고 든다.
      바깥 갓길 (grass_path_2, 밟힌 풀)  ─┐
      가운데   (dirt_floor,  맨흙)       ├─ 두 재질이 겹치며 경계가 풀린다
      바깥 갓길 (grass_path_2)          ─┘
    갓길은 노면보다 ROAD_SHOULDER 만큼 낮아 완만한 어깨가 생긴다.
    """
    P = _resample(pts, ROAD_STEP)
    if len(P) < 2:
        return 0

    # 각 정점의 진행 방향 = 앞뒤 구간 방향의 평균
    tan = []
    for i, p in enumerate(P):
        a = P[max(0, i - 1)]
        b = P[min(len(P) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        tan.append((dx / L, dy / L))

    # --- 1단계: 좌우 가장자리 위치를 먼저 다 구한다 (정점은 아직 안 만든다)
    LP, RP, AS = [], [], []
    arc = 0.0
    for i, (x, y) in enumerate(P):
        if i:
            arc += math.hypot(x - P[i - 1][0], y - P[i - 1][1])
        AS.append(arc)
        tx, ty = tan[i]
        # 이등분선 보정: 꺾인 각이 클수록 오프셋을 늘려야 폭이 유지된다.
        # 급커브에서 무한대로 가므로 잘라 준다.
        d0 = tan[max(0, i - 1)]
        c = max(0.45, tx * d0[0] + ty * d0[1])
        m = min(ROAD_MITER_MAX, 1.0 / c)
        # 좌우를 **따로** 흔들어야 길이 구불구불해진다. 같은 값을 쓰면
        # 폭만 늘었다 줄었다 하는 소시지가 된다.
        hl = width * 0.5 * (1.0 + ROAD_WOBBLE * _smooth_noise(salt, arc)) * m
        hr = width * 0.5 * (1.0 + ROAD_WOBBLE * _smooth_noise(salt + 7919, arc)) * m
        # 갓길 폭은 노면 폭에 비례하되 상한을 둔다 — 9 m 대로에서 갓길이
        # 1.5 m 를 넘으면 길이 아니라 밭두렁처럼 보인다.
        vw = min(ROAD_VERGE_MAX, width * ROAD_VERGE)
        LP.append(((x - ty * hl, y + tx * hl),
                   (x - ty * (hl - vw), y + tx * (hl - vw))))
        RP.append(((x + ty * hr, y - tx * hr),
                   (x + ty * (hr - vw), y - tx * (hr - vw))))

    # --- 2단계: 지면 높이를 재고 **길이 방향으로 다듬는다.**
    # 지면은 12 m 격자를 삼각화한 면이라 능선에서 각이 진다. 그 위를 2.5 m
    # 간격으로 그대로 따라가면 길이 잘게 꺾여 울퉁불퉁했다. 이동평균으로
    # 완만하게 만들되, 다듬은 결과가 땅에 잠기지 않게 바닥을 받쳐 준다.
    def profile(pts2):
        g = [_z(dem, px, py) for px, py in pts2]
        if ROAD_SMOOTH <= 0 or len(g) < 3:
            return g
        out = []
        for i in range(len(g)):
            a = max(0, i - ROAD_SMOOTH)
            b = min(len(g), i + ROAD_SMOOTH + 1)
            # z(띄움) + 다듬은 높이가 원래 지면 + ROAD_CLEAR 밑으로 못 간다
            out.append(max(sum(g[a:b]) / (b - a), g[i] + ROAD_CLEAR - z))
        return out

    # 높이는 **노면 안쪽 선** 기준으로 한 번만 잰다. 네 줄을 따로 재면
    # 같은 단면에서 좌우가 어긋나 길이 비틀린다.
    zl = profile([p[1] for p in LP])
    zr = profile([p[1] for p in RP])

    core_bm, core_uv = slot(core_mat)
    verge_bm, verge_uv = slot(verge_mat)

    def line(bm, pts2, zs, drop):
        return [bm.verts.new((pts2[i][0], pts2[i][1], z + zs[i] - drop))
                for i in range(len(P))]

    # 노면(안쪽 두 줄)과 갓길(바깥 두 줄). 갓길은 어깨만큼 낮다.
    cL = line(core_bm, [p[1] for p in LP], zl, 0.0)
    cR = line(core_bm, [p[1] for p in RP], zr, 0.0)
    vLo = line(verge_bm, [p[0] for p in LP], zl, ROAD_SHOULDER)
    vLi = line(verge_bm, [p[1] for p in LP], zl, 0.0)
    vRi = line(verge_bm, [p[1] for p in RP], zr, 0.0)
    vRo = line(verge_bm, [p[0] for p in RP], zr, ROAD_SHOULDER)

    T = ROAD_TEX_M
    vw = min(ROAD_VERGE_MAX, width * ROAD_VERGE)
    n = 0

    def strip(bm, uvl, a, b, ua, ub):
        """정점열 a, b 사이를 쿼드로 잇고 UV 를 미터 단위로 깐다."""
        cnt = 0
        for i in range(len(P) - 1):
            try:
                f = bm.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
            except ValueError:
                continue
            for lp, (u, s) in zip(f.loops, ((ua, AS[i]), (ua, AS[i + 1]),
                                            (ub, AS[i + 1]), (ub, AS[i]))):
                lp[uvl].uv = (u / T, s / T)
            cnt += 1
        return cnt

    n += strip(core_bm, core_uv, cL, cR, 0.0, width)
    n += strip(verge_bm, verge_uv, vLo, vLi, 0.0, vw)
    n += strip(verge_bm, verge_uv, vRi, vRo, 0.0, vw)
    return n


def _junction_cap(bm, uvl, x, y, r, z, dem, salt):
    """교차점에 팔각 조각을 깐다.

    띠 두 개가 다른 각도로 만나면 모서리에 삼각 틈이 남는다. 반지름이
    양쪽 폭의 절반이라 틈을 정확히 덮는다.
    """
    vs = []
    for k in range(8):
        a = math.pi * 2.0 * k / 8.0
        rr = r * (1.0 + 0.05 * _wobble(x + k, y - k, salt))
        px, py = x + math.cos(a) * rr, y + math.sin(a) * rr
        # UV 도 미터 기준 — 띠와 결의 크기가 맞아야 이음매가 안 보인다
        vs.append((bm.verts.new((px, py, z + _z(dem, px, py))),
                   ((px - x) / ROAD_TEX_M, (py - y) / ROAD_TEX_M)))
    try:
        f = bm.faces.new([v for v, _ in vs])
    except ValueError:
        return 0
    for lp, (_, uv) in zip(f.loops, vs):
        lp[uvl].uv = uv
    return 1


def build_roads(osm, P, coll, dem=None):
    """도로 폴리라인을 흙길 띠로 깐다.

    지면 슬래브 위에 살짝 띄워 z-fighting 을 피하고, 교차점에는 조각을
    덧대 틈을 메운다.
    """
    bins, uvls = {}, {}
    n = 0

    def slot(mat):
        if mat not in bins:
            bins[mat] = bmesh.new()
            uvls[mat] = bins[mat].loops.layers.uv.new("UVMap")
        return bins[mat], uvls[mat]

    # 교차점을 먼저 센다 — 반경 안 도로 way 들이 공유하는 노드다.
    use = {}
    keep = []
    for w in osm.tagged("highway"):
        cls = w["tags"]["highway"]
        if cls not in ROAD_W:
            continue
        keep.append(w)
        for r in w["refs"]:
            use.setdefault(r, []).append(cls)

    for w in keep:
        cls = w["tags"]["highway"]
        wd = ROAD_W[cls]
        mat = ROAD_MAT.get(cls, ROAD_MAT_DEFAULT)
        # 교차부에서 way 끼리 **정확히 같은 높이로 겹치면** 그 면들이 서로
        # 깜빡인다. way id 로 8 mm 단위 계단을 줘서 겹치는 두 면이 절대
        # 동일 평면에 놓이지 않게 한다.
        z = ((ROAD_Z if mat == ROAD_MAT_DEFAULT else WALK_Z)
             + (int(w["id"]) % 12) * 0.008)
        salt = int(w["id"]) & 0xffff

        # **반경 밖은 자른다.** way 하나를 통째로 살리면 도로가 반경 밖
        # 786 m 까지 뻗어 나갔다. 반경 안에 들어오는 연속 토막들로 쪼갠다.
        run = []
        pts = P.poly(osm.coords(w))
        for p in pts:
            if math.hypot(p[0], p[1]) <= geo.RADIUS_M + 8.0:
                run.append(p)
            else:
                if len(run) >= 2:
                    n += _ribbon(slot, mat, VERGE_MAT, run, wd, z, dem, salt)
                run = []
        if len(run) >= 2:
            n += _ribbon(slot, mat, VERGE_MAT, run, wd, z, dem, salt)

    # 교차점 조각 — 굵은 쪽 재질에 올린다
    for r, classes in use.items():
        if len(classes) < 2:
            continue
        ll = osm.nodes.get(r)
        if ll is None:
            continue
        x, y = P(*ll)
        if math.hypot(x, y) > geo.RADIUS_M:
            continue
        top = max(classes, key=lambda c: ROAD_W[c])
        mat = ROAD_MAT.get(top, ROAD_MAT_DEFAULT)
        bm, uvl = slot(mat)
        z = (ROAD_Z if mat == ROAD_MAT_DEFAULT else WALK_Z) + 0.1
        n += _junction_cap(bm, uvl, x, y, ROAD_W[top] * 0.5, z, dem,
                           int(r) & 0xffff)

    for mat, bm in bins.items():
        if bm.faces:
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
            bm_to_object(bm, "도시_도로_%s" % mat, mat, coll)
        else:
            bm.free()
    return n


# ------------------------------------------------------------------ 소품
#
# 스케치팹 CC-BY 에셋. hwaseong_props.blend 에 정규화해 두었다.
#   소나무  KCISA 3acb4031a6234a7590ea9ed78ad7c8bd  13,133 삼각형
#   상가팩  abhayexe 2f603ad8d5c640f7b9794f6916f9fbdd  38,870 삼각형
# Seoul City / Modern City Block 은 **Free Standard** 라 쓰지 않는다 — CC 가 아니다.
PROPS_BLEND = "hwaseong_props.blend"
# 여러 벌 뿌리므로 세게 깎는다. 가로수 31그루 × 원본 13,133 = 40만이라
# 감축 없이는 도시 전체(1,326)의 300배가 된다.
PROP_RATIO = {"소나무": 0.15, "상가": 0.15}
# 한옥 70여 채가 예산의 대부분을 먹으므로 가로수는 성기게 심는다.
TREE_SPACING = 34.0
COLL_PROP = "화성_도시_소품"
# 상가팩(abhayexe, CC BY 4.0)은 더 이상 쓰지 않는다 — build_props 주석 참조.
ATTRIBUTION = "소나무: 한국문화정보원(KCISA), CC BY 4.0"


def _prop_mesh(name):
    """소품 원본을 (정점, 면) 리스트로 읽는다.

    **감축은 hwaseong_props.blend 에 이미 구워져 있다.** 여기서 모디파이어를
    걸고 depsgraph 로 평가하려 했더니 두 가지가 터졌다: 링크 안 된 오브젝트는
    모디파이어가 무시돼 640k 삼각형이 그대로 들어갔고, 링크해서 update() 를
    부르니 Blender 가 EXCEPTION_ACCESS_VIOLATION 으로 죽었다.
    소품 파일에 미리 적용해 두면 여기서는 평범한 메시만 읽으면 된다.

    오브젝트를 복제하지 않고 지오메트리만 여러 번 굽는다 — 복제하면
    MeshPart 가 배치 수만큼 늘어나는데, 소품 하나에 그럴 값어치가 없다.
    """
    import bpy
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        PROPS_BLEND)
    if name not in bpy.data.objects:
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.objects = [name] if name in src.objects else []
    ob = bpy.data.objects.get(name)
    if ob is None:
        return None, None
    me = ob.data
    verts = [tuple(v.co) for v in me.vertices]
    # **UV 를 같이 들고 와야 한다.** 처음엔 정점·면만 옮겼는데, 그러면 찍힌
    # 한옥의 uv_layers 가 비어 텍스처가 아예 붙지 않는다(렌더에서 확인).
    uvl = me.uv_layers.active
    faces = []
    for p in me.polygons:
        uv = ([tuple(uvl.data[li].uv) for li in p.loop_indices] if uvl else None)
        faces.append((tuple(p.vertices), p.material_index, uv))
    mats = [m for m in me.materials]
    # Bulk Import 는 2048px 초과 텍스처에서 불안정하다. 소품 라이브러리의
    # 소나무 잎 한 장이 2126x2241 이므로, 씬에 가져온 복사본만 비율을
    # 유지해 최대 2048px 로 줄이고 패킹한다. 같은 이미지는 한 번만 처리한다.
    seen = set()
    for mat in mats:
        if mat is None or not mat.use_nodes:
            continue
        for node in mat.node_tree.nodes:
            if node.type != 'TEX_IMAGE' or node.image is None:
                continue
            image = node.image
            key = image.as_pointer()
            if key in seen:
                continue
            seen.add(key)
            width, height = image.size
            longest = max(width, height)
            if longest <= 2048:
                continue
            ratio = 2048.0 / longest
            new_width = max(1, int(round(width * ratio)))
            new_height = max(1, int(round(height * ratio)))
            image.scale(new_width, new_height)
            image.pack()
            print("  소품 텍스처 축소: %s %dx%d -> %dx%d" % (
                image.name, width, height, new_width, new_height))
    return (verts, faces), mats


def _stamp(bm, geom, mat4):
    """소품 지오메트리 한 벌을 bm 에 굽는다. 머티리얼 인덱스와 UV 를 보존한다."""
    from mathutils import Vector
    verts, faces = geom
    lay = bm.loops.layers.uv.verify()
    bv = [bm.verts.new(mat4 @ Vector(v)) for v in verts]
    for idx, mi, uv in faces:
        try:
            f = bm.faces.new([bv[i] for i in idx])
        except ValueError:
            continue
        f.material_index = mi
        if uv:
            for lp, c in zip(f.loops, uv):
                lp[lay].uv = c


def _to_object_multi(bm, name, mats, coll):
    """bm_to_object 는 팔레트 키 하나만 받는다. 소품은 스케치팹 원본
    머티리얼을 여러 장 그대로 써야 하므로 여기서 직접 만든다."""
    import bpy
    me = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def build_props(osm, P, coll, dem=None):
    """가로수는 간선로를 따라, 상가 소품은 OSM amenity 노드에 앉힌다."""
    import bpy
    from mathutils import Matrix, Vector

    spots_tree, spots_shop = [], []
    for w in osm.tagged("highway"):
        if w["tags"]["highway"] not in ("secondary", "tertiary"):
            continue
        pts = P.poly(osm.coords(w))
        acc = 0.0
        for a, b in zip(pts, pts[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy)
            if L < 0.1:
                continue
            wd = ROAD_W[w["tags"]["highway"]] / 2.0 + 2.6
            n = 0
            while acc + TREE_SPACING <= L:
                acc += TREE_SPACING
                n += 1
                t = acc / L
                cx, cy = a[0] + dx * t, a[1] + dy * t
                px, py = -dy / L * wd, dx / L * wd
                for s in (-1.0, 1.0):
                    x, y = cx + s * px, cy + s * py
                    if math.hypot(x, y) <= geo.RADIUS_M:
                        spots_tree.append((x, y, math.atan2(dy, dx)))
            acc = max(0.0, acc - L)

    # **상가 소품은 뺐다.**
    # abhayexe 의 Asian Shop Pack 을 OSM 편의시설 노드(식당·카페·은행 등)에
    # 앉혔는데, 간판이 Standard Chartered · 7-Eleven 같은 현대 상호라
    # 한옥 마을 한복판에 눈높이로 서 있으면 바로 튄다. 도시를 한옥으로
    # 바꾸기 전에 넣은 것이라 시대가 안 맞는다.
    #
    # 되살리려면 아래 주석을 풀고 _prop_mesh 목록에 "상가" 를 더하면 된다 —
    # hwaseong_props.blend 의 오브젝트는 지우지 않고 남겨 두었다.
    #
    # AMEN = ("restaurant", "cafe", "bank", "bakery", "pub", "fast_food")
    # for nid, tags in osm.node_tags.items():
    #     if tags.get("amenity") in AMEN or tags.get("shop"):
    #         lat, lon = osm.nodes[nid]
    #         x, y = P(lat, lon)
    #         if math.hypot(x, y) <= geo.RADIUS_M:
    #             spots_shop.append((x, y, 0.0))

    n = 0
    for name, spots in (("소나무", spots_tree),):
        if not spots:
            continue
        geom, mats = _prop_mesh(name)
        if geom is None:
            print("  소품 %s 없음 — %s 를 만들었는지 확인" % (name, PROPS_BLEND))
            continue
        bm = bmesh.new()
        for x, y, rot in spots:
            _stamp(bm, geom,
                   Matrix.Translation(Vector((x, y, _z(dem, x, y))))
                   @ Matrix.Rotation(rot, 4, 'Z'))
            n += 1
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        _to_object_multi(bm, "도시_소품_%s" % name, mats, coll)
        if name in bpy.data.objects:                 # 원본은 씬에 남기지 않는다
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    return n, len(spots_tree), len(spots_shop)


# build_ground 는 없앴다.
#
# 도시마다 지반을 한 장씩 깔았더니 장안문·팔달문 두 도시에서 **똑같은 회색
# 판이 두 장** 나란히 생겼고, 그 밑의 사이트 지면 슬래브까지 겹쳐 경계에
# 단차와 이음매가 보였다. 지반은 build_hs._build_ground 가 **사이트 전체에
# 한 장만** 깐다. 도로는 그 위 ROAD_Z/WALK_Z 에 얹힌다.


def build_site(anchor, cb_name, cr_name, cp_name):
    """앵커 하나짜리 도시. 좌표는 그 문을 원점으로 잡힌다."""
    osm, P = geo.load(anchor)
    from . import dem as _dem
    d = _dem.get(anchor)
    cb = new_collection(cb_name)
    cr = new_collection(cr_name)
    cp = new_collection(cp_name)
    n_box, n_hanok, n_skip = build_buildings(osm, P, cb, d)
    n_seg = build_roads(osm, P, cr, d)
    n_pr, n_tree, n_shop = build_props(osm, P, cp, d)
    print("도시[%s]: 한옥 %d채 + 박스 %d채(버림 %d) / 도로 %d구간 / 소품 %d(가로수 %d, 상가 %d) / 방위 %.1f도"
          % (anchor, n_hanok, n_box, n_skip, n_seg, n_pr, n_tree, n_shop, P.bearing))
    return [cb, cr, cp]


def build_all():
    out = []
    for anchor, cb, cr, cp in CITY_SITES:
        out += build_site(anchor, cb, cr, cp)
    print("  %s" % ATTRIBUTION)
    return out
