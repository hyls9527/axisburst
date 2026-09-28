#!/usr/bin/env node
/**
 * 把导出的 SVG 用浏览器离屏渲染成 PNG，用于人工核对形状。
 * 线稿的交付物是 SVG，所以验证必须看 SVG 的渲染结果，而不是 Blender 里的实体预览。
 *
 * 用法：node tools/preview-svg.mjs <svg 路径> [输出 png 路径] [--width 1200] [--height 900]
 */

import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

const argv = process.argv.slice(2);
const positional = [];
const flags = new Map();
for (let i = 0; i < argv.length; i += 1) {
  if (argv[i].startsWith('--')) {
    flags.set(argv[i].slice(2), argv[i + 1]);
    i += 1;
  } else {
    positional.push(argv[i]);
  }
}
const flag = (name, fallback) => (flags.has(name) ? Number(flags.get(name)) : fallback);

if (!positional.length) {
  console.error('用法: node tools/preview-svg.mjs <svg> [png] [--width W] [--height H]');
  process.exit(1);
}

const svgPath = resolve(positional[0]);
const pngPath = positional[1] ? resolve(positional[1]) : svgPath.replace(/\.svg$/i, '.preview.png');
const width = flag('width', 1200);
const height = flag('height', 900);

const svg = readFileSync(svgPath, 'utf8').replace(/<\?xml[^>]*\?>/, '');
const wrapper = `<!DOCTYPE html><meta charset="utf-8">
<style>
  html,body{margin:0;height:100%;background:#e9e6df;}
  body{display:grid;place-items:center;}
  svg{width:${width - 80}px;height:${height - 80}px;}
</style>
${svg}`;

mkdirSync(dirname(pngPath), { recursive: true });
const tmpHtml = pngPath.replace(/\.png$/i, '.wrap.html');
writeFileSync(tmpHtml, wrapper, 'utf8');

execFileSync(EDGE, [
  '--headless=new',
  '--disable-gpu',
  '--hide-scrollbars',
  `--window-size=${width},${height}`,
  `--screenshot=${pngPath}`,
  `file:///${tmpHtml.replace(/\\/g, '/')}`,
], { stdio: 'ignore' });

console.log(`${svgPath}  →  ${pngPath}`);
