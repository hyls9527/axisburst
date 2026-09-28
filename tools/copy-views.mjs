#!/usr/bin/env node
/** 把 Blender 出的三视图拷进 assets/views/，供页面直接引用。 */
import { copyFileSync, mkdirSync, readdirSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(ROOT, 'blender/out/sishan/views');
const DST = join(ROOT, 'assets/views');

if (!existsSync(SRC)) {
  console.error(`缺少视图产物：${SRC}（先跑 sishan-assembly 段）`);
  process.exit(1);
}

mkdirSync(DST, { recursive: true });
const files = readdirSync(SRC).filter((f) => f.endsWith('.png'));
for (const f of files) copyFileSync(join(SRC, f), join(DST, f));
console.log(`[copy-views] ${files.length} 张 → assets/views/`);
console.log(`[copy-views] ${files.sort().join(' ')}`);
