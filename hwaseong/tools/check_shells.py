# -*- coding: utf-8 -*-
"""FBX 의 **연결 껍질(connected shell)** 수를 세어 메시가 갈렸는지 판정한다.

    blender -b -noaudio -P check_shells.py -- <익스포트_폴더> [파일.fbx ...]

왜 이게 필요한가
    화성 건물이 오버데어에서 폐가처럼 부서져 보였다. 그런데 블렌더 뷰포트에서는
    완벽했고, 치수도 완벽했다(check_fbx_roundtrip.py 로 bbox 오차 0.000 m 확인).
    원인은 **위상**이었다 — 데시메이트를 용접 없이 돌려서 메시가 면 2개짜리
    조각 수천 개로 갈려 있었다.

    갈린 면들이 좌표상 딱 붙어 있으면 블렌더는 그대로 그려 준다. 그래서 눈으로는
    절대 안 보인다. 엔진이 LOD 생성이나 메시 최적화를 돌리는 순간 흩어진다.

읽는 법
    면/껍질 비가 판정값이다.

        ~2      면 2개마다 따로 논다. **완전히 갈렸다**
        ~5      심하게 갈렸다
        20 이상 정상
        수백~수천  잘 용접된 메시

    공간 분할(split_mesh_lossless)로 쪼갠 조각은 껍질이 많은 게 **정상**이다 —
    슬랩 하나가 집 여러 채를 잘라 담으므로. CTB 가 17~34 로 나오는 건 그 때문이다.
    판정은 **같은 그룹 안에서 유독 낮은 것**을 찾는 식으로 한다.

고치는 법은 rebake_hanok.py 를 보라 — 용접(WELD_M 0.008) 뒤에 데시메이트하고,
**ratio 를 0.45 아래로 내리지 않는다**(0.30 이면 다시 갈린다).
"""
import os
import sys

import bmesh
import bpy


def shells(me):
    """면 수와 연결 껍질 수를 돌려준다."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    seen = set()
    n = 0
    for f in bm.faces:
        if f.index in seen:
            continue
        n += 1
        stack = [f]
        seen.add(f.index)
        while stack:
            for e in stack.pop().edges:
                for nf in e.link_faces:
                    if nf.index not in seen:
                        seen.add(nf.index)
                        stack.append(nf)
    out = (len(bm.faces), n)
    bm.free()
    return out


def check(path):
    # 파일마다 빈 씬에서 연다 — 안 그러면 이전 파일의 메시가 섞여 집계된다.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    rows = []
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            rows.append((o.name,) + shells(o.data))
    if not rows:
        print("%-14s 메시 없음" % os.path.basename(path))
        return
    tf = sum(r[1] for r in rows)
    ts = sum(r[2] for r in rows)
    worst = min(rows, key=lambda r: r[1] / max(r[2], 1))
    print("%-14s 메시%3d 면%8d 껍질%7d  면/껍질 %6.1f   최악: %-30s %5.1f"
          % (os.path.basename(path), len(rows), tf, ts, tf / max(ts, 1),
             worst[0][:30], worst[1] / max(worst[2], 1)))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        sys.exit(__doc__)
    d = argv[0]
    names = argv[1:] or sorted(f for f in os.listdir(d) if f.lower().endswith(".fbx"))
    for n in names:
        check(os.path.join(d, n))


main()
