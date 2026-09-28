"""AxisBurst · 零件建模工具层

零件模块只负责「用这些积木堆出自己的几何」，不关心相机、线稿、导出。
这样一个零件可以单独建、单独看，确认形状对了再进总装。

坐标约定：零件在**自己的局部坐标系**里建模，Z 轴 = 装配轴，
z=0 是零件在装配体里的落位基准面。装配时由 build_assembly.py 统一平移。
"""

from __future__ import annotations

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

TAU = math.tau


# Blender 4/5 之间 bmesh 造体的参数名改过（radius vs diameter），这里做一次兼容
def _create_cone(bm, *, segments, r1, r2, depth):
    try:
        return bmesh.ops.create_cone(
            bm, cap_ends=True, cap_tris=False, segments=segments,
            radius1=r1, radius2=r2, depth=depth,
        )
    except TypeError:
        return bmesh.ops.create_cone(
            bm, cap_ends=True, cap_tris=False, segments=segments,
            diameter1=r1 * 2.0, diameter2=r2 * 2.0, depth=depth,
        )


def _create_uvsphere(bm, *, segments, radius):
    try:
        return bmesh.ops.create_uvsphere(
            bm, u_segments=segments, v_segments=max(6, segments // 2), radius=radius,
        )
    except TypeError:
        return bmesh.ops.create_uvsphere(
            bm, u_segments=segments, v_segments=max(6, segments // 2), diameter=radius * 2.0,
        )


# ---------------------------------------------------------------- 集合

def new_collection(name: str) -> bpy.types.Collection:
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def move_to(obj: bpy.types.Object, col: bpy.types.Collection) -> bpy.types.Object:
    for existing in list(obj.users_collection):
        existing.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def obj_from_bmesh(name: str, bm: bmesh.types.BMesh, col: bpy.types.Collection) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    return obj


# ---------------------------------------------------------------- 回转体

def lathe(
    col: bpy.types.Collection,
    name: str,
    profile: list[tuple[float, float]],
    *,
    segments: int = 160,
    bevel: float = 0.0,
    bevel_segments: int = 2,
) -> bpy.types.Object:
    """把 (半径, 高度) 折线绕 Z 轴旋转成实体。

    profile 必须首尾都落在轴上（r=0），这样转出来才是封闭实体。
    半径/高度越大，倒角 bevel 越要小，否则会自交。
    """
    closed = profile[0] == profile[-1]
    if not closed and (profile[0][0] != 0 or profile[-1][0] != 0):
        raise ValueError(
            "lathe profile 要么首尾落在旋转轴上（r=0），要么首尾重合构成闭合截面（环形件）"
        )

    bm = bmesh.new()
    verts = [bm.verts.new((r, 0.0, z)) for r, z in profile]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]

    bmesh.ops.spin(
        bm,
        geom=verts + edges,
        cent=(0.0, 0.0, 0.0),
        axis=(0.0, 0.0, 1.0),
        dvec=(0.0, 0.0, 0.0),
        angle=TAU,
        steps=segments,
        use_merge=True,
        use_normal_flip=False,
    )
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)

    if bevel > 0:
        sharp = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > 0.35]
        if sharp:
            bmesh.ops.bevel(
                bm,
                geom=sharp,
                offset=bevel,
                offset_type="OFFSET",
                segments=bevel_segments,
                profile=0.5,
                affect="EDGES",
                clamp_overlap=True,
            )

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bmesh(name, bm, col)


# ---------------------------------------------------------------- 螺栓

def hex_bolt(
    col: bpy.types.Collection,
    name: str,
    *,
    head_r: float,
    head_h: float,
    shank_r: float,
    shank_h: float,
    at: tuple[float, float, float],
) -> bpy.types.Object:
    """六角头螺栓：头 + 光杆，沿 +Z 生长，原点在头底面中心。"""
    bm = bmesh.new()

    head = _create_cone(bm, segments=6, r1=head_r, r2=head_r, depth=head_h)
    for v in head["verts"]:
        v.co.z += head_h / 2.0

    shank = _create_cone(bm, segments=20, r1=shank_r, r2=shank_r, depth=shank_h)
    for v in shank["verts"]:
        v.co.z -= shank_h / 2.0

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = obj_from_bmesh(name, bm, col)
    obj.location = at
    return obj


def bolt_ring(
    col: bpy.types.Collection,
    name: str,
    *,
    count: int,
    ring_r: float,
    head_r: float,
    head_h: float,
    shank_r: float,
    shank_h: float,
    z: float,
    phase: float = 0.0,
) -> list[bpy.types.Object]:
    bolts = []
    for i in range(count):
        a = phase + i / count * TAU
        bolts.append(hex_bolt(
            col, f"{name}_{i}",
            head_r=head_r, head_h=head_h, shank_r=shank_r, shank_h=shank_h,
            at=(ring_r * math.cos(a), ring_r * math.sin(a), z),
        ))
    return bolts


# ---------------------------------------------------------------- 滚花 / 齿

def knurl(
    col: bpy.types.Collection,
    name: str,
    *,
    radius: float,
    z0: float,
    z1: float,
    count: int = 72,
    depth: float = 0.018,
    width: float = 0.028,
) -> bpy.types.Object:
    """圆周直纹滚花：一圈薄棱，是让机加工零件「看起来是真的」最省事的一招。"""
    bm = bmesh.new()
    height = z1 - z0
    for i in range(count):
        a = i / count * TAU
        piece = bmesh.ops.create_cube(bm, size=1.0)
        spin = Matrix.Rotation(a, 3, "Z")      # 绕 Z 轴排到圆周上
        for v in piece["verts"]:
            v.co.x *= width
            v.co.y *= depth
            v.co.z *= height
            v.co.z += z0 + height / 2.0
            v.co.y += radius                   # 贴到圆周，薄片沿径向朝外
            v.co = spin @ v.co

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bmesh(name, bm, col)


def spur_teeth(
    col: bpy.types.Collection,
    name: str,
    *,
    count: int,
    root_r: float,
    tip_r: float,
    z0: float,
    z1: float,
    tooth_width_deg: float = 9.0,
    phase: float = 0.0,
) -> bpy.types.Object:
    """直齿：整圈齿廓一次挤出，比一堆小方块干净得多。"""
    bm = bmesh.new()
    half = math.radians(tooth_width_deg) / 2.0
    for i in range(count):
        a = phase + i / count * TAU
        pts = [
            (a - half - math.radians(5.0), root_r),
            (a - half, tip_r),
            (a + half, tip_r),
            (a + half + math.radians(5.0), root_r),
        ]
        ring = []
        for z in (z0, z1):
            ring.append([
                bm.verts.new((r * math.cos(t), r * math.sin(t), z)) for t, r in pts
            ])
        bm.faces.new(ring[0][::-1])
        bm.faces.new(ring[1])
        for k in range(len(pts)):
            n = (k + 1) % len(pts)
            bm.faces.new((ring[0][k], ring[0][n], ring[1][n], ring[1][k]))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bmesh(name, bm, col)


# ---------------------------------------------------------------- 加强筋

def gussets(
    col: bpy.types.Collection,
    name: str,
    *,
    count: int,
    r_in: float,
    r_out: float,
    z0: float,
    z1: float,
    thickness: float,
    phase: float = 0.0,
) -> bpy.types.Object:
    """放射状加强筋：三角撑板，一圈 count 片。"""
    bm = bmesh.new()
    step = (r_out - r_in) / 4.0

    for i in range(count):
        a = phase + i / count * TAU
        outline = [
            (r_in, z0), (r_in, z1),
            (r_in + step * 2, z1), (r_in + step * 2.5, z1 - (z1 - z0) * 0.45),
            (r_out, z0),
        ]
        # 两侧各造一片并桥接
        shells = []
        for sign in (-1.0, 1.0):
            shells.append([
                bm.verts.new((
                    r * math.cos(a) - sign * thickness / 2.0 * math.sin(a),
                    r * math.sin(a) + sign * thickness / 2.0 * math.cos(a),
                    z,
                ))
                for r, z in outline
            ])
        bm.faces.new(shells[0])
        bm.faces.new(shells[1][::-1])
        for k in range(len(outline)):
            n = (k + 1) % len(outline)
            bm.faces.new((shells[0][k], shells[0][n], shells[1][n], shells[1][k]))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bmesh(name, bm, col)


# ---------------------------------------------------------------- 散热片 / 钻孔

def annular_fins(
    col: bpy.types.Collection,
    name: str,
    *,
    count: int,
    r_in: float,
    r_out: float,
    z_start: float,
    spacing: float,
    thickness: float,
    segments: int = 144,
) -> bpy.types.Object:
    """一圈圈薄圆盘散热片 —— 机加工件最出效果的一档细节。"""
    bm = bmesh.new()
    for i in range(count):
        z0 = z_start + i * spacing
        z1 = z0 + thickness
        ring_lo = []
        ring_hi = []
        for k in range(segments):
            a = k / segments * TAU
            c, s = math.cos(a), math.sin(a)
            ring_lo.append((bm.verts.new((r_in * c, r_in * s, z0)), bm.verts.new((r_out * c, r_out * s, z0))))
            ring_hi.append((bm.verts.new((r_in * c, r_in * s, z1)), bm.verts.new((r_out * c, r_out * s, z1))))
        for k in range(segments):
            n = (k + 1) % segments
            bm.faces.new((ring_lo[k][1], ring_lo[n][1], ring_hi[n][1], ring_hi[k][1]))   # 外圈
            bm.faces.new((ring_lo[n][0], ring_lo[k][0], ring_hi[k][0], ring_hi[n][0]))   # 内圈
            bm.faces.new((ring_hi[k][0], ring_hi[k][1], ring_hi[n][1], ring_hi[n][0]))   # 顶面
            bm.faces.new((ring_lo[k][0], ring_lo[n][0], ring_lo[n][1], ring_lo[k][1]))   # 底面

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bmesh(name, bm, col)


def drill_holes(
    target: bpy.types.Object,
    *,
    count: int,
    ring_r: float,
    hole_r: float,
    z0: float,
    z1: float,
    phase: float = 0.0,
    name: str = "drill",
) -> None:
    """在 target 上打一圈轴向通孔（布尔差集，逐个 Apply）。

    真孔会进线稿的轮廓/交线，是「像真零件」而不是「像积木」的关键差异。
    """
    saved_active = bpy.context.view_layer.objects.active
    for i in range(count):
        a = phase + i / count * TAU
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=40, radius=hole_r, depth=(z1 - z0),
            location=(ring_r * math.cos(a), ring_r * math.sin(a), (z0 + z1) / 2.0),
        )
        cutter = bpy.context.object
        cutter.name = f"__cutter_{name}_{i}"

        mod = target.modifiers.new(name, "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cutter
        mod.solver = "EXACT"

        bpy.ops.object.select_all(action="DESELECT")
        target.select_set(True)
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(cutter, do_unlink=True)

    if saved_active:
        bpy.context.view_layer.objects.active = saved_active


def spheres(
    col: bpy.types.Collection,
    name: str,
    *,
    count: int,
    ring_r: float,
    ball_r: float,
    z: float,
    phase: float = 0.0,
    segments: int = 20,
) -> bpy.types.Object:
    """一圈滚珠 —— 轴承里最能说明问题的那部分是看得见的珠。"""
    bm = bmesh.new()
    for i in range(count):
        a = phase + i / count * TAU
        center = Vector((ring_r * math.cos(a), ring_r * math.sin(a), z))
        ball = bmesh.ops.create_uvsphere(
            bm, u_segments=segments, v_segments=max(6, segments // 2), radius=ball_r,
        )
        for v in ball["verts"]:
            v.co += center
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bmesh(name, bm, col)


def radial_ribs(
    col: bpy.types.Collection,
    name: str,
    *,
    count: int,
    r_in: float,
    r_out: float,
    z: float,
    height: float,
    thickness: float,
    phase: float = 0.0,
) -> bpy.types.Object:
    """平盘面上的放射状辐条（涡轮盘 / 定子盘的那种纹理）。

    从俯视角度看，这一层辐条是让「一个圆盘」变成「一个零件」最有效的东西。
    """
    bm = bmesh.new()
    half = thickness / 2.0
    for i in range(count):
        a = phase + i / count * TAU
        c, s = math.cos(a), math.sin(a)
        # 切向单位向量
        tx, ty = -s, c
        quad = []
        for r in (r_in, r_out):
            for t in (-half, half):
                for zz in (z, z + height):
                    quad.append(bm.verts.new((r * c + t * tx, r * s + t * ty, zz)))
        # 顶点顺序：r0/t-/z0, r0/t-/z1, r0/t+/z0, r0/t+/z1, r1/t-/z0, ...
        v = quad
        faces = [
            (v[0], v[1], v[3], v[2]),      # 内端面
            (v[4], v[6], v[7], v[5]),      # 外端面
            (v[0], v[4], v[5], v[1]),      # 侧面 t-
            (v[2], v[3], v[7], v[6]),      # 侧面 t+
            (v[1], v[5], v[7], v[3]),      # 顶面
            (v[0], v[2], v[6], v[4]),      # 底面
        ]
        for f in faces:
            bm.faces.new(f)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bmesh(name, bm, col)


# ---------------------------------------------------------------- 外部形状 / 精修

def from_svg(
    col: bpy.types.Collection,
    name: str,
    svg_path: str,
    *,
    thickness: float,
    target_width: float | None = None,
    offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> bpy.types.Object:
    """把一张 SVG 轮廓拉成实体。

    这是「手工画形状」和「代码建形状」之间的桥：轮廓可以在矢量工具里画准
    （或者直接从参考图描下来），再进来做厚度、精修、上线稿。
    """
    before = set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=svg_path)
    imported = [o for o in bpy.data.objects if o not in before]
    if not imported:
        raise RuntimeError(f"SVG 没导入出对象：{svg_path}")

    bpy.ops.object.select_all(action="DESELECT")
    for obj in imported:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = imported[0]
    bpy.ops.object.convert(target="MESH")
    mesh_objs = [o for o in bpy.context.selected_objects if o.type == "MESH"]

    bpy.ops.object.select_all(action="DESELECT")
    for obj in mesh_objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objs[0]
    bpy.ops.object.join()
    joined = bpy.context.object
    joined.name = name

    if thickness:
        solidify = joined.modifiers.new("solidify", "SOLIDIFY")
        solidify.thickness = thickness
        solidify.offset = 0.0
        bpy.ops.object.modifier_apply(modifier=solidify.name)

    # SVG 进 Blender 的单位换算不是 1:1，所以按实测包围盒定标，而不是靠调用方猜缩放
    xs = [v.co.x for v in joined.data.vertices]
    ys = [v.co.y for v in joined.data.vertices]
    zs = [v.co.z for v in joined.data.vertices]
    width = max(xs) - min(xs)
    scale = (target_width / width) if (target_width and width) else 1.0

    centre = Vector(((max(xs) + min(xs)) / 2.0, (max(ys) + min(ys)) / 2.0, (max(zs) + min(zs)) / 2.0))
    for v in joined.data.vertices:
        v.co = (v.co - centre) * scale
    joined.data.update()
    joined.scale = (1.0, 1.0, 1.0)

    if any(offset):
        joined.location = Vector(joined.location) + Vector(offset)
    move_to(joined, col)
    return joined


def refine(
    obj: bpy.types.Object,
    *,
    subdivide: int = 0,
    smooth_iterations: int = 0,
    smooth_factor: float = 0.5,
) -> bpy.types.Object:
    """bmesh 级别的「代码雕刻」：细分 + 平滑。

    造型不够顺滑时用它收边，headless 下稳定可用（真雕刻笔刷在 headless 里 poll 不过）。
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for _ in range(subdivide):
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    for _ in range(smooth_iterations):
        bmesh.ops.smooth_vert(
            bm, verts=bm.verts[:], factor=smooth_factor,
            use_axis_x=True, use_axis_y=True, use_axis_z=True,
        )
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


def sculpt_filter(
    obj: bpy.types.Object,
    *,
    filter_type: str = "SMOOTH",
    iterations: int = 4,
    factor: float = 0.5,
) -> bpy.types.Object:
    """用雕刻的「滤镜」整体塑形 —— 这是 headless 下最接近真雕刻的一条路。

    filter_type 取值从 bpy.ops.sculpt.mesh_filter 的 RNA 里读，
    常见：SMOOTH / INFLATE / SHARPEN / RANDOM / RELAX。
    """
    if bpy.app.background:
        raise RuntimeError(
            "sculpt.mesh_filter 在 --background 下会 EXCEPTION_ACCESS_VIOLATION（已实测崩溃）。"
            "雕刻类操作只能走 Blender GUI + MCP 那条路。headless 请用 refine()/from_svg()。"
        )

    saved = bpy.context.view_layer.objects.active
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="SCULPT")
    result = None
    try:
        result = bpy.ops.sculpt.mesh_filter(
            type=filter_type, strength=factor, iteration_count=iterations,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[sculpt_filter] {filter_type} 失败：{type(exc).__name__}: {exc}")
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
        if saved:
            bpy.context.view_layer.objects.active = saved
    return obj
