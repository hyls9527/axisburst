# AxisBurst · 线稿工作台

机械零件**分层线稿 SVG**爆炸分解动画的可复用工作台：技能 + Blender 管线 + 工具链。

两个产品实例（轴爆装配体 / 四季山河摆件）已清空，仓库只剩机器。
删掉的内容都在 tag `pre-cleanup-20260929` 里：`git checkout pre-cleanup-20260929 -- <路径>` 可取回。

## 里面有什么

```
.agents/skills/      技能真源（.claude/skills、.workbuddy/skills 是指向它的 junction）
AGENTS.md            工作台说明：技能表 / MCP / 管线 / 踩过的坑
blender/             headless 管线：零件 → 部件 → 总装 → 分层线稿 SVG
  render_kit.py       场景 / 相机 / Line Art / SVG 导出（公共层）
  partkit.py          建模积木（bmesh 加减）
  builder.py          装配落位（Z 轴 = 装配轴）
  manifest.py         零件 / 部件 / 总装 三级清单
  from_cad.py         CAD 网格 → 线稿管线
  parts/ components/  零件 / 部件注册表（当前为空）
  probe_*.py          能力实测脚本（headless 下什么能跑、什么会崩）
  CONTROL.md          headless 造型能力的实测边界与开源选型
tools/               工具链：构建编排 / SVG 规范化 / 无头预览 / 静态服务 / 活动 Blender 通道
```

## 跑

```bash
npm run build                 # 全管线
node tools/build.mjs --list   # 看有哪些段
npm run dev                   # 静态服务器 http://127.0.0.1:5178
```

```bash
node tools/normalize-svg.mjs               # 总装线稿 → 前端用的分层 SVG
node tools/preview-svg.mjs <svg> <png>     # 无头浏览器渲染 SVG，人工核对
```

## 依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| `animejs` | ^4.2.2 | 前端时序动画 |
| `svgo` | ^4.1.0 | 导出 SVG 的规范化 / 压缩 / 统一线宽 |
| Blender | 5.2.2 LTS | headless 建模与线稿（路径见 AGENTS.md） |
| `uv` | — | `uv tool run --from build123d python` 跑 code-CAD |

## anime.js v4 速记

```js
import { createTimeline } from './vendor/anime.js';

const tl = createTimeline({ autoplay: false, defaults: { ease: 'out(3)' } });
tl.add('.part[data-id="shaft"]', { x: 145, y: -196 }, 280);
```

v4 的入口是 `createTimeline()`，链式 `.add(target, params, position)`；v3 的 `anime.timeline()` 不再用。
