"""AxisBurst · 场景 / 相机 / 线稿 / 导出 的公共部分。

单零件验证（build_part.py）和总装（build_assembly.py）共用这一层，
保证两条路出来的线稿风格完全一致。
"""

from __future__ import annotations

import math
import os

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

RES_X, RES_Y = 1400, 900
ASPECT = RES_X / RES_Y

# 与总装一致的观察方向（等轴测偏正视）
VIEW_DIR = Vector((1.0, -1.16, 0.62)).normalized()


# ---------------------------------------------------------------- 场景

def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def scene_bounds(objects) -> tuple[Vector, Vector]:
    lo = Vector((math.inf,) * 3)
    hi = Vector((-math.inf,) * 3)
    for obj in objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            for i in range(3):
                lo[i] = min(lo[i], world[i])
                hi[i] = max(hi[i], world[i])
    return lo, hi


def bbox_corners(lo: Vector, hi: Vector) -> list[Vector]:
    return [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]


# ---------------------------------------------------------------- 相机

def make_camera() -> bpy.types.Object:
    scene = bpy.context.scene
    data = bpy.data.cameras.new("CAM")
    data.type = "ORTHO"
    data.ortho_scale = 4.0
    cam = bpy.data.objects.new("CAM", data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    return cam


def fit_camera(cam: bpy.types.Object, corners: list[Vector], *, pad: float = 1.14) -> None:
    """把正交相机对准这一组世界坐标点，自动定尺寸并居中。

    两遍：先按包围盒给一个尺度，量出投影范围后再精确缩放 + 平移居中。
    """
    scene = bpy.context.scene

    def point_at(center: Vector) -> None:
        cam.location = center + VIEW_DIR * 40.0
        cam.rotation_euler = (-VIEW_DIR).to_track_quat("-Z", "Y").to_euler()

    center = sum(corners, Vector()) / len(corners)
    span = max((c - center).length for c in corners)

    point_at(center)
    cam.data.ortho_scale = max(span * 2.4, 0.5)
    bpy.context.view_layer.update()

    def measure() -> tuple[float, float, float, float]:
        xs, ys = [], []
        for p in corners:
            c = world_to_camera_view(scene, cam, p)
            xs.append(c.x)
            ys.append(c.y)
        return min(xs), max(xs), min(ys), max(ys)

    min_x, max_x, min_y, max_y = measure()
    cam.data.ortho_scale *= max(max_x - min_x, max_y - min_y) * pad
    bpy.context.view_layer.update()

    # 居中：把投影中心推到画面中心
    min_x, max_x, min_y, max_y = measure()
    frame_w = cam.data.ortho_scale if ASPECT >= 1 else cam.data.ortho_scale * ASPECT
    frame_h = cam.data.ortho_scale / ASPECT if ASPECT >= 1 else cam.data.ortho_scale
    basis = cam.matrix_world.to_3x3()
    right = basis @ Vector((1.0, 0.0, 0.0))
    up = basis @ Vector((0.0, 1.0, 0.0))
    cam.location += right * (((min_x + max_x) / 2.0 - 0.5) * frame_w)
    cam.location += up * (((min_y + max_y) / 2.0 - 0.5) * frame_h)
    bpy.context.view_layer.update()


# ---------------------------------------------------------------- 线稿

def add_line_art(
    name: str,
    collection: bpy.types.Collection,
    *,
    radius: float = 0.0035,
    crease_deg: float = 132.0,
    intersection: bool = True,
) -> bpy.types.Object:
    """给一个集合建 Line Art → Grease Pencil 图层。

    必须用 grease_pencil_add(type='LINEART_COLLECTION')：手工 grease_pencils.new()
    造出来的空图层不会被 Line Art 求值，导出会得到空 SVG。
    """
    bpy.ops.object.grease_pencil_add(type="LINEART_COLLECTION")
    gp = bpy.context.object
    gp.name = "LA_" + name
    gp.data.name = "LA_" + name
    gp.data.layers[0].name = name

    mod = next(m for m in gp.modifiers if m.type == "LINEART")
    mod.name = "LineArt_" + name
    mod.source_type = "COLLECTION"
    mod.source_collection = collection
    mod.target_layer = name
    mod.use_contour = True
    mod.use_crease = True
    mod.use_edge_mark = True
    # 有机件减面后会产生大量自交边，画出来就是一片碎点，默认关掉
    mod.use_intersection = intersection
    mod.use_loose = False
    mod.use_material = False
    mod.crease_threshold = math.radians(crease_deg)
    mod.radius = radius
    mod.use_cache = True
    return gp


def export_svg(gp_objects, path: str) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for gp in gp_objects:
        gp.select_set(True)
    bpy.context.view_layer.objects.active = gp_objects[0]
    bpy.ops.wm.grease_pencil_export_svg(
        filepath=path,
        use_fill=False,
        use_uniform_width=True,
        use_clip_camera=False,
        selected_object_type="SELECTED",
    )


def count_strokes(gp_object) -> tuple[int, int]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = gp_object.evaluated_get(depsgraph)
    strokes = sum(len(f.drawing.strokes) for layer in evaluated.data.layers for f in layer.frames)
    points = sum(
        len(s.points) for layer in evaluated.data.layers for f in layer.frames for s in f.drawing.strokes
    )
    return strokes, points


# ---------------------------------------------------------------- 预览渲染

def setup_render(path: str) -> None:
    scene = bpy.context.scene
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = path
    scene.render.film_transparent = False

    # Workbench 不渲染 Grease Pencil，预览一律用 EEVEE
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            scene.render.engine = engine
            break
        except Exception:  # noqa: BLE001
            continue

    world = bpy.data.worlds.new("W")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.92, 0.91, 0.88, 1.0)
    scene.world = world

    sun_data = bpy.data.lights.new("Sun", type="SUN")
    sun_data.energy = 3.2
    sun = bpy.data.objects.new("Sun", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(54.0), 0.0, math.radians(36.0))

    paper = bpy.data.materials.new("Paper")
    paper.use_nodes = True
    bsdf = paper.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.95, 0.94, 0.91, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.85
        bsdf.inputs["Metallic"].default_value = 0.25

    ink = bpy.data.materials.new("Ink")
    ink.use_nodes = True
    ink_bsdf = ink.node_tree.nodes.get("Principled BSDF")
    if ink_bsdf:
        ink_bsdf.inputs["Base Color"].default_value = (0.04, 0.04, 0.05, 1.0)

    for obj in bpy.data.objects:
        if obj.type == "MESH" and not obj.data.materials:
            obj.data.materials.append(paper)
        elif obj.type == "GREASEPENCIL" and ink.name not in [m.name for m in obj.data.materials if m]:
            obj.data.materials.append(ink)


def render(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.render.render(write_still=True)
