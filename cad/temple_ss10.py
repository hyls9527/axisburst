"""SS-10 寺庙建筑 —— 木 + 金属。台基 + 台阶 + 殿身 + 檐廊柱 + 庑殿顶 + 正脊。
工作尺度 1 单位 = 100 mm。
"""
import os

from build123d import (
    Axis, Box, BuildPart, BuildSketch, Circle, Locations, Plane, Rectangle,
    RectangleRounded, chamfer, export_step, export_stl, extrude, loft,
)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

PW, PD, PH = 1.50, 0.90, 0.10      # 台基
BW, BD, BH = 1.14, 0.54, 0.34      # 殿身


def build():
    steps = {}
    with BuildPart() as part:
        # 台基
        with BuildSketch(Plane.XY):
            RectangleRounded(PW, PD, 0.06)
        extrude(amount=PH)
        # 台阶
        with BuildSketch(Plane.XY):
            with Locations((0, -PD / 2 - 0.055)):
                Rectangle(0.46, 0.11)
        extrude(amount=PH * 0.55)
        steps["platform"] = len(part.part.faces())

        # 殿身
        with BuildSketch(Plane.XY.offset(PH)):
            RectangleRounded(BW, BD, 0.03)
        extrude(amount=BH)
        steps["body"] = len(part.part.faces())

        # 檐廊柱（正面 6 根）
        for i in range(6):
            x = -BW / 2 + 0.10 + i * (BW - 0.20) / 5
            with BuildSketch(Plane.XY.offset(PH)):
                with Locations((x, -BD / 2 - 0.055)):
                    Circle(0.028)
            extrude(amount=BH)
        steps["columns"] = len(part.part.faces())

        # 庑殿顶：四段 loft 出举折
        z0 = PH + BH
        for w, d, dz in ((1.46, 0.86, 0.02), (1.18, 0.58, 0.13), (0.62, 0.20, 0.245), (0.30, 0.06, 0.30)):
            with BuildSketch(Plane.XY.offset(z0 + dz)):
                Rectangle(w, d)
        loft()
        steps["roof"] = len(part.part.faces())

        # 正脊 + 两端鸱吻
        with BuildSketch(Plane.XY.offset(z0 + 0.30)):
            Rectangle(0.46, 0.075)
        extrude(amount=0.055)
        for sx in (-1, 1):
            with BuildSketch(Plane.XY.offset(z0 + 0.30)):
                with Locations((sx * 0.24, 0)):
                    Circle(0.038)
            extrude(amount=0.095)
        steps["ridge"] = len(part.part.faces())

        try:
            chamfer(part.edges().filter_by(Axis.Z), length=0.008)
            steps["chamfer"] = "ok"
        except Exception as exc:
            steps["chamfer"] = f"跳过 {type(exc).__name__}"

    return part.part, steps


def main():
    os.makedirs(OUT, exist_ok=True)
    solid, steps = build()
    stl = os.path.join(OUT, "temple_ss10.stl")
    step = os.path.join(OUT, "temple_ss10.step")
    export_stl(solid, stl)
    export_step(solid, step)
    bb = solid.bounding_box().size
    print(f"[cad] 阶段 {steps}")
    print(f"[cad] 面 {len(solid.faces())} 边 {len(solid.edges())} 体积 {solid.volume:,.4f} 合法 {solid.is_valid}")
    print(f"[cad] 尺寸 {bb.X*100:.0f} x {bb.Y*100:.0f} x {bb.Z*100:.0f} mm")
    print(f"[cad] STL {os.path.getsize(stl):,}  STEP {os.path.getsize(step):,}")


if __name__ == "__main__":
    main()
