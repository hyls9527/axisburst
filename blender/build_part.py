"""AxisBurst · 单零件验证器

一次只建一个零件，单独出线稿 SVG + 预览图，确认形状对了再进总装。

用法：
  blender.exe --background --factory-startup --python blender/build_part.py -- --part <零件id>
  blender.exe --background --factory-startup --python blender/build_part.py -- --all

产物：
  blender/out/parts/<id>.png   单件预览
  blender/out/parts/<id>.svg   单件线稿（分层结构 = 总装同款）
"""

from __future__ import annotations

import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import partkit as kit          # noqa: E402
import manifest                # noqa: E402
import render_kit as rk        # noqa: E402
import parts                   # noqa: E402


def parse_args() -> dict:
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    args = {"part": None, "all": False, "out": "blender/out"}
    i = 0
    while i < len(argv):
        if argv[i] == "--part" and i + 1 < len(argv):
            args["part"] = argv[i + 1]
            i += 2
        elif argv[i] == "--all":
            args["all"] = True
            i += 1
        elif argv[i] == "--out" and i + 1 < len(argv):
            args["out"] = argv[i + 1]
            i += 2
        else:
            i += 1
    return args


def build_one(module, out_dir: str) -> dict:
    rk.reset_scene()

    col = kit.new_collection("P_" + module.ID)
    module.build(col)

    objects = [o for o in col.objects if o.type == "MESH"]
    if not objects:
        raise RuntimeError(f"{module.ID} 没建出任何几何")
    lo, hi = rk.scene_bounds(objects)

    cam = rk.make_camera()
    rk.fit_camera(cam, rk.bbox_corners(lo, hi))

    gp = rk.add_line_art(module.ID, col, radius=max(0.0022, (hi - lo).length * 0.0016))
    rk.setup_render(os.path.join(out_dir, "parts", f"{module.ID}.png"))

    bpy.context.view_layer.update()

    svg_path = os.path.join(out_dir, "parts", f"{module.ID}.svg")
    rk.export_svg([gp], svg_path)
    rk.render(os.path.join(out_dir, "parts", f"{module.ID}.png"))

    strokes, points = rk.count_strokes(gp)
    size = [round(hi[i] - lo[i], 3) for i in range(3)]

    record = manifest.part_record(
        module,
        size=size,
        bbox=[[round(lo[i], 3) for i in range(3)], [round(hi[i], 3) for i in range(3)]],
        strokes=strokes,
        points=points,
    )
    record["objects"] = len(objects)
    manifest.write_record(os.path.join(out_dir, "parts", f"{module.ID}.json"), record)
    return record


def main() -> None:
    args = parse_args()
    out_dir = os.path.abspath(args["out"])
    os.makedirs(os.path.join(out_dir, "parts"), exist_ok=True)

    if args["all"]:
        targets = parts.load_parts()
    elif args["part"]:
        targets = [parts.by_id(args["part"])]
    else:
        print("[usage] --part <id> | --all")
        print("[parts]", ", ".join(m.ID for m in parts.load_parts()))
        return

    for module in targets:
        info = build_one(module, out_dir)
        m = info["measured"]
        print(f"[part] {info['pn']:<8} {info['label']:<10} ×{info['qty']:<2} "
              f"Z={info['z']:>6}  尺寸 {m['size']}  笔画 {m['strokes']:>4}")

    payload = manifest.collect(
        os.path.join(out_dir, "parts"), "*.json",
        os.path.join(out_dir, "parts_manifest.json"),
        {"kind": "part-manifest", "title": "AxisBurst 零件清单"},
    )
    print(f"[manifest] 零件 {payload['count']} 项 → {os.path.join(out_dir, 'parts_manifest.json')}")
    print(manifest.table(payload["items"]))


if __name__ == "__main__":
    main()
