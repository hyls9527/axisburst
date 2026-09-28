"""AB-1102 下法兰 —— 压住下轴承的环形法兰。

要点：外圈滚花便于手拧、8 个螺栓孔、内孔台阶定位轴承外圈。
"""

from __future__ import annotations

import partkit as kit

ID = "flange_lower"
PN = "AB-1102"
LABEL = "下法兰"
LABEL_EN = "LOWER FLANGE"
GROUP = "housing-unit"
ORDER = 1
QTY = 1
Z = 0.355                    # 落在座体上盘辐条顶面
MATERIAL = "45 钢"
PROCESS = "车削 + 钻孔 + 滚花"

PARAMS = [
    ("外径", "Ø2.60"),
    ("内孔", "Ø1.80"),
    ("厚度", "0.14"),
    ("螺栓孔", "8 × Ø0.16"),
    ("滚花", "64 齿"),
]


def build(col, kit_ctx=None):
    profile = [
        (0.90, 0.000),
        (1.30, 0.000),       # 底面（环形）
        (1.30, 0.110),
        (1.24, 0.140),
        (0.90, 0.140),       # 顶面
        (0.90, 0.000),
    ]
    body = kit.lathe(col, "flange_lower_body", profile, segments=160, bevel=0.010, bevel_segments=2)

    # 外圈滚花
    kit.knurl(
        col, "flange_lower_knurl",
        radius=1.245, z0=0.012, z1=0.128,
        count=64, depth=0.016, width=0.026,
    )

    # 8 个螺栓通孔
    kit.drill_holes(
        body, count=8, ring_r=1.045, hole_r=0.080,
        z0=-0.05, z1=0.19, phase=0.3927, name="bolt_hole",
    )

    return col
