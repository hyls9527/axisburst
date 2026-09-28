# 造型控制力：社区做法与开源选型

问题：参数化脚本（`bmesh` 加减）只能做规整回转体，做不出倒角过渡、有机曲面、
以及"形状说不清"的机械件。以下是在 headless 下**实测**的行为 + 社区/开源界的通行做法。

## 一、Blender 自身在 headless 下的实测边界

| 手段 | 结论 | 证据 |
|---|---|---|
| 雕刻笔刷 `sculpt.brush_stroke` | 不可用 | `poll() failed, context is incorrect`（需要 3D 视口区域） |
| 雕刻滤镜 `sculpt.mesh_filter` | **会崩进程** | `EXCEPTION_ACCESS_VIOLATION`，转储在 `%TEMP%\blender.crash.txt` |
| bmesh 细分 + 平滑 | 可用 | 266 → 1058 顶点，稳定 |
| `import_curve.svg` → 实体 | 可用 | 导入直接得到 MESH，SOLIDIFY 加厚 |
| 几何节点 / 置换 / 体素重网格 / 元球 | 可用 | 类型与算子齐备 |

复现脚本：`blender/probe_capabilities.py`、`blender/probe_control.py`。

**推论：雕刻类操作只能走 Blender GUI + MCP 那条路（真视口在，poll 才过）。
headless 管线永远拿不到雕刻。**

社区侧印证：Blender StackExchange 只有「How to use sculpt mode tools in edit mode」
这种问题，说明雕刻在 Edit Mode / 脚本里没有等价物。

## 二、社区对"精确机械件"的实际答案：不在 Blender 里建模

StackExchange 上被顶得最高的相关条目，与我们的痛点逐条对应：

| 社区条目 | 对应我们的问题 |
|---|---|
| Extrude and bevel an imported svg curve（13 票） | SVG 轮廓 → 实体 → 倒角，是通行做法 |
| Remove extra points in export to SVG（6 票） | 就是我们把线稿导出后"线条又乱又多"的那个问题 |
| How to export fills on Freestyle SVG export?（8 票） | 线稿填充/线型控制 |
| Has anyone figured out a way to mitigate the slow down from Line Art modifiers?（4 票） | Line Art 的规模瓶颈 |

## 三、开源选型（按星标）

### 精确几何：用 code-CAD，而不是 Blender 的 mesh

| 项目 | ★ | 说明 |
|---|---|---|
| [CadQuery/cadquery](https://github.com/CadQuery/cadquery) | 5851 | 基于 OCCT 的参数化 CAD 脚本框架，真 B-rep、真倒角圆角、可导 STEP |
| [gumyr/build123d](https://github.com/gumyr/build123d) | 3226 | 同门更现代的 Python CAD 库，API 更顺手 |
| [partcad/partcad](https://github.com/partcad/partcad) | 498 | 模块化硬件的"包管理"，把零件/装配当依赖管 |
| [bernhard-42/vscode-ocp-cad-viewer](https://github.com/bernhard-42/vscode-ocp-cad-viewer) | 405 | VS Code 里看 CadQuery/build123d 模型 |
| [Irev-Dev/curated-code-cad](https://github.com/Irev-Dev/curated-code-cad) | 327 | code-CAD 项目总清单（选型从这里翻） |
| [Casys-AI/mcp-build123d](https://github.com/Casys-AI/mcp-build123d) | 6 | 把 build123d 包成 MCP，agent 直接写参数化 CAD |

**这是关键判断**：要"机械件该有的精确形状"，社区的做法是在 code-CAD 里建，再进 Blender
做风格化/线稿/动画。用 Blender 的 mesh 布尔去逼近 B-rep 是逆着工具走。

### Blender 内手工精确建模

| 项目 | ★ | 说明 |
|---|---|---|
| [hlorus/CAD_Sketcher](https://github.com/hlorus/CAD_Sketcher) | 3438 | 带约束的二维草图 → 拉伸/旋转/放样。Blender 里最接近"能控制"的做法 |

### 线稿与风格化

| 项目 | ★ | 说明 |
|---|---|---|
| [folkertdev/freestyle-svg-exporter](https://github.com/folkertdev/freestyle-svg-exporter) | 61 | Freestyle 线稿导出 SVG 的插件本体，Blender 5.2 的 `addons_core` 里已经没有它 |
| 项目内 `svgo` | — | 已装，负责导出的规范化与压缩 |

### 细节生成（greeble 等）

星标都不高（`DanielAskerov/Greeble-Tool` 2★、`sherrybai/greebles-generator` 8★），
目前的 `partkit.radial_ribs / knurl / annular_fins` 自写反而更可控，暂不引入。

## 四、建议的三段式管线

```
① 精确形状   code-CAD（build123d / CadQuery）
              ├─ 真倒角/圆角/螺纹/薄壁，尺寸可读、可参数化
              └─ 导出 STEP / STL / OBJ
                    ↓
② 风格化     Blender（headless 管线）
              ├─ 导入几何 → Line Art → 每零件一个图层
              └─ 导出分层 SVG
                    ↓
③ 清理+动效  svgo 规范化 → anime.js v4 时序
```

「说不清形状」的件（有机过渡、手感推拉）才开 Blender GUI + MCP 手工雕刻，
做完导回同一套管线。

## 五、待验证（不要当结论用）

- `CAD_Sketcher` 是否兼容 Blender 5.2（仓库 README 以 4.x 为主），需实测。
- `freestyle-svg-exporter` 是老插件，5.x 的 API 改动可能导致不可用；若要，
  优先用 Blender 扩展平台上的版本。

## 六、已验证：code-CAD 这条路在本机跑得通

```
uv tool run --from build123d python -c "..."
→ BUILD123D_OK 0.13.0   (uv 自动选用 Python 3.12.14)
→ CAD_OK volume=12386.0 faces=20 bytes=877284   （带 R3 竖边倒角 + Ø12 通孔 + R1 孔口倒角，导出 STL）
```

要点：

- `uv` 会**自己挑一个装得上的 Python**（本机系统 Python 是 3.14，OCCT 没有 3.14 轮子，
  uv 自动落到 3.12），所以既不用改系统 Python，也不用手工建虚拟环境。
- 真 B-rep：倒角、圆角、通孔都是一等公民，`body.volume` / `len(body.faces())` 可直接断言，
  **几何质量可以写测试**——这是 mesh 布尔做不到的。
- 产物：`blender/out/probe/cad_demo.stl`

结论：**① 精确形状这一段，改用 build123d，不再用 bmesh 硬凑。**
