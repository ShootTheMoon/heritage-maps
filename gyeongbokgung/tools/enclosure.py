# -*- coding: utf-8 -*-
"""근정전·사정전 일곽의 회랑(回廊)·담장·문.

부재는 모두 원점에서 X축을 길이 방향으로 삼아 만든 뒤,
오브젝트 트랜스폼으로 제자리에 앉힌다. 그래야 같은 생성기로
동서남북 네 면을 모두 만들 수 있다.
"""

import bpy
import bmesh
import math
import importlib

import hanok
import roof
importlib.reload(hanok)
importlib.reload(roof)

from hanok import (new_collection, bm_to_object, bm_box, build_columns,
                   build_beams, build_brackets, build_platform, build_stairs)

# ------------------------------------------------------------------ 제원

COR = dict(depth=4.4, bay=3.3, plat_h=0.85, col_h=3.60,
           eave=5.60, ridge=8.20, eave_out=2.20, end_out=0.90)

GATE = dict(
    bays_x=[4.2, 5.6, 4.2],          # 정면 3칸 = 14.0m
    bays_y=[3.0, 3.4, 3.0],          # 측면 3칸 = 9.4m
    plat=(20.0, 15.0, 1.30),
    floor=1.30, col_h=4.40,
    upper_x=[-5.6, 0.0, 5.6],        # 상층 기둥열
    upper_y=[-2.4, 2.4],
    high_col_top=10.20,
    low_eave=7.30, low_top=9.00,
    up_eave=11.30, up_ridge=15.20,
    eave_out_low=2.60, eave_out_up=2.40,
)

# 근정전 일곽 — 회랑이 두르는 사각형
ENC_X = 42.0          # 동서 회랑의 x
ENC_S = -78.0         # 남 회랑 (근정문)
ENC_N = 32.0          # 북 회랑
GATE_GAP = 20.0       # 남면 가운데 근정문 자리

# 사정전 일곽 — 담장
SJ_X = 30.0
SJ_S = 56.0
SJ_N = 98.0


def _place(objs, loc, rot_z=0.0):
    for ob in objs:
        ob.location = loc
        ob.rotation_euler.z = rot_z
    return objs


# -------------------------------------------------------------- 회랑 한 채


def build_corridor(name, coll, length, wall_side=1.0, roofed=True, walled=True):
    """회랑 한 구간. 길이 방향은 X, 바깥쪽(wall_side)에 벽을 세운다.

    walled=False 면 사방이 트인 문간채가 된다.
    """
    d = COR['depth']
    ph, ch = COR['plat_h'], COR['col_h']
    objs = []

    # 기단
    bm = bmesh.new()
    bm_box(bm, 0, 0, ph / 2, length + 0.5, d + 1.1, ph)
    bm_box(bm, 0, 0, ph + 0.06, length + 0.9, d + 1.5, 0.12)
    objs.append(bm_to_object(bm, name + "_기단", 'granite', coll))

    # 기둥열 — 안팎 두 줄
    n = max(2, int(round(length / COR['bay'])))
    xs = [-length / 2 + length * i / n for i in range(n + 1)]
    ys = [-d / 2, d / 2]
    col_top = ph + ch
    st, cl, _ = build_columns(name, coll, xs, ys, ph, ch, 0.26)
    objs += [st, cl]
    objs.append(build_beams(name + "_창방", coll, xs, ys, col_top,
                            depth=0.34, thick=0.24))
    g, r = build_brackets(name, coll, xs, ys, col_top + 0.20,
                          tiers=2, spacing=COR['bay'])
    objs += [g, r]

    # 바깥 벽 — 하부는 사고석, 상부는 회벽
    if walled:
        yw = wall_side * d / 2
        bm = bmesh.new()
        bm_box(bm, 0, yw, ph + 0.55, length, 0.50, 1.10)
        objs.append(bm_to_object(bm, name + "_화방벽", 'granite_d', coll))
        bm = bmesh.new()
        bm_box(bm, 0, yw, ph + 1.10 + (ch * 0.93 - 1.10) / 2,
               length, 0.42, ch * 0.93 - 1.10)
        objs.append(bm_to_object(bm, name + "_회벽", 'dc_white', coll))

    # 마루
    bm = bmesh.new()
    bm_box(bm, 0, 0, ph + 0.09, length, d, 0.18)
    objs.append(bm_to_object(bm, name + "_마루", 'wood_dark', coll))

    if roofed:
        objs += roof.build_gable_roof(
            name, coll,
            length + 2 * COR['end_out'], d + 2 * COR['eave_out'],
            COR['eave'], COR['ridge'])
    return objs


def build_corner(name, coll):
    """회랑이 꺾이는 모서리 — 모임지붕을 얹은 작은 정자."""
    d = COR['depth']
    ph, ch = COR['plat_h'], COR['col_h']
    objs = []

    bm = bmesh.new()
    bm_box(bm, 0, 0, ph / 2, d + 1.1, d + 1.1, ph)
    bm_box(bm, 0, 0, ph + 0.06, d + 1.5, d + 1.5, 0.12)
    objs.append(bm_to_object(bm, name + "_기단", 'granite', coll))

    xs = ys = [-d / 2, d / 2]
    col_top = ph + ch
    st, cl, _ = build_columns(name, coll, xs, ys, ph, ch, 0.26)
    objs += [st, cl]
    objs.append(build_beams(name + "_창방", coll, xs, ys, col_top,
                            depth=0.34, thick=0.24))
    g, r = build_brackets(name, coll, xs, ys, col_top + 0.20,
                          tiers=2, spacing=d)
    objs += [g, r]

    side = d + 2 * COR['eave_out']
    objs += roof.build_skirt_roof(name, coll, side, side, 0.7, 0.7,
                                  COR['eave'], COR['ridge'] + 0.35,
                                  lift=0.75, out=0.42)
    return objs


# ---------------------------------------------------------------- 근정문


def build_gate(name, coll):
    """근정문 — 정면 3칸 중층 팔작지붕."""
    from hanok import grid_positions, build_walls
    xs, W = grid_positions(GATE['bays_x'])
    ys, D = grid_positions(GATE['bays_y'])
    objs = []

    psx, psy, ph = GATE['plat']
    objs.append(build_platform(name + "_기단", coll, 0, 0, 0, ph, psx, psy))
    objs.append(build_stairs(name + "_남계단", coll, 0, -psy / 2, 0, ph, 7.0))
    objs.append(build_stairs(name + "_북계단", coll, 0, psy / 2, 0, ph, 7.0,
                             sgn=1.0))

    z = GATE['floor']
    col_top = z + GATE['col_h']
    st, cl, _ = build_columns(name + "_하층", coll, xs, ys, z,
                              GATE['col_h'], 0.34, perimeter_only=True)
    objs += [st, cl]
    objs.append(build_beams(name + "_하층_창방", coll, xs, ys, col_top))
    g, r = build_brackets(name + "_하층", coll, xs, ys, col_top + 0.26, tiers=3)
    objs += [g, r]

    ux, uy = GATE['upper_x'], GATE['upper_y']
    st2, cl2, _ = build_columns(name + "_고주", coll, ux, uy, z,
                                GATE['high_col_top'] - z, 0.38)
    objs += [st2, cl2]

    eo = GATE['eave_out_low']
    objs += roof.build_skirt_roof(
        name, coll, W + 2 * eo, D + 2 * eo,
        (ux[-1] - ux[0]) + 1.2, (uy[-1] - uy[0]) + 1.2,
        GATE['low_eave'], GATE['low_top'])

    up_h = GATE['high_col_top'] - GATE['low_top']
    objs += list(build_walls(name + "_상층벽", coll, ux, uy,
                             GATE['low_top'], up_h, sill=0.35))
    objs.append(build_beams(name + "_상층_창방", coll, ux, uy,
                            GATE['high_col_top']))
    g2, r2 = build_brackets(name + "_상층", coll, ux, uy,
                            GATE['high_col_top'] + 0.26, tiers=3)
    objs += [g2, r2]

    eu = GATE['eave_out_up']
    objs += roof.build_hip_gable_roof(
        name + "_상층", coll,
        (ux[-1] - ux[0]) + 2 * eu, (uy[-1] - uy[0]) + 2 * eu,
        GATE['up_eave'], GATE['up_ridge'],
        ridge_ratio=0.52, gable_ratio=0.50, lift=0.85, out=0.48, eave_out=eu)
    return objs


# ------------------------------------------------------------------ 담장


def build_wall_run(name, coll, length, height=2.65):
    """경복궁식 담장 — 사고석 기단 + 회벽 + 기와 갓."""
    objs = []
    base_h = 0.95
    bm = bmesh.new()
    bm_box(bm, 0, 0, base_h / 2, length, 0.92, base_h)
    objs.append(bm_to_object(bm, name + "_사고석", 'granite_d', coll))

    bm = bmesh.new()
    bm_box(bm, 0, 0, base_h + (height - base_h) / 2, length, 0.72,
           height - base_h)
    objs.append(bm_to_object(bm, name + "_회벽", 'dc_white', coll))

    # 기와 갓 — 얕은 맞배 단면을 길게 뽑는다
    bm = bmesh.new()
    bm_box(bm, 0, 0, height + 0.10, length, 1.22, 0.20)
    bm_box(bm, 0, 0, height + 0.30, length, 0.85, 0.22)
    bm_box(bm, 0, 0, height + 0.46, length, 0.42, 0.20)
    objs.append(bm_to_object(bm, name + "_기와갓", 'tile', coll))
    return objs


# ---------------------------------------------------------------- 일곽 조립


def build_enclosure():
    coll = new_collection("회랑_담장")
    d = COR['depth']

    ns_len = (ENC_X * 2 - d) / 2 - GATE_GAP / 2      # 남면 좌우 회랑 길이
    n_len = ENC_X * 2 - d                             # 북면 회랑
    ew_len = (ENC_N - ENC_S) - d                      # 동서 회랑

    # 동서 회랑 — ±90° 돌리면 local +y 가 안쪽을 향하므로 벽은 -y 쪽에 세운다
    for sx in (-1.0, 1.0):
        objs = build_corridor("회랑_%s" % ("서" if sx < 0 else "동"),
                              coll, ew_len, wall_side=-1.0)
        _place(objs, (sx * ENC_X, (ENC_S + ENC_N) / 2, 0.0),
               rot_z=math.radians(90 if sx > 0 else -90))

    # 남 회랑 — 가운데는 근정문 자리로 비운다
    for sx in (-1.0, 1.0):
        cx = sx * (GATE_GAP / 2 + ns_len / 2)
        objs = build_corridor("회랑_남%s" % ("서" if sx < 0 else "동"),
                              coll, ns_len, wall_side=-1.0)
        _place(objs, (cx, ENC_S, 0.0))

    # 북 회랑
    objs = build_corridor("회랑_북", coll, n_len, wall_side=1.0)
    _place(objs, (0.0, ENC_N, 0.0))

    # 네 모서리
    for sx in (-1.0, 1.0):
        for sy, tag in ((ENC_S, "남"), (ENC_N, "북")):
            objs = build_corner("회랑_모서리_%s%s" %
                                (tag, "서" if sx < 0 else "동"), coll)
            _place(objs, (sx * ENC_X, sy, 0.0))

    # 근정문
    _place(build_gate("근정문", coll), (0.0, ENC_S, 0.0))

    # 사정전 일곽 담장
    sj_gap = 11.0
    for sx in (-1.0, 1.0):
        objs = build_wall_run("담장_%s" % ("서" if sx < 0 else "동"),
                              coll, SJ_N - SJ_S)
        _place(objs, (sx * SJ_X, (SJ_S + SJ_N) / 2, 0.0),
               rot_z=math.radians(90))
        # 근정전 일곽과 잇는 담장
        objs = build_wall_run("담장_연결_%s" % ("서" if sx < 0 else "동"),
                              coll, SJ_S - ENC_N)
        _place(objs, (sx * SJ_X, (ENC_N + SJ_S) / 2, 0.0),
               rot_z=math.radians(90))
        # 남면 담장 (가운데 사정문 자리)
        seg = (SJ_X * 2 - sj_gap) / 2
        objs = build_wall_run("담장_남%s" % ("서" if sx < 0 else "동"),
                              coll, seg)
        _place(objs, (sx * (sj_gap / 2 + seg / 2), SJ_S, 0.0))

    objs = build_wall_run("담장_북", coll, SJ_X * 2)
    _place(objs, (0.0, SJ_N, 0.0))

    # 사정문 — 짧은 맞배 문간채
    _place(build_corridor("사정문", coll, sj_gap, roofed=True, walled=False),
           (0.0, SJ_S, 0.0))

    n_obj = len([o for o in coll.objects if o.type == 'MESH'])
    n_v = sum(len(o.data.vertices) for o in coll.objects if o.type == 'MESH')
    return coll, n_obj, n_v
