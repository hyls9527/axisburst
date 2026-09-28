#!/usr/bin/env node
/**
 * 把 Blender 导出的线稿 SVG 规范化成前端可直接用的分层 SVG。
 *
 * 输入：blender/out/axisburst_lineart.svg + blender/out/axisburst_parts.json
 * 输出：assets/axisburst.svg（干净分层，零件 = <g class="part" data-part="...">）
 *       assets/parts.json（每个零件的 bbox / 中心 / 爆炸位移量）
 *
 * 为什么要这一步：
 *   1. Blender 的导出带一堆 uuid 包装层、每条 path 各自一个 stroke-width（0.14~0.16 不等）；
 *   2. 爆炸位移量原本写死在前端，改模型就对不上 —— 这里从 SVG 几何反算，模型改了自动跟。
 *
 * 用法：node tools/normalize-svg.mjs
 */

import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { optimize } from 'svgo';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');

// 默认处理四季山河；换产品用 --svg/--meta/--out/--out-parts 覆盖
const argv = process.argv.slice(2);
const opt = (name, fallback) => {
  const hit = argv.find((a) => a.startsWith(`--${name}=`));
  return hit ? hit.split('=').slice(1).join('=') : fallback;
};
const SRC_SVG = resolve(ROOT, opt('svg', 'blender/out/sishan/sishan_lineart.svg'));
const SRC_META = resolve(ROOT, opt('meta', 'blender/out/sishan/axisburst_parts.json'));
const OUT_SVG = resolve(ROOT, opt('out', 'assets/sishan.svg'));
const OUT_PARTS = resolve(ROOT, opt('out-parts', 'assets/sishan-parts.json'));
/** 短于「viewBox 宽 × 此比例」的笔画直接丢弃 —— 减面网格会留下大量碎点 */
const MIN_STROKE_RATIO = Number(opt('min-stroke', '0.0038'));

/** 线宽相对 viewBox 宽度取值：看板宽 1000px 时约 2px */
const STROKE_RATIO = 1 / 420;
/** 画面倾斜：把装配轴在画布里放斜，对齐参考图的斜向构图（Blender 侧不滚转） */
// 画面倾斜：机械件(AxisBurst)要放斜，山水件本身正立 —— 按产品传参，默认不转
const TILT_DEG = Number(opt('tilt', '0'));
/** 爆炸倍率：1 = 零件只散开到真实轴向间距，>1 更夸张 */
const SPREAD = 1.5;
/** 个别零件的手工修正（世界轴向 t 偏移 / 垂直轴线的额外位移，单位是 viewBox 单位） */
const PART_TWEAKS = {
  bolts: { tBias: 0.42, perp: 16 },
};

// ---------------------------------------------------------------- 解析

function readLayerGroups(svgText) {
  const groups = [];
  const layerRe = /<g id="layer\.([^.]+)\.[^"]*">([\s\S]*?)<\/g>/g;
  let match;
  while ((match = layerRe.exec(svgText)) !== null) {
    const [, id, body] = match;
    const paths = [...body.matchAll(/<path\b[^>]*\bd="([^"]+)"/g)].map((m) => m[1]);
    if (paths.length) groups.push({ id, paths });
  }
  return groups;
}

function bboxOfPaths(paths) {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const d of paths) {
    for (const [, x, y] of d.matchAll(/([-\d.]+),([-\d.]+)/g)) {
      const px = Number(x);
      const py = Number(y);
      if (px < minX) minX = px;
      if (px > maxX) maxX = px;
      if (py < minY) minY = py;
      if (py > maxY) maxY = py;
    }
  }
  return { minX, minY, maxX, maxY, cx: (minX + maxX) / 2, cy: (minY + maxY) / 2 };
}

const round = (n, p = 2) => Number(n.toFixed(p));

/** 把 path 里的坐标点整体绕 (cx, cy) 旋转 —— SVG 里正角度是顺时针（y 轴向下） */
function rotatePathData(d, deg, cx, cy) {
  const rad = (deg * Math.PI) / 180;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  return d.replace(/([-\d.]+),([-\d.]+)/g, (_, rawX, rawY) => {
    const x = Number(rawX) - cx;
    const y = Number(rawY) - cy;
    return `${(x * cos - y * sin + cx).toFixed(2)},${(x * sin + y * cos + cy).toFixed(2)}`;
  });
}

// ---------------------------------------------------------------- 主流程

const svgText = readFileSync(SRC_SVG, 'utf8');
const meta = JSON.parse(readFileSync(SRC_META, 'utf8'));

const rawGroups = readLayerGroups(svgText);
if (!rawGroups.length) throw new Error('没解析到任何 layer.* 分组，检查 Blender 导出');

// 先量原始范围，再整体倾斜，之后所有几何量都在倾斜后的坐标系里算
const rawBounds = rawGroups.reduce(
  (acc, g) => {
    const b = bboxOfPaths(g.paths);
    return {
      minX: Math.min(acc.minX, b.minX),
      minY: Math.min(acc.minY, b.minY),
      maxX: Math.max(acc.maxX, b.maxX),
      maxY: Math.max(acc.maxY, b.maxY),
    };
  },
  { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity }
);
const pivot = { x: (rawBounds.minX + rawBounds.maxX) / 2, y: (rawBounds.minY + rawBounds.maxY) / 2 };

const groups = rawGroups.map(({ id, paths }) => ({
  id,
  paths: paths.map((d) => rotatePathData(d, TILT_DEG, pivot.x, pivot.y)),
}));

// 丢掉碎点：减面后的有机网格会留下大量极短笔画，画出来是一片噪点
const minStroke = (rawBounds.maxX - rawBounds.minX) * MIN_STROKE_RATIO;
let droppedStrokes = 0;
const keptGroups = groups.map(({ id, paths }) => {
  const kept = paths.filter((d) => {
    const b = bboxOfPaths([d]);
    const len = Math.hypot(b.maxX - b.minX, b.maxY - b.minY);
    if (len < minStroke) {
      droppedStrokes += 1;
      return false;
    }
    return true;
  });
  return { id, paths: kept };
});

// 补齐 bbox，并按 Blender 给的装配次序排序
const parts = keptGroups
  .map(({ id, paths }) => {
    const info = meta.parts[id];
    if (!info) throw new Error(`SVG 里的图层 ${id} 在 axisburst_parts.json 里没有对应零件`);
    return { id, paths, ...bboxOfPaths(paths), order: info.order, label: info.label, t: info.axis_t };
  })
  .filter((p) => p.paths.length > 0)
  .sort((a, b) => a.order - b.order);

// 装配轴：用轴向 t 最小 / 最大的两个零件中心连线，得出 SVG 空间里的轴方向
const byT = [...parts].sort((a, b) => a.t - b.t);
const bottom = byT[0];
const top = byT.at(-1);
const rawAxis = { x: top.cx - bottom.cx, y: top.cy - bottom.cy };
const axisLen = Math.hypot(rawAxis.x, rawAxis.y);
const axis = { x: rawAxis.x / axisLen, y: rawAxis.y / axisLen };
const perp = { x: -axis.y, y: axis.x };

// SVG 单位 / 世界单位（沿装配轴）
const unitsPerWorld = axisLen / (top.t - bottom.t);
const tMean = parts.reduce((sum, p) => sum + p.t, 0) / parts.length;

// 整体范围
const bounds = parts.reduce(
  (acc, p) => ({
    minX: Math.min(acc.minX, p.minX),
    minY: Math.min(acc.minY, p.minY),
    maxX: Math.max(acc.maxX, p.maxX),
    maxY: Math.max(acc.maxY, p.maxY),
  }),
  { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity }
);
const vbW = bounds.maxX - bounds.minX;
const vbH = bounds.maxY - bounds.minY;
const strokeWidth = round(vbW * STROKE_RATIO, 3);

// 每个零件的爆炸位移量
const outParts = parts.map((p) => {
  const tweak = PART_TWEAKS[p.id] ?? {};
  const t = p.t + (tweak.tBias ?? 0);
  const along = (t - tMean) * unitsPerWorld * SPREAD;
  const extra = tweak.perp ?? 0;
  return {
    id: p.id,
    label: p.label,
    order: p.order,
    t: round(p.t, 4),
    center: [round(p.cx), round(p.cy)],
    bbox: [round(p.minX), round(p.minY), round(p.maxX - p.minX), round(p.maxY - p.minY)],
    explode: [
      round(axis.x * along + perp.x * extra),
      round(axis.y * along + perp.y * extra),
    ],
  };
});

// ---------------------------------------------------------------- 重建 SVG

const comments = outParts
  .map((p) => `  ${p.label} → 爆炸位移 (${p.explode[0]}, ${p.explode[1]})`)
  .join('\n');

const body = parts
  .map((p) => {
    const paths = p.paths.map((d) => `      <path d="${d}"/>`).join('\n');
    return `    <g class="part" id="part-${p.id}" data-part="${p.id}" data-order="${p.order}">\n${paths}\n    </g>`;
  })
  .join('\n');

const assembled = `<?xml version="1.0" encoding="UTF-8"?>
<!-- AxisBurst · 由 tools/normalize-svg.mjs 从 Blender 线稿重建
${comments}
-->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="${round(bounds.minX)} ${round(bounds.minY)} ${round(vbW)} ${round(vbH)}" fill="none" stroke="#111111" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round">
  <g id="assembly">
${body}
  </g>
</svg>
`;

const { data: normalized } = optimize(assembled, {
  multipass: true,
  plugins: [
    {
      name: 'preset-default',
      params: {
        overrides: {
          // 分组和 id 是这套动画的骨架，一律不许动
          collapseGroups: false,
          mergePaths: false,
          cleanupIds: false,
          convertShapeToPath: false,
        },
      },
    },
  ],
});

mkdirSync(dirname(OUT_SVG), { recursive: true });
writeFileSync(OUT_SVG, normalized, 'utf8');
writeFileSync(
  OUT_PARTS,
  JSON.stringify(
    {
      viewBox: [round(bounds.minX), round(bounds.minY), round(vbW), round(vbH)],
      strokeWidth,
      axis: [round(axis.x, 4), round(axis.y, 4)],
      spread: SPREAD,
      parts: outParts,
    },
    null,
    2
  ),
  'utf8'
);

console.log(`[normalize] ${parts.length} 个零件图层（丢弃碎点 ${droppedStrokes} 条）`);
console.log(`[normalize] viewBox ${round(vbW)}×${round(vbH)}  stroke-width ${strokeWidth}`);
console.log(`[normalize] axis (${round(axis.x, 3)}, ${round(axis.y, 3)})  ${round(unitsPerWorld, 2)} svg单位/世界单位`);
for (const p of outParts) {
  console.log(`[normalize]   ${p.id.padEnd(15)} t=${String(p.t).padStart(7)}  位移 (${String(p.explode[0]).padStart(7)}, ${String(p.explode[1]).padStart(7)})`);
}
console.log(`[normalize] 写出 ${OUT_SVG}`);
console.log(`[normalize] 写出 ${OUT_PARTS}`);
