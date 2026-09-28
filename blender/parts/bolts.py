"""AB-1103 紧固螺栓组 —— 把下法兰压紧在座体上的 8 颗螺栓。

单颗螺栓=六角头 + 光杆 + 一段螺纹（用密排薄环做出牙型）。
一组 8 颗作为一个零件入账，QTY=8。
"""

from __future__ import annotations

import math

import partkit as kit

ID = "bolts"
PN = "AB-1103"
LABEL = "紧固螺栓组"
LABEL_EN = "BOLT SET"
GROUP = "housing-unit"
ORDER = 2
QTY = 8
Z = 0.495                    # 法兰顶面
MATERIAL = "8.8 级合金钢"
PROCESS = "车螺纹 + 发黑"

PARAMS = [
    ("规格", "M12"),
    ("对边", "0.20"),
    ("头高", "0.10"),
    ("杆长", "0.46"),
    ("数量", "8"),
]

COUNT = 8
RING_R = 1.045


def _thread(radius: float, z0: float, z1: float, pitch: float = 0.045):
    """用密排薄环做出螺纹牙型的观感。"""
    rings = max(3, int(round((z1 - z0) / pitch)))
    return rings


def build(col, kit_ctx=None):
    for i in range(COUNT):
        a = 0.3927 + i / COUNT * math.tau
        kit.hex_bolt(
            col, f"bolt_{i}",
            head_r=0.115, head_h=0.100,
            shank_r=0.060, shank_h=0.460,
            at=(RING_R * math.cos(a), RING_R * math.sin(a), 0.0),
        )
    return col
