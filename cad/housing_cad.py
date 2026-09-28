"""AB-100 座体外壳 · build123d 版（与 blender/parts/housing.py 的 bmesh 版对照）

同一套设计参数，换成真 B-rep：回转、真倒角、真通孔。
导出 STEP（可继续加工/装配）+ STL（进 Blender 做线稿）。

运行：
  uv tool run --from build123d python cad/housing_cad.py
"""

from __future__ import annotations

import math
import os

from build123d import (
    Align, Axis, BuildLine, BuildPart, BuildSketch, Box, Cylinder, GeomType,
    Locations, Mode, Plane, Polygon, Pos, Rot, chamfer, export_step, export_stl,
    fillet, make_face, revolve,
)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

# 与 bmesh 版同一套参数（半径, 高度），首尾落在轴上
PROFILE = [
    (0.00, -0.620),
    (1.92, -0.620),
    (1.92, -0.460),
    (1.86, -0.420),
    (1.60, -0.400),
    (1.60, 0.100),
    (1.88, 0.160),
    (1.88, 0.260),
    (1.80, 0.300),
    (1.14, 0.300),
    (1.14, 0.180),
    (0.90, 0.140),
    (0.90, -0.340),
    (0.56, -0.400),
    (0.56, -0.620),
]

RIB_COUNT = 24
RIB_R_IN, RIB_R_OUT = 1.220, 1.780
RIB_Z, RIB_H, RIB_T = 0.300, 0.055, 0.042

BOLT_COUNT = 6
BOLT_RING, BOLT_R = 1.840, 0.058


def build():
    steps = {}

    with BuildPart() as part:
        # ① 回转体
        with BuildSketch(Plane.XZ):
            Polygon(*PROFILE)
        revolve(axis=Axis.Z)
        steps["revolve"] = len(part.part.faces())

        # ② 盘面放射辐条（24 条，一次算出来再 fused）
        rib = Box(RIB_R_OUT - RIB_R_IN, RIB_T, RIB_H,
                  align=(Align.MIN, Align.CENTER, Align.MIN))
        ribs = []
        for i in range(RIB_COUNT):
            a = i / RIB_COUNT * math.tau
            ribs.append(
                Pos(RIB_R_IN * math.cos(a), RIB_R_IN * math.sin(a), RIB_Z)
                * Rot(0, 0, math.degrees(a))
                * rib
            )
        for piece in ribs:
            part.part += piece
        steps["ribs"] = len(part.part.faces())

        # ③ 盘面螺栓孔（真通孔）
        with Locations(*[
            (BOLT_RING * math.cos(a), BOLT_RING * math.sin(a), RIB_Z)
            for a in (math.radians(15) + i / BOLT_COUNT * math.tau for i in range(BOLT_COUNT))
        ]):
            Cylinder(BOLT_R, 0.22, mode=Mode.SUBTRACT)
        steps["holes"] = len(part.part.faces())

        # ④ 真倒角：内外圆边
        circles = part.edges().filter_by(GeomType.CIRCLE)
        try:
            outer = circles.group_by(Axis.Z)[-1]
            chamfer(outer, length=0.02)
            steps["chamfer"] = "ok"
        except Exception as exc:  # noqa: BLE001
            steps["chamfer"] = f"跳过 {type(exc).__name__}"

    return part.part, steps


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    solid, steps = build()

    stl = os.path.join(OUT, "housing_cad.stl")
    step = os.path.join(OUT, "housing_cad.step")
    export_stl(solid, stl)
    export_step(solid, step)

    bb = solid.bounding_box()
    size = bb.size
    print(f"[cad] 阶段：{steps}")
    print(f"[cad] 体积 {solid.volume:,.1f}  面 {len(solid.faces())}  边 {len(solid.edges())}")
    print(f"[cad] 尺寸 {size.X:.3f} × {size.Y:.3f} × {size.Z:.3f}")
    print(f"[cad] 合法实体 {solid.is_valid}")
    print(f"[cad] STL {os.path.getsize(stl):,} 字节 → {stl}")
    print(f"[cad] STEP {os.path.getsize(step):,} 字节 → {step}")


if __name__ == "__main__":
    main()
