"""零件 / 部件 / 总装 三级清单。

每建完一个东西就往 out/ 写一份自己的 json；最后扫描汇总，按 ORDER 排序。
清单里同时有「设计参数」（模块声明的意图）和「实测尺寸」（从几何量出来的包围盒），
两者不一致时一眼能看出来，比只写一份更可信。
"""

from __future__ import annotations

import glob
import json
import os


def _write(path: str, payload: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def part_record(module, *, size=None, bbox=None, strokes=None, points=None) -> dict:
    return {
        "kind": "part",
        "id": module.ID,
        "pn": module.PN,
        "label": module.LABEL,
        "labelEn": module.LABEL_EN,
        "component": module.GROUP,
        "order": module.ORDER,
        "qty": module.QTY,
        "z": module.Z,
        "material": module.MATERIAL,
        "process": module.PROCESS,
        "params": [{"k": k, "v": v} for k, v in module.PARAMS],
        "measured": {
            "bbox": bbox,
            "size": size,
            "strokes": strokes,
            "points": points,
        },
    }


def component_record(module, parts: list[dict]) -> dict:
    return {
        "kind": "component",
        "id": module.ID,
        "pn": module.PN,
        "label": module.LABEL,
        "labelEn": module.LABEL_EN,
        "order": module.ORDER,
        "z": module.Z,
        "summary": module.SUMMARY,
        "parts": [p["id"] for p in parts],
    }


def write_record(path: str, record: dict) -> None:
    _write(path, record)


def collect(out_dir: str, pattern: str, out_path: str, header: dict) -> dict:
    """把散落的单件 json 汇总成一份排序后的清单。"""
    records = []
    for path in glob.glob(os.path.join(out_dir, pattern)):
        with open(path, encoding="utf-8") as handle:
            records.append(json.load(handle))
    records.sort(key=lambda r: (r.get("order", 0), r.get("id", "")))

    payload = dict(header)
    payload["count"] = len(records)
    payload["items"] = records
    _write(out_path, payload)
    return payload


def table(records: list[dict]) -> str:
    lines = []
    for r in records:
        params = "  ".join(f"{p['k']}={p['v']}" for p in r.get("params", [])[:3])
        lines.append(
            f"  {r['order']:>2}  {r['pn']:<8} {r['label']:<10} ×{r['qty']:<2} "
            f"Z={r['z']:>6}  {params}"
        )
    return "\n".join(lines)
