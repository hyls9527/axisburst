"""零件注册表（脚手架，当前为空）。

新增零件：在 parts/ 下加一个模块，导出 ID / LABEL / ORDER / Z / build(col)，
再把模块名加进 PART_MODULES。没写完的模块会被自动跳过，方便一个一个来。

产品实例已下架，这里只剩脚手架：要开始新零件时把模块名登记进来即可。
"""

from importlib import import_module

PART_MODULES: list[str] = []


def load_parts():
    """返回按 ORDER 排序的、已经写好 build() 的零件模块。"""
    loaded = []
    for name in PART_MODULES:
        try:
            loaded.append(import_module(f"parts.{name}"))
        except ModuleNotFoundError:
            continue
    return sorted(loaded, key=lambda m: m.ORDER)


def by_id(part_id: str):
    for module in load_parts():
        if module.ID == part_id:
            return module
    raise KeyError(f"没有这个零件：{part_id}")
