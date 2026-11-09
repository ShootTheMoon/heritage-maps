import bpy, os, sys, json, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OVD = os.path.join(ROOT, "06_OVERDARE")
man = json.load(open(os.path.join(OVD, "manifest.json"), encoding="utf-8"))
def clear():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for d in list(c): c.remove(d)
rep = {}; fails = []
for name, rec in man.items():
    if not rec.get("file"): continue   # 재사용 에셋(MST_EULALIA 등)은 파일이 없다
    clear(); path = os.path.join(OVD, rec["file"])
    bpy.ops.import_scene.fbx(filepath=path, use_image_search=False)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    tris = sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes)
    mats = [m for o in meshes for m in o.data.materials if m]
    noimg = [m.name for m in mats if not any(n.type=="TEX_IMAGE" and n.image and n.image.size[0] > 0 for n in m.node_tree.nodes)]
    dims = meshes[0].dimensions if meshes else None
    exp = [rec["bbox_max"][i]-rec["bbox_min"][i] for i in range(3)]
    # FBX -Z/Y 축 변환 후 재임포트 → Blender 축 복원되어야 함
    drift = max(abs(dims[i]-exp[i]) for i in range(3)) if dims else 99
    ok = len(meshes)==1 and tris<=30000 and not noimg and drift < 0.05 and os.path.getsize(path) < 250e6
    if not ok: fails.append((name, len(meshes), tris, noimg, round(drift,3)))
    rep[name] = {"meshes": len(meshes), "tris": tris, "mats": len(mats), "noimg": noimg, "drift": round(drift,3), "ok": ok}
json.dump(rep, open(os.path.join(OVD, "verify_export.json"), "w"), indent=1)
print("FILES", len(rep), "FAIL", fails)
