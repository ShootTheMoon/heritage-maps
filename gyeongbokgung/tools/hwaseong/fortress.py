# -*- coding: utf-8 -*-
"""화성 성곽 부재 — 홍예 · 여장 · 총안 · 옹성 · 전돌 몸체.

hanok.py 는 궁궐 전각 부재(기둥·공포·지붕)라 성곽 부재가 없다. 여기 둔다.

**불리언을 쓰지 않는다.** 홍예 구멍도 총안도 박스/프리즘 배열로 만든다.
불리언은 쿼드를 깨고 삼각형 수가 예측 불가하게 튀는데, 오버데어 상한이
파일당 3만이라 그게 그대로 파일 수로 온다(export_overdare.py:47).
"""

import math

import bmesh

from hanok import bm_box, bm_to_object


# --------------------------------------------------------------- 석재 켜쌓기


def bm_coursed(bm, cx, cy, z0, h, sx, sy, course=0.78, inset=0.13, batter=0.0):
    """장대석을 켜켜이 쌓은 벽체.

    통짜 박스로 두면 아무리 커도 흰 판자로 보인다 — 실제로 렌더에서
    그렇게 나왔다. 켜마다 들이밀어 수평 줄눈 그림자를 만든다.
    삼각형은 켜 수에 비례해 늘지만 켜당 6면뿐이라 싸다.

    **들이밈 깊이가 관건이다.** 처음에 5 cm 로 잡았더니 50 m 거리에서
    그림자가 안 잡혀 여전히 흰 판자였다. 13 cm 는 돼야 읽힌다 —
    실제 장대석 줄눈보다 과장이지만 축소해서 보는 것이 목적이다.
    """
    n = max(1, int(round(h / course)))
    ch = h / n
    for i in range(n):
        z = z0 + ch * (i + 0.5)
        f = (i + 0.5) / n
        d = inset if (i % 2) else 0.0          # 켜마다 번갈아 들이민다
        bm_box(bm, cx, cy, z,
               sx - 2.0 * (batter * f + d), sy - 2.0 * (batter * f + d), ch)


def bm_hyeonan(bm, cx, cy, z_top, depth, length, dia, sgn=-1.0):
    """현안(縣眼) — 성벽 바깥면을 위에서 아래로 비스듬히 뚫은 긴 홈.

    의궤가 길이와 지름을 척으로 적어 두는 부재다(동옹성 "길이 8척 5촌
    지름 1척"). 관통시키지 않고 바깥면에 파인 홈으로 표현한다 — 총안과
    같은 이유로 불리언을 쓰지 않는다.
    """
    n = 6
    for i in range(n):
        t = (i + 0.5) / n
        bm_box(bm, cx, cy + sgn * (depth / 2.0 - 0.04 - t * 0.10),
               z_top - length * t, dia, 0.12, length / n + 0.02)


# ------------------------------------------------------------------ 원호 벽


def bm_arc_wall(bm, cx, cy, z0, h, r_in, r_out, a0, a1, seg=24):
    """중심 (cx,cy) 를 도는 원호 벽 한 토막. 각도는 라디안.

    회전 오브젝트를 쓰지 않고 정점을 직접 놓는다 — 익스포터가 matrix_world 를
    굽기는 하지만, 조각마다 오브젝트를 만들면 MeshPart 수가 그만큼 늘어난다.
    """
    z1 = z0 + h
    prev = None
    for i in range(seg + 1):
        a = a0 + (a1 - a0) * i / seg
        ca, sa = math.cos(a), math.sin(a)
        ring = [
            bm.verts.new((cx + r_in * ca, cy + r_in * sa, z0)),
            bm.verts.new((cx + r_out * ca, cy + r_out * sa, z0)),
            bm.verts.new((cx + r_out * ca, cy + r_out * sa, z1)),
            bm.verts.new((cx + r_in * ca, cy + r_in * sa, z1)),
        ]
        if prev is not None:
            p = prev
            bm.faces.new([p[0], p[1], ring[1], ring[0]])   # 아랫면
            bm.faces.new([p[1], p[2], ring[2], ring[1]])   # 바깥면
            bm.faces.new([p[2], p[3], ring[3], ring[2]])   # 윗면
            bm.faces.new([p[3], p[0], ring[0], ring[3]])   # 안쪽면
        else:
            bm.faces.new(ring)                              # 시작 마구리
        prev = ring
    bm.faces.new(list(reversed(prev)))                      # 끝 마구리


# ------------------------------------------------------------------ 홍예문


def build_hongye(name, coll, sx, sy, wall_h, open_w, open_h,
                 slices=18, mat='granite_d', ring_mat='granite'):
    # 큰 석재 덩어리는 'granite'(알베도 0.42) 대신 'granite_d'(0.29) 를 쓴다.
    # 0.42 는 경복궁 월대 기준이라 밝아서, 바로 옆에 놓이는 KCISA 스캔
    # 성벽보다 하얗게 떠 보인다. 테두리·미석 같은 좁은 면만 밝은 쪽으로 남긴다.
    """홍예문이 뚫린 육축(석축) 한 덩어리.

    통로는 y 축을 따라 뚫린다. 반원 홍예 — 스프링 라인 위가 반지름
    open_w/2 인 반원이고, 그 아래는 수직 벽이다.

    구멍은 파는 게 아니라 **남는 부분만 쌓는다**:
      좌·우 벽 + 홍예 위를 세로로 썬 슬라이스들.
    """
    bm = bmesh.new()
    hw = open_w / 2.0
    spring = open_h - hw                      # 반원이 시작하는 높이

    # 좌우 무사(벽) — 통짜가 아니라 장대석 켜쌓기로 쌓는다
    side = (sx - open_w) / 2.0
    for s in (-1.0, 1.0):
        bm_coursed(bm, s * (hw + side / 2.0), 0.0, 0.0, wall_h, side, sy)

    # 홍예 위 — x 를 잘라 각 슬라이스를 아치 곡선 위에서 천장까지 채운다
    for i in range(slices):
        x0 = -hw + open_w * i / slices
        x1 = -hw + open_w * (i + 1) / slices
        xm = (x0 + x1) / 2.0
        z = spring + math.sqrt(max(0.0, hw * hw - xm * xm))
        if z >= wall_h - 1e-6:
            continue
        bm_box(bm, xm, 0.0, (z + wall_h) / 2.0, x1 - x0, sy, wall_h - z)
    ob = bm_to_object(bm, name, mat, coll)

    # 홍예석(테두리) — 통로 양 끝에 살짝 내밀어 그림자선을 만든다
    bm = bmesh.new()
    t, depth = 0.34, 0.16
    for face_y in (-sy / 2.0 - depth / 2.0, sy / 2.0 + depth / 2.0):
        for i in range(slices):
            a0 = math.pi * i / slices
            a1 = math.pi * (i + 1) / slices
            am = (a0 + a1) / 2.0
            xm = -hw * math.cos(am)
            zm = spring + hw * math.sin(am)
            w = open_w * math.pi / (2.0 * slices) + 0.06
            bm_box(bm, xm, face_y, zm, w, depth, t)
        for s in (-1.0, 1.0):
            bm_box(bm, s * (hw + t / 2.0), face_y, spring / 2.0, t, depth, spring)
    bm_to_object(bm, name + "_홍예석", ring_mat, coll)
    return ob


# ------------------------------------------------------------------ 여장


YEOJANG_H = 1.24          # 여장 몸체 높이
YEOJANG_T = 0.52          # 두께
MISEOK_T = 0.16           # 미석 두께
TAGU_W = 0.62             # 타구(여장 사이 낮은 틈) 폭
SEG_LEN = 3.20            # 여장 한 타(垜) 길이


def _chongan(bm, x, y, z, sx, sy, sz):
    """총안 — 실제로는 벽을 관통하는 경사 구멍이다. 게임 스케일에서는
    구멍을 뚫어 봐야 안 보이고 삼각형만 먹으므로, 살짝 파인 어두운 박스로
    표현한다. 불리언을 피하는 것과 같은 이유다."""
    bm_box(bm, x, y, z, sx, sy, sz)


def build_yeojang(name, coll, x0, x1, y, z0,
                  mat='floor', stone='granite', chongan=True,
                  h=None, t=None, seg_len=None, hole=None):
    """직선 구간 여장 — 미석 + 타(垜) + 타구 + 총안.

    x0→x1 로 뻗고 두께 중심이 y 다. 길이만 주면 임의 구간을 뽑을 수 있다.

    h / t / hole 은 의궤 실측값을 넘기기 위한 것이다. 창룡문·화서문은
    성가퀴 높이 4척 7촌, 두께 2척 1촌, 방안총혈 사방 8촌으로 적혀 있다.
    안 넘기면 모듈 기본값을 쓴다.
    """
    h = YEOJANG_H if h is None else h
    t = YEOJANG_T if t is None else t
    seg_len = SEG_LEN if seg_len is None else seg_len
    hole = 0.25 if hole is None else hole

    L = x1 - x0
    n = max(1, int(round(L / seg_len)))
    seg = L / n

    bm = bmesh.new()
    bm_box(bm, (x0 + x1) / 2.0, y, z0 + MISEOK_T / 2.0,
           L, t + 0.22, MISEOK_T)
    bm_to_object(bm, name + "_미석", stone, coll)

    bm = bmesh.new()
    zb = z0 + MISEOK_T
    for i in range(n):
        a = x0 + seg * i + TAGU_W / 2.0
        b = x0 + seg * (i + 1) - TAGU_W / 2.0
        bm_box(bm, (a + b) / 2.0, y, zb + h / 2.0, b - a, t, h)
        if not chongan:
            continue
        # 한 타에 원총안 1 + 근총안 2 가 기본 구성이다
        cw = (b - a) / 4.0
        _chongan(bm, (a + b) / 2.0, y - t / 2.0 + 0.06,
                 zb + h * 0.62, hole, 0.14, hole)
        for s in (-1.0, 1.0):
            _chongan(bm, (a + b) / 2.0 + s * cw, y - t / 2.0 + 0.06,
                     zb + h * 0.36, hole * 0.85, 0.14, hole * 0.85)
    return bm_to_object(bm, name, mat, coll)


def build_yeojang_arc(name, coll, cx, cy, r, a0, a1, z0, seg=20,
                      mat='floor', stone='granite'):
    """원호 구간 여장. 옹성 위에 얹는다."""
    bm = bmesh.new()
    bm_arc_wall(bm, cx, cy, z0, MISEOK_T,
                r - (YEOJANG_T + 0.22) / 2.0, r + (YEOJANG_T + 0.22) / 2.0,
                a0, a1, seg)
    bm_to_object(bm, name + "_미석", stone, coll)

    bm = bmesh.new()
    zb = z0 + MISEOK_T
    n = max(1, int(round(abs(a1 - a0) * r / SEG_LEN)))
    gap = TAGU_W / r
    for i in range(n):
        b0 = a0 + (a1 - a0) * i / n + gap / 2.0
        b1 = a0 + (a1 - a0) * (i + 1) / n - gap / 2.0
        bm_arc_wall(bm, cx, cy, zb, YEOJANG_H,
                    r - YEOJANG_T / 2.0, r + YEOJANG_T / 2.0,
                    b0, b1, max(2, seg // n))
    return bm_to_object(bm, name, mat, coll)


# ------------------------------------------------------------------ 옹성


def build_ongseong(name, coll, cx, cy, r, h, gap_deg, thick=1.9,
                   mat='granite_d', stone='granite'):
    """반원 옹성 — 성 바깥(-y)으로 돌출한다. 가운데가 개구부.

    개구부를 향해 두 갈래로 감싼다. 각도는 -y 방향(=-90도)을 중심으로
    좌우 대칭이고, gap_deg 만큼 가운데를 비운다.
    """
    g = math.radians(gap_deg) / 2.0
    mid = -math.pi / 2.0
    arcs = [(mid + g, mid + math.pi / 2.0), (mid - math.pi / 2.0, mid - g)]
    bm = bmesh.new()
    for a0, a1 in arcs:
        bm_arc_wall(bm, cx, cy, 0.0, h, r - thick / 2.0, r + thick / 2.0,
                    a0, a1, 28)
    ob = bm_to_object(bm, name, mat, coll)
    for i, (a0, a1) in enumerate(arcs):
        build_yeojang_arc("%s_여장_%d" % (name, i), coll, cx, cy, r,
                          a0, a1, h, mat=mat, stone=stone)
    return ob


# -------------------------------------------------------- 와장대·전붕판문


def build_wajangdae(name, coll, cx, y_top, z0, height, width, run,
                    steps=14, mat='granite', rail_mat='granite_d'):
    """와장대(臥長臺) 돌계단 — 육축 안쪽에서 성 위로 오르는 계단.

    창룡문 도설(의궤 p108): "좌우의 와장대는 길이가 각각 20척이고
    돌계단은 각각 14층이며 너비는 9척이다." 층수·너비·길이가 다 적힌
    부재라 그대로 세운다. 와장대는 계단 양옆을 비스듬히 누르는 긴 돌이다.
    """
    bm = bmesh.new()
    rise = height / steps
    for i in range(steps):
        d = run * (steps - i) / steps
        bm_box(bm, cx, y_top + d / 2.0, z0 + rise * (i + 0.5), width, d, rise)
    ob = bm_to_object(bm, name, mat, coll)

    # 양옆 와장대 — 경사진 긴 돌
    bm = bmesh.new()
    t = 0.34
    for s in (-1.0, 1.0):
        x = cx + s * (width / 2.0 + t / 2.0)
        for i in range(steps):
            d = run / steps
            bm_box(bm, x, y_top + run * (steps - i - 0.5) / steps,
                   z0 + rise * (i + 0.6), t, d, rise * 1.5)
    bm_to_object(bm, name + "_와장대", rail_mat, coll)
    return ob


def build_jeonbung_panmun(name, coll, x0, x1, y, z0, h, n,
                          mat='wood_dark', hole_mat='granite_d'):
    """전붕판문(戰棚板門) — 각루 바깥을 두른 판자문.

    동북각루 도설(의궤 p141): "전붕판문 16개를 설치하였는데, 만듦새는
    마치 병풍을 포개어 친 것 같다. 위에는 전안 각 1개씩을 내고,
    아래에 총안 각 2개씩을 뚫었다."
    병풍처럼 접힌 느낌을 내려고 한 짝씩 번갈아 조금씩 틀어 놓는다.
    """
    bm = bmesh.new()
    L = (x1 - x0) / n
    for i in range(n):
        cx = x0 + L * (i + 0.5)
        off = 0.05 if (i % 2) else -0.05          # 병풍처럼 접힌 자리
        bm_box(bm, cx, y + off, z0 + h / 2.0, L * 0.92, 0.10, h)
    ob = bm_to_object(bm, name, mat, coll)

    bm = bmesh.new()
    for i in range(n):
        cx = x0 + L * (i + 0.5)
        off = 0.05 if (i % 2) else -0.05
        bm_box(bm, cx, y + off - 0.04, z0 + h * 0.74, 0.13, 0.10, 0.20)   # 전안 1
        for s in (-1.0, 1.0):                                              # 총안 2
            bm_box(bm, cx + s * L * 0.22, y + off - 0.04, z0 + h * 0.34,
                   0.13, 0.10, 0.16)
    bm_to_object(bm, name + "_전안총안", hole_mat, coll)
    return ob


# ------------------------------------------------------------------ 전돌 몸체


def build_brick_body(name, coll, cx, cy, z0, h, sx, sy, batter=0.0,
                     levels=2, per_face=6, mat='floor'):
    """공심돈 전돌 몸체. 위로 살짝 좁아지고 층마다 면당 총안을 낸다.

    전돌은 장대석보다 켜가 훨씬 얇다. 벽돌 켜를 하나하나 세우면 삼각형이
    폭발하므로 6켜씩 묶은 정도의 줄눈만 넣는다 — 실루엣이 아니라 면의
    단조로움을 깨는 것이 목적이다.
    """
    bm = bmesh.new()
    bm_coursed(bm, cx, cy, z0, h, sx, sy,
               course=0.44, inset=0.035, batter=batter)

    # 층 사이 눈썹돌(미석) — 전돌 층이 몇인지 눈에 보이게 한다
    for i in range(1, levels):
        z = z0 + h * i / levels
        f = i / levels
        bm_box(bm, cx, cy, z, sx - 2 * batter * f + 0.24,
               sy - 2 * batter * f + 0.24, 0.14)
    ob = bm_to_object(bm, name, mat, coll)

    # 총안 — 면당 per_face 개, 층마다
    bm = bmesh.new()
    x0, y0 = sx / 2.0, sy / 2.0
    for lv in range(levels):
        f = (lv + 0.55) / levels
        z = z0 + h * f
        hx = x0 - batter * f
        hy = y0 - batter * f
        for k in range(per_face):
            u = -1.0 + 2.0 * (k + 0.5) / per_face
            bm_box(bm, cx + u * hx * 0.82, cy - hy + 0.05, z, 0.20, 0.12, 0.30)
            bm_box(bm, cx + u * hx * 0.82, cy + hy - 0.05, z, 0.20, 0.12, 0.30)
            bm_box(bm, cx - hx + 0.05, cy + u * hy * 0.82, z, 0.12, 0.20, 0.30)
            bm_box(bm, cx + hx - 0.05, cy + u * hy * 0.82, z, 0.12, 0.20, 0.30)
    bm_to_object(bm, name + "_총안", 'granite_d', coll)
    return ob
