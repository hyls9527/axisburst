"""部件（组件）注册表 —— 零件先组成部件，部件再组成总装。

每个部件模块导出：
    ID / PN / LABEL / LABEL_EN / ORDER / Z / PARTS / SUMMARY
其中 PARTS 是本部件包含的零件 id（按部件内装配顺序）。
零件还没写完的，构建时会被跳过并告警，方便一个一个补齐。
"""

from importlib import import_module

COMPONENT_MODULES = [
    "housing_unit",
    "rotary_unit",
    "cap_unit",
]


def load_components():
    loaded = []
    for name in COMPONENT_MODULES:
        try:
            loaded.append(import_module(f"components.{name}"))
        except ModuleNotFoundError:
            continue
    return sorted(loaded, key=lambda m: m.ORDER)


def by_id(component_id: str):
    for module in load_components():
        if module.ID == component_id:
            return module
    raise KeyError(f"没有这个部件：{component_id}")
