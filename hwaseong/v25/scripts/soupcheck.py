# -*- coding: utf-8 -*-
"""Soup check: faces / connected-shells per mesh. Run headless or in GUI.
Env SOUP_PREFIX = comma list of object-name prefixes to include (default: all).
Lines start with @@ so they can be grepped out of Blender noise."""
import bpy, bmesh, os

def shells(me):
    bm = bmesh.new(); bm.from_mesh(me)
    seen = set(); n = 0
    for v in bm.verts:
        if v.index in seen:
            continue
        n += 1; stack = [v]; seen.add(v.index)
        while stack:
            x = stack.pop()
            for e in x.link_edges:
                o = e.other_vert(x)
                if o.index not in seen:
                    seen.add(o.index); stack.append(o)
    bm.free(); return n

def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)

def run(prefixes=None, verbose=True):
    rows = []
    for o in bpy.data.objects:
        if o.type != 'MESH' or not len(o.data.polygons):
            continue
        if prefixes and not any(o.name.startswith(p) for p in prefixes):
            continue
        f = len(o.data.polygons); s = shells(o.data)
        rows.append((o.name, f, tris(o.data), s, round(f / max(s, 1), 1),
                     [round(d, 1) for d in o.dimensions]))
    if verbose:
        for r in rows:
            print("@@MESH %s faces=%d tris=%d shells=%d f/shell=%s dims=%s" % r)
    return rows

if __name__ == "__main__":
    print("@@FILE", bpy.data.filepath)
    for c in bpy.data.collections:
        print("@@COL", c.name, len(c.objects))
    print("@@IMG", sorted(i.name for i in bpy.data.images if i.name.startswith(("BC_", "JAM_", "NH_"))))
    pre = os.environ.get("SOUP_PREFIX", "")
    rows = run([p for p in pre.split(",") if p] or None)
    print("@@TOTAL meshes=%d faces=%d tris=%d" % (len(rows), sum(r[1] for r in rows), sum(r[2] for r in rows)))
