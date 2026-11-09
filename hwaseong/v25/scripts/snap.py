# -*- coding: utf-8 -*-
"""Viewport snapshots to PNG without touching the user's camera.
snap(eye, tgt, path, lens=35, w=800, h=500, shading='MATERIAL')
Uses the first VIEW_3D area; sets its view then calls render.opengl (viewport render)."""
import bpy, os
from mathutils import Vector

OUT = r"C:\Users\HSP\Desktop\blender\hwaseong_rebuild\v25\snaps"


def _area():
    for a in bpy.context.screen.areas:
        if a.type == 'VIEW_3D':
            return a


def look(eye, tgt, lens=35):
    a = _area(); sp = a.spaces.active; r3d = sp.region_3d
    eye = Vector(eye); tgt = Vector(tgt); d = tgt - eye
    r3d.view_perspective = 'PERSP'
    r3d.view_location = tgt; r3d.view_distance = d.length
    r3d.view_rotation = (-d).to_track_quat('Z', 'Y')
    sp.lens = lens; sp.clip_end = 3000
    return a


def snap(eye, tgt, name, lens=35, w=800, h=500, shading='MATERIAL'):
    os.makedirs(OUT, exist_ok=True)
    a = look(eye, tgt, lens)
    sp = a.spaces.active; sp.shading.type = shading
    sp.overlay.show_overlays = False
    sc = bpy.context.scene; rd = sc.render
    keep = (rd.resolution_x, rd.resolution_y, rd.resolution_percentage, rd.filepath, rd.image_settings.file_format)
    rd.resolution_x, rd.resolution_y, rd.resolution_percentage = w, h, 100
    rd.image_settings.file_format = 'PNG'
    path = os.path.join(OUT, name + ".png"); rd.filepath = path
    reg = [r for r in a.regions if r.type == 'WINDOW'][0]
    with bpy.context.temp_override(area=a, region=reg, space_data=sp):
        bpy.ops.render.opengl(write_still=True, view_context=True)
    rd.resolution_x, rd.resolution_y, rd.resolution_percentage, rd.filepath, rd.image_settings.file_format = keep
    sp.overlay.show_overlays = True
    return path
