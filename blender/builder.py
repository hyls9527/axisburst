"""AxisBurst · 组装器

零件在自己坐标系里建模，`Z` 是它在所属部件中的落位基准。
部件有自己在总装里的 `Z`。最终每个零件的轴向偏移 = 部件 Z + 零件 Z。

这里只负责「把几何摆到位」，线稿和渲染交给 render_kit。
"""

from __future__ import annotations

import bpy

import partkit as kit
import parts as parts_registry


class Built:
    def __init__(self, module, collection, parts):
        self.module = module
        self.collection = collection
        self.parts = parts          # [(part_module, part_collection), ...]


def _part_lookup():
    return {m.ID: m for m in parts_registry.load_parts()}


def build_component(component_module) -> Built:
    lookup = _part_lookup()
    root = kit.new_collection("C_" + component_module.ID)
    built_parts = []
    missing = []

    for part_id in component_module.PARTS:
        module = lookup.get(part_id)
        if module is None:
            missing.append(part_id)
            continue

        col = kit.new_collection("P_" + module.ID)
        root.children.link(col)
        module.build(col)

        dz = component_module.Z + module.Z
        if dz:
            for obj in col.objects:
                obj.location.z += dz

        built_parts.append((module, col))

    if missing:
        print(f"[warn] 部件 {component_module.ID} 缺零件：{', '.join(missing)}")

    return Built(component_module, root, built_parts)


def build_assembly(component_modules) -> list[Built]:
    return [build_component(c) for c in component_modules]


def mesh_objects(built: Built):
    return [o for _m, col in built.parts for o in col.objects if o.type == "MESH"]


def all_mesh_objects(builts: list[Built]):
    return [o for b in builts for o in mesh_objects(b)]
