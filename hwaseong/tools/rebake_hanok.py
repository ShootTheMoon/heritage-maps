# -*- coding: utf-8 -*-
"""한옥 소품 재감축 — 지붕 기와가 판때기로 튀어나오던 문제의 근본 수정.

증상
    도시 한옥의 지붕에서 큰 평면 조각이 기와 사이로 삐죽 솟아 있었다.
    가까이서만 보이지만 눈높이 시점에서는 바로 눈에 띈다.

원인
    감축 전 메시를 재 봤더니 **면 7,600개에 연결 껍질이 7,584개** 였다.
    사실상 모든 면이 서로 떨어진 조각이다. KCISA 원본은 FBX 로 나오면서
    삼각형마다 정점을 따로 들고 있고(324k 면에 정점 664k), 기와도 낱장
    메시로 모델링돼 있다. 그 상태로 Decimate COLLAPSE 를 걸면 낱장마다
    삼각형 하나로 접히는데, 굽은 기와의 바깥 꼭짓점 3개만 남으니 결과가
    **기와 모양이 아니라 임의 방향의 판때기**가 된다.

    → 감축 자체가 아니라 **감축 전에 용접을 안 한 것**이 버그였다.

수정
    용접(0.8 cm) → 평면 정리(6도) → COLLAPSE 순으로 간다.
    용접만으로 사랑채 껍질이 171,798 → 3,897 로 줄어든다.

목표 삼각형은 **껍질 수에서 유도한다.** 낱장 기와 하나가 삼각형 하나로
접히면 다시 판때기가 되므로, 껍질당 최소 FACES_PER_SHELL 장은 남긴다.
실험값: 사랑채를 8,000 으로 눌렀더니 평면 정리를 12도·30도로 아무리 세게
해도 기와가 갈렸고, 27,000 근처에서 깨끗했다(껍질당 약 7장).

    blender 를 GUI 로 띄우고 Sketchfab 애드온으로 아래 UID 를 받은 다음
    rebuild(...) 를 부르고, libraries.write 로 빼서 bake 스크립트로
    hwaseong_props.blend 에 넣는다. 애드온이 필요해 헤드리스로는 못 돈다.
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

# (이름, Sketchfab UID, 참조 bbox 크기 X,Y,Z) — 크기는 기존 소품과 맞춘다.
# city.HANOK 이 이 치수를 기준으로 footprint 에 맞춰 축척하므로 바뀌면 안 된다.
HANOK = [
    ("사랑채", "095e7862fb91443ca2658b1e98066e53", (8.75, 13.99, 5.69)),
    ("초가집", "e78d2a2c80b646279e44e2ceaf6a1fd2", (8.63, 8.27, 3.43)),
    ("대문",   "f844d3c578614148af2677add0678c97", (2.84, 5.21, 5.99)),
]

WELD_M = 0.008          # 용접 거리. 0.5 mm 로도 껍질이 171k→4.9k 로 떨어진다
PLANAR_DEG = 6.0        # 평면 정리 각. 12도부터 기와 모양이 뭉개진다
# **비율이 결과 면수보다 중요하다.** 껍질이 많은 메시에서는 비율을 바닥까지
# 밀어도 총 면수가 껍질 수에 걸려 안 내려간다. 대신 손댈 수 있는 껍질만
# 과하게 부수므로, 같은 29k 라도 비율 0.13 은 갈리고 0.45 는 멀쩡했다.
MIN_RATIO = 0.45


def _count_shells(bm):
    seen, n = set(), 0
    for f in bm.faces:
        if f.index in seen:
            continue
        n += 1
        stack = [f]
        seen.add(f.index)
        while stack:
            g = stack.pop()
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
    return n


TEX_PX = 1024           # 소품 라이브러리에 넣을 텍스처 한 변


def slim(objs, px=TEX_PX):
    """베이스 컬러만 남기고 텍스처를 줄인다.

    스케치팹 원본은 재질마다 baseColor·normal·metallicRoughness 3장씩,
    그중 상당수가 4K다. 그대로 구우면 세 채가 **443 MB** 로 나왔다.
    오버데어는 어차피 baseColor 한 장만 받고, 화면에서도 한옥 한 채가
    수십 픽셀이라 1K로 충분하다.
    """
    imgs, dropped = set(), 0
    for o in objs:
        for m in o.data.materials:
            if not m or not m.use_nodes:
                continue
            nt = m.node_tree
            for nd in list(nt.nodes):
                if nd.type != 'TEX_IMAGE' or not nd.image:
                    continue
                if 'baseColor' in nd.image.name or 'BaseColor' in nd.image.name:
                    imgs.add(nd.image)
                else:
                    nt.nodes.remove(nd)
                    dropped += 1
    for im in imgs:
        if max(im.size) > px:
            im.scale(px, px)
        im.pack()
    print("텍스처 정리: 베이스컬러 %d장 %dpx 로 축소, 부수 맵 %d장 제거"
          % (len(imgs), px, dropped))
    return len(imgs)


def descendants(root):
    """빈 오브젝트 아래 매달린 **메시만** 모은다.

    이름 접두사로 고르면 안 된다. 초가집 모델은 자식 이름이 H_02_* 와
    Object_* 로 섞여 있고, 그중 일부만 잡으면 바닥면이 빠져 bbox 가
    틀어진다(실제로 지붕이 8 m 짜리로 나왔다).
    """
    out, stack = [], [root]
    while stack:
        o = stack.pop()
        if o.type == 'MESH' and o.data and o.data.polygons:
            out.append(o)
        stack.extend(o.children)
    return out


def _join(objs, name):
    """여러 메시를 하나로 합치고 변환을 메시에 굽는다."""
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = name
    # **부모를 먼저 끊는다.** Sketchfab 임포트는 메시를 빈 오브젝트 밑에
    # 매달아 놓는데, 부모를 둔 채 matrix_world 를 단위행렬로 만들면 다음
    # 평가 때 부모 변환이 되살아난다. 그 바람에 사랑채가 0.866배로 작아졌다.
    mw = o.matrix_world.copy()
    o.parent = None
    o.data.transform(mw)
    o.matrix_basis = Matrix.Identity(4)
    return o


def _clip(o, lo, hi, margin=0.02):
    """감축이 원본 bbox 밖으로 밀어낸 정점의 면을 지운다.

    COLLAPSE 는 이차오차 최소화로 병합점을 잡는데, 그 점이 원래 형상
    바깥에 놓일 때가 있다. 사랑채에서는 정점 2개가 바닥 아래 0.87 m 로
    빠져 나가 건물 bbox 를 통째로 늘려 놨다. 몇 개 안 되므로 면째 지운다.
    """
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bad = [v for v in bm.verts
           if any(v.co[k] < lo[k] - margin or v.co[k] > hi[k] + margin
                  for k in range(3))]
    if bad:
        kill = {f for v in bad for f in v.link_faces}
        bmesh.ops.delete(bm, geom=list(kill), context='FACES')
        loose = [v for v in bm.verts if not v.link_faces]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context='VERTS')
        bm.to_mesh(o.data)
    bm.free()
    return len(bad)


def _fit(o, size):
    """참조 치수에 맞춰 등배 축척하고, X·Y 중심 / 지면 z=0 으로 옮긴다."""
    me = o.data
    lo = Vector((min(v.co[k] for v in me.vertices) for k in range(3)))
    hi = Vector((max(v.co[k] for v in me.vertices) for k in range(3)))
    cur = hi - lo
    # 축마다 비율이 조금씩 다르므로 **등배**로 간다 — 축별로 늘리면 기와가 찌그러진다.
    # 기준은 바닥면(X·Y)이다. city.HANOK 이 footprint 에 맞춰 다시 축척하므로
    # 평면 치수가 맞아야 하고, 높이는 그에 따라온다.
    s = min(size[0] / cur.x, size[1] / cur.y)
    print("    _fit: 현재 %.2f x %.2f x %.2f → 배율 %.4f" % (cur.x, cur.y, cur.z, s))
    for v in me.vertices:
        v.co = (v.co - Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))) * s
    return o


def prepare(name, objs):
    """Sketchfab 임포트를 하나로 합쳐 **원본 보관본**을 만든다.

    join 은 원본을 먹어 치우므로, 비율을 바꿔 가며 시험하려면 합친 결과를
    한 번 남겨 둬야 한다. 안 그러면 시도할 때마다 다시 내려받게 된다.
    """
    o = _join(objs, name + "_원본")
    o.use_fake_user = True
    o.data.use_fake_user = True
    return o


def rebuild(name, src, size, weld=WELD_M, planar=PLANAR_DEG,
            ratio=MIN_RATIO):
    """보관본 → 감축된 소품 하나. 원본은 건드리지 않는다."""
    me = src.data.copy()
    o = bpy.data.objects.new(name + "_새로", me)
    bpy.context.scene.collection.objects.link(o)
    n_in = len(me.polygons)

    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    sh0 = _count_shells(bm)
    # **용접이 핵심.** 이걸 빼면 낱장 기와가 그대로 남아 감축이 판때기를 만든다.
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=weld)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(planar),
                             verts=list(bm.verts), edges=list(bm.edges))
    bm.faces.ensure_lookup_table()
    shells = _count_shells(bm)
    bm.to_mesh(me)
    bm.free()

    n_mid = len(me.polygons)
    lo = Vector((min(v.co[k] for v in me.vertices) for k in range(3)))
    hi = Vector((max(v.co[k] for v in me.vertices) for k in range(3)))
    md = o.modifiers.new("dec", 'DECIMATE')
    md.ratio = ratio
    dg = bpy.context.evaluated_depsgraph_get()
    o.data = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    o.modifiers.clear()
    bpy.data.meshes.remove(me)
    n_out = _clip(o, lo, hi)
    if n_out:
        print("    감축이 bbox 밖으로 민 정점 %d개의 면을 제거" % n_out)
    _fit(o, size)
    old = bpy.data.objects.get(name)
    if old and old is not o:
        bpy.data.objects.remove(old, do_unlink=True)
    o.name = name
    o.data.name = name
    print("%-6s 원본 %7d면/껍질 %6d → 용접·평면 %7d면/껍질 %5d → 비율 %.2f → 최종 %6d"
          % (name, n_in, sh0, n_mid, shells, ratio, len(o.data.polygons)))
    return o
