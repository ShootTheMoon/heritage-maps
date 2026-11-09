# -*- coding: utf-8 -*-
"""화성 장안문 재제작 -- 스캔 soup 을 게임용 저폴리 + 베이크 텍스처로 바꾼다.
2026-08-30. Blender 5.2 / blender-mcp 경유로 실행한다.

왜 이 순서인가 (전부 실측으로 결정했다):
  1) 용접 2mm  -- 스캔은 삼각형마다 정점이 따로다. 2mm 면 면 손실 0.3% 로 정점 44% 가 준다.
                  문서의 8mm 는 한옥 마스터용이라 기와를 뭉갠다(면 64% 소멸, 실측).
  2) 복셀 리메시 -- 이 메시들은 껍질이 1,000~9,000 개인 soup 이라 collapse 감축이
                  원리적으로 불가능하다. f/shell 가드도 bbox 가드도 실패했다(둘 다 시도함).
                  리메시가 껍질을 1개로 만들면 그때부터 감축이 안전하다.
  3) 감축      -- 수밀 단일 껍질이라 부술 조각이 없다.
  4) UV + 베이크 -- 기와 요철은 어떤 예산으로도 지오메트리로 못 남긴다(리메시 0.10m 가
                  이미 뭉갠다). 오버데어는 텍스처 슬롯이 하나뿐이라 노멀맵을 못 받으므로
                  음영을 알베도에 굽는다.
"""
import bpy, bmesh, os, time
import numpy as np
from mathutils import Vector

OUT = "C:/Users/HSP/Desktop/blender/hwaseong_rebuild"
WELD = 0.002


def log(*a):
    print(*a)


def weld_all(dist=WELD):
    t0 = time.time()
    for me in bpy.data.meshes:
        if not len(me.vertices):
            continue
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
        bm.to_mesh(me); bm.free(); me.update()
    return time.time() - t0


def _view3d():
    """에디트 모드 오퍼레이터는 VIEW_3D 영역/리전이 있어야 poll 을 통과한다."""
    for w in bpy.data.window_managers[0].windows:
        for area in w.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for region in area.regions:
                if region.type == 'WINDOW':
                    return dict(window=w, screen=w.screen, area=area,
                                region=region, space_data=area.spaces.active)
    return {}


def _sel(objs, active):
    vl = bpy.context.view_layer
    for o in vl.objects:
        o.select_set(False)
    for o in objs:
        o.hide_viewport = False
        o.select_set(True)
    vl.objects.active = active
    ov = dict(active_object=active, selected_objects=list(objs),
              selected_editable_objects=list(objs), object=active)
    ov.update(_view3d())
    return ov


def join_copy(objs, name):
    """원본은 남기고 복제본을 하나로 합친다 (베이크 소스로 원본이 필요하다)."""
    cps = []
    for o in objs:
        c = o.copy(); c.data = o.data.copy()
        bpy.context.scene.collection.objects.link(c)
        cps.append(c)
    tgt = cps[0]; tgt.name = name; tgt.data.name = name
    if len(cps) > 1:
        ov = _sel(cps, tgt)
        with bpy.context.temp_override(**ov):
            bpy.ops.object.join()
    return tgt


def remesh(o, voxel):
    o.data.remesh_voxel_size = voxel
    o.data.remesh_voxel_adaptivity = 0.0
    ov = _sel([o], o)
    with bpy.context.temp_override(**ov):
        bpy.ops.object.voxel_remesh()
    return len(o.data.vertices)


def decimate(o, target_faces):
    nf = len(o.data.polygons)
    if nf <= target_faces:
        return nf
    m = o.modifiers.new("dec", 'DECIMATE'); m.decimate_type = 'COLLAPSE'
    m.ratio = target_faces / float(nf)
    dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    o.modifiers.remove(m)
    old = o.data; nm = old.name
    o.data = new; bpy.data.meshes.remove(old); new.name = nm
    return len(new.polygons)


def unwrap(o, margin=0.004):
    me = o.data
    while len(me.uv_layers) > 1:
        me.uv_layers.remove(me.uv_layers[-1])
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    me.uv_layers[0].name = "UVMap"
    ov = _sel([o], o)
    try:
        with bpy.context.temp_override(**ov):
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=margin)
            bpy.ops.object.mode_set(mode='OBJECT')
        return 'smart_project'
    except RuntimeError:
        _cube_project(o)
        return 'cube_fallback'


def _cube_project(o):
    """오퍼레이터 컨텍스트가 안 잡힐 때의 폴백. 면 법선의 최대 축으로 평면 투영하고
    ±X / ±Y / ±Z 세 묶음을 가로 3칸에 나눠 담는다. 겹치지 않으면 베이크는 성립한다."""
    me = o.data
    uvl = me.uv_layers[0].data
    co = [v.co for v in me.vertices]
    mn = Vector((min(p.x for p in co), min(p.y for p in co), min(p.z for p in co)))
    mx = Vector((max(p.x for p in co), max(p.y for p in co), max(p.z for p in co)))
    d = mx - mn
    s = max(d.x, d.y, d.z) or 1.0
    pair = [(1, 2), (0, 2), (0, 1)]
    for poly in me.polygons:
        n = poly.normal
        ax = max(range(3), key=lambda k: abs(n[k]))
        ui, vi = pair[ax]
        for li in poly.loop_indices:
            p = me.vertices[me.loops[li].vertex_index].co
            u = min(0.98, (p[ui] - mn[ui]) / s)
            v = min(0.98, (p[vi] - mn[vi]) / s)
            uvl[li].uv = ((ax + u + 0.01) / 3.0, (v + 0.01))


def _bake(lp, srcs, img, btype, size, extr, dist, **kw):
    mat = lp.data.materials[0]
    nt = mat.node_tree
    for n in [n for n in nt.nodes if n.type == 'TEX_IMAGE']:
        nt.nodes.remove(n)
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img
    nt.nodes.active = t
    for n in nt.nodes:
        n.select = (n == t)
    ov = _sel(list(srcs) + [lp], lp)
    with bpy.context.temp_override(**ov):
        bpy.ops.object.bake(type=btype, use_selected_to_active=True,
                            cage_extrusion=extr, max_ray_distance=dist,
                            margin=8, use_clear=True, **kw)


def bake_class(lp, srcs, name, size=2048, extr=0.12, dist=0.30,
               light=(0.30, 0.45, 0.84), lo=0.62, hi=1.18, gain=1.0):
    """노멀 + 디퓨즈를 굽고, 노멀에서 음영을 만들어 알베도에 곱한 뒤 PNG 로 저장한다.
    AO 베이크는 이 씬에서 전부 0 이 나와 못 쓴다. 노멀 기반이 결정적이고 빠르다."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 1

    mat = bpy.data.materials.new("MAT_" + name)
    mat.use_nodes = True
    lp.data.materials.clear(); lp.data.materials.append(mat)

    for nm in ("_nrm_" + name, "_col_" + name):
        if nm in bpy.data.images:
            bpy.data.images.remove(bpy.data.images[nm])
    nrm = bpy.data.images.new("_nrm_" + name, size, size, alpha=False, float_buffer=True)
    nrm.colorspace_settings.name = 'Non-Color'
    col = bpy.data.images.new("_col_" + name, size, size, alpha=False)

    _bake(lp, srcs, nrm, 'NORMAL', size, extr, dist)
    _bake(lp, srcs, col, 'DIFFUSE', size, extr, dist, pass_filter={'COLOR'})

    n = np.empty(size * size * 4, dtype=np.float32); nrm.pixels.foreach_get(n)
    c = np.empty(size * size * 4, dtype=np.float32); col.pixels.foreach_get(c)
    n = n.reshape(-1, 4); c = c.reshape(-1, 4)

    v = n[:, :3] * 2.0 - 1.0
    L = np.linalg.norm(v, axis=1, keepdims=True); L[L < 1e-6] = 1.0
    v /= L
    Ld = np.array(light, dtype=np.float32); Ld /= np.linalg.norm(Ld)
    shade = (lo + (hi - lo) * np.clip(v @ Ld, 0.0, 1.0))[:, None]

    out = np.clip(c[:, :3] * shade * gain, 0.0, 1.0)
    valid = c[:, :3].sum(axis=1) > 0.01
    if valid.any():
        out[~valid] = out[valid].mean(axis=0)

    fin = bpy.data.images.get("BC_" + name)
    if fin:
        bpy.data.images.remove(fin)
    fin = bpy.data.images.new("BC_" + name, size, size, alpha=False)
    fin.pixels.foreach_set(np.concatenate(
        [out, np.ones((out.shape[0], 1), dtype=np.float32)], axis=1).ravel())
    os.makedirs(OUT, exist_ok=True)
    fin.filepath_raw = "%s/%s_BC.png" % (OUT, name)
    fin.file_format = 'PNG'
    fin.save()

    nt = mat.node_tree
    for x in [x for x in nt.nodes if x.type == 'TEX_IMAGE']:
        nt.nodes.remove(x)
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = fin
    b = next((x for x in nt.nodes if x.type == 'BSDF_PRINCIPLED'), None)
    if b:
        nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    bpy.data.images.remove(nrm); bpy.data.images.remove(col)
    return fin.filepath_raw, float(100.0 * valid.sum() / len(valid)), float(out[valid].mean())


def build_class(objs, name, voxel, target_faces, size=2048, extr=0.12, dist=0.30, **bk):
    """한 부류를 통째로: 합치기 -> 리메시 -> 감축 -> UV -> 베이크."""
    t0 = time.time()
    v_in = sum(len(o.data.vertices) for o in objs)
    f_in = sum(len(o.data.polygons) for o in objs)
    old = bpy.data.objects.get("LP_" + name)
    if old:
        bpy.data.meshes.remove(old.data)
    lp = join_copy(objs, "LP_" + name)
    v_rm = remesh(lp, voxel)
    decimate(lp, target_faces)
    unwrap(lp)
    path, cov, mean = bake_class(lp, objs, name, size=size, extr=extr, dist=dist, **bk)
    return dict(name=name, objs=len(objs), v_in=v_in, f_in=f_in, v_remesh=v_rm,
                v_out=len(lp.data.vertices), f_out=len(lp.data.polygons),
                tex=path, coverage=cov, mean=mean, secs=time.time() - t0)
