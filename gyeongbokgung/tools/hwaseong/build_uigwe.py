# -*- coding: utf-8 -*-
"""화성성역의궤 도설로 세우는 시설물 — 화서문 · 서북공심돈 · 방화수류정.

KCISA 스캔이 없는 것들이다(스케치팹에 장안문·팔달문뿐). 경복궁·덕수궁과
같은 방식으로 hanok / roof 모듈을 써서 절차 생성한다.

치수는 uigwe.py 에 있고, 대부분 **의궤 도설 원문에서 읽은 measured** 다.
아직 derived 인 것은 문루 칸 폭과 방화수류정 칸 크기뿐이다.

저작 규약은 KCISA 모델과 같다: 건물 원점 = 자기 중심, 지면 = z 0,
바깥면 = -Y. 그래야 layout.BUILDINGS 가 둘을 같은 방식으로 앉힌다.
"""

import math

import bmesh

import hanok
import roof
from hanok import (new_collection, grid_positions, build_platform, build_stairs,
                   build_columns, build_beams, build_ikgong, build_walls,
                   build_gyeja_railing, bm_box, bm_to_object)

from . import fortress as F
from .uigwe import (HWASEOMUN, SEO_ONGSEONG, SEOBUK_GONGSIMDON,
                    BANGHWASURYUJEONG, val, ja)

COLL_HSM = "화성_화서문"
COLL_GSD = "화성_공심돈"
COLL_BSJ = "화성_방화수류정"


def _place_prop(coll, name, x, y, z, scale=1.0, yaw=0.0):
    """hwaseong_props.blend 의 KCISA 스캔 한 채를 앉힌다.

    **목조부는 절차 생성 대신 스캔을 쓴다.** hanok 모듈로 지은 문루·누각이
    바로 옆 장안문 스캔 옆에서 확연히 떨어졌다. 석조(육축·홍예·옹성·전돌
    몸체·여장)는 의궤 실측으로 지은 것이 더 정확하므로 그대로 둔다.

    전부 한국문화정보원(KCISA) CC-BY 공공저작물이다 — 장안문·팔달문과 같은 출처.
    """
    import bmesh
    from mathutils import Matrix, Vector
    from .city import _prop_mesh, _stamp, _to_object_multi

    geom, mats = _prop_mesh(name)
    if geom is None:
        print("  소품 %s 없음 — hwaseong_props.blend 확인" % name)
        return None
    bm = bmesh.new()
    _stamp(bm, geom,
           Matrix.Translation(Vector((x, y, z)))
           @ Matrix.Rotation(math.radians(yaw), 4, 'Z')
           @ Matrix.Scale(scale, 4))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    ob = _to_object_multi(bm, "%s_%s" % (coll.name, name), mats, coll)
    import bpy
    if name in bpy.data.objects:            # 원본은 씬에 남기지 않는다
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    return ob


# ------------------------------------------------------------------ 화서문


def build_hwaseomun():
    """화서문 — 단층 문루 + 홍예 육축 + 서옹성.

    의궤 p111: "홍예와 문루의 제도는 모두 창룡문과 같다." 그래서 홍예 치수는
    창룡문 도설(p108)에서 가져온다. 무사 너비·높이만 화서문 고유값이다.
    """
    H, O = HWASEOMUN, SEO_ONGSEONG
    coll = new_collection(COLL_HSM)

    yuk_h = val(H, 'yukchuk_h')                 # 18척
    yuk_sy = val(H, 'yukchuk_depth')            # 30척
    hw = val(H, 'hongye_out_w')                 # 12척 — 바깥 홍예가 보이는 구멍
    hh = val(H, 'hongye_out_h')                 # 15척
    # 육축 총 너비 = 홍예 + 바깥 무사 좌우
    yuk_sx = hw + 2.0 * val(H, 'musa_out_w')

    F.build_hongye("화서문_육축", coll, yuk_sx, yuk_sy, yuk_h, hw, hh)

    # --- 육축 위 성가퀴. 창룡문 실측: 높이 4척7촌, 두께 2척1촌, 총혈 사방 8촌.
    yj = dict(h=val(H, 'yeojang_h'), t=val(H, 'yeojang_t'),
              hole=val(H, 'chongan_size'))
    xs, W = grid_positions(val(H, 'bay_x'))
    ys, D = grid_positions(val(H, 'bay_y'))
    for s in (-1.0, 1.0):
        a, b = s * (W / 2.0 + 0.9), s * yuk_sx / 2.0
        F.build_yeojang("화서문_여장_%s" % ("남" if s > 0 else "북"), coll,
                        min(a, b), max(a, b),
                        -yuk_sy / 2.0 + yj['t'] / 2.0, yuk_h, **yj)

    # --- 서옹성. 둘레에서 유도한 반지름(안 76척/π, 바깥 110척/π)을 쓴다.
    r_in, r_out = val(O, 'r_in'), val(O, 'r_out')
    F.build_ongseong("화서문_옹성", coll, 0.0, -yuk_sy / 2.0,
                     (r_in + r_out) / 2.0, val(O, 'h'), val(O, 'gap_deg'),
                     thick=r_out - r_in)

    # --- 옹성 바깥면 현안 셋 (동옹성 준용: 길이 8척 5촌, 지름 1척)
    bm = bmesh.new()
    for i in range(val(O, 'hyeonan_n')):
        a = math.radians(-90.0) + (i - 1) * math.radians(34.0)
        bm_box(bm, r_out * math.cos(a) * 0.99,
               -yuk_sy / 2.0 + r_out * math.sin(a) * 0.99,
               val(O, 'h') - val(O, 'hyeonan_len') / 2.0,
               val(O, 'hyeonan_dia'), val(O, 'hyeonan_dia'),
               val(O, 'hyeonan_len'))
    bm_to_object(bm, "화서문_옹성_현안", 'granite_d', coll)

    # --- 와장대 돌계단 좌우 2개. 육축 안쪽(+Y)에서 성 위로 오른다.
    #     창룡문 실측: 길이 20척, 14층, 너비 9척.
    for s in (-1.0, 1.0):
        F.build_wajangdae("화서문_와장대_%s" % ("남" if s > 0 else "북"), coll,
                          s * (hw / 2.0 + val(H, 'musa_out_w') * 0.55),
                          yuk_sy / 2.0, 0.0, yuk_h,
                          val(H, 'wajangdae_w'), val(H, 'wajangdae_len'),
                          steps=val(H, 'wajangdae_steps'))

    # --- 좌우 성벽 구간.
    #
    # **스캔 조각으로 바꾸려다 되돌렸다.** 스케치팹에 성곽 에셋이 하나도 없어
    # (한국 성벽·일반 성벽 모듈 검색 모두 0건) 장안문 스캔에서 직선 구간
    # 26.5 m 를 잘라 타일링해 봤는데, 잘린 자리가 **열린 껍데기**로 남고
    # 감축이 그걸 더 부숴서 성벽이 누더기가 됐다. 이 스캔은 타일링용 모듈이
    # 아니라 164 m 를 통으로 만든 것이라 중간을 자를 수 없다.
    # 절차 생성 켜쌓기가 더 낫다.
    for s in (-1.0, 1.0):
        x0, x1 = s * yuk_sx / 2.0, s * (yuk_sx / 2.0 + 26.0)
        bm = bmesh.new()
        # 통짜 박스로 두면 26 m 짜리 흰 판자가 된다. 켜마다 들이밀어 줄눈을 낸다.
        F.bm_coursed(bm, (x0 + x1) / 2.0, 0.0, 0.0, yuk_h - 0.6,
                     abs(x1 - x0), yuk_sy * 0.62, batter=0.35)
        bm_to_object(bm, "화서문_성벽_%s" % ("남" if s > 0 else "북"),
                     'granite_d', coll)
        F.build_yeojang("화서문_성벽여장_%s" % ("남" if s > 0 else "북"), coll,
                        min(x0, x1), max(x0, x1),
                        -yuk_sy * 0.31 + yj['t'] / 2.0, yuk_h - 0.6, **yj)

    # --- 문루. 앞면 3칸·옆면 2칸, 기둥 사이 모두 개방(벽체 없음).
    # **hanok 모듈로 짓던 것을 KCISA 관덕정 스캔으로 바꿨다.** 절차 생성
    # 문루가 바로 옆 장안문 스캔 옆에서 확연히 떨어졌다. 관덕정은 단층 팔작
    # 대형 목조라 단층인 화서문 문루에 형식이 맞는다.
    # (엄밀히는 제주 관덕정이지 화서문 문루가 아니다 — 고증이 아니라 대역이다.)
    build_platform("화서문_기단", coll, 0, 0, yuk_h, 0.45, W + 2.2, D + 2.0)
    _place_prop(coll, "관덕정", 0.0, 0.0, yuk_h + 0.63,
                scale=W / 12.01)          # 관덕정 원본 정면 12.01 m → 문루 정면
    return coll


# -------------------------------------------------------------- 서북공심돈


def build_gongsimdon():
    """서북공심돈 — 치 15척 + 전돌 몸체 18척(아래 사방 23척 → 위 21척) + 와가.

    의궤 p132. **사방(四方)** 이라고 적혀 있으니 평면은 정사각형이다.
    층마다 포혈 20개(사방 1척) — 네 면이므로 면당 5개.
    """
    G = SEOBUK_GONGSIMDON
    coll = new_collection(COLL_GSD)

    chi_h = val(G, 'chiseong_h')
    body_h = val(G, 'body_h')
    base = val(G, 'body_base')
    batter = val(G, 'body_batter')
    chi = val(G, 'chi_size')

    build_platform("공심돈_치성", coll, 0, 0, 0.0, chi_h, chi, chi,
                   batter=0.42, mat='granite_d')

    # 층마다 20개 = 네 면에 5개씩
    per_face = max(1, val(G, 'chongan_per_level') // 4)
    F.build_brick_body("공심돈_몸체", coll, 0, 0, chi_h, body_h,
                       base, base, batter=batter, levels=2,
                       per_face=per_face)

    # --- 치 서북 2면에 각각 현안 2구멍 (의궤 p132)
    bm = bmesh.new()
    for sgn, axis in ((-1.0, 'y'), (-1.0, 'x')):        # 서·북 두 면
        for k in (-1, 1):
            if axis == 'y':
                F.bm_hyeonan(bm, k * chi * 0.22, -chi / 2.0 + 0.06,
                             chi_h - 0.30, 0.26, chi_h * 0.55, ja(1))
            else:
                bm_box(bm, -chi / 2.0 + 0.10, k * chi * 0.22,
                       chi_h - 0.30 - chi_h * 0.28, ja(1), ja(1), chi_h * 0.55)
    bm_to_object(bm, "공심돈_치성_현안", 'granite_d', coll)

    z3 = chi_h + body_h
    top_w = val(G, 'body_top')
    bm = bmesh.new()
    bm_box(bm, 0, 0, z3 - 0.16, top_w, top_w, 0.32)   # 몸체 상단 안쪽으로 먹인다
    bm_to_object(bm, "공심돈_3층바닥", 'floor', coll)

    # --- 아래층 안쪽의 벽돌 홍예 소문 (의궤 p133 "벽돌로 된 홍예 모양의 작은 문")
    bm = bmesh.new()
    ow, oh = ja(4), ja(6)
    hwd = ow / 2.0
    for i in range(10):
        a0 = math.pi * i / 10
        a1 = math.pi * (i + 1) / 10
        am = (a0 + a1) / 2.0
        bm_box(bm, -hwd * math.cos(am), chi / 2.0 - 0.05,
               chi_h + (oh - hwd) + hwd * math.sin(am),
               ow * math.pi / 20 + 0.05, 0.12, 0.22)
    bm_box(bm, 0.0, chi / 2.0 - 0.05, chi_h + (oh - hwd) / 2.0, ow, 0.12, oh - hwd)
    bm_to_object(bm, "공심돈_홍예소문", 'granite_d', coll)

    # --- 3층 여장. 사방을 두른다.
    yj = dict(h=ja(3), t=ja(2), hole=val(G, 'chongan_size'))
    for s in (-1.0, 1.0):
        F.build_yeojang("공심돈_여장_y%+d" % s, coll,
                        -top_w / 2.0, top_w / 2.0,
                        s * (top_w / 2.0 - yj['t'] / 2.0), z3, **yj)
    bm = bmesh.new()
    for s in (-1.0, 1.0):
        bm_box(bm, s * (top_w / 2.0 - yj['t'] / 2.0), 0.0,
               z3 + F.MISEOK_T + yj['h'] / 2.0,
               yj['t'], top_w - yj['t'] * 2, yj['h'])
    bm_to_object(bm, "공심돈_여장_측", 'floor', coll)

    # --- 와가(瓦家) — "가로세로 2간의 집". 용마루가 총 40자에 오게 맞춘다.
    wz = z3
    nb = val(G, 'waga_bays')
    wxs, WW = grid_positions([ja(8)] * nb)
    wys, WD = grid_positions([ja(8)] * nb)
    ch = val(G, 'waga_h') * 0.46
    build_columns("공심돈_와가기둥", coll, wxs, wys, wz, ch, 0.19,
                  perimeter_only=True)
    build_beams("공심돈_와가창방", coll, wxs, wys, wz + ch, depth=0.30, thick=0.22)

    # --- 상층 판벽 + 전안 (의궤 p132: "상층의 벽돌로 된 면 위쪽은 판자로
    #     둘렀으며 문마다 각각 전안을 뚫었다"). 기둥만 세워 두면 안 된다.
    bm, bh = bmesh.new(), bmesh.new()
    pw, pt = WW + 0.10, 0.11
    zc = wz + ch * 0.52
    for s in (-1.0, 1.0):
        bm_box(bm, 0.0, s * WD / 2.0, zc, pw, pt, ch * 0.86)
        bm_box(bm, s * WW / 2.0, 0.0, zc, pt, pw, ch * 0.86)
        for k in (-1, 1):                       # 문마다 전안 하나씩
            bm_box(bh, k * WW * 0.22, s * (WD / 2.0 - 0.03), zc + ch * 0.18,
                   0.14, 0.10, 0.20)
            bm_box(bh, s * (WW / 2.0 - 0.03), k * WD * 0.22, zc + ch * 0.18,
                   0.10, 0.14, 0.20)
    bm_to_object(bm, "공심돈_와가판벽", 'wood_dark', coll)
    bm_to_object(bh, "공심돈_와가전안", 'granite_d', coll)

    # 지붕은 KCISA 퇴은정(창원의 집 정자) 스캔으로 얹는다. 절차 생성 지붕이
    # 장안문 스캔 옆에서 확연히 떨어졌다. 원본 5.50 m 정면을 와가 폭에 맞춘다.
    _place_prop(coll, "퇴은정", 0.0, 0.0, wz + ch * 0.94,
                scale=(WW + 1.1) / 5.50)
    return coll


# ------------------------------------------------------------ 방화수류정


def build_banghwasuryujeong():
    """동북각루(방화수류정) — 용두 바위 위 2층 누각.

    의궤 p139 평면: "동서로 세 간인데 가운데는 온돌을 놓았고, 북쪽으로 한 간을
    붙이고, 남쪽은 반 간을 물리었으며, 서쪽의 한 간은 또 길게 두 간을 늘리었다."
    → 단순한 ㄱ자가 아니라 세 덩어리가 물린 불규칙 평면이다.
    좌표 규약상 **-Y 가 북(성 바깥)**, +Y 가 남이다.
    """
    B = BANGHWASURYUJEONG
    coll = new_collection(COLL_BSJ)

    bc, bs, bn = val(B, 'bay_center'), val(B, 'bay_side'), val(B, 'bay_ns')
    f1, f2 = val(B, 'floor1_h'), val(B, 'floor2_h')
    base_h = ja(8)

    mxs, MW = grid_positions([bs, bc, bs])       # 동서 3간
    mys, MD = grid_positions([bn])               # 남북 1간
    # 북쪽 1간 (-Y). 주채와 합쳐 한 지붕 아래 둔다.
    nys, ND = grid_positions([bn])
    north_y = -bn
    # 서쪽 1간을 남(+Y)으로 두 간 늘림
    west_x = -(bc / 2.0 + bs / 2.0)
    wxs, WW2 = grid_positions([bs])
    wys, WD2 = grid_positions([bn, bn])
    west_y = bn / 2.0 + WD2 / 2.0

    # --- 용두 바위 + 석축
    rr = val(B, 'rock_r')
    bm = bmesh.new()
    hanok.bm_cylinder(bm, 0.0, 0.0, -1.2, base_h - 0.5, rr, rr * 0.78, seg=20)
    bm_to_object(bm, "방화수류정_용두바위", 'granite_d', coll)
    build_platform("방화수류정_석축", coll, 0, -bn / 2.0, base_h - 0.5, 0.5,
                   MW + 2.6, MD + ND + 2.6, mat='granite_d')
    build_platform("방화수류정_석축_서익", coll, west_x, west_y,
                   base_h - 0.5, 0.5, WW2 + 2.2, WD2 + 2.2, mat='granite_d')

    # --- 용연(龍淵) — 성 밖(-y). 사이트 지면 윗면이 z=0 이라 그 위에 얹는다.
    bm = bmesh.new()
    hanok.bm_cylinder(bm, -2.0, -val(B, 'yongyeon_r') - rr * 0.8, 0.02, 0.10,
                      val(B, 'yongyeon_r'), val(B, 'yongyeon_r'), seg=28)
    bm_to_object(bm, "방화수류정_용연", 'dc_blue', coll)

    # --- 동북 성면 벽돌 (의궤 p141: 높이 7척, 두께 4척4촌)
    bm = bmesh.new()
    bm_box(bm, 0.0, north_y - bn / 2.0 - val(B, 'wall_t') / 2.0,
           val(B, 'wall_h') / 2.0, MW + 2.6, val(B, 'wall_t'), val(B, 'wall_h'))
    bm_to_object(bm, "방화수류정_성면벽돌", 'floor', coll)

    # --- 누각 본채. **hanok 모듈 2층 누각을 KCISA 망경루 스캔으로 바꿨다.**
    # 절차 생성 누각이 바로 옆 장안문 스캔 옆에서 확연히 떨어졌다.
    # 망경루는 제주 관덕정 옆 2층 누각이라 형식이 맞는다 — 다만 방화수류정
    # 자체는 아니다(대역이지 고증이 아니다). 의궤가 적은 ㄱ자 꺾임과
    # 가운데 온돌방은 이 대역으로는 표현되지 않는다.
    z = base_h
    _place_prop(coll, "망경루", 0.0, -bn / 2.0, z, scale=MW / 13.01)
    z2 = base_h + f1 + 0.24          # 전붕판문·난간 높이 기준으로 계속 쓴다

    # --- 누대(樓臺). 정간 남쪽. 높이 4척, 남북 13척4촌, 동서 16척4촌.
    nu_h, nu_ns, nu_ew = val(B, 'nudae_h'), val(B, 'nudae_ns'), val(B, 'nudae_ew')
    bm = bmesh.new()
    bm_box(bm, 0.0, bn / 2.0 + nu_ns / 2.0, base_h - nu_h / 2.0,
           nu_ew, nu_ns, nu_h)
    bm_to_object(bm, "방화수류정_누대", 'granite', coll)
    build_stairs("방화수류정_계단", coll, 0.0, bn / 2.0 + nu_ns, 0.0,
                 base_h - nu_h, 2.2, sgn=1.0)

    # --- 서익(西翼). 의궤 "서쪽의 한 간은 또 길게 두 간을 늘리었다".
    # 망경루 한 채로는 이 꺾임이 안 나오므로 작은 정자를 곁에 붙여 표현한다.
    _place_prop(coll, "퇴은정", west_x, west_y, base_h, scale=WW2 / 5.50)

    # --- 전붕판문(戰棚板門) 16개. 의궤 p141: 위 전안 1, 아래 총안 2씩.
    #     "만듦새는 마치 병풍을 포개어 친 것 같다."
    z2b = base_h + f1 + 0.24
    F.build_jeonbung_panmun("방화수류정_전붕판문", coll,
                            -MW / 2.0 - 0.6, MW / 2.0 + 0.6,
                            north_y - bn / 2.0 - 0.5, z2b - 0.24, ja(6),
                            val(B, 'panmun_n'))

    # --- 서남 벽돌 담 + 담 남쪽 홍예 소문 (의궤 p141)
    bm = bmesh.new()
    bm_box(bm, west_x - WW2 / 2.0 - 0.5, west_y,
           val(B, 'wall_h') / 2.0, 0.6, WD2 + 1.6, val(B, 'wall_h'))
    bm_to_object(bm, "방화수류정_서남담", 'floor', coll)

    # --- 절병통(節甁桶) — 용마루 한가운데 3마디. 이 건물의 표지다(의궤 p140).
    # 망경루 스캔에는 절병통이 없으므로 이것만 절차로 얹는다. 높이는
    # 스캔 원본 7.14 m 를 MW 비율로 줄인 값 위에 놓는다.
    bm = bmesh.new()
    zc = base_h + 7.14 * (MW / 13.01) - 0.35
    for i, (r0, r1, hgt) in enumerate(((0.34, 0.26, 0.42),
                                       (0.26, 0.20, 0.36),
                                       (0.20, 0.05, 0.32))):
        hanok.bm_cylinder(bm, 0.0, -bn / 2.0, zc, zc + hgt, r0, r1, seg=12)
        zc += hgt
    bm_to_object(bm, "방화수류정_절병통", 'tile', coll)
    return coll


def build_all():
    hanok.setup_materials()
    made = [build_hwaseomun(), build_gongsimdon(), build_banghwasuryujeong()]
    n = sum(len(c.objects) for c in made)
    tris = sum(sum(max(0, len(p.vertices) - 2) for p in o.data.polygons)
               for c in made for o in c.objects if o.type == 'MESH')
    print("의궤 시설물: 컬렉션 %d / 메시 %d / 삼각형 %d" % (len(made), n, tris))
    return made
