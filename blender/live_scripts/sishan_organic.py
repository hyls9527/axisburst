"""SS-02/03/04/06/07/09/11/12 —— 8 个有机件，在活动 Blender 里一次生成。
工作尺度 1 单位 = 100 mm。全部导出 OBJ，随后走 blender/from_cad.py 出线稿。
"""
import math
import os
import random

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

OUT = r"C:\Users\Administrator\workspace\axisburst\blender\out\live"
os.makedirs(OUT, exist_ok=True)
random.seed(20260929)


def log(*a):
    print("ORGANIC", *a)


def clear():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)


def mesh_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def displace(ob, amp, freq, zmin=0.0):
    for v in ob.data.vertices:
        x, y, z = v.co
        if z <= zmin:
            continue
        d = noise.turbulence(Vector((x * freq, y * freq, 11.0)), 4, False) - 0.5
        d2 = noise.turbulence(Vector((x * freq * 3.1, y * freq * 3.1, 41.0)), 2, False) - 0.5
        v.co.z += (d * amp + d2 * amp * 0.35)


def export(ob, name):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    path = os.path.join(OUT, name + ".obj")
    bpy.ops.wm.obj_export(filepath=path, export_selected_objects=True)
    return path


def cyl(bm, p0, p1, r, seg=10):
    d = Vector(p1) - Vector(p0)
    length = d.length
    if length < 1e-5:
        return
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                                radius1=r, radius2=r * 0.86, depth=length)
    quat = d.normalized().to_track_quat("Z", "Y")
    mat = Matrix.Translation((Vector(p0) + Vector(p1)) / 2) @ quat.to_matrix().to_4x4()
    for v in res["verts"]:
        v.co = mat @ v.co


def blob(bm, c, r, seg=12):
    res = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(6, seg // 2), radius=r)
    for v in res["verts"]:
        v.co += Vector(c)


def branch(bm, p, direction, length, radius, depth, rng, up=0.55, spread=0.75):
    if depth <= 0 or length < 0.02:
        return []
    end = Vector(p) + Vector(direction).normalized() * length
    cyl(bm, p, end, radius)
    tips = [end]
    for _ in range(2 if depth > 1 else 1):
        nd = Vector(direction).normalized() + Vector((
            rng.uniform(-spread, spread), rng.uniform(-spread, spread), up))
        tips += branch(bm, end, nd, length * rng.uniform(0.55, 0.78),
                       radius * 0.66, depth - 1, rng, up, spread)
    return tips


# ---------------------------------------------------------------- 各件

def ss02_pond():
    bm = bmesh.new()
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=48,
                                radius1=1.05, radius2=1.05, depth=0.12)
    for v in res["verts"]:
        v.co.z += 0.06
    # 荷叶
    for i in range(9):
        a = i / 9 * math.tau + 0.3
        r = 0.30 + (i % 3) * 0.24
        c = (math.cos(a) * r, math.sin(a) * r * 0.62, 0.135)
        leaf = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=20,
                                     radius1=0.105, radius2=0.095, depth=0.022)
        for v in leaf["verts"]:
            v.co.y *= 0.82
            v.co += Vector(c)
    # 花苞
    for i in range(3):
        a = i / 3 * math.tau + 1.1
        c = (math.cos(a) * 0.62, math.sin(a) * 0.40, 0.19)
        bud = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=14,
                                    radius1=0.05, radius2=0.012, depth=0.15)
        for v in bud["verts"]:
            v.co += Vector(c)
    return mesh_obj("SS02_hetang", bm)


def ss03_waterfall():
    bm = bmesh.new()
    rows, cols = 26, 9
    grid = []
    for i in range(rows):
        t = i / (rows - 1)
        z = 1.70 - t * 1.62
        curve = 0.20 * math.sin(t * math.pi * 0.9)
        w = 0.26 * (1.0 - 0.35 * t)
        row = []
        for j in range(cols):
            u = j / (cols - 1) - 0.5
            row.append(bm.verts.new((u * 2 * w + 0.05 * curve, curve * 1.5 + 0.02 * math.sin(u * 9),
                                     z + 0.03 * math.sin(u * 12 + t * 6))))
        grid.append(row)
    for i in range(rows - 1):
        for j in range(cols - 1):
            bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = mesh_obj("SS03_pubu", bm)
    m = ob.modifiers.new("s", "SOLIDIFY")
    m.thickness = 0.035
    m.offset = 0.0
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=m.name)
    for v in ob.data.vertices:
        v.co.y += noise.turbulence(Vector((v.co.x * 6, v.co.z * 4, 3.0)), 3, False) * 0.03
    return ob


def ss04_stream():
    bm = bmesh.new()
    rows, cols = 40, 7
    grid = []
    for i in range(rows):
        t = i / (rows - 1)
        x = -2.10 + t * 4.20
        y = 0.55 * math.sin(t * math.pi * 1.6)
        w = 0.14 + 0.10 * math.sin(t * math.pi)
        row = []
        for j in range(cols):
            u = j / (cols - 1) - 0.5
            row.append(bm.verts.new((x, y + u * 2 * w, 0.02 + 0.02 * math.sin(t * 26 + u * 5))))
        grid.append(row)
    for i in range(rows - 1):
        for j in range(cols - 1):
            bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = mesh_obj("SS04_liushui", bm)
    m = ob.modifiers.new("s", "SOLIDIFY")
    m.thickness = 0.04
    m.offset = 0.0
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=m.name)
    return ob


def ss06_bamboo():
    bm = bmesh.new()
    for i in range(15):
        a = i / 15 * math.tau
        r = 0.30 + (i % 4) * 0.42
        x, y = math.cos(a) * r, math.sin(a) * r * 0.55
        h = 0.85 + (i % 5) * 0.16
        tilt = 0.04 * ((i % 3) - 1)
        top = Vector((x + tilt, y + tilt * 0.6, h))
        cyl(bm, (x, y, 0.0), top, 0.026 + (i % 3) * 0.004, seg=8)
        for k in range(int(h / 0.22)):
            z = 0.12 + k * 0.22
            f = z / h
            px = x + tilt * f
            py = y + tilt * 0.6 * f
            ring = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=8,
                                         radius1=0.036, radius2=0.036, depth=0.018)
            for v in ring["verts"]:
                v.co += Vector((px, py, z))
    return mesh_obj("SS06_zhulin", bm)


def make_tree(name, height, depth, radius, leaf_r, leaf_count, hue):
    bm = bmesh.new()
    rng = random.Random(1000 + depth)
    tips = branch(bm, (0, 0, 0), (0, 0, 1), height, radius, depth, rng)
    for tip in tips:
        for _ in range(leaf_count):
            off = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.4, 1.0)))
            blob(bm, tip + off * leaf_r * 0.8, leaf_r * rng.uniform(0.6, 1.15), seg=8)
    return mesh_obj(name, bm)


def ss11_pine():
    bm = bmesh.new()
    cyl(bm, (0, 0, 0), (0.03, 0.02, 0.70), 0.055, seg=10)
    for i in range(4):
        z = 0.42 + i * 0.26
        r = 0.46 - i * 0.09
        res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=18,
                                    radius1=r, radius2=0.02, depth=0.26)
        for v in res["verts"]:
            v.co.x = v.co.x * 1.0 + 0.03 * (i % 2)
            v.co += Vector((0.02 * i, 0.01 * i, z))
        # 每层挑出枝：光滑锥面几乎没有转折线，加枝条才有线稿
        rng = random.Random(700 + i)
        for k in range(9):
            a = k / 9 * math.tau + i * 0.35
            x0, y0 = 0.04 * math.cos(a), 0.04 * math.sin(a)
            x1 = math.cos(a) * (r * 0.94)
            y1 = math.sin(a) * (r * 0.94)
            z1 = z + 0.24 - rng.uniform(0.02, 0.07) - 0.10
            cyl(bm, (x0, y0, z + 0.06), (x1, y1, z1), 0.016, seg=6)
    return mesh_obj("SS11_hansong", bm)


def ss12_peak():
    nx, ny = 96, 62
    bm = bmesh.new()
    verts = {}
    for i in range(nx):
        for j in range(ny):
            x = (i / (nx - 1) - 0.5) * 3.4
            y = (j / (ny - 1) - 0.5) * 2.3
            d = math.hypot(x / 1.5, y / 1.05)
            h = 0.0
            if d < 1.0:
                h = 2.05 * (0.5 + 0.5 * math.cos(math.pi * min(1.0, d))) ** 1.25
            verts[(i, j)] = bm.verts.new((x, y, h))
    for i in range(nx - 1):
        for j in range(ny - 1):
            bm.faces.new((verts[(i, j)], verts[(i + 1, j)], verts[(i + 1, j + 1)], verts[(i, j + 1)]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = mesh_obj("SS12_xueshan", bm)
    displace(ob, 0.36, 0.85)
    m = ob.modifiers.new("s", "SOLIDIFY")
    m.thickness = 0.60
    m.offset = -1.0
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=m.name)
    for v in ob.data.vertices:
        if v.co.z > 0.02:
            v.co.z += (noise.turbulence(Vector((v.co.x * 2.6, v.co.y * 2.6, 31.0)), 3, False) - 0.5) * 0.18
    return ob


# ---------------------------------------------------------------- 主流程

clear()
log("开始，场景物体 =", len(bpy.data.objects))

builders = [
    ("SS02_hetang", ss02_pond),
    ("SS03_pubu", ss03_waterfall),
    ("SS04_liushui", ss04_stream),
    ("SS06_zhulin", ss06_bamboo),
    ("SS07_taoshu", lambda: make_tree("SS07_taoshu", 0.55, 4, 0.045, 0.052, 4, 0)),
    ("SS09_fengshu", lambda: make_tree("SS09_fengshu", 0.72, 4, 0.055, 0.070, 5, 1)),
    ("SS11_hansong", ss11_pine),
    ("SS12_xueshan", ss12_peak),
]

for name, fn in builders:
    try:
        ob = fn()
        bb = ob.dimensions
        export(ob, name)
        log(name, "顶点", len(ob.data.vertices), "面", len(ob.data.polygons),
            "尺寸mm", [round(v * 100) for v in bb])
    except Exception as exc:
        log(name, "失败", type(exc).__name__, exc)

log("完成，场景物体 =", len(bpy.data.objects))
