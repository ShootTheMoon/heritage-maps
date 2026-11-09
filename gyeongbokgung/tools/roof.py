# -*- coding: utf-8 -*-
"""팔작지붕(hip-and-gable) 생성기.

지붕면을 네 갈래(전면·후면 경사 + 좌우 추녀면)로 나눠 매개변수 격자로 만든 뒤,
전체 정점에 처마 곡선 변형을 적용한다.

  - 앙곡(仰曲): 추녀 끝이 위로 들리는 곡선  → deform 의 z 상승
  - 안허리곡:   추녀 끝이 밖으로 뻗는 곡선  → deform 의 xy 확장

변형은 "변형 전 좌표계"에서 만든 모든 부재(지붕면·기와골·용마루·서까래)에
동일하게 적용되므로 부재끼리 어긋나지 않는다.
"""

import bpy
import bmesh
import math

from hanok import bm_to_object, bm_box, get_mat, DANCHEONG
from roofprofile import RoofProfile, mulmae_to_deg      # noqa: F401

# 3구간 물매 + 겹처마를 전역으로 켜는 스위치.
#
# 기본은 꺼짐이다. 그래야 예전 출력이 정점 단위로 보존되고, CP-1 의
# "무변경 리팩터" 를 해시로 증명할 수 있다.
#
# **환경변수에서 읽는다.** 그냥 모듈 변수로 두면 build.py 의
# importlib.reload(roof) 가 이 파일을 다시 실행하면서 값을 False 로
# 되돌려 버린다. 실제로 그렇게 조용히 꺼진 채로 빌드된 적이 있다.
#     set HANOK_MULMAE=1   또는   os.environ['HANOK_MULMAE'] = '1'
# 직접 대입(roof.USE_MULMAE = True)도 여전히 되지만, 그 뒤에 reload 가
# 끼면 날아간다는 점을 기억할 것.
import os as _os
USE_MULMAE = _os.environ.get('HANOK_MULMAE', '0') == '1'

# 부연/서까래 비. 실측 석어당 0.450 / 준명당 0.383 의 중앙.
BUYEON_RATIO = 0.40


# --------------------------------------------------------------- 변형 함수


def make_deform(W, D, h0, h1, lift, out, sharp=4.0, decay=1.5):
    """처마 곡선 변형 함수를 만든다.

    W, D : 변형 전 지붕 평면 크기
    h0, h1 : 처마 높이, 용마루 높이
    lift : 추녀 끝 최대 상승량 (앙곡)
    out  : 추녀 끝 최대 외밀기 (안허리곡)
    """
    hw, hd = W / 2.0, D / 2.0
    span = max(1e-6, h1 - h0)

    def deform(x, y, z):
        u = min(1.0, max(0.0, (z - h0) / span))
        tx = min(1.0, abs(x) / hw)
        ty = min(1.0, abs(y) / hd)
        k = (tx ** sharp) * (ty ** sharp) * ((1.0 - u) ** decay)
        sx = 1.0 if x >= 0 else -1.0
        sy = 1.0 if y >= 0 else -1.0
        return (x + out * sx * k, y + out * sy * k, z + lift * k)

    return deform


def apply_deform(obj, deform):
    for v in obj.data.vertices:
        v.co = deform(v.co.x, v.co.y, v.co.z)
    obj.data.update()


# ------------------------------------------------------- 격자면 + 기와골


def _add_grid(bm, P, nu, nv):
    """매개변수 함수 P(u,v) 로 격자면을 만들고 정점 배열을 돌려준다."""
    grid = []
    for i in range(nu + 1):
        row = []
        u = i / nu
        for j in range(nv + 1):
            row.append(bm.verts.new(P(u, j / nv)))
        grid.append(row)
    for i in range(nu):
        for j in range(nv):
            a, b, c, d = grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]
            # 삼각형 영역에서는 정점이 겹칠 수 있으므로 축약면을 건너뛴다
            if len({a, b, c, d}) < 3:
                continue
            try:
                bm.faces.new([a, b, c, d])
            except ValueError:
                pass
    return grid


def _add_ribs(bm, P, n_rib, n_seg, axis, r=0.085):
    """수키와(볼록 기와골). axis='v' 면 v 방향으로, 'u' 면 u 방향으로 흐른다."""
    for k in range(n_rib + 1):
        t = k / n_rib
        prev = None
        for s in range(n_seg + 1):
            w = s / n_seg
            u, v = (t, w) if axis == 'v' else (w, t)
            x, y, z = P(u, v)
            # 흐름 방향의 접선을 구해 단면을 세운다
            eps = 1e-3
            u2, v2 = (t, min(1.0, w + eps)) if axis == 'v' else (min(1.0, w + eps), t)
            x2, y2, z2 = P(u2, v2)
            tx, ty, tz = x2 - x, y2 - y, z2 - z
            tl = math.sqrt(tx * tx + ty * ty + tz * tz) or 1.0
            tx, ty, tz = tx / tl, ty / tl, tz / tl
            # 접선에 수직인 수평 벡터
            nx, ny = -ty, tx
            nl = math.hypot(nx, ny) or 1.0
            nx, ny = nx / nl, ny / nl
            ring = []
            for a_i in range(5):
                a = math.pi * a_i / 4
                ring.append(bm.verts.new((
                    x + nx * r * math.cos(a),
                    y + ny * r * math.cos(a),
                    z + r * math.sin(a) + r * 0.35)))
            if prev:
                for i in range(4):
                    if len({prev[i], prev[i + 1], ring[i + 1], ring[i]}) < 3:
                        continue
                    try:
                        bm.faces.new([prev[i], prev[i + 1], ring[i + 1], ring[i]])
                    except ValueError:
                        pass
            prev = ring


def _prism(bm, p0, p1, r, sides=6, square=False):
    """p0→p1 을 잇는 각기둥. square=True 면 네모(부연), 아니면 다각형(서까래).

    삼각형 수가 부재 수에 정비례하므로(한 채에 200~260개) 단면을 6각으로
    억제한다. 아래에서 올려다볼 때 6각과 12각은 구별되지 않는다.
    """
    import mathutils
    a = mathutils.Vector(p0)
    b = mathutils.Vector(p1)
    d = b - a
    if d.length < 1e-6:
        return
    d.normalize()
    up = mathutils.Vector((0.0, 0.0, 1.0))
    if abs(d.dot(up)) > 0.99:
        up = mathutils.Vector((1.0, 0.0, 0.0))
    u = d.cross(up).normalized()
    v = d.cross(u).normalized()

    if square:
        offs = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
        ring = [(u * (r * ox) + v * (r * oy)) for ox, oy in offs]
    else:
        ring = []
        for i in range(sides):
            t = 2.0 * math.pi * i / sides
            ring.append(u * (r * math.cos(t)) + v * (r * math.sin(t)))

    va = [bm.verts.new(a + o) for o in ring]
    vb = [bm.verts.new(b + o) for o in ring]
    n = len(ring)
    for i in range(n):
        j = (i + 1) % n
        try:
            bm.faces.new([va[i], va[j], vb[j], vb[i]])
        except ValueError:
            pass
    for cap in (va, list(reversed(vb))):
        try:
            bm.faces.new(cap)
        except ValueError:
            pass


def build_gyeopcheoma(bm, hw, hd, z_slope, eave_out, *,
                      pitch=0.31, dia=0.165, b=0.45, thickness=0.26,
                      inset=0.35, chakgo=True, pyeonggodae=True):
    """겹처마 — 서까래(원형) 위에 부연(각형)이 한 번 더 나간다.

    이 프로젝트 건물은 전부 겹처마다. 아래에서 보면 **서까래 마구리가 두 줄로
    층져** 보이는데, 그게 한식 처마의 가장 눈에 띄는 특징이다.

    r 은 용마루에서 잰 수평거리이고 z_slope(r) 이 지붕면 높이다. RoofProfile 을
    쓰면 마지막 구간이 부연 물매라, 부연을 z_slope 위에 그대로 놓기만 해도
    서까래보다 완만해진다 — 각도를 따로 계산할 필요가 없다.

      서까래  지름 dia ≈ 처마깊이/10.6 (석어당·준명당 실측 모두 165mm)
      부연    한 변 0.85·dia 의 각재. 개수는 서까래와 **같다**
      부연착고 둘 사이를 막는 연속 띠
      평고대  초매기(서까래 끝) · 이매기(부연 끝) 두 줄.
              처마선을 그대로 따라가므로 **앙곡·안허리곡의 검산기**가 된다 —
              이게 매끈하지 않으면 곡선이 틀린 것이다.

    변형 전 좌표계에서 만든다. 호출부가 나중에 apply_deform 을 걸면 지붕면과
    함께 움직인다.
    """
    b = max(0.05, min(b, eave_out * 0.6))
    # **피치는 지름에서 나온다.** 고정값을 쓰면 큰 건물에서 서까래가 서로
    # 붙어 판때기가 된다 (사정전에서 순간격 4.6cm 가 나왔다).
    # 실측: 석어당 D165 @ 피치 307 → 피치 ≈ 1.86 × 지름.
    pitch = max(pitch, dia * 1.86)
    sq = dia * 0.425                       # 부연 반치수
    drop_r = thickness + dia * 0.75        # 지붕면 아래로 서까래 중심까지
    drop_b = thickness + dia * 0.42        # 부연은 서까래 위에 얹히므로 덜 내린다

    def emit(half_along, half_out, axis):
        """axis='y' 면 서까래가 ±y 로 뻗고 처마선이 x 를 따라 흐른다."""
        span = 2.0 * half_along - 2.0 * inset
        n = max(2, int(round(span / pitch)))
        r_in = half_out - eave_out - 0.25   # 기둥열보다 조금 안쪽에서 시작
        r_mid = half_out - b                # 서까래 끝 = 초매기
        r_out = half_out                    # 부연 끝  = 이매기
        for sgn in (-1.0, 1.0):
            for i in range(n + 1):
                t = -half_along + inset + span * i / n
                def P(r, drop):
                    z = z_slope(r) - drop
                    return (t, sgn * r, z) if axis == 'y' else (sgn * r, t, z)
                _prism(bm, P(r_in, drop_r), P(r_mid, drop_r), dia / 2.0, 6)
                _prism(bm, P(r_mid, drop_b), P(r_out, drop_b), sq, square=True)
            # 부연착고 — 서까래 끝과 부연 사이를 막는 띠
            if chakgo:
                z = z_slope(r_mid) - drop_b
                if axis == 'y':
                    bm_box(bm, 0.0, sgn * r_mid, z + dia * 0.30,
                           span + 2 * inset, dia * 0.30, dia * 0.62)
                else:
                    bm_box(bm, sgn * r_mid, 0.0, z + dia * 0.30,
                           dia * 0.30, span + 2 * inset, dia * 0.62)
            # 평고대 두 줄
            if pyeonggodae:
                for r, drop, w in ((r_mid, drop_r, dia * 0.55),
                                   (r_out, drop_b, dia * 0.62)):
                    z = z_slope(r) - drop
                    if axis == 'y':
                        bm_box(bm, 0.0, sgn * r, z, span + 2 * inset, w, w)
                    else:
                        bm_box(bm, sgn * r, 0.0, z, w, span + 2 * inset, w)

    emit(hw, hd, 'y')      # 전·후 처마
    emit(hd, hw, 'x')      # 좌·우 처마


def _faces_up(bm):
    """지붕면의 노멀을 모두 위쪽으로 통일한다.

    영역마다 매개변수 방향이 달라(좌우/전후 대칭) 면의 감김이 뒤집히는데,
    그대로 두면 Solidify 가 위로 두께를 만들어 수키와를 덮어버린다.
    """
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    bm.normal_update()


def _sweep_box(bm, p0, p1, w, h):
    """두 점을 잇는 각진 마루(용마루·추녀마루) 를 만든다."""
    dx, dy, dz = (p1[i] - p0[i] for i in range(3))
    ln = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    dx, dy, dz = dx / ln, dy / ln, dz / ln
    nx, ny = -dy, dx
    nl = math.hypot(nx, ny) or 1.0
    nx, ny = nx / nl, ny / nl
    rings = []
    for p in (p0, p1):
        ring = []
        for sgn_n, sgn_z in ((-1, 0), (1, 0), (1, 1), (-1, 1)):
            ring.append(bm.verts.new((
                p[0] + nx * w / 2 * sgn_n,
                p[1] + ny * w / 2 * sgn_n,
                p[2] + h * sgn_z)))
        rings.append(ring)
    a, b = rings
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new([a[i], a[j], b[j], b[i]])
    bm.faces.new(list(reversed(a)))
    bm.faces.new(b)


# ------------------------------------------------------------ 지붕 본체


def build_hip_gable_roof(name, coll, W, D, h0, h1,
                         ridge_ratio=0.58, gable_ratio=0.52,
                         lift=1.00, out=0.55, thickness=0.32,
                         rib_pitch=0.33, rafters=True, concavity=1.42,
                         pal=None, ornaments='full', profile=None,
                         eave_out=None, rafter_pitch=0.31, purlins='auto'):
    """팔작지붕 한 채. gable_ratio=1.0 이면 우진각지붕이 된다.

    W, D  : 처마 끝 기준 지붕 크기
    h0, h1: 처마 높이, 용마루 높이
    ridge_ratio : 용마루 길이 / W  (합각 위치를 정한다)
    gable_ratio : 합각 밑변이 놓이는 높이 비율 (h0→h1 사이).
                  **1.0 이면 합각이 사라져 우진각지붕**(대한문 등)이 된다.
                  ridge_ratio 를 0 으로 줄이는 방식은 쓰면 안 된다 —
                  합각이 남아 지붕을 뚫고 서고 0면적 면이 대량 생긴다.
    concavity   : 지붕면의 조로 곡선. 1이면 직선, 클수록 오목해진다.
    pal         : 부재 역할 → 재질 키. 백골집은 hanok.BAEKGOL 을 넘긴다.
    ornaments   : 'full'       취두 + 잡상 (정전·정문)
                  'ridge_only' 취두만          (준명당·즉조당)
                  'none'       둘 다 없음      (석어당 백골집)
    profile     : roofprofile.RoofProfile. 주면 3구간 물매(단연·장연·부연)를
                  쓰고 concavity 는 무시된다. None 이면 예전 곡선 그대로다.
                  **h0/h1 은 profile 과 반드시 일치시켜 넘길 것** — 합각 높이
                  h2 와 마루 스윕이 아직 h0/h1 을 직접 쓴다.
    """
    pal = pal or DANCHEONG

    # gable_ratio = 1.0 이면 합각이 사라지고 우진각지붕이 된다.
    #   h2 = h1, yg = 0 이 되어 P_side 와 P_end 가 항등적으로 일치하고
    #   추녀선이 정확히 닫힌다 (대한문·궁궐 정문 형식).
    # 반드시 **입력에서** 판정할 것. 0.999 같은 값이 들어오면 yg 가 아주 작지만
    # 0 이 아니라, 0면적 쿼드와 지붕을 뚫고 선 합각벽이 생긴다.
    hipped = (gable_ratio >= 0.995)
    if hipped:
        gable_ratio = 1.0

    hw, hd = W / 2.0, D / 2.0
    xg = hw * ridge_ratio                       # 합각벽이 서는 x
    h2 = h0 + (h1 - h0) * gable_ratio           # 추녀면이 합각을 만나는 높이
    span = h1 - h0

    # 전역 스위치가 켜져 있으면 여기서 프로파일을 만든다. 호출부는 처마
    # 내밀기만 넘기면 된다 — 안 넘기면 지붕 크기에서 추정한다.
    if profile is None and USE_MULMAE:
        if eave_out is None:
            eave_out = max(0.8, min(hd * 0.24, 3.4))
        _b = eave_out * BUYEON_RATIO / (1.0 + BUYEON_RATIO)
        # **삼량가에는 중도리가 없으므로 꺾임도 없다.**
        # 석어당 상층이 그렇다 — 실측(EM050289 p.166 앙시도)에서 도리 띠가
        # 3줄뿐이고 물매는 28.7° 단일 경사다. 여기에 45° 단연을 넣으면
        # 있지도 않은 부재의 꺾임을 만드는 셈이다.
        _struct = max(0.0, D - 2.0 * eave_out)
        _three = (purlins == 3) or (purlins == 'auto' and _struct <= 4.5)
        profile = RoofProfile(R=hd, h0=h0, h1=h1, b=_b, jouro=0.03,
                              m_dan=(None if _three else 10.0), name=name)
        for _msg in profile.assert_sane(strict=False):
            print("  [물매 경고] %s: %s" % (name, _msg))

    # 종단면 곡선. profile 을 주면 3구간 물매(단연·장연·부연)를 쓰고,
    # None 이면 예전 거듭제곱 곡선을 그대로 쓴다 — 기존 출력이 바뀌지 않는다.
    #
    # 예전 곡선은 꺾임이 없다: 용마루 45° 에서 처마 0° 까지 매끄럽게 흘러
    # **평평해야 할 곳이 가파르고 가팔라야 할 곳이 평평하다.**
    # 실측(석어당 2015)은 단연 45° / 장연 28° / 부연 22° 의 두 번 꺾인 선이다.
    if profile is not None:
        def z_slope(y, _p=profile):
            return _p.z(abs(y))

        # 합각 밑변 — 3구간 모델에는 닫힌 역함수가 없어 이분법으로 푼다
        yg = profile.r_at_z(h2)
    else:
        def prof(t):
            """t=0 처마 → t=1 용마루. 위로 갈수록 급해지는 오목 곡선."""
            return t ** concavity

        def z_slope(y):                         # 전후 경사면 (조로 곡선)
            return h0 + span * prof(1.0 - abs(y) / hd)

        # 합각 밑변이 놓이는 y — 곡선의 역함수로 구한다
        yg = hd * (1.0 - gable_ratio ** (1.0 / concavity))

    surf = bmesh.new()
    ribs = bmesh.new()

    # --- 전후 경사면: 가운데(사다리꼴) + 좌우(추녀쪽 삼각형)
    for sy in (-1.0, 1.0):
        def P_mid(u, v, sy=sy):
            x = -xg + 2 * xg * u
            y = sy * hd * (1.0 - v)
            return (x, y, z_slope(y))

        nu = max(6, int(2 * xg / rib_pitch / 3))
        _add_grid(surf, P_mid, nu, 10)
        _add_ribs(ribs, P_mid, max(4, int(2 * xg / rib_pitch)), 12, 'v')

        for sx in (-1.0, 1.0):
            def P_side(u, v, sx=sx, sy=sy):
                x = sx * (xg + (hw - xg) * u)
                y_top = sy * (yg + (hd - yg) * u)
                y = sy * hd + (y_top - sy * hd) * v
                return (x, y, z_slope(y))

            _add_grid(surf, P_side, 8, 10)
            _add_ribs(ribs, P_side, max(3, int((hw - xg) / rib_pitch)), 12, 'v')

    # --- 좌우 추녀면 (사다리꼴, x 방향으로만 경사)
    for sx in (-1.0, 1.0):
        def P_end(u, v, sx=sx):
            x = sx * (hw - (hw - xg) * u)
            y_span = hd - (hd - yg) * u
            y = -y_span + 2 * y_span * v
            # 추녀마루가 전후 경사면과 정확히 맞물리도록 같은 곡선에서 높이를 딴다
            return (x, y, z_slope(y_span))

        # 우진각에서는 추녀면이 주 시각면이 되므로 격자를 촘촘하게
        _add_grid(surf, P_end, 14 if hipped else 8, 14)
        _add_ribs(ribs, P_end, max(4, int(2 * hd / rib_pitch)),
                  14 if hipped else 10, 'u')

    # --- 합각벽 (박공). 윗변은 지붕면과 같은 조로 곡선을 따라간다
    # 우진각은 합각 자체가 없다 (yg = 0 이라 만들면 면 0개짜리 껍데기가 된다).
    NG = 16
    gable_edge = [(-yg + 2 * yg * i / NG,
                   z_slope(-yg + 2 * yg * i / NG)) for i in range(NG + 1)]

    gable = None
    if not hipped:
        gable = bmesh.new()
        for sx in (-1.0, 1.0):
            x = sx * xg
            prev = None
            for y, zt in gable_edge:
                top = gable.verts.new((x, y, zt))
                bot = gable.verts.new((x, y, h2))
                if prev is not None:
                    pt, pb = prev
                    if abs(zt - h2) > 1e-5 or abs(pt.co.z - h2) > 1e-5:
                        face = [pb, pt, top, bot]
                        gable.faces.new(face if sx > 0 else list(reversed(face)))
                prev = (top, bot)

    # --- 마루: 용마루 / 추녀마루 / 내림마루
    ridge = bmesh.new()
    _sweep_box(ridge, (-xg - 0.35, 0, h1), (xg + 0.35, 0, h1), 0.62, 0.78)
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            _sweep_box(ridge, (sx * hw, sy * hd, h0),
                       (sx * xg, sy * yg, h2), 0.46, 0.52)      # 추녀마루
        # 내림마루 — 합각 윗변의 곡선을 따라 마디마디 잇는다.
        # 우진각은 yg=0 이라 전 구간이 p0==p1 인 축약 스윕이 되므로 건너뛴다.
        if not hipped:
            for i in range(NG):
                y0, z0_ = gable_edge[i]
                y1, z1_ = gable_edge[i + 1]
                _sweep_box(ridge, (sx * xg, y0, z0_), (sx * xg, y1, z1_), 0.40, 0.44)
        # 취두 — 용마루 양 끝 장식
        if ornaments in ('full', 'ridge_only'):
            bm_box(ridge, sx * (xg + 0.45), 0, h1 + 0.72, 0.72, 0.66, 1.30)

    # --- 잡상 / 서까래
    if rafters:
        if ornaments == 'full':                  # 잡상
            for sx in (-1.0, 1.0):
                for sy in (-1.0, 1.0):
                    for i in range(5):
                        t = 0.10 + i * 0.15
                        bx = sx * hw + (sx * xg - sx * hw) * t
                        by = sy * hd + (sy * yg - sy * hd) * t
                        bz = h0 + (h2 - h0) * t + 0.42
                        bm_box(ridge, bx, by, bz, 0.24, 0.24, 0.34)

        eaves = bmesh.new()
        if profile is not None:
            # 겹처마 — 서까래 지름은 건물 크기에서 나온다.
            # 실측: 석어당 처마 1,740 / 연목 165, 준명당 1,769 / 165
            # → 규칙 "처마깊이/10" 은 두 건물 모두 6~7% 크다. 10.6 으로 나눈다.
            eo = eave_out if eave_out else max(0.8, hd * 0.18)
            build_gyeopcheoma(eaves, hw, hd, z_slope, eo,
                              pitch=rafter_pitch, dia=eo / 10.6,
                              b=profile.b, thickness=thickness)
        else:
            # 예전 처마. 서까래가 건물 크기와 무관하게 0.16/0.13 고정이고
            # 처마선 안쪽에 짧게 붙어 있을 뿐이라 겹처마로 보이지 않는다.
            n = int(W / 0.42)
            for i in range(n + 1):
                x = -hw + W * i / n
                for sy in (-1.0, 1.0):
                    bm_box(eaves, x, sy * (hd - 0.55), h0 - 0.16, 0.16, 1.5, 0.16)
                    bm_box(eaves, x, sy * (hd - 0.30), h0 + 0.02, 0.13, 1.0, 0.13)
            m = int(D / 0.42)
            for j in range(m + 1):
                y = -hd + D * j / m
                for sx in (-1.0, 1.0):
                    bm_box(eaves, sx * (hw - 0.55), y, h0 - 0.16, 1.5, 0.16, 0.16)
                    bm_box(eaves, sx * (hw - 0.30), y, h0 + 0.02, 1.0, 0.13, 0.13)
    else:
        eaves = None

    # --- 오브젝트화 + 변형 적용
    deform = make_deform(W, D, h0, h1, lift, out)
    objs = []

    _faces_up(surf)
    ob_surf = bm_to_object(surf, name + "_지붕면", pal['tile'], coll)
    solid = ob_surf.modifiers.new("두께", 'SOLIDIFY')
    solid.thickness = thickness
    solid.offset = -1.0
    objs.append(ob_surf)
    objs.append(bm_to_object(ribs, name + "_수키와", pal['tile'], coll))
    objs.append(bm_to_object(ridge, name + "_마루", pal['tile'], coll))
    if gable is not None:
        ob_gable = bm_to_object(gable, name + "_합각", pal['gable'], coll)
        gs = ob_gable.modifiers.new("두께", 'SOLIDIFY')
        gs.thickness = 0.45
        gs.offset = 0.0
        objs.append(ob_gable)
    if eaves:
        objs.append(bm_to_object(eaves, name + "_서까래", pal['rafter'], coll))

    for ob in objs:
        apply_deform(ob, deform)

    return objs


def build_gable_roof(name, coll, W, D, h0, h1,
                     lift=0.55, out=0.28, thickness=0.26,
                     rib_pitch=0.31, concavity=1.35, pal=None):
    """맞배지붕 — 회랑·행각처럼 길게 이어지는 건물용.

    용마루가 X 축을 따라 W 만큼 뻗고, 앞뒤 두 면만 경사진다.
    양 끝은 박공(합각 없이 수직으로 잘린 면)으로 마감한다.
    """
    pal = pal or DANCHEONG
    hw, hd = W / 2.0, D / 2.0
    span = h1 - h0

    def z_slope(y):
        return h0 + span * ((1.0 - abs(y) / hd) ** concavity)

    surf = bmesh.new()
    ribs = bmesh.new()
    ridge = bmesh.new()
    gable = bmesh.new()

    for sy in (-1.0, 1.0):
        def P(u, v, sy=sy):
            y = sy * hd * (1.0 - v)
            return (-hw + W * u, y, z_slope(y))
        _add_grid(surf, P, max(8, int(W / 2.0)), 8)
        _add_ribs(ribs, P, max(6, int(W / rib_pitch)), 10, 'v')

    # 박공면 — 지붕 곡선을 따라 내려오는 삼각 벽
    NG = 14
    edge = [(-hd + 2 * hd * i / NG, z_slope(-hd + 2 * hd * i / NG))
            for i in range(NG + 1)]
    for sx in (-1.0, 1.0):
        x, prev = sx * hw, None
        for y, zt in edge:
            top = gable.verts.new((x, y, zt))
            bot = gable.verts.new((x, y, h0 - 0.25))
            if prev is not None:
                pt, pb = prev
                if zt > h0 - 0.24 or pt.co.z > h0 - 0.24:
                    f = [pb, pt, top, bot]
                    gable.faces.new(f if sx > 0 else list(reversed(f)))
            prev = (top, bot)
        # 박공(내림)마루
        for i in range(NG):
            y0, z0_ = edge[i]
            y1, z1_ = edge[i + 1]
            _sweep_box(ridge, (x, y0, z0_), (x, y1, z1_), 0.34, 0.38)

    _sweep_box(ridge, (-hw - 0.25, 0, h1), (hw + 0.25, 0, h1), 0.50, 0.58)

    # 서까래
    eaves = bmesh.new()
    n = max(2, int(W / 0.42))
    for i in range(n + 1):
        x = -hw + W * i / n
        for sy in (-1.0, 1.0):
            bm_box(eaves, x, sy * (hd - 0.45), h0 - 0.14, 0.15, 1.2, 0.15)

    deform = make_deform(W, D, h0, h1, lift, out)
    _faces_up(surf)
    ob_surf = bm_to_object(surf, name + "_지붕면", pal['tile'], coll)
    sm = ob_surf.modifiers.new("두께", 'SOLIDIFY')
    sm.thickness = thickness
    sm.offset = -1.0

    objs = [ob_surf,
            bm_to_object(ribs, name + "_수키와", pal['tile'], coll),
            bm_to_object(ridge, name + "_마루", pal['tile'], coll),
            bm_to_object(gable, name + "_박공", pal['gable'], coll),
            bm_to_object(eaves, name + "_서까래", pal['rafter'], coll)]
    for ob in objs:
        apply_deform(ob, deform)
    return objs


def build_skirt_roof(name, coll, W, D, W2, D2, h0, h1,
                     lift=0.95, out=0.50, thickness=0.30,
                     rib_pitch=0.33, concavity=1.35, pal=None):
    """중층 건물의 하층 지붕(裳簷).

    처마 사각형(W×D, 높이 h0)에서 상층 벽에 물리는 사각형(W2×D2, 높이 h1)까지
    네 면이 감싸 올라가는 형태. 상층은 이 위에 다시 팔작지붕을 얹는다.
    """
    pal = pal or DANCHEONG
    hw, hd = W / 2.0, D / 2.0
    hw2, hd2 = W2 / 2.0, D2 / 2.0
    span = h1 - h0

    surf = bmesh.new()
    ribs = bmesh.new()
    ridge = bmesh.new()

    def slope(sy, swap):
        """swap=False 면 전후면(y 방향 경사), True 면 좌우면(x 방향 경사)."""
        def P(u, v):
            t = v ** (1.0 / concavity)          # 조로 곡선
            if not swap:
                y = sy * (hd + (hd2 - hd) * t)
                x = (-hw + 2 * hw * u) + ((-hw2 + 2 * hw2 * u) - (-hw + 2 * hw * u)) * t
            else:
                x = sy * (hw + (hw2 - hw) * t)
                y = (-hd + 2 * hd * u) + ((-hd2 + 2 * hd2 * u) - (-hd + 2 * hd * u)) * t
            return (x, y, h0 + span * v)
        return P

    for sy in (-1.0, 1.0):
        for swap in (False, True):
            P = slope(sy, swap)
            _add_grid(surf, P, 20, 8)
            edge = W if not swap else D
            _add_ribs(ribs, P, max(6, int(edge / rib_pitch)), 10, 'v')

    # 추녀마루 4개 + 상층벽에 닿는 수평 마루
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            _sweep_box(ridge, (sx * hw, sy * hd, h0),
                       (sx * hw2, sy * hd2, h1), 0.42, 0.48)
    for sy in (-1.0, 1.0):
        _sweep_box(ridge, (-hw2, sy * hd2, h1), (hw2, sy * hd2, h1), 0.40, 0.42)
        _sweep_box(ridge, (sy * hw2, -hd2, h1), (sy * hw2, hd2, h1), 0.40, 0.42)

    # 서까래
    eaves = bmesh.new()
    n = int(W / 0.42)
    for i in range(n + 1):
        x = -hw + W * i / n
        for sy in (-1.0, 1.0):
            bm_box(eaves, x, sy * (hd - 0.55), h0 - 0.16, 0.16, 1.5, 0.16)
            bm_box(eaves, x, sy * (hd - 0.30), h0 + 0.02, 0.13, 1.0, 0.13)
    m = int(D / 0.42)
    for j in range(m + 1):
        y = -hd + D * j / m
        for sx in (-1.0, 1.0):
            bm_box(eaves, sx * (hw - 0.55), y, h0 - 0.16, 1.5, 0.16, 0.16)
            bm_box(eaves, sx * (hw - 0.30), y, h0 + 0.02, 1.0, 0.13, 0.13)

    deform = make_deform(W, D, h0, h1, lift, out)
    _faces_up(surf)
    ob_surf = bm_to_object(surf, name + "_하층지붕면", pal['tile'], coll)
    sm = ob_surf.modifiers.new("두께", 'SOLIDIFY')
    sm.thickness = thickness
    sm.offset = -1.0

    objs = [ob_surf,
            bm_to_object(ribs, name + "_하층수키와", pal['tile'], coll),
            bm_to_object(ridge, name + "_하층마루", pal['tile'], coll),
            bm_to_object(eaves, name + "_하층서까래", pal['rafter'], coll)]
    for ob in objs:
        apply_deform(ob, deform)
    return objs
