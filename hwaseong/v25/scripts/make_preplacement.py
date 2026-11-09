# -*- coding: utf-8 -*-
r"""Pre-placement for v25: manifest.json -> placement_v25_pre.json (positions/sizes in OVERDARE cm with
DELTA applied, meshId EMPTY). After the FBX files are published in Studio, run
gyeongbokgung\make_placement.py --manifest <this manifest> to fill ovdrassetid:// ids (same DELTA).
Also emits collision_parts.json for the ground Part(s) and checks the Changdeokgung X range.
Usage: python make_preplacement.py <export dir>"""
import io, json, os, sys, collections

DELTA = (-58000.0, -5000.0, 0.0)          # hwaseong-handover-spec: -70000 overlaps Changdeokgung by 22 m
CDG_X = (27000.0, 33000.0)                # Changdeokgung occupancy on the level (cm)


def main(d):
    m = json.load(io.open(os.path.join(d, "manifest.json"), encoding="utf-8"))
    items, xs, zs = [], [], []
    for x in m["meshes"]:
        cf, sz = x["cframe_cm"], x["size_cm"]
        w = (cf["X"] + DELTA[0], cf["Y"] + DELTA[1], cf["Z"] + DELTA[2])
        xs += [w[0] - sz["X"] / 2, w[0] + sz["X"] / 2]; zs += [w[2] - sz["Z"] / 2, w[2] + sz["Z"] / 2]
        items.append({"name": x["slug"], "group": x["group"], "file": x["file"], "tris": x["tris"],
                      "expected_asset_name": x["expected_asset_name"], "material_key": x["material_key"],
                      "meshId": "", "cframe": {"X": round(w[0], 3), "Y": round(w[1], 3), "Z": round(w[2], 3)},
                      "orientation": {"X": 0, "Y": 0, "Z": 0},
                      "size_cm": {"X": sz["X"], "Y": sz["Y"], "Z": sz["Z"]}})
    parts = []
    for p in m.get("parts", []):
        cf, sz = p["cframe_cm"], p["size_cm"]
        parts.append({"name": p.get("slug") or p.get("name"), "group": p["group"], "className": "Part",
                      "cframe": {"X": round(cf["X"] + DELTA[0], 3), "Y": round(cf["Y"] + DELTA[1], 3),
                                 "Z": round(cf["Z"] + DELTA[2], 3)},
                      "size_cm": {"X": sz["X"], "Y": sz["Y"], "Z": sz["Z"]},
                      "material": "Ground", "color3": [107, 92, 71], "anchored": True, "canCollide": True})
    out = {"schema": "hwaseong-v25-preplacement/1", "delta_cm": DELTA, "parent": "Hwaseong Arena",
           "source_manifest": os.path.abspath(os.path.join(d, "manifest.json")),
           "totals": {"meshparts": len(items), "parts": len(parts), "files": len(m["files"]),
                      "tris": sum(i["tris"] for i in items)},
           "bbox_x_cm": [round(min(xs)), round(max(xs))], "bbox_z_cm": [round(min(zs)), round(max(zs))],
           "items": items, "parts": parts}
    ov = not (max(xs) < CDG_X[0] or min(xs) > CDG_X[1])
    out["changdeokgung_overlap"] = ov
    json.dump(out, io.open(os.path.join(d, "placement_v25_pre.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"delta_cm": DELTA, "parts": parts}, io.open(os.path.join(d, "collision_parts.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    byg = collections.Counter(i["group"] for i in items)
    print("MESHPARTS %d  PARTS %d  FILES %d  TRIS %d" % (len(items), len(parts), len(m["files"]), out["totals"]["tris"]))
    print("BY_GROUP", dict(byg))
    print("X range cm %d..%d  Z range cm %d..%d  Changdeokgung overlap: %s" % (min(xs), max(xs), min(zs), max(zs), ov))
    return 1 if ov else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
