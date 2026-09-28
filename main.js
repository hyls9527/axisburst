/**
 * 四季山河 · 爆炸分解时序（anime.js v4）
 * 装配 → 停留标注 → 弹性爆炸展开 → 收回，循环。
 * 几何与位移量全部来自 Blender 管线产出的 assets/，前端不写死任何坐标。
 */
import { createTimeline, createSpring, stagger, utils } from './vendor/anime.js';

const PHASE = {
  hold: 320,
  step: 110,      // 零件间隔（stagger）
  seat: 820,      // 单件归位时长
  rest: 900,      // 停住看标注
  outStep: 80,
  out: 880,
};

const [meta, svgText] = await Promise.all([
  fetch('./assets/sishan-parts.json').then((r) => r.json()),
  fetch('./assets/sishan.svg').then((r) => r.text()),
]);

const parts = [...meta.parts].sort((a, b) => a.order - b.order);

// 四季语义色（SPEC-四季山河.md）：春粉 / 夏绿青 / 秋红橙 / 冬白墨
const SEASON_COLOR = {
  'SS-01': '#3a2a22', 'SS-02': '#4d8f7a', 'SS-03': '#7fb4c4', 'SS-04': '#8fc4d4',
  'SS-05': '#a8623a', 'SS-06': '#5f8f4e', 'SS-07': '#e08aa8', 'SS-08': '#8d8578',
  'SS-09': '#c0502a', 'SS-10': '#8a5a3c', 'SS-11': '#2f4a3c', 'SS-12': '#eef2f6',
};
const drawing = document.getElementById('drawing');
drawing.innerHTML = svgText;
const svg = drawing.querySelector('svg');

const kwList = document.getElementById('keywords');
kwList.innerHTML = parts
  .map((p) => `<li class="kw" data-part="${p.id}"><span class="kw-i">${String(p.order + 1).padStart(2, '0')}</span><span class="kw-c" style="background:${SEASON_COLOR[p.id] ?? '#999'}"></span><span>${p.label}</span></li>`)
  .join('');

const el = (id) => svg.querySelector(`[data-part="${id}"]`);
const kw = (id) => kwList.querySelector(`.kw[data-part="${id}"]`);

// 起始：全部处于爆炸位
for (const p of parts) {
  utils.set(el(p.id), { x: p.explode[0], y: p.explode[1] });
  utils.set(kw(p.id), { opacity: 0.25 });
}

const readout = document.getElementById('readout');
readout.innerHTML = [
  ['零件', `${parts.length} 件`],
  ['装配轴', `(${meta.axis[0].toFixed(3)}, ${meta.axis[1].toFixed(3)})`],
  ['弹簧', 'stiffness 88 / damping 12'],
  ['时序', `stagger ${PHASE.step}ms · 单件 ${PHASE.seat}ms`],
  ['爆炸倍率', `${meta.spread}×`],
].map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('');

const phaseEl = document.getElementById('phase');
const clockEl = document.getElementById('clock');
const btnPlay = document.getElementById('btn-play');
const btnRestart = document.getElementById('btn-restart');
const speedEl = document.getElementById('speed');
const speedVal = document.getElementById('speed-val');

const n = parts.length;
const assembleAt = PHASE.hold;
const assembleEnd = assembleAt + PHASE.step * (n - 1) + PHASE.seat;
const explodeAt = assembleEnd + PHASE.rest;

const spring = createSpring({ stiffness: 88, damping: 12 });

let playing = true;
function setPlaying(v) {
  playing = v;
  btnPlay.textContent = v ? '暂停' : '播放';
}

const tl = createTimeline({
  loop: true,
  autoplay: true,
  defaults: { ease: spring },
  onUpdate: (self) => {
    const t = self.currentTime;
    clockEl.textContent = `${(t / 1000).toFixed(2)}s`;
    phaseEl.textContent =
      t < assembleAt ? '初始状态'
        : t < assembleEnd ? '装配中'
          : t < explodeAt ? '停留标注'
            : t < explodeAt + PHASE.outStep * (n - 1) + PHASE.out ? '爆炸展开' : '收回装配';
  },
})
  // ① 依次归位（stagger + spring）
  .add('.part', { x: 0, y: 0, duration: PHASE.seat, delay: stagger(PHASE.step) }, assembleAt)
  // ② 编号随件点亮
  .add('.kw', { opacity: 1, color: ['#a7a49b', '#15161a'], duration: 240, delay: stagger(PHASE.step) }, assembleAt)
  // ③ 沿装配轴弹性炸开（方向与位移量来自 Blender）
  .add('.part', {
    x: (t, i) => parts[i].explode[0],
    y: (t, i) => parts[i].explode[1],
    duration: PHASE.out,
    ease: 'in(2)',
    delay: stagger(PHASE.outStep),
  }, explodeAt)
  .add('.kw', { opacity: 0.25, duration: 320, delay: stagger(PHASE.outStep) }, explodeAt);

btnPlay.addEventListener('click', () => {
  if (playing) { tl.pause(); setPlaying(false); } else { tl.play(); setPlaying(true); }
});
btnRestart.addEventListener('click', () => { tl.restart(); setPlaying(true); });
speedEl.addEventListener('input', () => {
  tl.speed = Number(speedEl.value);
  speedVal.textContent = `${Number(speedEl.value).toFixed(1)}×`;
});

window.sishan = { tl, parts, meta };

// 三视图 × 风格缩略图（由 tools/copy-views.mjs + plates.mjs 产出）
const platesEl = document.getElementById('plates');
try {
  const plates = await fetch('./assets/views/manifest.json').then((r) => r.json());
  const byView = {};
  for (const it of plates.items) (byView[it.view] ??= []).push(it);
  platesEl.innerHTML = Object.entries(byView).map(([view, items]) => `
    <figure class="plate">
      <figcaption>${items[0].viewLabel}</figcaption>
      <img src="./assets/views/${items.find((i) => i.style === 'line')?.file ?? items[0].file}" alt="${items[0].viewLabel}线稿" />
    </figure>`).join('');
} catch {
  platesEl.hidden = true;
}
