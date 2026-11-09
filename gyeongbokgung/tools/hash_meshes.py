# -*- coding: utf-8 -*-
"""CP-1 게이트 — 전체 메시의 정점 해시를 찍는다.

    blender -b -P hash_meshes.py -- <출력.json> [--site all|gbg|dsg]

지붕 재작성처럼 위험한 변경을 하기 전에 기준선을 남기고, 변경 후 같은 것을
다시 찍어 diff 한다. "눈으로 보니 똑같다" 는 증거가 아니다.

해시는 **월드 좌표**에서 뜬다. 배치 행렬이 바뀌어도 잡히도록.
"""

import hashlib
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(bpy.data.filepath or __file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def mesh_hash(obj):
    """정점을 월드 좌표로 0.1mm 격자에 스냅해 해시한다.

    부동소수 마지막 비트까지 비교하면 무관한 재계산에도 깨진다.
    0.1mm 는 이 프로젝트에서 의미 있는 최소 단위보다 훨씬 작다.
    """
    mw = obj.matrix_world
    h = hashlib.sha1()
    for v in obj.data.vertices:
        w = mw @ v.co
        h.update(b"%d,%d,%d;" % (round(w.x * 1e4), round(w.y * 1e4),
                                 round(w.z * 1e4)))
    return h.hexdigest()[:16]


def snapshot(colls=None):
    out = {}
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or not obj.data.vertices:
            continue
        if colls is not None:
            names = {c.name for c in obj.users_collection}
            if not (names & colls):
                continue
        out[obj.name] = {
            'hash': mesh_hash(obj),
            'verts': len(obj.data.vertices),
            'polys': len(obj.data.polygons),
            'tris': sum(max(0, len(p.vertices) - 2) for p in obj.data.polygons),
        }
    return out


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    out_path = argv[0] if argv else 'mesh_hashes.json'
    site = 'all'
    if '--site' in argv:
        site = argv[argv.index('--site') + 1]

    # 씬 비우기 — 기본 큐브 등이 섞이면 diff 가 오염된다
    bpy.ops.wm.read_factory_settings(use_empty=True)

    import build
    if site in ('all', 'gbg'):
        build.build_all()
    if site in ('all', 'dsg'):
        try:
            from deoksugung import build_dsg
            build_dsg.build_all()
        except Exception as e:
            print("덕수궁 건너뜀: %s" % e)

    snap = snapshot()
    total_tris = sum(v['tris'] for v in snap.values())
    payload = {
        'meshes': snap,
        'summary': {'objects': len(snap), 'tris': total_tris,
                    'verts': sum(v['verts'] for v in snap.values())},
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1, sort_keys=True)
    print("HASHED %d meshes, %d tris -> %s" % (len(snap), total_tris, out_path))


if __name__ == '__main__':
    main()
