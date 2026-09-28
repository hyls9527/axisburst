"""四季山河 · 总装 —— 12 件按装配关系摆位，导出分层 SVG（零件 = 图层）。
工作尺度 1 单位 = 100 mm。
"""
from __future__ import annotations

import json
import os
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import partkit as kit          # noqa: E402
import render_kit as rk        # noqa: E402

# 编号 / 名称 / OBJ 名 / (x, y, z) mm→单位 / 线稿参数
LAYOUT = [
    ("SS-01", "底座",        "base_ss01",      (0.00, 0.00, 0.00),  55),
    ("SS-08", "山体岩石",     "SS08_shan",      (0.00, 0.00, 0.72),  160),
    ("SS-02", "荷塘",        "SS02_hetang",    (0.35, -1.65, 0.72), 160),
    ("SS-04", "流水",        "SS04_liushui",   (-0.35, -1.15, 1.62), 160),
    ("SS-03", "瀑布",        "SS03_pubu",      (0.62, -0.88, 1.95), 160),
    ("SS-06", "竹林",        "SS06_zhulin",    (-1.86, -1.02, 1.02), 160),
    ("SS-05", "亭台",        "pavilion_ss05",  (1.46, -0.62, 1.50), 55),
    ("SS-07", "春桃树",       "SS07_taoshu",    (-1.52, -0.90, 1.38), 160),
    ("SS-10", "寺庙建筑",     "temple_ss10",    (0.52, 0.30, 2.18),  55),
    ("SS-11", "寒松",        "SS11_hansong",   (1.58, 0.48, 2.28),  160),
    ("SS-09", "枫树",        "SS09_fengshu",   (-1.18, 0.22, 2.36), 160),
    ("SS-12", "雪山主峰",     "SS12_xueshan",   (-0.86, 0.34, 3.16), 160),
]

LIVE = os.path.join(HERE, "out", "live")
CAD = os.path.abspath(os.path.join(HERE, "..", "cad", "out"))


def obj_path(name):
    for base in (LIVE, CAD):
        p = os.path.join(base, name + ".obj")
        if os.path.exists(p):
            return p
    for base in (LIVE, CAD):
        p = os.path.join(base, name + ".stl")
        if os.path.exists(p):
            return p
    return None


def parse_out():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = "blender/out/sishan"
    for i, a in enumerate(argv):
        if a == "--out" and i + 1 < len(argv):
            out = argv[i + 1]
    return os.path.abspath(out)


def main():
    out_dir = parse_out()
    os.makedirs(out_dir, exist_ok=True)
    rk.reset_scene()

    def import_part(pn, objname, loc):
        path = obj_path(objname)
        if not path:
            return None
        before = set(bpy.data.objects)
        if path.lower().endswith(".obj"):
            bpy.ops.wm.obj_import(filepath=path)
        else:
            bpy.ops.wm.stl_import(filepath=path)
        new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
        if not new:
            return None
        bpy.ops.object.select_all(action="DESELECT")
        for o in new:
            o.select_set(True)
        bpy.context.view_layer.objects.active = new[0]
        if len(new) > 1:
            bpy.ops.object.join()
        obj = bpy.context.object
        obj.name = pn
        obj.location = loc
        col = kit.new_collection("P_" + pn)
        kit.move_to(obj, col)
        # 把变换烘进网格，后面射线求交才在同一个坐标系里
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        return obj

    gp_objects = []
    placed = {}
    missing = []
    by_pn = {pn: (objname, loc, crease) for pn, _l, objname, loc, crease in LAYOUT}

    # ① 先放底座与山体 —— 其余件要坐在山体表面，所以这两件必须先到位
    for pn in ("SS-01", "SS-08"):
        objname, loc, _c = by_pn[pn]
        obj = import_part(pn, objname, loc)
        if obj is None:
            missing.append(objname)
        else:
            placed[pn] = obj

    # ② 用山体的 BVH 求每件所在 (x,y) 的山面高度
    mountain = placed.get("SS-08")
    bvh = None
    if mountain is not None:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        bvh = BVHTree.FromObject(mountain, depsgraph)
        mlo, mhi = rk.scene_bounds([mountain])
        print(f"[sishan] 山体采样范围 z {mlo.z:.2f}~{mhi.z:.2f}")

    def surface_z(x, y, fallback):
        if bvh is None:
            return fallback
        origin = Vector((x, y, 20.0))
        hit = bvh.ray_cast(origin, Vector((0.0, 0.0, -1.0)), 40.0)
        if hit and hit[0] is not None:
            return hit[0].z
        return None

    # ③ 其余件按山面高度落位；离山的件（荷塘/流水）保留手工 z
    for pn, label, objname, loc, crease in LAYOUT:
        if pn in placed:
            continue
        x, y, z_manual = loc
        z = surface_z(x, y, z_manual)
        embed = 0.05
        if z is None:
            z = z_manual
            note = "手工"
        else:
            z = z + embed
            note = f"贴山面 {z - embed:.2f}"
        obj = import_part(pn, objname, (x, y, z))
        if obj is None:
            missing.append(objname)
            continue
        placed[pn] = obj
        print(f"[sishan] {pn} {label} 落位 z={z:.2f} ({note})")

    bpy.context.view_layer.update()
    all_meshes = list(placed.values())
    if not all_meshes:
        raise SystemExit("总装没有任何几何")

    lo, hi = rk.scene_bounds(all_meshes)
    cam = rk.make_camera()
    rk.fit_camera(cam, rk.bbox_corners(lo, hi))

    span = (hi - lo).length
    for pn, label, objname, loc, crease in LAYOUT:
        if pn not in placed:
            continue
        col = bpy.data.collections["P_" + pn]
        gp = rk.add_line_art(pn, col, radius=max(0.0022, span * 0.0012), crease_deg=float(crease))
        gp_objects.append(gp)

    rk.setup_render(os.path.join(out_dir, "sishan.png"))
    bpy.context.view_layer.update()
    svg_path = os.path.join(out_dir, "sishan_lineart.svg")

    geo = {"axis_world": [0.0, 0.0, 1.0], "parts": {}}
    for order, (pn, label, objname, loc, crease) in enumerate(LAYOUT):
        if pn not in placed:
            continue
        obj = placed[pn]
        plo, phi = rk.scene_bounds([obj])
        centre = (plo + phi) / 2.0
        geo["parts"][pn] = {
            "order": order,
            "label": label,
            "bbox_world": {"min": [round(v, 5) for v in plo], "max": [round(v, 5) for v in phi]},
            "center_world": [round(v, 5) for v in centre],
            "axis_t": round(centre.z, 5),
        }
    with open(os.path.join(out_dir, "axisburst_parts.json"), "w", encoding="utf-8") as fh:
        json.dump(geo, fh, ensure_ascii=False, indent=2)

    rk.export_svg(gp_objects, svg_path)
    rk.render(os.path.join(out_dir, "sishan.png"))

    total = sum(rk.count_strokes(gp)[0] for gp in gp_objects)
    print(f"[sishan] 零件 {len(placed)}/{len(LAYOUT)}  图层 {len(gp_objects)}  笔画 {total}")
    print(f"[sishan] 总尺寸 mm {[round((hi[i]-lo[i])*100) for i in range(3)]}")
    if missing:
        print("[sishan] 缺件：", ", ".join(missing))
    print(f"[sishan] 写出 {svg_path}")


if __name__ == "__main__":
    main()
