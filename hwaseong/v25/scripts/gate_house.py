# -*- coding: utf-8 -*-
"""장안문 문루 절차 생성 (2차). KCISA 스캔 문루(soup)를 hanok.py/roof.py 팔레트 모델로 교체한다.
실측 기준: 정면 5칸 ~21.5 m, 측면 2칸 ~7.8 m, 중층 우진각지붕(gable_ratio=1.0), 육축 상면 위에 선다.
Run in GUI: ns={}; exec(open(p,encoding='utf-8').read(), ns); ns['main']()"""
import bpy, bmesh, sys, importlib
G = r"C:\Users\HSP\Desktop\blender\gyeongbokgung"
if G not in sys.path:
    sys.path.append(G)
import hanok, roof
importlib.reload(hanok); importlib.reload(roof)
from hanok import (new_collection, grid_positions, build_columns, build_beams, build_brackets,
                   build_walls, build_gyeja_railing, bm_to_object, bm_box)

P = dict(
    bays_x=[4.3, 4.6, 5.0, 4.6, 4.3],   # 정면 5칸 22.8 m (KCISA Column bbox)
    bays_y=[4.05, 4.05],                # 측면 2칸 8.1 m
    up_x=[3.8, 4.1, 4.6, 4.1, 3.8],     # 상층 20.4 m (KCISA GH_Wall bbox)
    up_y=[2.8, 2.8],                    # 상층 5.6 m
    z0=7.70,                            # 육축 상면 (KCISA Floor min z)
    col_h=3.40,
    low_eave=11.60, low_top=13.20,      # KCISA 하층 처마 11.35, 상층벽 12.7~14.6
    high_col_top=16.20,
    up_eave=17.00, up_ridge=21.20,      # KCISA 상층 처마 16.8, 용마루 21.2
    eave_out_low=3.45, eave_out_up=3.80,
)
COL = "화성_장안문"
LEFTOVERS = ["장안문_GH_Wall_01", "장안문_RammedEarth_01", "장안문_Pedestal_01", "장안문_Note_01", "장안문_Signboard_002_01"]


def clear_kcisa_gatehouse():
    """KCISA 목조 문루 32개 + 다른 컬렉션에 남는 문루 부속(적심·상층벽·초석·현판)을 뺀다.
    육축·옹성·성벽은 화성_성벽에 있어 그대로."""
    c = bpy.data.collections[COL]
    n = 0
    for o in list(c.objects):
        if o.name.startswith("장안문_"):
            bpy.data.objects.remove(o, do_unlink=True); n += 1
    for nm in LEFTOVERS:
        o = bpy.data.objects.get(nm)
        if o:
            bpy.data.objects.remove(o, do_unlink=True); n += 1
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for x in [x for x in blk if x.users == 0]:
            blk.remove(x)
    return n


def build():
    hanok.setup_materials()
    coll = new_collection("문루_절차")
    xs, W = grid_positions(P['bays_x']); ys, D = grid_positions(P['bays_y'])
    z = P['z0']
    bm = bmesh.new(); bm_box(bm, 0, 0, z - 0.09, W + 1.6, D + 1.6, 0.18); bm_to_object(bm, "문루_마루", 'wood_dark', coll)
    col_top = z + P['col_h']
    build_columns("문루_하층", coll, xs, ys, z, P['col_h'], 0.36, perimeter_only=True)
    build_beams("문루_하층_창방", coll, xs, ys, col_top)
    build_brackets("문루_하층", coll, xs, ys, col_top + 0.26, tiers=2, spacing=1.7)
    build_walls("문루_하층벽", coll, xs, ys, z, P['col_h'])
    # 상층 (고주)
    xs2, W2 = grid_positions(P['up_x']); ys2, D2 = grid_positions(P['up_y'])
    build_columns("문루_고주", coll, xs2, ys2, z, P['high_col_top'] - z, 0.40, perimeter_only=True)
    eo = P['eave_out_low']
    roof.build_skirt_roof("문루", coll, W + 2 * eo, D + 2 * eo, W2 + 1.2, D2 + 1.2, P['low_eave'], P['low_top'])
    up_h = P['high_col_top'] - P['low_top']
    build_walls("문루_상층벽", coll, xs2, ys2, P['low_top'], up_h, sill=0.45)
    build_beams("문루_상층_창방", coll, xs2, ys2, P['high_col_top'])
    build_brackets("문루_상층", coll, xs2, ys2, P['high_col_top'] + 0.26, tiers=2, spacing=1.7)
    eu = P['eave_out_up']
    roof.build_hip_gable_roof("문루_상층", coll, W2 + 2 * eu, D2 + 2 * eu, P['up_eave'], P['up_ridge'],
                              ridge_ratio=0.45, gable_ratio=1.0, lift=1.0, out=0.55, eave_out=eu)
    return coll


def main():
    removed = clear_kcisa_gatehouse()
    coll = build()
    tgt = bpy.data.collections[COL]
    objs = list(coll.objects)
    for o in objs:
        tgt.objects.link(o); coll.objects.unlink(o)
    bpy.data.collections.remove(coll)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs if o.type == 'MESH')
    print("@@GATEHOUSE removed_kcisa=%d built=%d tris=%d mats=%d" % (
        removed, len(objs), tris, len({m.name for o in objs for m in o.data.materials if m})))
    return objs
