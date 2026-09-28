"""探测 Blender 在 headless（--background）下还有哪些建模控制手段可用。

结论会写进 AGENTS.md。这里只测「能不能用」，不做造型。
"""

from __future__ import annotations

import os
import tempfile

import bpy


def report(name, ok, detail=""):
    print(f"[probe] {name:<28} {'OK  ' if ok else 'FAIL'} {detail}")


bpy.ops.wm.read_factory_settings(use_empty=True)

# ---------------------------------------------------------------- 1 雕刻
sculpt_ops = [o for o in dir(bpy.ops.sculpt) if not o.startswith("_")]
report("sculpt 算子存在", bool(sculpt_ops), f"{len(sculpt_ops)} 个，如 {sculpt_ops[:4]}")

bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1.0)
obj = bpy.context.object
bpy.context.view_layer.objects.active = obj

sculpt_ok = False
detail = ""
try:
    bpy.ops.object.mode_set(mode="SCULPT")
    brush = bpy.data.brushes.new("probe_brush", mode="SCULPT")
    brush.sculpt_tool = "DRAW"
    obj.data.use_paint_mask = False
    # 试着画一笔（headless 下通常因为没有 region/3D 视图而失败）
    res = bpy.ops.sculpt.brush_stroke(stroke=[{"name": "p", "location": (0.0, 0.0, 1.2), "pressure": 1.0}])
    sculpt_ok = "FINISHED" in res
    detail = str(res)
except Exception as exc:  # noqa: BLE001
    detail = f"{type(exc).__name__}: {exc}"
finally:
    try:
        bpy.ops.object.mode_set(mode="OBJECT")
    except Exception:  # noqa: BLE001
        pass
report("sculpt.brush_stroke 可调用", sculpt_ok, detail)

# ---------------------------------------------------------------- 2 bmesh 平滑 / 细分
import bmesh  # noqa: E402

bm = bmesh.new()
bm.from_mesh(obj.data)
before = len(bm.verts)
bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
bmesh.ops.smooth_vert(bm, verts=bm.verts[:], factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
after = len(bm.verts)
report("bmesh 细分+平滑", after > before, f"{before} → {after} 顶点")
bm.free()

# ---------------------------------------------------------------- 3 SVG 曲线导入
svg = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <path d="M10,90 L10,40 C10,20 30,10 50,10 C70,10 90,20 90,40 L90,90 Z"
        fill="none" stroke="#000"/>
</svg>
"""
tmp = os.path.join(tempfile.gettempdir(), "probe_shape.svg")
with open(tmp, "w", encoding="utf-8") as fh:
    fh.write(svg)

svg_ok = False
detail = ""
try:
    res = bpy.ops.import_curve.svg(filepath=tmp)
    imported = [o for o in bpy.context.selected_objects]
    svg_ok = "FINISHED" in res and bool(imported)
    kinds = {o.type for o in imported}
    detail = f"{res}, 得到 {[o.type for o in imported]}"
except Exception as exc:  # noqa: BLE001
    detail = f"{type(exc).__name__}: {exc}"
report("import_curve.svg", svg_ok, detail)

# 曲线 → 实体
if svg_ok:
    curve_obj = next((o for o in bpy.context.selected_objects if o.type == "CURVE"), None)
    if curve_obj:
        curve_obj.data.extrude = 0.25
        bpy.context.view_layer.objects.active = curve_obj
        curve_obj.select_set(True)
        try:
            bpy.ops.object.convert(target="MESH")
            mesh = bpy.context.object
            report("曲线 → 实体", mesh.type == "MESH", f"{len(mesh.data.vertices)} 顶点")
        except Exception as exc:  # noqa: BLE001
            report("曲线 → 实体", False, f"{type(exc).__name__}: {exc}")

# ---------------------------------------------------------------- 4 其它控制手段
report("曲线倒角/扫掠", hasattr(bpy.types.Curve, "bevel_object"))
report("几何节点", hasattr(bpy.types, "NodesModifier") or hasattr(bpy.types, "GeometryNodeTree"))
report("置换修改器", "DISPLACE" in {i.identifier for i in bpy.types.Modifier.bl_rna.properties["type"].enum_items})
report("重置点云(Metaball)", hasattr(bpy.types, "MetaBall"))
report("网格转体素重网格", "REMESH" in {i.identifier for i in bpy.types.Modifier.bl_rna.properties["type"].enum_items})
report("图像作为建模参考", hasattr(bpy.types, "Image"))

print("[probe] done")
