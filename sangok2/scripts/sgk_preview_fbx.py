import bpy, os, sys, math
from mathutils import Vector
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OVD = os.path.join(ROOT, "06_OVERDARE"); OUTD = os.path.join(ROOT, "04_Previews")
files = sys.argv[sys.argv.index("--")+1:]
for f in files:
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=os.path.join(OVD, f), use_image_search=False)
    ob = [o for o in bpy.data.objects if o.type=="MESH"][0]
    for m in ob.data.materials:
        m.blend_method = "HASHED"
    d = max(ob.dimensions); c = Vector(ob.location) + Vector((0,0,ob.dimensions.z/2))
    cam = bpy.data.objects.new("C", bpy.data.cameras.new("C")); bpy.context.scene.collection.objects.link(cam)
    cam.location = c + Vector((d*1.3, -d*1.6, d*0.5)); dirv = c - cam.location; cam.rotation_euler = dirv.to_track_quat("-Z","Y").to_euler()
    bpy.context.scene.camera = cam
    sun = bpy.data.objects.new("S", bpy.data.lights.new("S","SUN")); bpy.context.scene.collection.objects.link(sun); sun.rotation_euler=(math.radians(50),0,math.radians(-60)); sun.data.energy=4
    w = bpy.context.scene.world or bpy.data.worlds.new("W"); bpy.context.scene.world = w; w.use_nodes=True; w.node_tree.nodes["Background"].inputs[0].default_value=(0.5,0.6,0.7,1)
    sc = bpy.context.scene; sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x = sc.render.resolution_y = 700; sc.eevee.taa_render_samples = 16
    sc.render.filepath = os.path.join(OUTD, "fbx_" + os.path.splitext(os.path.basename(f))[0] + ".png"); bpy.ops.render.render(write_still=True); print("rendered", sc.render.filepath)
