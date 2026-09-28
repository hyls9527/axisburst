#!/usr/bin/env node
/** 生成三视图展示用的清单 assets/views/manifest.json。 */
import { existsSync, mkdirSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const DIR = join(ROOT, 'assets/views');
mkdirSync(DIR, { recursive: true });

const VIEW_LABEL = { front: '正视图', side: '侧视图', top: '俯视图' };
const STYLE_LABEL = { line: '线稿', clay: '灰模', wire: '线框', season: '四季色稿' };

const files = existsSync(DIR) ? readdirSync(DIR).filter((f) => f.endsWith('.png')) : [];
const items = [];
for (const f of files) {
  const m = /^(front|side|top)_(line|clay|wire|season)\.png$/.exec(f);
  if (!m) continue;
  items.push({ file: f, view: m[1], style: m[2], viewLabel: VIEW_LABEL[m[1]], styleLabel: STYLE_LABEL[m[2]] });
}
const order = { front: 0, side: 1, top: 2 };
items.sort((a, b) => order[a.view] - order[b.view] || a.style.localeCompare(b.style));

writeFileSync(join(DIR, 'manifest.json'), JSON.stringify({ count: items.length, items }, null, 2));
console.log(`[plates] ${items.length} 张视图 → assets/views/manifest.json`);
