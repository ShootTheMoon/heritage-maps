# -*- coding: utf-8 -*-
"""덕수궁 전각 조립.

중화전·중화문은 국가유산청 실측 모델을 쓰므로 여기서 만들지 않는다.
여기서 절차적으로 세우는 것은 다섯: 석어당 · 준명당 · 즉조당 · 복도각 · 대한문.

건물은 전부 **원점에서 정면이 −Y** 를 보도록 만든다(경복궁과 같은 저작 규약).
배치는 layout.place() 가 한 번에 씌운다.
"""

import bpy
import bmesh
import importlib

import hanok
import roof
import sites
importlib.reload(hanok)
importlib.reload(roof)
importlib.reload(sites)

from hanok import (new_collection, grid_positions, build_platform, build_stairs,
                   build_columns, build_beams, build_brackets, build_ikgong,
                   build_walls, build_gyeja_railing, bm_to_object, bm_box,
                   DANCHEONG, BAEKGOL)

from . import layout
importlib.reload(layout)


def _floor_slab(coll, name, z, sx, sy, mat='wood_dark'):
    bm = bmesh.new()
    bm_box(bm, 0, 0, z - 0.09, sx, sy, 0.18)
    return bm_to_object(bm, name, mat, coll)


# ------------------------------------------------------------------ 석어당


def build_seokeodang():
    """석어당 — 궁궐에서 유일하게 올라갈 수 있는 2층 목조 건물.

    핵심은 **백골집**이다. 단청이 없고, 취두·용두·잡상도 전부 없다.
    1층은 초익공, 2층은 공포 없는 민도리집이라 창방만 건다.
    """
    S = layout.SED
    coll = new_collection("덕수궁_석어당")
    pal = BAEKGOL
    xs, W = grid_positions(S['bays_x'])
    ys, D = grid_positions(S['bays_y'])
    uxs, uW = grid_positions(S['up_bays_x'])
    uys, uD = grid_positions(S['up_bays_y'])

    psx, psy, ph = S['plat']
    build_platform("석어당_기단", coll, 0, 0, 0, ph, psx, psy)
    build_stairs("석어당_서계단", coll, -4.6, -psy / 2, 0, ph, 3.0)
    build_stairs("석어당_동계단", coll, 4.6, -psy / 2, 0, ph, 3.0)

    z = S['floor']
    _floor_slab(coll, "석어당_마루", z, W + 1.0, D + 1.0)

    # --- 1층: 초익공
    col_top = z + S['col_h']
    build_columns("석어당_하층", coll, xs, ys, z, S['col_h'], 0.20,
                  perimeter_only=True, pal=pal)
    build_beams("석어당_하층_창방", coll, xs, ys, col_top,
                depth=0.34, thick=0.24, pyeongbang=False, pal=pal)
    build_ikgong("석어당_하층", coll, xs, ys, col_top + 0.02,
                 tiers=1, reach=0.70, pal=pal)
    build_walls("석어당_하층벽", coll, xs, ys, z, S['col_h'], pal=pal)

    # --- 고주: 2층까지 통으로
    build_columns("석어당_고주", coll, uxs, uys, z,
                  S['up_col_top'] - z, 0.22, pal=pal)

    # --- 하층 지붕
    eo = S['eave_out_low']
    roof.build_skirt_roof("석어당", coll, W + 2 * eo, D + 2 * eo,
                          uW + 0.9, uD + 0.9,
                          S['low_eave'], S['low_top'], pal=pal)

    # --- 2층: 민도리집 (공포 없음). 사방에 창을 낸 망루 성격.
    up_h = S['up_col_top'] - S['low_top']
    build_walls("석어당_상층벽", coll, uxs, uys, S['low_top'], up_h,
                sill=0.30, pal=pal)
    build_beams("석어당_상층_창방", coll, uxs, uys, S['up_col_top'],
                depth=0.30, thick=0.22, pyeongbang=False, pal=pal)

    eu = S['eave_out_up']
    roof.build_hip_gable_roof("석어당_상층", coll,
                              uW + 2 * eu, uD + 2 * eu,
                              S['up_eave'], S['up_ridge'],
                              ridge_ratio=0.60, gable_ratio=0.50,
                              lift=0.70, out=0.40, eave_out=eu,
                              pal=pal, ornaments='none')
    return coll


# ------------------------------------------------------------------ 준명당


def build_junmyeongdang():
    """준명당 — 초익공 단층. 용두는 있고 잡상은 없다."""
    S = layout.JMD
    coll = new_collection("덕수궁_준명당")
    xs, W = grid_positions(S['bays_x'])
    ys, D = grid_positions(S['bays_y'])

    psx, psy, ph = S['plat']
    build_platform("준명당_기단", coll, 0, 0, 0, ph, psx, psy)
    build_stairs("준명당_계단", coll, 0, -psy / 2, 0, ph, 5.5)

    z = S['floor']
    _floor_slab(coll, "준명당_마루", z, W + 1.0, D + 1.0)

    col_top = z + S['col_h']
    build_columns("준명당", coll, xs, ys, z, S['col_h'], 0.21,
                  perimeter_only=True)
    build_beams("준명당_창방", coll, xs, ys, col_top,
                depth=0.36, thick=0.25, pyeongbang=False)
    build_ikgong("준명당", coll, xs, ys, col_top + 0.02, tiers=1, reach=0.78)
    build_walls("준명당_벽", coll, xs, ys, z, S['col_h'])

    # 동단 누마루 — 한 단 올려 계자난간을 두른다
    build_gyeja_railing("준명당_누마루", coll, xs[-2], xs[-1] + 0.4,
                        ys[0] - 0.4, z + 0.12)

    eo = S['eave_out']
    roof.build_hip_gable_roof("준명당", coll, W + 2 * eo, D + 2 * eo,
                              S['eave'], S['ridge'],
                              ridge_ratio=0.56, gable_ratio=0.50,
                              lift=0.80, out=0.45, eave_out=eo,
                              ornaments='ridge_only')
    return coll


# ------------------------------------------------------------------ 즉조당


def build_jeukjodang():
    """즉조당 — 초익공 단층. **네모 초석 + 네모기둥**이 중화전과 다른 점."""
    S = layout.JJD
    coll = new_collection("덕수궁_즉조당")
    xs, W = grid_positions(S['bays_x'])
    ys, D = grid_positions(S['bays_y'])

    psx, psy, ph = S['plat']
    build_platform("즉조당_기단", coll, 0, 0, 0, ph, psx, psy)
    build_stairs("즉조당_계단", coll, 0, -psy / 2, 0, ph, 6.0)

    z = S['floor']
    _floor_slab(coll, "즉조당_마루", z, W + 1.0, D + 1.0)

    col_top = z + S['col_h']
    build_columns("즉조당", coll, xs, ys, z, S['col_h'], 0.20,
                  perimeter_only=True, shape='square')
    build_beams("즉조당_창방", coll, xs, ys, col_top,
                depth=0.36, thick=0.25, pyeongbang=False)
    build_ikgong("즉조당", coll, xs, ys, col_top + 0.02, tiers=1, reach=0.80)
    build_walls("즉조당_벽", coll, xs, ys, z, S['col_h'])

    # 동단 누마루 — 한 단 올라간 마루
    build_gyeja_railing("즉조당_누마루", coll, xs[-2], xs[-1] + 0.4,
                        ys[0] - 0.4, z + 0.12)

    eo = S['eave_out']
    roof.build_hip_gable_roof("즉조당", coll, W + 2 * eo, D + 2 * eo,
                              S['eave'], S['ridge'],
                              ridge_ratio=0.56, gable_ratio=0.50,
                              lift=0.82, out=0.46, eave_out=eo,
                              ornaments='ridge_only')
    return coll


# ------------------------------------------------------------------ 복도각


def build_bokdogak():
    """준명당 ↔ 즉조당을 잇는 짧은 복도.

    두 건물 중심 간격이 20.9 m 인데 각각의 반폭 합이 18.9 m 라 **빈 구간이
    2 m 밖에 안 된다.** 그래서 지붕을 양 끝에서 잘라(trim) 벽선에서 끝낸다 —
    roof.py 에 회첨골(valley) 로직이 없어서 그대로 두면 두 건물을 파고든다.

    칸수(2칸)와 지붕형(맞배)은 사진 판독이고 사료 확인은 안 됐다.
    """
    S = layout.BDG
    coll = new_collection("덕수궁_복도각")

    # 준명당 동쪽 끝 ~ 즉조당 서쪽 끝 사이
    gap = (layout.UV['즉조당'][0] - layout.UV['준명당'][0]) \
        - (sum(layout.JJD['bays_x']) + sum(layout.JMD['bays_x'])) / 2.0
    L = max(1.2, gap)
    d = S['depth']
    xs, _ = grid_positions([L / S['bays']] * S['bays'])
    ys = [-d / 2, d / 2]

    bm = bmesh.new()
    bm_box(bm, 0, 0, S['floor'] / 2, L + 0.4, d + 0.6, S['floor'])
    bm_to_object(bm, "복도각_기단", 'granite', coll)

    z = S['floor']
    _floor_slab(coll, "복도각_마루", z, L, d)

    col_top = z + S['col_h']
    build_columns("복도각", coll, xs, ys, z, S['col_h'], 0.16)
    build_beams("복도각_창방", coll, xs, ys, col_top,
                depth=0.26, thick=0.18, pyeongbang=False)
    build_ikgong("복도각", coll, xs, ys, col_top + 0.02, tiers=1,
                 reach=0.45, boaji=False)

    # 양옆 계자난간 — 복도각의 특징
    for sy in (-1.0, 1.0):
        build_gyeja_railing("복도각_%s" % ("남" if sy < 0 else "북"), coll,
                            xs[0], xs[-1], sy * d / 2, z + 0.10, height=0.70)

    # 지붕은 양 끝을 벽선에서 끊는다 (trim). 그래야 두 건물을 파고들지 않는다.
    eo = S['eave_out']
    roof.build_gable_roof("복도각", coll, L, d + 2 * eo,
                          S['eave'], S['ridge'], lift=0.25, out=0.12)
    return coll


# ------------------------------------------------------------------ 대한문


def build_daehanmun():
    """대한문 — 덕수궁 정문. **다포계 우진각지붕**(합각 없음).

    2020~2023 에 월대가 복원됐으므로 현재 모습에는 월대가 있어야 한다.
    """
    S = layout.DHM
    coll = new_collection("덕수궁_대한문")
    xs, W = grid_positions(S['bays_x'])
    ys, D = grid_positions(S['bays_y'])

    wsx, wsy, wh = S['woldae']
    build_platform("대한문_월대", coll, 0, 0, 0, wh, wsx, wsy)
    build_stairs("대한문_월대계단", coll, 0, -wsy / 2, 0, wh, 8.0)

    psx, psy, ph = S['plat']
    build_platform("대한문_기단", coll, 0, 0, wh, ph, psx, psy)
    build_stairs("대한문_계단", coll, 0, -psy / 2, wh, ph, 6.0)

    z = wh + ph
    _floor_slab(coll, "대한문_마루", z, W + 1.0, D + 1.0, mat='floor')

    col_top = z + S['col_h']
    build_columns("대한문", coll, xs, ys, z, S['col_h'], 0.32,
                  perimeter_only=True)
    build_beams("대한문_창방", coll, xs, ys, col_top)
    build_brackets("대한문", coll, xs, ys, col_top + 0.26, tiers=3, spacing=1.7)

    # 삼문(三門) — 판문 세 짝. 문짝이 없으면 정자처럼 보인다.
    bm_door = bmesh.new()
    bm_stud = bmesh.new()
    dh = S['col_h'] * 0.82
    for i in range(len(xs) - 1):
        cx = (xs[i] + xs[i + 1]) / 2.0
        w = (xs[i + 1] - xs[i]) * 0.92
        for leaf in (-1, 1):                     # 두 짝씩
            lx = cx + leaf * w / 4.0
            bm_box(bm_door, lx, ys[0], z + dh / 2 + 0.1, w / 2 - 0.05, 0.12, dh)
        # 문선(테두리) + 중간 띠장
        bm_box(bm_stud, cx, ys[0], z + dh + 0.18, w + 0.24, 0.18, 0.20)
        for k in (0.30, 0.62):
            bm_box(bm_stud, cx, ys[0], z + dh * k + 0.1, w, 0.16, 0.10)
    bm_to_object(bm_door, "대한문_판문", 'wood_red', coll)
    bm_to_object(bm_stud, "대한문_문선", 'dc_green', coll)

    eo = S['eave_out']
    roof.build_hip_gable_roof("대한문", coll, W + 2 * eo, D + 2 * eo,
                              S['eave'], S['ridge'],
                              ridge_ratio=0.42,
                              gable_ratio=1.0,          # ← 우진각
                              lift=0.80, out=0.45, eave_out=eo,
                              ornaments='full')
    return coll


# ------------------------------------------------------------------ 조립


def build_madang():
    """조정(朝庭)과 지면.

    중화전 회랑·행각은 1933년 일제가 공원화하며 철거했고 복원되지 않았다.
    따라서 조정은 회랑 없이 열린 마당으로 만든다.
    삼도(가운데 어도 + 좌우 신도)와 품계석 24기는 그대로 있다.
    """
    coll = new_collection("덕수궁_마당")

    v0, v1 = layout.UV['중화문'][1] + 4.0, -12.0    # 중화문 앞 ~ 중화전 월대
    cu, cv = 0.0, (v0 + v1) / 2.0
    length = v1 - v0

    # 지면 — 대한문(U +165.9)까지 덮어야 한다. 중화전 일곽만 덮으면
    # 대한문이 허공에 뜬다.
    us = [layout.UV[k][0] for k in layout.UV]
    vs = [layout.UV[k][1] for k in layout.UV]
    gu0, gu1 = min(us) - 40.0, max(us) + 40.0
    gv0, gv1 = min(vs) - 30.0, max(vs) + 40.0
    bm = bmesh.new()
    bm_box(bm, (gu0 + gu1) / 2, (gv0 + gv1) / 2, -0.25,
           gu1 - gu0, gv1 - gv0, 0.5)
    bm_to_object(bm, "마당_지면", 'floor', coll)

    bm = bmesh.new()
    bm_box(bm, cu, cv, 0.06, 62.0, length, 0.12)       # 조정 박석
    bm_to_object(bm, "마당_박석", 'granite', coll)

    # 삼도 — 가운데 어도가 한 단 높고 좌우 신도가 한 단 낮다
    bm = bmesh.new()
    bm_box(bm, cu, cv, 0.20, 3.2, length, 0.24)
    for du in (-2.6, 2.6):
        bm_box(bm, cu + du, cv, 0.15, 2.0, length, 0.16)
    bm_to_object(bm, "마당_삼도", 'granite', coll)

    # 품계석 24기 — 문관 동, 무관 서. 정1품~종3품 6기 + 4~9품 6기 = 12기씩
    bm = bmesh.new()
    for i in range(12):
        v = v1 - 8.0 - i * 3.2
        for du in (-7.2, 7.2):
            bm_box(bm, cu + du, v, 0.55, 0.42, 0.36, 0.86)
            bm_box(bm, cu + du, v, 0.10, 0.62, 0.56, 0.20)
    bm_to_object(bm, "마당_품계석", 'granite_d', coll)
    return coll


BUILDERS = [
    ('석어당', build_seokeodang),
    ('준명당', build_junmyeongdang),
    ('즉조당', build_jeukjodang),
    ('대한문', build_daehanmun),
]


def build_all(place=True):
    hanok.setup_materials()
    made = {}
    for name, fn in BUILDERS:
        coll = fn()
        made[name] = coll
        if place:
            layout.place(name, list(coll.objects))

    # 복도각은 두 건물 사이에 놓이므로 UV 표가 아니라 중점에 앉힌다
    bd = build_bokdogak()
    made['복도각'] = bd
    if place:
        u = (layout.UV['준명당'][0] + layout.UV['즉조당'][0]) / 2.0
        v = (layout.UV['준명당'][1] + layout.UV['즉조당'][1]) / 2.0
        hanok.place_objects(list(bd.objects),
                            matrix=layout.site_matrix(u, v, 0.0))

    # 마당은 이미 궁 축 좌표로 만들어졌으므로 사이트 행렬만 씌운다
    md = build_madang()
    made['마당'] = md
    if place:
        hanok.place_objects(list(md.objects),
                            matrix=layout.site_matrix(0.0, 0.0, 0.0))

    tot_o = sum(len(c.objects) for c in made.values())
    tot_t = sum(sum(len(p.vertices) - 2 for p in o.data.polygons)
                for c in made.values() for o in c.objects if o.type == 'MESH')
    return made, tot_o, tot_t
