# -*- coding: utf-8 -*-
"""익스포트한 FBX 를 **다시 열어** 매니페스트와 대조한다.

    blender -b -noaudio -P check_fbx_roundtrip.py -- <익스포트_폴더> [파일.fbx ...]

왜 이게 필요한가
    배치가 틀렸는지 익스포트가 틀렸는지 가르려면 **독립적인 경로로 측정**해야 한다.
    매니페스트 값을 레벨에서 다시 읽어 비교하는 건 검증이 아니다 — 내가 쓴 값을
    내가 읽는 것일 뿐이다.

    FBX 를 블렌더로 되열면 익스포터를 거치지 않은 경로로 치수를 잴 수 있다.
    화성에서 이걸 돌려 bbox 오차 0.000 m / 삼각형 수 완전 일치를 확인했고,
    그래서 익스포터를 용의선상에서 지우고 위상 쪽(check_shells.py)으로 갔다.

보는 것
    삼각형 수   매니페스트와 일치해야 한다
    bbox        매니페스트 size_cm 과 일치해야 한다
                매니페스트는 오버데어 축(X=bx, Y=bz, Z=-by)이라 되돌려서 비교한다
    이미지      0 이면 텍스처가 안 실렸다 (check_export_textures.py 로 전수 검사)
"""
import io
import json
import os
import sys

import bpy
from mathutils import Vector


def check(d, name, man):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=os.path.join(d, name))

    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    tris = 0
    lo = Vector((1e18,) * 3)
    hi = Vector((-1e18,) * 3)
    for o in objs:
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    sz = hi - lo

    exp = [x for x in man["meshes"] if x["file"] == name]
    et = sum(x["tris"] for x in exp)
    print("== %s ==" % name)
    print("   오브젝트 %d / 삼각형 %d (매니페스트 %d) / 머티리얼 %d / 이미지 %d"
          % (len(objs), tris, et, len(bpy.data.materials), len(bpy.data.images)))
    print("   bbox  %.2f x %.2f x %.2f m" % (sz.x, sz.y, sz.z))
    if len(exp) == 1:
        s = exp[0]["size_cm"]
        # 오버데어 축을 블렌더 축으로 되돌린다: X=bx, Y=bz, Z=-by
        e = (s["X"] / 100.0, s["Z"] / 100.0, s["Y"] / 100.0)
        print("   기대  %.2f x %.2f x %.2f m   차이 %+.3f / %+.3f / %+.3f"
              % (e[0], e[1], e[2], sz.x - e[0], sz.y - e[1], sz.z - e[2]))
    if tris != et:
        print("   !! 삼각형 수가 다르다 — 익스포트와 매니페스트가 어긋났다")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        sys.exit(__doc__)
    d = argv[0]
    man = json.load(io.open(os.path.join(d, "manifest.json"), encoding="utf-8"))
    names = argv[1:] or sorted(f for f in os.listdir(d) if f.lower().endswith(".fbx"))
    for n in names:
        check(d, n, man)


main()
