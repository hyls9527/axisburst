# Design · mech-explode

## Style anchor
日本高达模型说明书（Bandai Gunpla instruction sheet）× 工程爆炸图（exploded assembly drawing）。
细线、零件编号、装配轴线、克制的高亮色。

## Palette
| Token | Hex | Use |
|---|---|---|
| bg | `#12151A` | 页面底 |
| panel | `#1A1F26` | 控件/侧栏 |
| line | `#C8D0DA` | 零件线稿 |
| muted | `#6B7785` | 次级文字/网格 |
| accent | `#FF6B2C` | 当前零件、播放头、强调 |
| cyan | `#5EC8FF` | 引出线（克制） |
| fill-dark | `#2A3140` | 零件暗面 |
| fill-mid | `#3D4A5C` | 零件中间面 |

## Typography
- UI / 标题：`Space Grotesk`, `Segoe UI`, sans-serif
- 技术标注：`IBM Plex Mono`, `Cascadia Code`, `Consolas`, monospace
- 标题 28–32px / 500；正文 14px；标注 11–12px mono 大写 + 字距

## Layout
- 全屏暗色舞台
- 左上：标题 + 零件清单
- 中央：SVG 装配体
- 底部：播放/进度/速度/拆装切换
- 装配轴：约 35° 等轴测斜向

## Signature moments
1. 零件按装配顺序依次飞出，带短促过冲（`out(3)` / spring）
2. 引出线 + 编号在对应零件停住时点亮

## Slide / asset notes
纯代码 SVG，无外部图片。
