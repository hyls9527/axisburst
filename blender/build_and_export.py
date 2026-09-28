"""
AxisBurst · Blender 5.2 分层线稿 SVG 通路

目标：用 Blender 程序化生成机械装配体，导出「每个零件一个 <g>」的分层线稿 SVG，
供前端用 anime.js v4 做时序爆炸分解（对齐 animejs.com 首屏那种工程线稿质感）。

用法：
  blender.exe --background --factory-startup --python blender/build_and_export.py -- --out blender/out

产物：
  <out>/axisburst_lineart.svg   分层线稿，零件 = Grease Pencil 图层 = SVG group
  <out>/preview.png             渲染预览，用于人工核对造型与视角
"""

from __future__ import annotations

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

# 零件显示名（SVG 里的 id 是英文，前端要中文标注）
PART_LABELS = {
    "housing": "座体外壳",
    "flange-lower": "下法兰",
    "bolts": "紧固螺栓",
    "bearing-lower": "下轴承",
    "gear": "主齿轮",
    "bearing-upper": "上轴承",
    "shaft": "传动轴",
    "cap": "端盖",
}

# ---------------------------------------------------------------- 参数

# 画面的斜向构图由 tools/normalize-svg.mjs 的 TILT_DEG 统一负责。
# 这里保持 0：Grease Pencil 的 SVG 导出会把相机滚转算掉，在两边都加会算重复。
CAM_ROLL_DEG = 0.0
CAM_ORTHO_SCALE = 7.6
TARGET_Z = 1.60               # 画面中心对准的装配体高度

LINE_RADIUS = 0.0026          # 线宽（世界单位，Line Art radius）
CREASE_DEG = 138.0            # 折角阈值：超过才画结构线

RES_X, RES_Y = 1400, 900


def parse_out_dir() -> str:
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = "blender/out"
    for i, a in enumerate(argv):
        if a == "--out" and i + 1 < len(argv):
            out = argv[i + 1]
    return os.path.abspath(out)


# ---------------------------------------------------------------- 建模工具

def new_part(name: str) -> bpy.types.Collection:
    """每个零件一个集合 —— 这是分层的最小单位。"""
    col = bpy.data.collections.new("P_" + name)
    bpy.context.scene.collection.children.link(col)
    return col


def move_to(obj: bpy.types.Object, col: bpy.types.Collection) -> None:
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)


def cylinder(col, name, radius, depth, z, *, verts=72, x=0.0, y=0.0, rot=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=verts, radius=radius, depth=depth,
        location=(x, y, z), rotation=rot,
    )
    obj = bpy.context.object
    obj.name = name
    move_to(obj, col)
    return obj


def cone(col, name, r1, r2, depth, z, *, verts=72, x=0.0, y=0.0):
    bpy.ops.mesh.primitive_cone_add(
        vertices=verts, radius1=r1, radius2=r2, depth=depth, location=(x, y, z),
    )
    obj = bpy.context.object
    obj.name = name
    move_to(obj, col)
    return obj


def torus(col, name, major, minor, z, *, x=0.0, y=0.0):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major, minor_radius=minor,
        major_segments=64, minor_segments=16,
        location=(x, y, z),
    )
    obj = bpy.context.object
    obj.name = name
    move_to(obj, col)
    return obj


def box(col, name, sx, sy, sz, x, y, z, rot_z=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, y, z), rotation=(0.0, 0.0, rot_z))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (sx, sy, sz)
    move_to(obj, col)
    return obj


# ---------------------------------------------------------------- 装配体

def build_assembly() -> list[str]:
    """返回零件 id 列表（顺序 = 装配顺序 = SVG 图层顺序）。"""

    parts: list[str] = []

    # 1 座体
    col = new_part("housing")
    parts.append("housing")
    cylinder(col, "housing_base", 1.72, 0.16, -0.34, verts=96)
    cylinder(col, "housing_body", 1.50, 0.52, 0.02, verts=96)
    cylinder(col, "housing_lip", 1.62, 0.10, 0.32, verts=96)
    torus(col, "housing_rib", 1.55, 0.045, -0.06)

    # 2 下法兰
    col = new_part("flange-lower")
    parts.append("flange-lower")
    cylinder(col, "flange_lower", 1.22, 0.13, 0.45, verts=96)

    # 3 螺栓组（法兰孔位）
    col = new_part("bolts")
    parts.append("bolts")
    for i in range(8):
        a = i / 8.0 * math.tau
        r = 1.36
        cylinder(col, f"bolt_{i}", 0.085, 0.30, 0.45,
                 verts=6, x=r * math.cos(a), y=r * math.sin(a))

    # 4 下轴承
    col = new_part("bearing-lower")
    parts.append("bearing-lower")
    cylinder(col, "bl_outer", 0.88, 0.34, 0.68, verts=72)
    torus(col, "bl_race_a", 0.88, 0.05, 0.55)
    torus(col, "bl_race_b", 0.88, 0.05, 0.82)

    # 5 主齿轮
    col = new_part("gear")
    parts.append("gear")
    cylinder(col, "gear_disk", 0.96, 0.20, 1.02, verts=96)
    for i in range(18):
        a = i / 18.0 * math.tau
        box(col, f"tooth_{i}", 0.34, 0.11, 0.20,
            1.00 * math.cos(a), 1.00 * math.sin(a), 1.02, rot_z=a)
    cylinder(col, "gear_hub", 0.40, 0.28, 1.02, verts=48)

    # 6 上轴承
    col = new_part("bearing-upper")
    parts.append("bearing-upper")
    cylinder(col, "bu_outer", 0.80, 0.30, 1.32, verts=72)
    torus(col, "bu_race_a", 0.80, 0.045, 1.20)
    torus(col, "bu_race_b", 0.80, 0.045, 1.44)

    # 7 传动轴
    col = new_part("shaft")
    parts.append("shaft")
    cylinder(col, "shaft_main", 0.34, 1.25, 1.95, verts=64)
    cone(col, "shaft_taper", 0.34, 0.22, 0.42, 2.76, verts=64)
    cylinder(col, "shaft_tip", 0.20, 0.55, 3.05, verts=48)
    box(col, "shaft_key", 0.10, 0.20, 0.42, 0.30, 0.0, 2.00)

    # 8 端盖
    col = new_part("cap")
    parts.append("cap")
    cylinder(col, "cap_body", 0.58, 0.22, 3.42, verts=64)
    cylinder(col, "cap_top", 0.34, 0.14, 3.55, verts=48)
    for i in range(4):
        a = i / 4.0 * math.tau + math.pi / 4
        cylinder(col, f"cap_screw_{i}", 0.055, 0.26, 3.42,
                 verts=6, x=0.42 * math.cos(a), y=0.42 * math.sin(a))

    return parts


# ---------------------------------------------------------------- 线稿

def build_lineart(parts: list[str]) -> list[bpy.types.Object]:
    """每个零件一个 Line Art 对象 —— 导出后各成一个 SVG 图层组。

    关键：必须用 bpy.ops.object.grease_pencil_add(type='LINEART_COLLECTION') 建对象，
    手工 bpy.data.grease_pencils.new() 造出来的空图层不会被 Line Art 求值（0 笔画）。
    """
    gp_objects: list[bpy.types.Object] = []

    for pid in parts:
        bpy.ops.object.grease_pencil_add(type="LINEART_COLLECTION")
        gp_obj = bpy.context.object
        gp_obj.name = "LA_" + pid
        gp_obj.data.name = "LA_" + pid

        # 图层名 = 零件 id，导出后 SVG 里就是这个 id
        layer = gp_obj.data.layers[0]
        layer.name = pid

        mod = next(m for m in gp_obj.modifiers if m.type == "LINEART")
        mod.name = "LineArt_" + pid
        mod.source_type = "COLLECTION"
        mod.source_collection = bpy.data.collections["P_" + pid]
        mod.target_layer = pid
        mod.use_contour = True
        mod.use_crease = True
        mod.use_edge_mark = True
        mod.use_intersection = True
        mod.use_loose = False
        mod.use_material = False
        mod.crease_threshold = math.radians(CREASE_DEG)
        mod.radius = LINE_RADIUS
        mod.use_cache = True

        gp_objects.append(gp_obj)

    return gp_objects


# ---------------------------------------------------------------- 相机 / 渲染

def build_camera():
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("CAM")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = CAM_ORTHO_SCALE
    cam = bpy.data.objects.new("CAM", cam_data)
    scene.collection.objects.link(cam)

    target = Vector((0.0, 0.0, TARGET_Z))
    loc = Vector((3.6, -4.2, TARGET_Z + 2.1))
    cam.location = loc
    aim = (target - loc).to_track_quat("-Z", "Y").to_matrix().to_4x4()
    # 绕相机自身 Z 轴（即视线方向）滚转，得到画面里的斜向构图
    cam.matrix_world = Matrix.Translation(loc) @ aim @ Matrix.Rotation(math.radians(CAM_ROLL_DEG), 4, "Z")

    scene.camera = cam
    return cam


# ---------------------------------------------------------------- 零件元数据

def part_stats(parts: list[str], cam: bpy.types.Object) -> dict:
    """导出每个零件在世界空间的包围盒 + 沿装配轴的次序。

    爆炸方向 = 装配轴（世界 +Z）。这里只给世界空间事实，
    投影到 SVG 二维空间交给 tools/normalize-svg.mjs —— 那边能直接从 SVG 里量。
    """
    axis = Vector((0.0, 0.0, 1.0))
    stats: dict[str, dict] = {}

    for index, pid in enumerate(parts):
        col = bpy.data.collections["P_" + pid]
        lo = Vector((math.inf,) * 3)
        hi = Vector((-math.inf,) * 3)
        for obj in col.objects:
            for corner in obj.bound_box:
                world = obj.matrix_world @ Vector(corner)
                for axis_i in range(3):
                    lo[axis_i] = min(lo[axis_i], world[axis_i])
                    hi[axis_i] = max(hi[axis_i], world[axis_i])

        center = (lo + hi) / 2.0
        stats[pid] = {
            "order": index,
            "label": PART_LABELS.get(pid, pid),
            "bbox_world": {
                "min": [round(v, 5) for v in lo],
                "max": [round(v, 5) for v in hi],
            },
            "center_world": [round(v, 5) for v in center],
            # 沿装配轴的位置，前端按它排序 / 决定爆炸次序
            "axis_t": round(center.dot(axis), 5),
        }

    return {
        "axis_world": list(axis),
        "parts": stats,
    }


def setup_render(out_dir: str) -> None:
    scene = bpy.context.scene
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.join(out_dir, "preview.png")
    scene.render.film_transparent = False

    # 注意：Workbench 不渲染 Grease Pencil，预览线稿必须用 EEVEE/Cycles
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            scene.render.engine = engine
            break
        except Exception:  # noqa: BLE001
            continue
    print("[render] engine =", scene.render.engine)

    # 实体：纸白材质；线稿：墨黑材质（Grease Pencil 走自己的材质色）
    paper = bpy.data.materials.new("Paper")
    paper.diffuse_color = (0.96, 0.95, 0.92, 1.0)
    if not paper.node_tree:
        paper.use_nodes = True
    paper_bsdf = paper.node_tree.nodes.get("Principled BSDF")
    if paper_bsdf:
        paper_bsdf.inputs["Base Color"].default_value = (0.96, 0.95, 0.92, 1.0)
        paper_bsdf.inputs["Roughness"].default_value = 0.85

    ink = bpy.data.materials.new("Ink")
    ink.diffuse_color = (0.05, 0.05, 0.06, 1.0)
    if not ink.node_tree:
        ink.use_nodes = True
    ink_bsdf = ink.node_tree.nodes.get("Principled BSDF")
    if ink_bsdf:
        ink_bsdf.inputs["Base Color"].default_value = (0.05, 0.05, 0.06, 1.0)

    for obj in bpy.data.objects:
        if obj.type == "MESH":
            if not obj.data.materials:
                obj.data.materials.append(paper)
        elif obj.type == "GREASEPENCIL":
            if ink.name not in [m.name for m in obj.data.materials if m]:
                obj.data.materials.append(ink)

    # 布光：一盏天光 + 环境光，够看造型就行
    sun_data = bpy.data.lights.new("Sun", type="SUN")
    sun_data.energy = 3.0
    sun = bpy.data.objects.new("Sun", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(52), 0.0, math.radians(38))

    world = bpy.data.worlds.new("W")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.93, 0.92, 0.89, 1.0)
    scene.world = world


# ---------------------------------------------------------------- 主流程

def main() -> None:
    out_dir = parse_out_dir()
    os.makedirs(out_dir, exist_ok=True)
    print("[out]", out_dir)

    bpy.ops.wm.read_factory_settings(use_empty=True)

    parts = build_assembly()
    print("[parts]", len(parts), parts)

    gp_objects = build_lineart(parts)
    cam = build_camera()
    setup_render(out_dir)

    bpy.context.view_layer.update()

    # 零件元数据（爆炸次序 / 包围盒），供前端拼时间轴
    import json

    meta_path = os.path.join(out_dir, "axisburst_parts.json")
    meta = part_stats(parts, cam)
    with open(meta_path, "w", encoding="utf-8") as handle:
        json.dump(meta, handle, ensure_ascii=False, indent=2)
    print("[json] written:", meta_path, os.path.getsize(meta_path))

    svg_path = os.path.join(out_dir, "axisburst_lineart.svg")
    bpy.ops.object.select_all(action="DESELECT")
    for gp_obj in gp_objects:
        gp_obj.select_set(True)
    bpy.context.view_layer.objects.active = gp_objects[0]

    svg_props = bpy.ops.wm.grease_pencil_export_svg.get_rna_type().properties
    print("[svg] selected_object_type enum:",
          [i.identifier for i in svg_props["selected_object_type"].enum_items])
    print("[svg] frame_mode enum:",
          [i.identifier for i in svg_props["frame_mode"].enum_items])

    bpy.ops.wm.grease_pencil_export_svg(
        filepath=svg_path,
        use_fill=False,
        use_uniform_width=True,
        use_clip_camera=False,   # True 会把相机框外的笔画裁掉，装配体容易缺角
        selected_object_type="SELECTED",
    )
    print("[svg] written:", svg_path, os.path.exists(svg_path),
          os.path.getsize(svg_path) if os.path.exists(svg_path) else 0)

    bpy.ops.render.render(write_still=True)
    print("[png] written:", bpy.context.scene.render.filepath)

    # 打印每个零件实际生成的笔画数，验证线稿真的生成了
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for gp_obj in gp_objects:
        evaluated = gp_obj.evaluated_get(depsgraph)
        strokes = sum(len(f.drawing.strokes) for L in evaluated.data.layers for f in L.frames)
        points = sum(len(s.points) for L in evaluated.data.layers for f in L.frames for s in f.drawing.strokes)
        print(f"[layer] {gp_obj.name:20s} strokes={strokes:4d} points={points:6d}")


if __name__ == "__main__":
    main()
