# AxisBurst · Agent 工作台

机械零件**分层线稿 SVG**爆炸分解（anime.js v4 时序）的**可复用工作台**。
目标视觉：工程爆炸图 / 模型说明书线稿 —— 对齐 animejs.com v4 首屏那类「细线稿 + 等宽标注 + 装配时序」。

> **当前状态：空工作台。** 两个产品实例（轴爆装配体 / 四季山河摆件）已清空，
> 仓库只留**技能 + 线稿管线 + 工具链 + 文档**。
> 删掉的内容都在 tag `pre-cleanup-20260929` 里：`git checkout pre-cleanup-20260929 -- <路径>` 可取回。
> 起新产品的入口见下面「管线」一节末尾。

## 项目级技能（所有 agent 通用）

技能放在 **`.agents/skills/<技能名>/SKILL.md`**（公共入口）。任何 agent 进入本项目即可发现并使用，不依赖全局安装。

各宿主入口都是指向公共入口的 **junction**，同一份文件、改一处全都生效：

| 入口 | 服务的 agent | 状态 |
|---|---|---|
| `.agents/skills` | Codex / Cursor / Gemini CLI / Copilot / OpenCode / Roo / OpenHands …（公共入口，真源） | 真源 |
| `.claude/skills` | Claude Code | junction → `.agents/skills` |
| `.workbuddy/skills` | WorkBuddy | junction → `.agents/skills` |

本机只装了这几个宿主；新宿主就绪后按同样方式加 junction（宿主主目录不存在时不预先创建）。

| 技能 | 干什么 | 来源 | ★ |
|---|---|---|---|
| `animejs-skills` | anime.js **v4** 专项：timeline / stagger / spring / SVG 线稿动画 | [BowTiedSwan/animejs-skills](https://github.com/BowTiedSwan/animejs-skills) | 48 |
| `taste-skill` | 前端设计口味（反模板化 UI），`name: design-taste-frontend` | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | 90.9k |
| `image-to-code` | 参考图 → 代码：先自生成设计图再深读实现 | 同上仓库 | 90.9k |
| `open-websearch` | 联网搜索 / 抓页面（引擎选型、配置） | 项目内后补安装 | — |
| `self-learning` | 把调试出来的「可行路径」沉淀成可复用技能 | [Kulaxyz/self-learning-skills](https://github.com/Kulaxyz/self-learning-skills) | 960 |
| `cad-skill` | 参数化建模（CadQuery），`name: parametric-3d-printing` | [flowful-ai/cad-skill](https://github.com/flowful-ai/cad-skill) | 625 |
| `blender-modeler` | Blender 建模总纲 | [arjun988/blender-skills](https://github.com/arjun988/blender-skills) | 237 |
| `hard-surface` | 硬表面建模（机械零件主力） | 同上 | 237 |
| `procedural-modeling` | 程序化建模（与本项目脚本路线一致） | 同上 | 237 |
| `vector-style` | 矢量 / 线稿风格 | 同上 | 237 |
| `scene-assembly` | 装配体组装与层级 | 同上 | 237 |
| `qa-review` | 建模质量检查 | 同上 | 237 |

选题规则：**同类能力选最强、优先高星**。`arjun988/blender-skills` 共 94 个子技能，这里只装了与本项目相关的 6 个（避免上下文膨胀）；需要别的（`geometry-nodes` / `isometric-style` / `archviz` …）按同样方式装。

> 前 4 个技能原本装在全局 `~/.codex/skills`，已迁到项目内，全局不再保留副本。其余 7 个是后补的项目级安装。

## Blender MCP（GUI 实时控制）

项目里 4 个 Blender 技能（`blender-modeler` / `hard-surface` / `procedural-modeling` / `scene-assembly`，另加 `qa-review`）的正文都写着 **via MCP**，所以 MCP 是配套组件，不是可选项。

| 组件 | 状态 |
|---|---|
| `uv` / `uvx` | 已装（winget 版，在 PATH） |
| Blender 插件 | 已装 → `%APPDATA%\Blender Foundation\Blender\5.2\scripts\addons\blender_mcp.py`，已验证可 `addon_utils.enable("blender_mcp")` |
| 项目级 MCP 配置 | `.mcp.json`（`mcpServers.blender` → `uvx mcp-for-blender`） |
| Codex 全局配置 | 已写入 `~/.codex/config.toml` 的 `[mcp_servers.blender]` |

Codex 的 MCP 服务只能写在全局 `~/.codex/config.toml`（二进制里没找到项目级 MCP 配置的支持证据），已按下面这条命令配好：

```powershell
& "C:\Users\Administrator\AppData\Local\OpenAI\Codex\bin\bffc5354119c8421\codex.exe" `
  mcp add blender --env DISABLE_TELEMETRY=true -- uvx mcp-for-blender
```

> `codex` 不在用户终端的 PATH 里（`codex.exe` 的实际路径见上；版本 0.154.0-alpha.6.2）。换版本后 bin 下的哈希目录会变。

Claude Code 会直接读项目根的 `.mcp.json`，无需额外操作。

**遥测**：`mcp-for-blender` 默认会发一条匿名使用记录（收集内容本身是 opt-in，但这条记录默认开），官方声明数据「可能用于改进产品、研究和训练 AI 模型」。已在两处设 `DISABLE_TELEMETRY=true`：项目 `.mcp.json` 的 `env`，以及 Codex 全局配置。启动日志会打印 `Telemetry disabled via environment variable`，可用它确认。要恢复默认删掉该 env 即可。

**每次使用的三步**：打开 Blender → `Edit → Preferences → Add-ons` 启用 `Interface: MCP for Blender` → 3D 视图按 `N`，在 **MCP for Blender** 标签页点 **Start MCP Server**。

> 同一时间只跑一个 MCP server 实例。没启动 Blender 的 server 时，本项目的 agent 仍可走 headless 脚本（`blender/build_*.py`）——两条路并存。

## 工具依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| `animejs` | ^4.2.2 | 前端时序动画 |
| `svgo` | ^4.1.0 | 导出 SVG 的规范化 / 压缩 / 统一线宽 |

## Blender 工具链

| 项 | 值 |
|---|---|
| 可执行 | `D:\SteamLibrary\steamapps\common\Blender\blender.exe` |
| 版本 | Blender 5.2.2 LTS（内置 Python 3.13.13） |
| 控制方式 | headless：`blender --background --factory-startup --python <脚本> -- <参数>` |

## 管线：Blender → 分层线稿 SVG

分层结构：**零件 → 部件 → 总装**，一层一个脚本，都能单独跑。

```powershell
$bl = "D:\SteamLibrary\steamapps\common\Blender\blender.exe"

# 零件级：单件线稿 + 尺寸/参数记账
& $bl --background --factory-startup --python "blender\build_part.py"      -- --all --out "blender\out"
# 部件级：零件先组成部件并验证
& $bl --background --factory-startup --python "blender\build_component.py" -- --all --out "blender\out"
# 总装级：部件组成整体 → 总装分层线稿
& $bl --background --factory-startup --python "blender\build_assembly.py"  -- --out "blender\out"
```

一条命令跑全部（每段可单独重跑）：`npm run build`，`node tools/build.mjs --list` 看段落。

产物：

- `blender/out/axisburst_lineart.svg` —— 分层线稿。**零件 = SVG 图层组**（`layer.<零件id>`），纯 stroke 无 fill。
- `blender/out/axisburst_parts.json` / `assembly_manifest.json` —— 次序 / 包围盒 / 轴向位置 / 设计参数。
- `blender/out/preview.png` —— EEVEE 渲染预览，仅用于看造型；**线稿要看 SVG 渲染图**。
- `assets/axisburst.svg` + `assets/parts.json` —— 前端用的规范化分层 SVG 与爆炸位移量（`tools/normalize-svg.mjs`）。

装配顺序（也是 SVG 图层顺序）由各零件模块的 `ORDER` 决定。

> **起新产品**：`blender/parts/` 与 `blender/components/` 目前只有空注册表——管线能跑，但没有可建对象。
> 加零件＝在 `blender/parts/` 放一个模块，导出 `ID / LABEL / ORDER / Z / build(col)`，再把模块名登记进 `PART_MODULES`。

### 验证线稿（务必做）

SVG 才是交付物，用浏览器无头渲染回来看，不要只看 Blender 预览：

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless=new --disable-gpu `
  --window-size=900,1200 --screenshot="blender\out\svg_render.png" `
  "file:///C:/Users/Administrator/workspace/axisburst/blender/out/axisburst_lineart.svg"
```

## Blender 线稿坑（踩过的）

1. **必须用 `bpy.ops.object.grease_pencil_add(type='LINEART_COLLECTION')` 建对象。**
   手工 `bpy.data.grease_pencils.new()` + `layers.new()` 造出来的空图层，Line Art 求值恒为 0 笔画，导出的是空 SVG。
2. 修改器类型是 **`'LINEART'`**（不是 `GREASE_PENCIL_LINEART`）。
3. 一个零件一个 Line Art 对象、一层一零件 → 导出后天然是分层 SVG。图层的 `target_layer` 要跟着图层改名一起更新。
4. Blender 5.2 的 `addons_core` **不含** Freestyle SVG 导出插件；原生可用的是 `bpy.ops.wm.grease_pencil_export_svg`（参数：`use_fill` / `use_uniform_width` / `use_clip_camera` / `selected_object_type` / `frame_mode`）。
5. **源集合 `hide_render = True` 会让线稿一起消失** —— 预览别用这招，要单独看线稿就用浏览器渲染 SVG。
6. 导出 SVG 的 `stroke-width` 跟 `Line Art` 的 `radius`（当前 0.0026）挂钩，出来约 0.15px，偏细；要统一线宽在导出后做规范化，别逐个手改。
7. **Workbench 渲染引擎不渲染 Grease Pencil**，用 Workbench 预览线稿只会得到空白图。预览用 EEVEE（脚本已默认 EEVEE）。

## 待办

无。上一轮的三条待办（碎点收敛 / 寒松造型 / 四季配色入线稿）只对已下架的产品实例成立；
其中的碎点修复思路（导出前用 bmesh `remove_doubles` + `dissolve_degenerate` 清网格）留在 `git stash` 里，
`git stash show -p` 可看。
