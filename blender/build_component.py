"""AxisBurst · 部件验证器 —— 零件先组成部件，部件先自己验证。

用法：
  blender --background --factory-startup --python blender/build_component.py -- --component <部件id>
  blender --background --factory-startup --python blender/build_component.py -- --all

产物：
  blender/out/components/<id>.svg / .png    部件的线稿与预览
  blender/out/components/<id>.json          部件清单（编号 / 尺寸 / 参数 / 零件构成）
"""

from __future__ import annotations

import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import builder                   # noqa: E402
import components                # noqa: E402
import manifest                  # noqa: E402
import render_kit as rk          # noqa: E402


def parse_args() -> dict:
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    args = {"component": None, "all": False, "out": "blender/out"}
    i = 0
    while i < len(argv):
        if argv[i] == "--component" and i + 1 < len(argv):
            args["component"] = argv[i + 1]
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


def build_one(component_module, out_dir: str) -> dict:
    rk.reset_scene()

    built = builder.build_component(component_module)
    meshes = builder.mesh_objects(built)
    if not meshes:
        raise RuntimeError(f"{component_module.ID} 没有可用的零件")

    lo, hi = rk.scene_bounds(meshes)
    cam = rk.make_camera()
    rk.fit_camera(cam, rk.bbox_corners(lo, hi))

    # 每个零件一个 Line Art 对象 → 导出后每个零件一个 SVG 图层
    span = (hi - lo).length
    gp_objects = []
    strokes_total = 0
    for module, col in built.parts:
        gp = rk.add_line_art(module.ID, col, radius=max(0.0022, span * 0.0014))
        strokes, _ = rk.count_strokes(gp)
        strokes_total += strokes
        gp_objects.append(gp)

    rk.setup_render(os.path.join(out_dir, "components", f"{component_module.ID}.png"))
    bpy.context.view_layer.update()

    svg_path = os.path.join(out_dir, "components", f"{component_module.ID}.svg")
    rk.export_svg(gp_objects, svg_path)
    rk.render(os.path.join(out_dir, "components", f"{component_module.ID}.png"))

    # 部件内零件逐个记账
    part_records = []
    for module, col in built.parts:
        objs = [o for o in col.objects if o.type == "MESH"]
        plo, phi = rk.scene_bounds(objs)
        part_records.append(manifest.part_record(
            module,
            size=[round(phi[i] - plo[i], 3) for i in range(3)],
            bbox=[[round(plo[i], 3) for i in range(3)], [round(phi[i], 3) for i in range(3)]],
        ))

    record = manifest.component_record(component_module, part_records)
    record["measured"] = {
        "bbox": [[round(lo[i], 3) for i in range(3)], [round(hi[i], 3) for i in range(3)]],
        "size": [round(hi[i] - lo[i], 3) for i in range(3)],
        "strokes": strokes_total,
        "partCount": len(built.parts),
    }
    record["partDetails"] = part_records
    manifest.write_record(os.path.join(out_dir, "components", f"{component_module.ID}.json"), record)

    return record


def main() -> None:
    args = parse_args()
    out_dir = os.path.abspath(args["out"])
    os.makedirs(os.path.join(out_dir, "components"), exist_ok=True)

    if args["all"]:
        targets = components.load_components()
    elif args["component"]:
        targets = [components.by_id(args["component"])]
    else:
        print("[usage] --component <id> | --all")
        print("[components]", ", ".join(m.ID for m in components.load_components()))
        return

    for module in targets:
        record = build_one(module, out_dir)
        m = record["measured"]
        print(f"[component] {record['pn']:<8} {record['label']:<8} 零件 {m['partCount']}  "
              f"尺寸 {m['size']}  笔画 {m['strokes']}")
        print(manifest.table(record["partDetails"]))

    manifest.collect(
        os.path.join(out_dir, "components"), "*.json",
        os.path.join(out_dir, "components_manifest.json"),
        {"kind": "component-manifest", "title": "AxisBurst 部件清单"},
    )


if __name__ == "__main__":
    main()
