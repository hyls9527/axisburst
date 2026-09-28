"""验证「SVG 轮廓 → 实体 → 精修 → 线稿」这条路。

这是 headless 下能拿到的最强形状控制：轮廓可以在任意矢量工具里画准
（也可以直接从参考图描下来），再进来加厚度、做平滑、进线稿。

产物：blender/out/probe/bracket.svg / .png
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

OUT = os.path.abspath("blender/out/probe")

# 一张手写的轮廓（俯视）：带圆角、缺口腰身、两处安装耳的支架
OUTLINE = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 120" width="200" height="120">
  <path fill="#000" stroke="none" d="
    M 24,10
    H 176
    A 14,14 0 0 1 190,24
    V 44
    A 14,14 0 0 1 176,58
    H 132
    C 122,58 118,64 118,72
    C 118,80 122,86 132,86
    H 176
    A 14,14 0 0 1 190,100
    V 106
    A 14,14 0 0 1 176,120
    H 24
    A 14,14 0 0 1 10,106
    V 100
    A 14,14 0 0 1 24,86
    H 68
    C 78,86 82,80 82,72
    C 82,64 78,58 68,58
    H 24
    A 14,14 0 0 1 10,44
    V 24
    A 14,14 0 0 1 24,10
    Z" />
</svg>
"""


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    svg_path = os.path.join(OUT, "outline.svg")
    with open(svg_path, "w", encoding="utf-8") as handle:
        handle.write(OUTLINE)

    rk.reset_scene()
    col = kit.new_collection("P_bracket")

    # 1) 轮廓 → 实体（厚度 0.12，缩放 0.02 → 200px 宽变成 4.0 单位）
    obj = kit.from_svg(col, "bracket", svg_path, thickness=0.12, target_width=4.0)
    raw_verts = len(obj.data.vertices)

    # 2) 精修：细分两档 + 平滑，收掉导入折线
    kit.refine(obj, subdivide=2, smooth_iterations=6, smooth_factor=0.35)
    # 3) 立起来（轮廓本来是俯视 XY，转成沿 Z 有厚度）
    obj.rotation_euler = (1.5707963, 0.0, 0.0)
    bpy.context.view_layer.update()

    lo, hi = rk.scene_bounds([obj])
    cam = rk.make_camera()
    rk.fit_camera(cam, rk.bbox_corners(lo, hi))
    gp = rk.add_line_art("bracket", col, radius=max(0.004, (hi - lo).length * 0.003))
    rk.setup_render(os.path.join(OUT, "bracket.png"))
    bpy.context.view_layer.update()

    rk.export_svg([gp], os.path.join(OUT, "bracket.svg"))
    rk.render(os.path.join(OUT, "bracket.png"))

    strokes, points = rk.count_strokes(gp)
    print(f"[control] 导入轮廓 → {raw_verts} 顶点 → 精修后 {len(obj.data.vertices)} 顶点")
    print(f"[control] 线稿笔画 {strokes}  点 {points}")
    print(f"[control] 尺寸 {[round(hi[i] - lo[i], 3) for i in range(3)]}")
    print(f"[control] 写出 {os.path.join(OUT, 'bracket.svg')}")


if __name__ == "__main__":
    main()
