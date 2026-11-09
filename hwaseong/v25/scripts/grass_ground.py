# -*- coding: utf-8 -*-
"""Grass ground like the Sangok map (user: "바닥은 잔디밭, 산옥 리버전때처럼").
Same asset the Sangok terrain used: Poly Haven aerial_grass_rock 1k from JSN_Sangok2\_TexLib, tiled every 4 m
with the Sangok tint (sgk_dress.py: ("grass", aerial_grass_rock, 4.0, (0.80, 0.86, 0.66))).
One plane object, textures untouched."""
import bpy, bmesh, os
TEX = r"C:\Users\HSP\Desktop\blender\JSN_Sangok2\_TexLib\polyhaven\aerial_grass_rock"
NAME = "지면_잔디"


def _img(fn, noncolor=False):
    img = bpy.data.images.load(os.path.join(TEX, fn), check_existing=True)
    if noncolor:
        img.colorspace_settings.name = 'Non-Color'
    return img


def grass_material(tint=(0.80, 0.86, 0.66)):
    m = bpy.data.materials.get("잔디_aerial_grass_rock")
    if m:
        return m
    m = bpy.data.materials.new("잔디_aerial_grass_rock"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]
    def tex(fn, x, y, noncolor=False):
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = _img(fn, noncolor); n.location = (x, y); return n
    diff = tex("aerial_grass_rock_diff_1k.png", -700, 300)
    ao = tex("aerial_grass_rock_ao_1k.png", -700, 0, True)
    rough = tex("aerial_grass_rock_rough_1k.png", -700, -300, True)
    nor = tex("aerial_grass_rock_nor_gl_1k.png", -700, -600, True)
    mul_ao = nt.nodes.new('ShaderNodeMixRGB'); mul_ao.blend_type = 'MULTIPLY'; mul_ao.inputs['Fac'].default_value = 1.0; mul_ao.location = (-400, 300)
    mul_tint = nt.nodes.new('ShaderNodeMixRGB'); mul_tint.blend_type = 'MULTIPLY'; mul_tint.inputs['Fac'].default_value = 1.0; mul_tint.location = (-200, 300)
    mul_tint.inputs['Color2'].default_value = (tint[0], tint[1], tint[2], 1.0)
    nmap = nt.nodes.new('ShaderNodeNormalMap'); nmap.location = (-400, -600)
    nt.links.new(diff.outputs['Color'], mul_ao.inputs['Color1']); nt.links.new(ao.outputs['Color'], mul_ao.inputs['Color2'])
    nt.links.new(mul_ao.outputs['Color'], mul_tint.inputs['Color1']); nt.links.new(mul_tint.outputs['Color'], bsdf.inputs['Base Color'])
    nt.links.new(rough.outputs['Color'], bsdf.inputs['Roughness'])
    nt.links.new(nor.outputs['Color'], nmap.inputs['Color']); nt.links.new(nmap.outputs['Normal'], bsdf.inputs['Normal'])
    m.diffuse_color = (0.30, 0.42, 0.20, 1.0)
    return m


def main(size=(200.0, 150.0), centre=(0.0, 5.0), tile=4.0, z=-0.02):
    old = bpy.data.objects.get(NAME)
    if old:
        bpy.data.meshes.remove(old.data)
    me = bpy.data.meshes.new(NAME); bm = bmesh.new()
    sx, sy = size
    vs = [bm.verts.new((x, y, 0.0)) for x, y in ((-sx / 2, -sy / 2), (sx / 2, -sy / 2), (sx / 2, sy / 2), (-sx / 2, sy / 2))]
    f = bm.faces.new(vs); uv = bm.loops.layers.uv.new("UVMap")
    for l in f.loops:
        l[uv].uv = ((l.vert.co.x + sx / 2) / tile, (l.vert.co.y + sy / 2) / tile)   # 4 m tiles like Sangok
    bm.to_mesh(me); bm.free()
    me.materials.append(grass_material())
    o = bpy.data.objects.new(NAME, me); o.location = (centre[0], centre[1], z)
    col = bpy.data.collections.get("화성_지면") or bpy.data.collections.new("화성_지면")
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    col.objects.link(o)
    print("@@GRASS", NAME, size, "tile", tile)
    return o
