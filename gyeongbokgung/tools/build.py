# -*- coding: utf-8 -*-
"""경복궁 근정전·사정전 조립 스크립트.

좌표계: +Y = 북(北). 근정전이 원점, 남쪽(-Y)이 조정(朝庭), 북쪽(+Y)이 사정전.
치수는 실측값을 기준으로 했다.
  근정전 — 정면 5칸 30m, 측면 5칸 21m, 중층 팔작지붕, 2단 월대
  사정전 — 정면 5칸 20m, 측면 3칸 12m, 단층 팔작지붕
"""

import bpy
import bmesh
import importlib

import hanok
import roof
importlib.reload(hanok)
importlib.reload(roof)

from hanok import (new_collection, grid_positions, build_platform, build_stairs,
                   build_dapdo, build_balustrade, build_columns, build_beams,
                   build_brackets, build_walls, bm_to_object, bm_box)

# ------------------------------------------------------------------ 근정전

GJ = dict(
    bays_x=[5.2, 6.0, 7.6, 6.0, 5.2],      # 정면 5칸 = 30.0m
    bays_y=[3.6, 4.2, 5.4, 4.2, 3.6],      # 측면 5칸 = 21.0m
    woldae_low=(52.0, 40.0, 0.00, 1.35),   # sx, sy, z0, 높이
    woldae_up=(41.0, 31.0, 1.35, 1.35),
    floor=2.70,
    col_h=6.30,                            # 외진주
    high_col_top=16.20,                    # 고주(상층 기둥) 머리
    low_eave=10.90, low_top=13.80,         # 하층 지붕
    up_eave=18.10, up_ridge=24.20,         # 상층 지붕
    eave_out_low=3.40, eave_out_up=3.20,
)

SJ = dict(
    bays_x=[3.4, 4.0, 5.2, 4.0, 3.4],      # 정면 5칸 = 20.0m
    bays_y=[3.6, 4.8, 3.6],                # 측면 3칸 = 12.0m
    platform=(26.0, 18.0, 0.00, 1.25),
    floor=1.25,
    col_h=4.60,
    eave=7.40, ridge=12.60,
    eave_out=2.80,
)

SAJEONGJEON_Y = 75.0                        # 근정전 북쪽 거리


def _floor_slab(coll, name, cx, cy, z, sx, sy):
    bm = bmesh.new()
    bm_box(bm, cx, cy, z - 0.09, sx, sy, 0.18)
    return bm_to_object(bm, name, 'wood_dark', coll)


def build_geunjeongjeon():
    """근정전 — 중층 팔작지붕 정전."""
    coll = new_collection("근정전")
    xs, W = grid_positions(GJ['bays_x'])
    ys, D = grid_positions(GJ['bays_y'])

    # --- 2단 월대
    for tag, (sx, sy, z0, h) in (("하월대", GJ['woldae_low']),
                                 ("상월대", GJ['woldae_up'])):
        build_platform(tag, coll, 0, 0, z0, h, sx, sy)
        build_balustrade(tag + "_난간", coll, z0 + h + 0.18, sx - 0.5, sy - 0.5)
        # 남쪽 정면 계단 — 좌우 계단 + 가운데 답도
        y_front = -sy / 2.0
        for off in (-4.6, 4.6):
            build_stairs(tag + "_계단", coll, off, y_front, z0, h, 4.0)
        build_dapdo(tag + "_답도", coll, 0.0, y_front, z0, h, 4.4)
        # 북쪽·동서 계단
        build_stairs(tag + "_북계단", coll, 0.0, sy / 2.0, z0, h, 6.0, sgn=1.0)

    z = GJ['floor']
    _floor_slab(coll, "근정전_마루", 0, 0, z, W + 1.6, D + 1.6)

    # --- 하층: 외진주 + 창방/평방 + 공포
    col_top = z + GJ['col_h']
    build_columns("근정전_하층", coll, xs, ys, z, GJ['col_h'], 0.44,
                  perimeter_only=True)
    build_beams("근정전_하층_창방", coll, xs, ys, col_top)
    build_brackets("근정전_하층", coll, xs, ys, col_top + 0.26, tiers=4)
    build_walls("근정전_하층벽", coll, xs, ys, z, GJ['col_h'])

    # --- 고주(내진주) — 상층까지 통으로 올라간다
    ixs, iys = xs[1:-1], ys[1:-1]
    build_columns("근정전_고주", coll, ixs, iys, z,
                  GJ['high_col_top'] - z, 0.50)

    # --- 하층 지붕
    eo = GJ['eave_out_low']
    iW = ixs[-1] - ixs[0]
    iD = iys[-1] - iys[0]
    roof.build_skirt_roof("근정전", coll,
                          W + 2 * eo, D + 2 * eo,
                          iW + 1.4, iD + 1.4,
                          GJ['low_eave'], GJ['low_top'])

    # --- 상층: 벽 + 창방/평방 + 공포 + 팔작지붕
    up_h = GJ['high_col_top'] - GJ['low_top']
    # 상층은 머름을 둔 창(窓)
    build_walls("근정전_상층벽", coll, ixs, iys, GJ['low_top'], up_h, sill=0.45)
    build_beams("근정전_상층_창방", coll, ixs, iys, GJ['high_col_top'])
    build_brackets("근정전_상층", coll, ixs, iys,
                   GJ['high_col_top'] + 0.26, tiers=4)

    eu = GJ['eave_out_up']
    roof.build_hip_gable_roof("근정전_상층", coll,
                              iW + 2 * eu, iD + 2 * eu,
                              GJ['up_eave'], GJ['up_ridge'],
                              ridge_ratio=0.56, gable_ratio=0.50,
                              lift=1.15, out=0.62, eave_out=eu)
    return coll


def build_sajeongjeon():
    """사정전 — 단층 팔작지붕 편전."""
    coll = new_collection("사정전")
    xs, W = grid_positions(SJ['bays_x'])
    ys, D = grid_positions(SJ['bays_y'])

    sx, sy, z0, h = SJ['platform']
    plat = build_platform("사정전_기단", coll, 0, 0, z0, h, sx, sy)
    st = build_stairs("사정전_계단", coll, 0.0, -sy / 2.0, z0, h, 6.5)

    z = SJ['floor']
    _floor_slab(coll, "사정전_마루", 0, 0, z, W + 1.4, D + 1.4)

    col_top = z + SJ['col_h']
    build_columns("사정전", coll, xs, ys, z, SJ['col_h'], 0.38,
                  perimeter_only=True)
    build_beams("사정전_창방", coll, xs, ys, col_top)
    build_brackets("사정전", coll, xs, ys, col_top + 0.26, tiers=3, spacing=1.7)
    build_walls("사정전_벽", coll, xs, ys, z, SJ['col_h'])

    eo = SJ['eave_out']
    roof.build_hip_gable_roof("사정전", coll,
                              W + 2 * eo, D + 2 * eo,
                              SJ['eave'], SJ['ridge'],
                              ridge_ratio=0.54, gable_ratio=0.50,
                              lift=0.95, out=0.52, eave_out=eo)

    # 컬렉션 전체를 북쪽으로 이동.
    # 행렬 합성이라 이미 놓인 트랜스폼 위에 덧씌워진다. 사정전 객체는 전부
    # identity 라 결과는 예전의 location.y += 와 동일하다.
    hanok.place_objects(list(coll.objects), origin=(0.0, SAJEONGJEON_Y, 0.0))
    return coll


# ------------------------------------------------------------------ 조정


def build_courtyard():
    """조정(朝庭) — 박석 바닥, 어도, 품계석 받침."""
    import enclosure
    coll = new_collection("조정")

    # 지면 — 회랑·담장 바깥은 두지 않는다. 일곽 안쪽만 깐다.
    E = enclosure
    pad = E.COR['depth'] / 2 + 0.9          # 회랑 몸채까지 덮을 여유
    gate_s = E.ENC_S - E.GATE['plat'][1] / 2 - 1.5   # 근정문 기단까지 물린다
    # (x0, x1, y0, y1)
    patches = [
        ("지면_근정전일곽", -E.ENC_X - pad, E.ENC_X + pad,
         gate_s, E.ENC_N + pad),
        ("지면_사정전일곽", -E.SJ_X - 1.2, E.SJ_X + 1.2,
         E.ENC_N + pad, E.SJ_N + 1.2),
    ]
    for name, x0, x1, y0, y1 in patches:
        bm = bmesh.new()
        bm_box(bm, (x0 + x1) / 2, (y0 + y1) / 2, -0.25,
               x1 - x0, y1 - y0, 0.50)
        bm_to_object(bm, name, 'floor', coll)

    # 조정 바닥 — 회랑 안쪽을 가득 채운다
    y0, y1 = -76.0, -19.0
    bm = bmesh.new()
    bm_box(bm, 0, (y0 + y1) / 2, 0.06, 79.0, y1 - y0, 0.12)
    bm_to_object(bm, "조정_박석", 'granite', coll)

    # 어도 — 가운데 한 단 솟은 길. 같은 화강암이라 높이차로만 드러난다
    bm = bmesh.new()
    bm_box(bm, 0, (y0 + y1) / 2, 0.20, 3.2, y1 - y0, 0.24)
    bm_box(bm, -2.6, (y0 + y1) / 2, 0.15, 2.0, y1 - y0, 0.16)
    bm_box(bm, 2.6, (y0 + y1) / 2, 0.15, 2.0, y1 - y0, 0.16)
    bm_to_object(bm, "어도", 'granite', coll)

    return coll


def rank_stone_positions():
    """품계석 자리 — 어도 좌우 각 12기 (정1품~종9품)."""
    pos = []
    for i in range(12):
        y = -26.0 - i * 3.2
        for sx in (-1.0, 1.0):
            pos.append((sx * 7.2, y))
    return pos


def build_all():
    hanok.setup_materials()
    gj = build_geunjeongjeon()
    sj = build_sajeongjeon()
    cy = build_courtyard()
    total = sum(len(c.objects) for c in (gj, sj, cy))
    verts = sum(len(o.data.vertices) for c in (gj, sj, cy)
                for o in c.objects if o.type == 'MESH')
    return total, verts
