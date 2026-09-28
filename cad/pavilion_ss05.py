"""SS-05 亭台 —— 木构。台基 + 四柱 + 额枋 + 曲面攒尖顶 + 宝顶。
工作尺度 1 单位 = 100 mm。
"""
import os

from build123d import (
    Axis, BuildPart, BuildSketch, Circle, Locations, Plane, Rectangle,
    RectangleRounded, chamfer, export_step, export_stl, extrude, loft,
)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

PLAT = 0.64          # 台基边长
PLAT_H = 0.09
COL_R = 0.034
COL_H = 0.32
COL_XY = 0.235


def build():
    steps = {}
    with BuildPart() as part:
        # 台基
        with BuildSketch(Plane.XY):
            RectangleRounded(PLAT, PLAT, 0.045)
        extrude(amount=PLAT_H)
        steps["platform"] = len(part.part.faces())

        # 四柱
        for sx in (-1, 1):
            for sy in (-1, 1):
                with BuildSketch(Plane.XY.offset(PLAT_H)):
                    with Locations((sx * COL_XY, sy * COL_XY)):
                        Circle(COL_R)
                extrude(amount=COL_H)
        steps["columns"] = len(part.part.faces())

        # 额枋（连接柱头的方框）
        with BuildSketch(Plane.XY.offset(PLAT_H + COL_H)):
            Rectangle(COL_XY * 2 + 0.10, COL_XY * 2 + 0.10)
            RectangleRounded(COL_XY * 2 - 0.10, COL_XY * 2 - 0.10, 0.02)
        extrude(amount=0.055)
        steps["beams"] = len(part.part.faces())

        z0 = PLAT_H + COL_H + 0.055
        # 攒尖顶：四段截面 loft 出凹曲屋面
        for size, dz in ((0.72, 0.005), (0.50, 0.115), (0.24, 0.205), (0.06, 0.255)):
            with BuildSketch(Plane.XY.offset(z0 + dz)):
                RectangleRounded(size, size, min(0.03, size * 0.2))
        loft()
        steps["roof"] = len(part.part.faces())

        z1 = z0 + 0.255
        # 宝顶
        with BuildSketch(Plane.XY.offset(z1)):
            Circle(0.055)
        extrude(amount=0.05)
        with BuildSketch(Plane.XY.offset(z1 + 0.05)):
            Circle(0.03)
        extrude(amount=0.05)
        steps["finial"] = len(part.part.faces())

        try:
            chamfer(part.edges().filter_by(Axis.Z), length=0.008)
            steps["chamfer"] = "ok"
        except Exception as exc:
            steps["chamfer"] = f"跳过 {type(exc).__name__}"

    return part.part, steps


def main():
    os.makedirs(OUT, exist_ok=True)
    solid, steps = build()
    stl = os.path.join(OUT, "pavilion_ss05.stl")
    step = os.path.join(OUT, "pavilion_ss05.step")
    export_stl(solid, stl)
    export_step(solid, step)
    bb = solid.bounding_box().size
    print(f"[cad] 阶段 {steps}")
    print(f"[cad] 面 {len(solid.faces())} 边 {len(solid.edges())} 体积 {solid.volume:,.4f} 合法 {solid.is_valid}")
    print(f"[cad] 尺寸 {bb.X*100:.0f} x {bb.Y*100:.0f} x {bb.Z*100:.0f} mm")
    print(f"[cad] STL {os.path.getsize(stl):,}  STEP {os.path.getsize(step):,}")


if __name__ == "__main__":
    main()
