# -*- coding: utf-8 -*-
"""User request 2026-09-09: "에셋 디폴트값으로 전부 재정렬" — rebuild the scene from UNMODIFIED assets:
KCISA v24 collections as-is (no weld/join/decimate), heritage FBX modules raw (no decimate/bake),
props raw (no bake), then lay out with assemble_v25 and hide the prototype collections.
Run in GUI: ns={}; exec(open(p,encoding='utf-8').read(), ns); ns['main']()"""
import bpy, os, sys
RB = r"C:\Users\HSP\Desktop\blender\hwaseong_rebuild"; V25 = os.path.join(RB, "v25")
for p in (RB, V25):
    if p not in sys.path:
        sys.path.append(p)
import importlib, rebuild, kit_namhan, props_bake, assemble_v25, snap, gate_house, props_bk
for m in (rebuild, kit_namhan, props_bake, assemble_v25, snap, gate_house, props_bk):
    importlib.reload(m)

V24 = os.path.join(RB, "janganmun_v24.blend")
PROTOS = os.path.join(V25, "protos_bk.blend")   # P_동아시아집(1024 tex) + P_BK_* (BlenderKit, already collapsed)
PROPS = r"C:\Users\HSP\Desktop\blender\gyeongbokgung\hwaseong_props.blend"
RAW_PROPS = ["초가집", "대문", "바위무리"]


def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.cameras, bpy.data.lights):
        for x in [x for x in blk if x.users == 0]:
            blk.remove(x)


def link_col(c):
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c


def append_v24():
    with bpy.data.libraries.load(V24, link=False) as (df, dt):
        dt.collections = [n for n in df.collections if n in ("화성_장안문", "화성_성벽", "화성_소품")]
    for c in dt.collections:
        link_col(c)
    print("@@V24", [(c.name, len(c.objects)) for c in dt.collections])


def kit_raw():
    kit = link_col(bpy.data.collections.new("KIT_NH"))
    for i, (key, kw, *_rest) in enumerate(kit_namhan.MODULES):
        src, d = kit_namhan.import_module(key, kw)
        fixed, missing = kit_namhan.relink_textures([src], kit_namhan.tex_files(d))
        dims = kit_namhan.align(src)
        src.name = "NH_" + key; src.data.name = src.name
        for c in list(src.users_collection):
            c.objects.unlink(src)
        kit.objects.link(src); src.location = (0.0, 200.0 + 12.0 * i, 0.0)
        print("@@KIT_RAW", key, dims, len(src.data.polygons), "mats", len(src.data.materials), "missing", missing[:2])


def props_raw():
    pc = link_col(bpy.data.collections.new("KIT_PROPS"))
    with bpy.data.libraries.load(PROPS, link=False) as (df, dt):
        dt.objects = [n for n in df.objects if n in RAW_PROPS]
    for i, o in enumerate(dt.objects):
        o.name = "P_" + o.name; pc.objects.link(o)
        dims = assemble_v25.bake_and_ground(o); o.location = (0.0, 300.0 + 20.0 * i, 0.0)
        print("@@PROP_RAW", o.name, dims, len(o.data.materials))
    with bpy.data.libraries.load(PROTOS, link=False) as (df, dt):
        dt.objects = [n for n in df.objects if n.startswith(("P_동아시아집", "P_BK_"))]
    for i, o in enumerate(dt.objects):
        if o:
            pc.objects.link(o); o.location = (60.0, 440.0 + 15.0 * i, 0.0)
    props_bake.pine()
    props_bake.millstone(tri_target=10 ** 9)


def viewport_reset():
    a = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D'); sp = a.spaces.active
    sp.lens = 50; sp.clip_start = 0.1; sp.clip_end = 2000
    sp.shading.type = 'MATERIAL'; sp.overlay.show_overlays = True
    snap.look((0, 70, 28), (0, 0, 10), 35)


def main():
    clear_scene(); append_v24(); kit_raw(); props_raw()
    assemble_v25.PROP_NAMES = list(RAW_PROPS)
    assemble_v25.main(); assemble_v25.consolidate(); assemble_v25.roads()
    gate_house.main()          # KCISA 목조 문루 -> 절차 생성 문루
    props_bk.main()            # BlenderKit 소품 배치 (프로토타입은 protos_bk.blend 에서)
    for m in bpy.data.materials:  # 임포터가 알파를 연결한 재질은 OPAQUE (오버데어는 알파를 안 쓴다)
        b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if m.use_nodes else None
        if b and b.inputs['Alpha'].is_linked and m.name.startswith("M_Ox_Mill"):
            for l in list(b.inputs['Alpha'].links):
                m.node_tree.links.remove(l)
            m.blend_method = 'OPAQUE'
    for n in ("KIT_NH", "KIT_PROPS"):
        bpy.context.view_layer.layer_collection.children[n].exclude = True
    viewport_reset()
    cols = [c for c in bpy.data.collections if c.name.startswith("화성_")]
    print("@@RESET objs=%d tris=%d" % (sum(len(c.objects) for c in cols),
          sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for c in cols for o in c.objects if o.type == 'MESH')))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(V25, "hwaseong_v25.blend"))
    print("@@SAVED", bpy.data.filepath)
