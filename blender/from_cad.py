"""把 CAD 导出的网格接进现有线稿管线。

用法：blender --background --factory-startup --python blender/from_cad.py -- \
        --mesh cad/out/housing_cad.stl --name housing --out blender/out/cad
"""

from __future__ import annotations

import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import partkit as kit          # noqa: E402
import render_kit as rk        # noqa: E402


def parse_args() -> dict:
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    args = {"mesh": None, "name": "part", "out": "blender/out/cad",
            "decimate": "0.14", "crease": "160", "radius": None, "smooth": "8"}
    i = 0
    while i < len(argv):
        if argv[i] in ("--mesh", "--name", "--out", "--decimate", "--crease", "--radius", "--smooth") and i + 1 < len(argv):
            args[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            i += 1
    return args


def main() -> None:
    args = parse_args()
    mesh_path = os.path.abspath(args["mesh"])
    out_dir = os.path.abspath(args["out"])
    os.makedirs(out_dir, exist_ok=True)

    rk.reset_scene()
    col = kit.new_collection("P_" + args["name"])

    # Blender 4.1+ 把 STL 挪到了 wm.stl_import，老写法 import_mesh.stl 已经没了
    lower = mesh_path.lower()
    if lower.endswith(".stl"):
        candidates = ("stl_import", "import_mesh_stl")
    elif lower.endswith(".obj"):
        candidates = ("obj_import", "import_scene_obj")
    else:
        raise SystemExit(f"暂不支持的格式：{mesh_path}")

    for name in candidates:
        op = getattr(bpy.ops.wm, name, None)
        if op is not None:
            op(filepath=mesh_path)
            break
    else:
        raise SystemExit(f"找不到可用的导入算子：{candidates}")

    imported = [o for o in bpy.context.selected_objects if o.type == "MESH"]
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = args["name"]
    kit.move_to(obj, col)

    raw_faces = len(obj.data.polygons)
    # 有机网格先减面：否则 Line Art 会把每个三角边都画出来（密成线框）
    decimate = float(args["decimate"])
    if 0.0 < decimate < 1.0:
        mod = obj.modifiers.new("decimate", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = decimate
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        print(f"[from_cad] 减面 {raw_faces} → {len(obj.data.polygons)} (ratio {decimate})")

    # 减面会把轮廓削成多边形；补几步平滑把转折拉回顺滑，
    # 笔画数照样低（线少），但轮廓不像低多边形了。
    smooth_iters = int(args["smooth"])
    if smooth_iters > 0:
        mod = obj.modifiers.new("smooth", "SMOOTH")
        mod.factor = 0.9
        mod.iterations = smooth_iters
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        print(f"[from_cad] 平滑 {smooth_iters} 次")

    lo, hi = rk.scene_bounds([obj])
    cam = rk.make_camera()
    rk.fit_camera(cam, rk.bbox_corners(lo, hi))
    # 折角阈值调高：只保留轮廓和真正的转折线，不画平缓面
    radius = float(args["radius"]) if args["radius"] else max(0.0022, (hi - lo).length * 0.0014)
    gp = rk.add_line_art(args["name"], col, radius=radius, crease_deg=float(args["crease"]))
    rk.setup_render(os.path.join(out_dir, f"{args['name']}.png"))
    bpy.context.view_layer.update()

    svg_path = os.path.join(out_dir, f"{args['name']}.svg")
    rk.export_svg([gp], svg_path)
    rk.render(os.path.join(out_dir, f"{args['name']}.png"))

    strokes, points = rk.count_strokes(gp)
    print(f"[from_cad] 顶点 {len(obj.data.vertices)}  面 {len(obj.data.polygons)}")
    print(f"[from_cad] 尺寸 {[round(hi[i] - lo[i], 3) for i in range(3)]}")
    print(f"[from_cad] 线稿 笔画 {strokes}  点 {points}")
    print(f"[from_cad] {svg_path}")


if __name__ == "__main__":
    main()
