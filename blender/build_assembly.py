"""AxisBurst · 总装层 —— 部件组成整体，导出总装线稿与清单。

这是三层结构的最后一层：零件 → 部件 → 总装。
导出的一份 SVG 里每个零件仍是一个独立图层，供前端做时序分解。

产物：
  blender/out/axisburst_lineart.svg   总装分层线稿（layer.<零件id>）
  blender/out/axisburst_parts.json    规范化工具要的几何事实（次序/包围盒/轴向位置）
  blender/out/assembly_manifest.json  总装清单（编号/数量/参数，按部件与装配顺序排好）
  blender/out/assembly.png            预览
"""

from __future__ import annotations

import json
import math
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
from mathutils import Vector     # noqa: E402


def parse_args() -> dict:
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    args = {"out": "blender/out"}
    i = 0
    while i < len(argv):
        if argv[i] == "--out" and i + 1 < len(argv):
            args["out"] = argv[i + 1]
            i += 2
        else:
            i += 1
    return args


def main() -> None:
    out_dir = os.path.abspath(parse_args()["out"])
    os.makedirs(out_dir, exist_ok=True)

    rk.reset_scene()

    component_modules = components.load_components()
    builts = builder.build_assembly(component_modules)
    meshes = builder.all_mesh_objects(builts)
    if not meshes:
        raise SystemExit("总装没有任何几何：检查 parts/ 与 components/ 的零件是否齐全")

    lo, hi = rk.scene_bounds(meshes)
    cam = rk.make_camera()
    rk.fit_camera(cam, rk.bbox_corners(lo, hi))

    # 每个零件一个 Line Art 对象 → 导出后 layer.<零件id>
    span = (hi - lo).length
    gp_objects = []
    geometry = {"axis_world": [0.0, 0.0, 1.0], "parts": {}}
    rich_records = []
    order = 0

    for built in builts:
        part_records = []
        for module, col in built.parts:
            objects = [o for o in col.objects if o.type == "MESH"]
            plo, phi = rk.scene_bounds(objects)
            centre = (plo + phi) / 2.0

            geometry["parts"][module.ID] = {
                "order": order,
                "label": module.LABEL,
                "bbox_world": {
                    "min": [round(v, 5) for v in plo],
                    "max": [round(v, 5) for v in phi],
                },
                "center_world": [round(v, 5) for v in centre],
                "axis_t": round(centre.z, 5),
            }
            rich_records.append(manifest.part_record(
                module,
                size=[round(phi[i] - plo[i], 3) for i in range(3)],
                bbox=[[round(plo[i], 3) for i in range(3)], [round(phi[i], 3) for i in range(3)]],
            ))
            order += 1

            gp = rk.add_line_art(module.ID, col, radius=max(0.0022, span * 0.0014))
            gp_objects.append(gp)
            part_records.append(module.ID)

        built.records = part_records

    rk.setup_render(os.path.join(out_dir, "assembly.png"))
    bpy.context.view_layer.update()

    svg_path = os.path.join(out_dir, "axisburst_lineart.svg")
    # 先写几何清单，再出线稿 —— 保证同一轮里线稿是最新的产物，
    # 下游的新鲜度检查（tools/build.mjs 的 assets 段）才有意义。
    with open(os.path.join(out_dir, "axisburst_parts.json"), "w", encoding="utf-8") as handle:
        json.dump(geometry, handle, ensure_ascii=False, indent=2)

    rk.export_svg(gp_objects, svg_path)
    rk.render(os.path.join(out_dir, "assembly.png"))

    # 总装清单：先部件、后零件，都按各自 ORDER
    assembled = []
    for built in builts:
        assembled.append({
            "kind": "component",
            "pn": built.module.PN,
            "label": built.module.LABEL,
            "labelEn": built.module.LABEL_EN,
            "order": built.module.ORDER,
            "z": built.module.Z,
            "summary": built.module.SUMMARY,
            "parts": [m.ID for m, _ in built.parts],
        })
    rich_by_id = {r["id"]: r for r in rich_records}
    full = {
        "kind": "assembly-manifest",
        "title": "AxisBurst 总装清单",
        "assembly": {
            "id": "axisburst",
            "label": "轴爆总装",
            "components": assembled,
            "size": [round(hi[i] - lo[i], 3) for i in range(3)],
            "partCount": len(rich_records),
            "componentCount": len(builts),
        },
        "parts": sorted(rich_by_id.values(), key=lambda r: (r["component"], r["order"])),
    }
    with open(os.path.join(out_dir, "assembly_manifest.json"), "w", encoding="utf-8") as handle:
        json.dump(full, handle, ensure_ascii=False, indent=2)

    total_strokes = sum(rk.count_strokes(gp)[0] for gp in gp_objects)
    print(f"[assembly] 部件 {len(builts)}  零件 {len(rich_records)}  笔画 {total_strokes}")
    print(f"[assembly] 尺寸 {[round(hi[i] - lo[i], 3) for i in range(3)]}")
    for entry in assembled:
        print(f"[assembly]   {entry['pn']:<8} {entry['label']:<8} 零件 {len(entry['parts'])}")
    print(f"[assembly] 写出 {svg_path}")


if __name__ == "__main__":
    main()
