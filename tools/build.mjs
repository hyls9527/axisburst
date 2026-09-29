#!/usr/bin/env node
/**
 * 线稿构建管线：一条命令跑完 精确建模 → 网格 → 零件 → 部件 → 总装线稿 → 前端资产。
 *
 *   node tools/build.mjs                  # 全跑
 *   node tools/build.mjs --only=cad,mesh  # 只跑某几段
 *   node tools/build.mjs --skip=components
 *   node tools/build.mjs --list
 *
 * 环境变量：
 *   AXISBURST_BLENDER  Blender 可执行文件（默认 D:\SteamLibrary\...\blender.exe）
 *   AXISBURST_UV       uv 可执行文件（默认走 PATH 上的 uv）
 *
 * 每一段都能单独跑，也可以只跑失败的下一段——不用每次从头。
 */

import { execFileSync } from 'node:child_process';
import { readdirSync, existsSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const BLENDER = process.env.AXISBURST_BLENDER
  ?? 'D:\\SteamLibrary\\steamapps\\common\\Blender\\blender.exe';
const UV = process.env.AXISBURST_UV ?? 'uv';

const py = (rel) => join(ROOT, rel);
const mtime = (abs) => statSync(abs).mtimeMs;
const ls = (dir, ext) => (existsSync(join(ROOT, dir))
  ? readdirSync(join(ROOT, dir)).filter((f) => f.endsWith(ext) && !f.startsWith('_'))
  : []);

const stages = [
  {
    name: 'cad',
    what: '精确建模（build123d）→ STEP + STL',
    commands: () => ls('cad', '.py').map((f) => ({
      bin: UV, args: ['tool', 'run', '--from', 'build123d', 'python', py(`cad/${f}`)], label: f,
    })),
  },
  {
    name: 'mesh',
    what: 'CAD 网格 → Blender 线稿 SVG',
    commands: () => ls('cad/out', '.stl').map((f) => ({
      bin: BLENDER,
      args: ['--background', '--factory-startup', '--python', py('blender/from_cad.py'),
        '--', '--mesh', py(`cad/out/${f}`), '--name', f.replace(/\.stl$/, ''),
        '--out', py('blender/out/cad')],
      label: f,
    })),
  },
  {
    name: 'parts',
    what: '零件级：单件线稿 + 尺寸/参数记账',
    commands: () => [{
      bin: BLENDER,
      args: ['--background', '--factory-startup', '--python', py('blender/build_part.py'),
        '--', '--all', '--out', py('blender/out')],
      label: 'all parts',
    }],
  },
  {
    name: 'components',
    what: '部件级：零件组装成部件并验证',
    commands: () => [{
      bin: BLENDER,
      args: ['--background', '--factory-startup', '--python', py('blender/build_component.py'),
        '--', '--all', '--out', py('blender/out')],
      label: 'all components',
    }],
  },
  {
    name: 'assembly',
    what: '总装级：部件组成整体 → 总装分层线稿',
    commands: () => [{
      bin: BLENDER,
      args: ['--background', '--factory-startup', '--python', py('blender/build_assembly.py'),
        '--', '--out', py('blender/out')],
      label: 'assembly',
    }],
  },
  {
    name: 'assets',
    what: '线稿规范化 → 前端资产（assets/）',
    commands: () => {
      const input = py('blender/out/axisburst_lineart.svg');
      const parts = py('blender/out/axisburst_parts.json');
      if (!existsSync(input) || !existsSync(parts)) {
        throw new Error(
          '缺少总装输出：需要先跑 assembly 段（blender/build_assembly.py）'
          + '生成 axisburst_lineart.svg 与 axisburst_parts.json。',
        );
      }
      if (mtime(parts) > mtime(input)) {
        throw new Error(
          'assets 段的输入不一致：零件清单比总装线稿新，说明线稿是上一次的产物。重跑 assembly 段。',
        );
      }
      return [{ bin: process.execPath, args: [py('tools/normalize-svg.mjs')], label: 'svgo' }];
    },
  },
];

// ---------------------------------------------------------------- 参数

const argv = process.argv.slice(2);
const argValue = (name) => {
  const hit = argv.find((a) => a.startsWith(`--${name}=`));
  return hit ? hit.split('=')[1].split(',').map((s) => s.trim()).filter(Boolean) : null;
};

if (argv.includes('--list')) {
  console.log('可用阶段：');
  for (const s of stages) console.log(`  ${s.name.padEnd(12)} ${s.what}`);
  process.exit(0);
}

const only = argValue('only');
const skip = new Set(argValue('skip') ?? []);
const selected = stages.filter((s) => (!only || only.includes(s.name)) && !skip.has(s.name));

// ---------------------------------------------------------------- 执行

function run(bin, args, label) {
  const started = Date.now();
  try {
    execFileSync(bin, args, { cwd: ROOT, stdio: 'pipe', encoding: 'utf8' });
    return { ok: true, ms: Date.now() - started, label };
  } catch (error) {
    const tail = (error.stdout ?? '') + (error.stderr ?? '');
    return {
      ok: false, ms: Date.now() - started, label,
      detail: tail.split(/\r?\n/).filter(Boolean).slice(-3).join(' | ').slice(0, 200),
    };
  }
}

const summary = [];
for (const stage of selected) {
  let commands;
  try {
    commands = stage.commands();
  } catch (error) {
    console.log(`\n▶ ${stage.name.padEnd(11)} ${stage.what}`);
    console.log(`  ✗ 前置检查未通过：${error.message}`);
    summary.push({ stage: stage.name, ok: false, ms: 0, count: 0 });
    continue;
  }
  console.log(`\n▶ ${stage.name.padEnd(11)} ${stage.what}  (${commands.length} 个任务)`);
  if (!commands.length) {
    console.log('  跳过：没有可处理的输入');
    summary.push({ stage: stage.name, ok: true, ms: 0, count: 0 });
    continue;
  }

  let ok = true;
  let total = 0;
  for (const cmd of commands) {
    const result = run(cmd.bin, cmd.args, cmd.label);
    total += result.ms;
    if (result.ok) {
      console.log(`  ✓ ${result.label}  ${(result.ms / 1000).toFixed(1)}s`);
    } else {
      ok = false;
      console.log(`  ✗ ${result.label}  ${(result.ms / 1000).toFixed(1)}s`);
      if (result.detail) console.log(`      ${result.detail}`);
    }
  }
  summary.push({ stage: stage.name, ok, ms: total, count: commands.length });
}

console.log('\n──────── 汇总 ────────');
for (const row of summary) {
  console.log(`  ${row.ok ? '✓' : '✗'} ${row.stage.padEnd(11)} ${row.count} 个任务  ${(row.ms / 1000).toFixed(1)}s`);
}
const failed = summary.filter((r) => !r.ok);
console.log(failed.length ? `\n${failed.length} 段失败：${failed.map((r) => r.stage).join(', ')}` : '\n全部通过');
process.exit(failed.length ? 1 : 0);
