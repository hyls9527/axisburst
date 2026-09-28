"""SS-08 山体岩石 —— 在活动 Blender 里跑（经 tools/blender-live.py 投递）。
山石要雕刻，而雕刻在 --background 下不可用（笔刷 poll 失败、mesh_filter 崩进程）。
工作尺度：1 单位 = 100 mm。摆件总宽 560 深 320，主峰高约 230。
"""
import math
import os
import bmesh
import bpy
from mathutils import Vector, noise

OUT = r"C:\Users\Administrator\workspace\axisburst\blender\out\live"
os.makedirs(OUT, exist_ok=True)
W, D = 5.6, 3.2
GRID_X, GRID_Y = 132, 76
PEAKS = [
    (-1.15, 0.30, 2.30, 2.15),
    (1.30, -0.20, 1.30, 1.75),
    (0.30, 0.85, 0.95, 1.40),
    (-2.20, -0.70, 0.72, 1.25),
    (2.15, 0.60, 0.55, 1.05),
]

def log(*parts):
    print("SS08", *parts)

# 绝对不要用 bpy.ops.wm.read_factory_settings()：它会重载整个 Blender 状态，
# 把 MCP 插件的 socket 服务器一起干掉，等于切断自己的控制通道（已踩过）。
# 只删对象，不动 addon 与场景属性。
for _ob in list(bpy.data.objects):
    bpy.data.objects.remove(_ob, do_unlink=True)
for _col in list(bpy.data.collections):
    if _col.users == 0:
        bpy.data.collections.remove(_col)
log("清空场景，剩余物体 =", len(bpy.data.objects))

bpy.ops.mesh.primitive_grid_add(x_subdivisions=GRID_X, y_subdivisions=GRID_Y, size=1.0)
obj = bpy.context.object
obj.name = "SS08_shan"
log("基底网格顶点", len(obj.data.vertices))
for v in obj.data.vertices:
    v.co.x *= W
    v.co.y *= D

for v in obj.data.vertices:
    x, y = v.co.x, v.co.y
    h = 0.0
    for px, py, peak, radius in PEAKS:
        d = math.hypot(x - px, y - py) / radius
        if d < 1.0:
            h = max(h, peak * (0.5 + 0.5 * math.cos(math.pi * d)) ** 1.4)
    edge = max(abs(x) / (W / 2), abs(y) / (D / 2))
    if edge > 0.70:
        h *= max(0.0, 1.0 - (edge - 0.70) / 0.30)
    v.co.z = h
log("高度场完成，最高", round(max(v.co.z for v in obj.data.vertices), 3))

# 噪声留到平滑之后再加，否则会被 SMOOTH 抹平（第一版就是这么变成圆包的）
def add_detail(tag):
    total = 0.0
    for v in obj.data.vertices:
        x, y, z = v.co
        if z <= 0.002:
            continue
        amp = min(1.0, z / 0.45)
        c = noise.turbulence(Vector((x * 0.75, y * 0.75, 7.0)), 4, False)
        m = noise.turbulence(Vector((x * 1.80, y * 1.80, 23.0)), 3, False)
        f = noise.turbulence(Vector((x * 4.20, y * 4.20, 51.0)), 2, False)
        d = (c - 0.5) * 0.46 + (m - 0.5) * 0.20 + (f - 0.5) * 0.075
        v.co.z += d * amp
        total += abs(d * amp)
    log(tag, "平均起伏", round(total / max(1, len(obj.data.vertices)), 4))

bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")

solid = obj.modifiers.new("solidify", "SOLIDIFY")
solid.thickness = 0.55
solid.offset = -1.0
solid.use_even_offset = True
bpy.ops.object.modifier_apply(modifier=solid.name)
log("加厚完成，顶点", len(obj.data.vertices))

add_detail("基底层噪声")

sculpt_log = []
if bpy.app.background:
    sculpt_log.append("background 跳过雕刻（会崩）")
else:
    bpy.ops.object.mode_set(mode="SCULPT")
    # 顺序：先轻平滑掉网格棱角 → 再加细节噪声 → 最后锐化出岩石面
    for ftype, strength, iters in (
        ("SMOOTH", 0.25, 2),
    ):
        try:
            r = bpy.ops.sculpt.mesh_filter(type=ftype, strength=strength, iteration_count=iters)
            sculpt_log.append(ftype + "x" + str(iters) + " " + str(r))
        except Exception as exc:
            sculpt_log.append(ftype + " 失败 " + type(exc).__name__)
    bpy.ops.object.mode_set(mode="OBJECT")
    add_detail("平滑后补细节")
    bpy.ops.object.mode_set(mode="SCULPT")
    for ftype, strength, iters in (
        ("SHARPEN", 0.38, 2),
        ("SHARPEN", 0.22, 1),
    ):
        try:
            r = bpy.ops.sculpt.mesh_filter(type=ftype, strength=strength, iteration_count=iters)
            sculpt_log.append(ftype + "x" + str(iters) + " " + str(r))
        except Exception as exc:
            sculpt_log.append(ftype + " 失败 " + type(exc).__name__)
    bpy.ops.object.mode_set(mode="OBJECT")
log("雕刻：", " | ".join(sculpt_log))

# ---------------------------------------------------------------- 6b 尺寸归一化
lo = [min(getattr(v.co, a) for v in obj.data.vertices) for a in "xyz"]
hi = [max(getattr(v.co, a) for v in obj.data.vertices) for a in "xyz"]
sx, sy = hi[0] - lo[0], hi[1] - lo[1]
fit = min(W / sx, D / sy)          # 等比缩小，不拉伸变形
if abs(fit - 1.0) > 1e-4:
    for v in obj.data.vertices:
        v.co.x *= fit
        v.co.y *= fit
    log("归一化缩放", round(fit, 4))

lo = [min(getattr(v.co, a) for v in obj.data.vertices) for a in "xyz"]
hi = [max(getattr(v.co, a) for v in obj.data.vertices) for a in "xyz"]
log("包围盒 mm：", [round((hi[i] - lo[i]) * 100, 1) for i in range(3)])

blend_path = os.path.join(OUT, "SS08_shan.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
log("存档", blend_path)

try:
    obj_path = os.path.join(OUT, "SS08_shan.obj")
    bpy.ops.wm.obj_export(filepath=obj_path, export_selected_objects=True)
    log("导出", obj_path)
except Exception as exc:
    log("OBJ 导出失败", type(exc).__name__, exc)

log("完成 顶点", len(obj.data.vertices), "面", len(obj.data.polygons))
