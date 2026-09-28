"""SS-01 底座 —— 黑檀木 + 金属。CAD 路线（真倒角、真圆角）。
工作尺度 1 单位 = 100 mm：摆件 560 × 320，底座高 70。
"""
import math
import os

from build123d import (
    Align, Axis, BuildLine, BuildPart, BuildSketch, Box, Cylinder, GeomType,
    Locations, Mode, Plane, RectangleRounded, chamfer, export_step, export_stl,
    extrude, fillet, make_face, mirror, revolve,
)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

W, D, H = 5.60, 3.20, 0.70
R_CORNER = 0.52
TOP_RECESS = 0.22          # 顶面承托凹台内缩
TOP_DEPTH = 0.10
FOOT_INSET = 0.34          # 底部圈足内缩
FOOT_HEIGHT = 0.14
RIM_BAND = 0.055           # 金属包边宽


def build():
    steps = {}
    with BuildPart() as part:
        with BuildSketch(Plane.XY):
            RectangleRounded(W, D, R_CORNER)
        extrude(amount=H)
        steps["body"] = len(part.part.faces())

        # 顶面承托凹台
        with BuildSketch(Plane.XY.offset(H)):
            RectangleRounded(W - 2 * TOP_RECESS, D - 2 * TOP_RECESS, R_CORNER - TOP_RECESS)
        extrude(amount=-TOP_DEPTH, mode=Mode.SUBTRACT)

        # 底部圈足：掏空中间，留一圈落地边
        with BuildSketch(Plane.XY):
            RectangleRounded(W - 2 * FOOT_INSET, D - 2 * FOOT_INSET, max(0.05, R_CORNER - FOOT_INSET))
        extrude(amount=FOOT_HEIGHT, mode=Mode.SUBTRACT)
        steps["recess"] = len(part.part.faces())

        # 金属包边：顶缘一圈细凸带
        with BuildSketch(Plane.XY.offset(H)):
            RectangleRounded(W - 2 * RIM_BAND, D - 2 * RIM_BAND, max(0.05, R_CORNER - RIM_BAND))
        extrude(amount=0.035, mode=Mode.SUBTRACT)
        with BuildSketch(Plane.XY.offset(H + 0.035)):
            RectangleRounded(W - 2 * RIM_BAND, D - 2 * RIM_BAND, max(0.05, R_CORNER - RIM_BAND))
        extrude(amount=-0.035, mode=Mode.SUBTRACT)
        steps["rim"] = len(part.part.faces())

        # 四角雕花足：角上的小圆台
        cx, cy = W / 2 - 0.42, D / 2 - 0.42
        for sx in (-1, 1):
            for sy in (-1, 1):
                with Locations((sx * cx, sy * cy, 0.0)):
                    Cylinder(0.20, FOOT_HEIGHT, align=(Align.CENTER, Align.CENTER, Align.MIN))
                with Locations((sx * cx, sy * cy, -0.02)):
                    Cylinder(0.11, 0.10, align=(Align.CENTER, Align.CENTER, Align.MIN))
        steps["feet"] = len(part.part.faces())

        # 真倒角
        try:
            vertical = part.edges().filter_by(Axis.Z)
            if vertical:
                chamfer(vertical, length=0.018)
            steps["chamfer"] = "ok"
        except Exception as exc:
            steps["chamfer"] = f"跳过 {type(exc).__name__}"

    return part.part, steps


def main():
    os.makedirs(OUT, exist_ok=True)
    solid, steps = build()
    stl = os.path.join(OUT, "base_ss01.stl")
    step = os.path.join(OUT, "base_ss01.step")
    export_stl(solid, stl)
    export_step(solid, step)
    bb = solid.bounding_box().size
    print(f"[cad] 阶段 {steps}")
    print(f"[cad] 面 {len(solid.faces())} 边 {len(solid.edges())} 体积 {solid.volume:,.3f} 合法 {solid.is_valid}")
    print(f"[cad] 尺寸 {bb.X:.3f} x {bb.Y:.3f} x {bb.Z:.3f}  (= {bb.X*100:.0f} x {bb.Y*100:.0f} x {bb.Z*100:.0f} mm)")
    print(f"[cad] STL {os.path.getsize(stl):,}  STEP {os.path.getsize(step):,}")


if __name__ == "__main__":
    main()
