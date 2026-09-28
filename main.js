/**
 * 机械零件 SVG 爆炸分解时序动画 · anime.js v4
 * 装配 → 弹性爆炸展开 → 停留 1s → 收回装配（循环）
 *
 * 分层约定：
 *   .part[data-part]  零件独立分组（动画只动这一层）
 *   .part .body       几何线稿
 *   .leader           引线标注层
 */
import {
  animate,
  createTimeline,
  stagger,
  spring,
  utils,
} from 'https://cdn.jsdelivr.net/npm/animejs@4.2.2/dist/modules/index.js';

// ---------- 齿轮几何 ----------
function gearMarkup() {
  const cx = 420;
  const cy = 365;
  const rIn = 68;
  const rOut = 92;
  const ryIn = 34;
  const ryOut = 46;
  const d = [];
  for (let i = 0; i < 14; i++) {
    const a0 = (i / 14) * Math.PI * 2;
    const a1 = ((i + 0.38) / 14) * Math.PI * 2;
    const a2 = ((i + 0.62) / 14) * Math.PI * 2;
    const a3 = ((i + 1) / 14) * Math.PI * 2;
    const p = (a, rx, ry) =>
      `${(cx + Math.cos(a) * rx).toFixed(2)} ${(cy + Math.sin(a) * ry).toFixed(2)}`;
    d.push(`M ${p(a0, rIn, ryIn)} L ${p(a1, rOut, ryOut)} L ${p(a2, rOut, ryOut)} L ${p(a3, rIn, ryIn)}`);
  }
  return `
    <path d="${d.join(' ')} Z" fill="url(#metalB)" stroke="#C8D0DA" stroke-width="1.25"/>
    <ellipse cx="${cx}" cy="${cy}" rx="${rIn}" ry="${ryIn}" fill="url(#metalA)" stroke="#C8D0DA" stroke-width="1.35"/>
    <ellipse cx="${cx}" cy="${cy}" rx="32" ry="16" fill="#1A1F26" stroke="#C8D0DA" stroke-width="1.1"/>
    <ellipse cx="${cx}" cy="${cy}" rx="14" ry="7" fill="#12151A" stroke="#6B7785" stroke-width="0.9"/>
    <rect x="${cx - 12}" y="${cy - 5}" width="24" height="10" rx="2" fill="#12151A" stroke="#C8D0DA" stroke-width="0.9"/>
  `;
}

document.getElementById('gear-body').innerHTML = gearMarkup();

// ---------- 零件（爆炸方向来自 data-dx / data-dy，与 SVG 轴向一致） ----------
const PARTS = [
  { id: 'endcap', name: '端盖' },
  { id: 'shaft', name: '传动轴' },
  { id: 'bearing-upper', name: '上轴承' },
  { id: 'gear', name: '主齿轮' },
  { id: 'bearing-lower', name: '下轴承' },
  { id: 'bolts', name: '紧固螺栓' },
  { id: 'housing', name: '座体外壳' },
];

const listEl = document.getElementById('part-list');
listEl.innerHTML = PARTS.map(
  (p, i) => `
  <li data-id="${p.id}">
    <span class="n">${String(i + 1).padStart(2, '0')}</span>
    <span>${p.name}</span>
  </li>`
).join('');

// ---------- 控件 ----------
const phaseEl = document.getElementById('phase');
const clockEl = document.getElementById('clock');
const btnPlay = document.getElementById('btn-play');
const btnRestart = document.getElementById('btn-restart');
const speedEl = document.getElementById('speed');
const speedVal = document.getElementById('speed-val');

const HOLD_MS = 1000;
let playing = true;

function explodeXY(el) {
  const scale = 2.6;
  return {
    x: Number(el.dataset.dx || 0) * scale,
    y: Number(el.dataset.dy || 0) * scale,
  };
}

function setPlaying(v) {
  playing = v;
  btnPlay.textContent = v ? '暂停' : '播放';
}

function updatePhase(t) {
  // 与下方时间轴阈值一致：展开→停 1s→收回
  if (t < 180) phaseEl.textContent = '装配状态';
  else if (t < 2100) phaseEl.textContent = '爆炸展开';
  else if (t < 2100 + HOLD_MS) phaseEl.textContent = '停留标注';
  else if (t < 3800) phaseEl.textContent = '收回装配';
  else phaseEl.textContent = '装配状态';
}

// ---------- 时间线：spring + stagger ----------
function buildTimeline() {
  return createTimeline({
    loop: true,
    autoplay: false,
    defaults: {
      ease: spring({ bounce: 0.35, duration: 520 }),
    },
    onUpdate: (self) => {
      clockEl.textContent = `${(self.currentTime / 1000).toFixed(2)}s`;
      updatePhase(self.currentTime);
    },
    onBegin: () => {
      setPlaying(true);
    },
  })
    // 装配原点
    .set('.part', { x: 0, y: 0 })
    .set('.leader', { opacity: 0.12 })

    // 1) 爆炸展开：stagger 依次沿轴向弹出
    .add(
      '.part',
      {
        x: (el) => explodeXY(el).x,
        y: (el) => explodeXY(el).y,
        ease: spring({ bounce: 0.45, duration: 560 }),
      },
      stagger(110, { start: 100 })
    )

    // 1b) 引线亮起
    .add(
      '.leader',
      { opacity: 1, duration: 360, ease: 'out(2)' },
      stagger(110, { start: 320 })
    )

    // 2) 停留 1s
    .add({}, HOLD_MS)

    // 3) 收回装配
    .add(
      '.part',
      {
        x: 0,
        y: 0,
        ease: spring({ bounce: 0.3, duration: 500 }),
      },
      stagger(80)
    )

    // 3b) 引线淡回
    .add('.leader', { opacity: 0.12, duration: 300, ease: 'out(2)' }, '<+=180')

    // 4) 装配态短暂停顿，无缝进入下一循环
    .add({}, 420);
}

const tl = buildTimeline();

btnPlay.addEventListener('click', () => {
  if (playing) {
    tl.pause();
    setPlaying(false);
    phaseEl.textContent = '已暂停';
  } else {
    tl.play();
    setPlaying(true);
  }
});

btnRestart.addEventListener('click', () => {
  tl.restart();
  setPlaying(true);
});

speedEl.addEventListener('input', () => {
  const r = Number(speedEl.value);
  speedVal.textContent = `${r.toFixed(1)}×`;
  tl.playbackRate = r;
});

listEl.addEventListener('click', (e) => {
  const li = e.target.closest('li');
  if (!li) return;
  document.querySelectorAll('#part-list li').forEach((el) => {
    el.classList.toggle('active', el === li);
  });
  const part = document.querySelector(`.part[data-part="${li.dataset.id}"]`);
  if (!part) return;
  // 点击反馈：微缩放回弹，不打断主时间线
  animate(part, {
    scale: [1.03, 1],
    ease: spring({ bounce: 0.5, duration: 320 }),
  });
});

// 自动播放
tl.play();
setPlaying(true);
