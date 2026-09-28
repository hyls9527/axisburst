# AxisBurst（轴爆）

机械零件 SVG 爆炸分解时序动画，基于 **anime.js v4**。

## 看什么

- 等轴测线稿装配体（座体 / 轴承 / 齿轮 / 轴 / 端盖 / 螺栓）
- 按装配约束顺序依次飞出的时序爆炸
- 引出线 + 零件编号随停顿点亮
- 可播放 / 暂停 / 反向装配 / 拖动进度 / 调速

## 运行

### 方式 A · 零构建（当前默认）

`index.html` 通过 import map 从 jsDelivr 加载 anime.js v4（需联网）。在 MiMo Desktop 预览，或任意静态服务器打开根目录。

`vendor/anime.js` 预留为离线本地副本入口；npm 安装后可把 import map 指回 `./vendor/anime.js` 或 `node_modules/animejs`。

### 方式 B · Vite（本地依赖）

```bash
npm install
npm run dev
```

## 结构

```
mech-explode/
  index.html      # 舞台与控件
  styles.css      # 工程图纸风视觉
  main.js         # 零件 SVG + anime.js 时序
  vendor/anime.js # anime.js v4 本地副本
  DESIGN.md       # 设计规范
  package.json
```

## 时序参数

| 项 | 值 |
|---|---|
| 总时长 | 4.0s |
| 起始静置 | 280ms |
| 零件间隔 | 380ms |
| 单件位移 | 720ms · `out(3)` |
| 零件数 | 7（含 4 螺栓组） |

## API 用法（anime.js v4）

```js
import { createTimeline, animate, utils } from './vendor/anime.js';

const tl = createTimeline({ autoplay: false, defaults: { ease: 'out(3)' } });
tl.add('.part[data-id="shaft"]', { x: 52 * 2.8, y: -70 * 2.8 }, 280);
```

与 v3 不同：入口为 `createTimeline()`，链式 `.add(target, params, position)`。
