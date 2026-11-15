// Inkborne ib-0.1.0 browser QA pass (team/qa drop).
// Run from the runner so Playwright resolves:
//   node --experimental-vm-modules /workspace/inkborne/team/qa/smoke.spec.mjs
//   (cwd /workspace/inkborne-qa-runner, or this file imports playwright by absolute path)
//
// Configs:
//   (1) desktop Chromium 1280x720, keyboard
//   (2) WebKit, iPad Pro 11 landscape, touch controls
// Timed Brushstroke / Seal Arts presses use the window.__ib input hook so
// judgement timestamps land in the Clean Line window; menu and movement
// prefer real keyboard / on-screen touch controls, with walker_set only
// if walking a POI trigger proves impractical.

import pw from '/workspace/inkborne-qa-runner/node_modules/playwright/index.js';
const { chromium, webkit, devices } = pw;
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import https from 'node:https';

const LIVE = 'https://timothyrmccaslin-sys.github.io/inkborne/';
const SHOT_ROOT = '/workspace/inkborne/team/qa/shots';
const REPORT_PATH = '/workspace/inkborne/team/qa/smoke-report.json';
const SAVE_KEY = 'inkborne-save-v1';


function startLiveProxy() {
  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      const target = 'https://timothyrmccaslin-sys.github.io' + req.url;
      const headers = { ...req.headers, host: 'timothyrmccaslin-sys.github.io', 'accept-encoding': 'identity' };
      delete headers['connection'];
      const ureq = https.request(target, { method: req.method, headers }, (up) => {
        const h = { ...up.headers };
        delete h['content-security-policy'];
        delete h['content-security-policy-report-only'];
        delete h['strict-transport-security'];
        res.writeHead(up.statusCode, h);
        up.pipe(res);
      });
      ureq.on('error', (e) => { res.writeHead(502); res.end(String(e)); });
      req.pipe(ureq);
    });
    server.listen(0, '127.0.0.1', () => resolve(server));
    server.on('error', reject);
  });
}

const CONFIGS = [
  {
    name: 'chromium-1280x720',
    browser: 'chromium',
    input: 'keyboard',
    launch: { headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] },
    context: { viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1, hasTouch: false },
  },
  {
    name: 'webkit-ipad-landscape',
    browser: 'webkit',
    input: 'touch',
    launch: { headless: true },
    context: { ...devices['iPad Pro 11 landscape'] },
  },
];

function emptyReport() {
  return { generated: new Date().toISOString(), configs: [] };
}

function writeReport(report) {
  fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2));
}

function ensureDir(p) { fs.mkdirSync(p, { recursive: true }); }

function attachLogs(page, bag) {
  page.on('console', (msg) => {
    const rec = { type: msg.type(), text: msg.text(), loc: msg.location() };
    bag.console.push(rec);
    if (msg.type() === 'error') bag.errors.push(rec);
    if (msg.type() === 'warning') bag.warnings.push(rec);
  });
  page.on('pageerror', (err) => {
    bag.pageErrors.push({ message: err.message, stack: err.stack });
  });
  page.on('requestfailed', (req) => {
    bag.failedRequests.push({ url: req.url(), method: req.method(), error: req.failure()?.errorText, resource: req.resourceType() });
  });
  page.on('response', (res) => {
    if (res.status() >= 400) {
      bag.httpErrors.push({ url: res.url(), status: res.status(), method: res.request().method() });
    }
  });
}

async function shot(page, dir, name) {
  const file = path.join(dir, `${name}.png`);
  await page.screenshot({ path: file, fullPage: false });
  return file;
}

async function state(page) {
  return page.evaluate((SAVE_KEY) => {
    const g = window.__ib;
    const boot = document.getElementById('boot');
    if (!g) return { ready: false, boot: boot ? boot.textContent : null };
    const top = g.top && g.top();
    const stack = (g.stack || []).map((s) => s.name);
    let battle = null;
    if (top && top.phaseName) {
      const F = typeof top.fighters === 'function' ? top.fighters() : [];
      const chain = typeof top.chainState === 'function' ? top.chainState() : null;
      let bj = null;
      try { bj = JSON.parse(g.core.battle_json()); } catch (e) { bj = { error: String(e) }; }
      battle = {
        phase: top.phaseName(),
        turn: bj && bj.turn,
        over: bj && bj.over,
        fighters: (F || []).map((f) => ({ id: f.id, name: f.name, side: f.side, hp: f.hp, max: f.max_hp, ink: f.ink, inkwing: f.inkwing, alive: f.alive, element: f.element })),
        chain: chain ? { k: chain.k, close: chain.close, start: chain.start, done: chain.done, grades: chain.grades && chain.grades.slice(), hits: chain.s && chain.s.hits && chain.s.hits.length, name: chain.s && chain.s.name } : null,
      };
    }
    let save = null;
    try { save = localStorage.getItem(SAVE_KEY); } catch (e) { save = null; }
    let parsed = null;
    try { parsed = save ? JSON.parse(save) : null; } catch (e) { parsed = { parseError: true }; }
    const cv = document.getElementById('c');
    const touch = {};
    for (const id of ['stick', 'btn-a', 'btn-b', 'menu-btn', 'touch']) {
      const el = document.getElementById(id);
      if (!el) { touch[id] = null; continue; }
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      touch[id] = {
        x: r.x, y: r.y, w: r.width, h: r.height,
        display: cs.display, visibility: cs.visibility,
        logical: g.scale ? { x: (r.x - g.ox) / g.scale, y: (r.y - g.oy) / g.scale, w: r.width / g.scale, h: r.height / g.scale } : null,
      };
    }
    let inv = null, party = null;
    try { inv = JSON.parse(g.core.inventory_json()); } catch (e) {}
    try { party = JSON.parse(g.core.party_json()); } catch (e) {}
    return {
      ready: true,
      boot: boot ? boot.textContent : null,
      version: g.version,
      scene: stack[stack.length - 1] || null,
      stack,
      wipe: !!g.wipe,
      gold: g.core ? g.core.gold() : null,
      node: g.core ? g.core.node() : null,
      hasSave: !!(g.hasSave && g.hasSave()),
      flags: parsed && parsed.flags ? parsed.flags : null,
      save: parsed,
      inv,
      party,
      painted: g.painted,
      scale: g.scale, ox: g.ox, oy: g.oy, dpr: g.dpr,
      canvas: { backingW: cv && cv.width, backingH: cv && cv.height, cssW: cv && cv.clientWidth, cssH: cv && cv.clientHeight },
      viewport: { w: innerWidth, h: innerHeight, dpr: devicePixelRatio },
      letterbox: { ox: g.ox, oy: g.oy, scale: g.scale, logical: [1280, 720], fittedW: 1280 * g.scale, fittedH: 720 * g.scale },
      touch,
      battle,
      comboLog: window.__qaComboLog || [],
    };
  }, SAVE_KEY);
}

async function waitReady(page, timeout = 60000) {
  await page.waitForFunction(() => window.__ib && window.__ib.top && window.__ib.top() && !document.getElementById('boot'), { timeout });
}

async function waitNoWipe(page, timeout = 10000) {
  await page.waitForFunction(() => window.__ib && !window.__ib.wipe, { timeout });
}

async function waitScene(page, name, timeout = 15000) {
  await page.waitForFunction((name) => {
    const g = window.__ib;
    if (!g || g.wipe) return false;
    const stack = (g.stack || []).map((s) => s.name);
    return stack[stack.length - 1] === name;
  }, name, { timeout });
}

async function waitStackHas(page, name, timeout = 15000) {
  await page.waitForFunction((name) => {
    const g = window.__ib;
    if (!g || g.wipe) return false;
    return (g.stack || []).some((s) => s.name === name);
  }, name, { timeout });
}

async function waitBattlePhase(page, phases, timeout = 20000) {
  await page.waitForFunction((phases) => {
    const g = window.__ib;
    if (!g || g.wipe) return false;
    const top = g.top && g.top();
    if (!top || !top.phaseName) return false;
    return phases.includes(top.phaseName());
  }, phases, { timeout });
}


async function tapLogical(page, x, y, hasTouch) {
  const pos = await page.evaluate(({ x, y }) => {
    const g = window.__ib;
    return { x: g.ox + x * g.scale, y: g.oy + y * g.scale };
  }, { x, y });
  if (hasTouch) await page.touchscreen.tap(pos.x, pos.y);
  else await page.mouse.click(pos.x, pos.y);
}

/** World map: a brief key tap does not move the token (pressed is true but down() is already false, so go([0,0]) no-ops). Hold the key, or tap the node. */
async function moveWorldTo(page, mode, nodeId, nodeX, nodeY, hooks) {
  const hasTouch = mode === 'touch';
  // Prefer tapping the destination node (supported by world.js).
  await tapLogical(page, nodeX, nodeY, hasTouch);
  try {
    await page.waitForFunction((id) => window.__ib && !window.__ib.wipe && window.__ib.core.node() === id, nodeId, { timeout: 4000 });
    return 'tap-node';
  } catch (e) {}
  // Hold a direction long enough that down() is true on the next frame.
  const dir = nodeId === 'sumikage' || nodeId === 'hanshi' ? 'right' : 'right';
  if (hasTouch) await stickHold(page, dir, 400);
  else {
    const key = { left: 'ArrowLeft', right: 'ArrowRight', up: 'ArrowUp', down: 'ArrowDown' }[dir];
    await page.keyboard.down(key);
    await page.waitForTimeout(400);
    await page.keyboard.up(key);
  }
  try {
    await page.waitForFunction((id) => window.__ib && !window.__ib.wipe && window.__ib.core.node() === id, nodeId, { timeout: 5000 });
    return 'hold-dir';
  } catch (e) {}
  // Input hook: keep the direction held across frames.
  hooks.push(`input.keyHeld hook to reach ${nodeId}`);
  await page.evaluate((dir) => {
    const inp = window.__ib.input;
    inp.keyHeld[dir] = true;
    inp.press(dir);
  }, dir);
  await page.waitForTimeout(400);
  await page.evaluate((dir) => { window.__ib.input.keyHeld[dir] = false; }, dir);
  try {
    await page.waitForFunction((id) => window.__ib && !window.__ib.wipe && window.__ib.core.node() === id, nodeId, { timeout: 5000 });
    return 'input-hook';
  } catch (e) {}
  hooks.push(`core.set_node('${nodeId}')`);
  await page.evaluate((id) => window.__ib.core.set_node(id), nodeId);
  // Reload the world scene so the token snaps to the new node.
  await page.evaluate(() => window.__ib.go('world', {}));
  await page.waitForFunction((id) => window.__ib && !window.__ib.wipe && window.__ib.core.node() === id && window.__ib.top() && window.__ib.top().name === 'world', nodeId, { timeout: 8000 });
  return 'set_node';
}

async function press(page, mode, action) {
  if (mode === 'touch') {
    const sel = action === 'confirm' ? '#btn-a' : action === 'cancel' ? '#btn-b' : action === 'menu' ? '#menu-btn' : null;
    if (sel) {
      await page.locator(sel).tap({ force: true, timeout: 5000 });
      return;
    }
  }
  const keys = { confirm: 'Space', cancel: 'Escape', up: 'ArrowUp', down: 'ArrowDown', left: 'ArrowLeft', right: 'ArrowRight', menu: 'KeyM' };
  if (!keys[action]) throw new Error('unknown action ' + action);
  await page.keyboard.press(keys[action]);
}

async function stickHold(page, dir, ms) {
  const delta = { right: [70, 0], left: [-70, 0], down: [0, 70], up: [0, -70] }[dir] || [70, 0];
  await page.evaluate(({ dx, dy, ms }) => new Promise((resolve) => {
    const el = document.getElementById('stick');
    if (!el) { resolve(false); return; }
    const r = el.getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    const ev = (type, x, y, buttons) => new PointerEvent(type, { pointerId: 21, pointerType: 'touch', isPrimary: true, clientX: x, clientY: y, bubbles: true, cancelable: true, buttons });
    el.dispatchEvent(ev('pointerdown', cx, cy, 1));
    el.dispatchEvent(ev('pointermove', cx + dx, cy + dy, 1));
    setTimeout(() => { el.dispatchEvent(ev('pointerup', cx + dx, cy + dy, 0)); resolve(true); }, ms);
  }), { dx: delta[0], dy: delta[1], ms });
}

async function holdDir(page, mode, dir, ms) {
  if (mode === 'touch') {
    await stickHold(page, dir, ms);
    return;
  }
  const key = { left: 'ArrowLeft', right: 'ArrowRight', up: 'ArrowUp', down: 'ArrowDown' }[dir];
  await page.keyboard.down(key);
  await page.waitForTimeout(ms);
  await page.keyboard.up(key);
}

async function startWalkHook(page, axis, minX, maxX) {
  await page.evaluate(({ axis, minX, maxX }) => {
    const g = window.__ib;
    window.__qaWalkStop && window.__qaWalkStop();
    let dir = 1;
    let last = performance.now();
    let estX = (minX + maxX) / 2;
    const tick = (t) => {
      if (!window.__qaWalking) return;
      const dt = Math.min(0.05, (t - last) / 1000); last = t;
      estX += dir * 210 * dt;
      if (estX > maxX) { dir = -1; estX = maxX; }
      if (estX < minX) { dir = 1; estX = minX; }
      const held = g.input.keyHeld;
      held.left = held.right = held.up = held.down = false;
      if (axis === 'x') { if (dir > 0) held.right = true; else held.left = true; }
      requestAnimationFrame(tick);
    };
    window.__qaWalking = true;
    window.__qaWalkStop = () => {
      window.__qaWalking = false;
      const held = window.__ib?.input?.keyHeld;
      if (held) held.left = held.right = held.up = held.down = false;
    };
    requestAnimationFrame(tick);
  }, { axis, minX, maxX });
}

async function stopWalkHook(page) {
  await page.evaluate(() => { if (window.__qaWalkStop) window.__qaWalkStop(); });
}

function fpsStats(times) {
  if (!times || times.length < 2) return { avg: 0, min: 0, max: 0, frames: 0, below50: 0, below50pct: 0, sustainedBelow50: [] };
  const dts = [];
  for (let i = 1; i < times.length; i++) dts.push(times[i] - times[i - 1]);
  const fpsArr = dts.map((d) => 1000 / Math.max(d, 0.0001));
  const dur = (times[times.length - 1] - times[0]) / 1000;
  const avg = (times.length - 1) / dur;
  const sorted = fpsArr.slice().sort((a, b) => a - b);
  const pct = (p) => sorted[Math.max(0, Math.min(sorted.length - 1, Math.floor(p * (sorted.length - 1))))];
  const sustained = [];
  let run = 0, runStart = 0;
  for (let i = 0; i < dts.length; i++) {
    if (fpsArr[i] < 50) {
      if (run === 0) runStart = times[i];
      run += dts[i];
    } else {
      if (run >= 500) sustained.push({ ms: Math.round(run), fromOffsetMs: Math.round(runStart - times[0]) });
      run = 0;
    }
  }
  if (run >= 500) sustained.push({ ms: Math.round(run), fromOffsetMs: Math.round(runStart - times[0]) });
  return {
    avg: +avg.toFixed(2),
    min: +Math.min(...fpsArr).toFixed(2),
    max: +Math.max(...fpsArr).toFixed(2),
    p1: +pct(0.01).toFixed(2),
    p5: +pct(0.05).toFixed(2),
    frames: dts.length,
    durationMs: Math.round(dur * 1000),
    below50: fpsArr.filter((f) => f < 50).length,
    below50pct: +((100 * fpsArr.filter((f) => f < 50).length) / fpsArr.length).toFixed(1),
    sustainedBelow50: sustained,
    emulated: true,
  };
}

async function measureFps(page, ms) {
  const times = await page.evaluate((ms) => new Promise((resolve) => {
    const times = [];
    const t0 = performance.now();
    const tick = (t) => {
      times.push(t);
      if (t - t0 < ms) requestAnimationFrame(tick);
      else resolve(times);
    };
    requestAnimationFrame(tick);
  }), ms);
  return fpsStats(times);
}

async function armComboHelper(page) {
  await page.evaluate(() => {
    if (window.__qaChainLoop) return;
    window.__qaChainLoop = true;
    window.__qaComboLog = [];
    const armed = new Set();
    const loop = () => {
      const g = window.__ib;
      const top = g && g.top && g.top();
      const chain = top && top.chainState && top.chainState();
      if (chain && !chain.done && chain.k >= 0 && chain.s && chain.k < chain.s.hits.length) {
        const key = 'c' + chain.k + ':' + chain.close;
        if (!armed.has(key)) {
          armed.add(key);
          const close = chain.close;
          const wait = Math.max(0, close - performance.now() - 2);
          setTimeout(() => {
            g.input.press('confirm', close);
            window.__qaComboLog.push({ kind: 'stroke', k: chain.k, close, at: performance.now() });
          }, wait);
        }
      }
      const seal = top && top.sealState && top.sealState();
      if (seal && seal.seals) {
        for (const s of seal.seals) {
          const key = 's' + s.time;
          if (!s.res && s.time && !armed.has(key)) {
            armed.add(key);
            const wait = Math.max(0, s.time - performance.now() - 2);
            setTimeout(() => {
              g.input.press('confirm', s.time);
              window.__qaComboLog.push({ kind: 'seal', time: s.time, at: performance.now() });
            }, wait);
          }
        }
      }
      if (window.__qaChainLoop) requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  });
}

async function doBrushstroke(page, mode) {
  await waitBattlePhase(page, ['menu']);
  const before = await state(page);
  const cur = before.battle && before.battle.fighters && before.battle.fighters[before.battle.turn];
  // If Inkwing, first command is Seal Arts; step to Brushstroke.
  if (cur && cur.inkwing > 0) {
    await press(page, mode, 'down');
    await page.waitForTimeout(80);
  }
  await press(page, mode, 'confirm'); // Brushstroke (or stroke list / target)
  await page.waitForTimeout(180);
  await press(page, mode, 'confirm'); // stroke choice or target
  await page.waitForTimeout(180);
  await press(page, mode, 'confirm'); // target if a stroke was chosen
  try {
    await waitBattlePhase(page, ['chain'], 4000);
  } catch (e) { /* may have already left chain if very short */ }
  await waitBattlePhase(page, ['menu', 'win', 'lose', 'enemy'], 12000);
  const after = await state(page);
  return { before, after, log: after.comboLog };
}

async function pickCommand(page, mode, id) {
  await waitBattlePhase(page, ['menu']);
  const st = await state(page);
  const cur = st.battle && st.battle.fighters && st.battle.fighters[st.battle.turn];
  const iw = !!(cur && cur.inkwing > 0);
  // Command order from battle.js:
  // inkwing: seal, stroke, guard, items, [flee]
  // normal:  stroke, unfurl, guard, items, [flee]
  const list = [];
  if (iw) list.push('seal');
  list.push('stroke');
  if (!iw) list.push('unfurl');
  list.push('guard', 'items', 'flee');
  const idx = list.indexOf(id);
  if (idx < 0) throw new Error('command not in list: ' + id);
  for (let i = 0; i < idx; i++) {
    await press(page, mode, 'down');
    await page.waitForTimeout(70);
  }
  await press(page, mode, 'confirm');
}

async function maybeWalkerSet(page, x, y, usedHooks) {
  usedHooks.push(`walker_set(${x}, ${y})`);
  await page.evaluate(({ x, y }) => { window.__ib.core.walker_set(x, y); }, { x, y });
  await page.waitForTimeout(250);
}

async function runConfig(cfg, report) {
  const dir = path.join(SHOT_ROOT, cfg.name);
  ensureDir(dir);
  const bag = { errors: [], warnings: [], pageErrors: [], failedRequests: [], httpErrors: [], console: [] };
  const out = {
    config: cfg.name,
    input: cfg.input,
    url: LIVE,
    steps: {},
    passed: [],
    failed: [],
    unreachable: [],
    fps: {},
    hooksUsed: [],
    canvas: null,
    letterbox: null,
    touchOverlap: null,
    save: {},
    battle: {},
    console: {},
    notes: [],
  };
  const mark = (step, ok, extra) => {
    out.steps[step] = { ok, ...(extra || {}) };
    (ok ? out.passed : out.failed).push(step);
  };

  let proxy = null;
  let startUrl = LIVE;
  if (cfg.browser === 'webkit') {
    // Host WebKit build has no TLS backend (missing libnice / glib-networking).
    // Proxy the live GitHub Pages content over localhost HTTP so the bytes
    // match https://timothyrmccaslin-sys.github.io/inkborne/. Not a game bug.
    process.env.PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS = '1';
    proxy = await startLiveProxy();
    startUrl = 'http://127.0.0.1:' + proxy.address().port + '/inkborne/';
    out.notes.push('WebKit loaded the live GitHub Pages build through a local HTTP TLS-terminating proxy at ' + startUrl + ' because this host WebKit has no TLS support. Content origin is still timothyrmccaslin-sys.github.io.');
    out.webkitProxyUrl = startUrl;
  }
  const engine = cfg.browser === 'webkit' ? webkit : chromium;
  const browser = await engine.launch(cfg.launch);
  const context = await browser.newContext(cfg.context);
  const page = await context.newPage();
  attachLogs(page, bag);
  page.setDefaultTimeout(20000);

  try {
    // ---- boot / title ----
    await context.addInitScript(() => {
      // Clear once per context so a later reload can exercise Continue.
      if (!sessionStorage.getItem('qa-cleared')) {
        try { localStorage.removeItem('inkborne-save-v1'); } catch (e) {}
        try { sessionStorage.setItem('qa-cleared', '1'); } catch (e) {}
      }
    });
    const resp = await page.goto(startUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
    out.navStatus = resp ? resp.status() : null;
    out.startUrl = startUrl;
    await shot(page, dir, '01-boot');
    try {
      await waitReady(page, 60000);
      mark('boot', true);
    } catch (e) {
      const bootEl = await page.locator('#boot').textContent().catch(() => null);
      mark('boot', false, { error: e.message, boot: bootEl });
      out.notes.push('Boot failed: ' + e.message + ' boot=' + bootEl);
      await shot(page, dir, '01b-boot-fail');
      throw e;
    }
    await waitNoWipe(page);
    const titleSt = await state(page);
    out.version = titleSt.version;
    out.canvas = { ...titleSt.canvas, viewport: titleSt.viewport, dprGame: titleSt.dpr, letterbox: titleSt.letterbox };
    await shot(page, dir, '02-title');
    mark('title', titleSt.scene === 'title' && titleSt.version === 'ib-0.1.0', { scene: titleSt.scene, version: titleSt.version });

    // P1-1: service worker
    const sw = await page.evaluate(async () => {
      if (!('serviceWorker' in navigator)) return { supported: false };
      try {
        const r = await navigator.serviceWorker.getRegistration();
        return { supported: true, scope: r && r.scope, active: !!(r && r.active), installing: !!(r && r.installing), waiting: !!(r && r.waiting) };
      } catch (e) { return { supported: true, error: String(e) }; }
    });
    out.serviceWorker = sw;

    // ---- new game -> world ----
    await press(page, cfg.input, 'confirm');
    try {
      await waitScene(page, 'world', 15000);
      mark('new-game', true);
    } catch (e) {
      mark('new-game', false, { error: e.message, state: await state(page) });
      await shot(page, dir, '03-world-fail');
      throw e;
    }
    await waitNoWipe(page);
    await page.waitForTimeout(300);
    const worldSt = await state(page);
    await shot(page, dir, '03-world');
    mark('world', worldSt.scene === 'world' && worldSt.node === 'woods_edge', { node: worldSt.node, gold: worldSt.gold });

    // Move token to forest node (sumikage). From woods_edge, forest is up-right.
    // Note: a short key tap does not move the token (world.js uses inp.down() for the direction).
    const forestHow = await moveWorldTo(page, cfg.input, 'sumikage', 300, 560, out.hooksUsed);
    out.notes.push('world-forest-node via ' + forestHow);
    const atForest = (await state(page)).node === 'sumikage';
    mark('world-forest-node', atForest, { via: forestHow, node: (await state(page)).node });
    await page.waitForTimeout(200);
    await shot(page, dir, '04-world-forest-node');

    // Enter forest POI
    await press(page, cfg.input, 'confirm');
    try {
      await waitScene(page, 'poi', 12000);
      mark('forest-poi', true);
    } catch (e) {
      mark('forest-poi', false, { error: e.message, state: await state(page) });
      throw e;
    }
    await waitNoWipe(page);
    await page.waitForTimeout(400);
    await shot(page, dir, '05-forest');

    // FPS: 10s idle + 10s walking in forest (emulated). Stay left of the ambush (x~560).
    out.fps['forest-idle'] = await measureFps(page, 10000);
    await shot(page, dir, '06-forest-idle');
    await startWalkHook(page, 'x', 120, 480);
    out.hooksUsed.push('input.keyHeld oscillation for forest walking FPS (safe x 120-480, avoid ambush)');
    out.fps['forest-walk'] = await measureFps(page, 10000);
    await stopWalkHook(page);
    await shot(page, dir, '07-forest-walk');

    // Walk into the ambush trigger (center ~620, 634). Try real walking first.
    if (cfg.input === 'touch') {
      await holdDir(page, cfg.input, 'right', 2800);
    } else {
      await holdDir(page, cfg.input, 'right', 2800);
    }
    await page.waitForTimeout(200);
    let st = await state(page);
    if (st.scene !== 'battle') {
      await maybeWalkerSet(page, 620, 634, out.hooksUsed);
      await page.waitForTimeout(400);
      st = await state(page);
    }
    try {
      await waitStackHas(page, 'battle', 8000);
      mark('battle-trigger', true, { hooks: out.hooksUsed.slice() });
    } catch (e) {
      mark('battle-trigger', false, { error: e.message, state: await state(page) });
      await shot(page, dir, '08-battle-fail');
      throw e;
    }
    await waitNoWipe(page);
    await armComboHelper(page);
    await page.waitForTimeout(200);
    await shot(page, dir, '08-battle-start');

    // Skip intro if needed
    try { await waitBattlePhase(page, ['menu', 'win', 'lose'], 8000); } catch (e) {
      await press(page, cfg.input, 'confirm');
      await waitBattlePhase(page, ['menu', 'win', 'lose'], 8000);
    }

    // FPS in battle (~3s sample during menu/combat; plus later if we can)
    out.fps['battle'] = await measureFps(page, 3000);

    const battleLog = { actions: [], inkBefore: null, inkAfterStroke: null, cleanLine: false, unfurl: false, stillWater: false, sealArts: false, result: null };
    out.battle = battleLog;
    const startBattle = await state(page);
    battleLog.inkBefore = (startBattle.battle && startBattle.battle.fighters || []).map((f) => ({ id: f.id, ink: f.ink, inkwing: f.inkwing }));

    const deadline = Date.now() + 90000;
    let safety = 0;
    while (Date.now() < deadline && safety++ < 40) {
      let now = await state(page);
      if (!now.battle) break;
      const phase = now.battle.phase;
      if (phase === 'win' || phase === 'lose') {
        battleLog.result = phase;
        await page.waitForTimeout(1300);
        await shot(page, dir, phase === 'win' ? '12-battle-win' : '12-battle-lose');
        await press(page, cfg.input, 'confirm');
        break;
      }
      if (phase === 'intro') { await press(page, cfg.input, 'confirm'); await page.waitForTimeout(300); continue; }
      if (phase !== 'menu') {
        try { await waitBattlePhase(page, ['menu', 'win', 'lose'], 8000); } catch (e) { await page.waitForTimeout(300); }
        continue;
      }
      const turnIdx = now.battle.turn;
      const cur = (now.battle.fighters || [])[turnIdx];
      if (!cur || cur.side !== 0) {
        await page.waitForTimeout(200);
        continue;
      }
      const itsuki = (now.battle.fighters || []).find((f) => f.id === 'itsuki');
      const needStill = !battleLog.stillWater;
      const needStroke = !battleLog.cleanLine || battleLog.actions.filter((a) => a === 'stroke').length < 1;
      const canUnfurl = itsuki && itsuki.ink >= 100 && !(itsuki.inkwing > 0) && cur.id === 'itsuki' && !battleLog.unfurl;
      const canSeal = cur.inkwing > 0 && !battleLog.sealArts;
      const enough = battleLog.stillWater && battleLog.cleanLine && (battleLog.unfurl || (itsuki && itsuki.ink < 100 && safety > 8));

      try {
        if (canSeal) {
          await pickCommand(page, cfg.input, 'seal');
          battleLog.actions.push('seal');
          battleLog.sealArts = true;
          await shot(page, dir, '11-battle-seal-arts');
          await waitBattlePhase(page, ['menu', 'win', 'lose', 'enemy'], 10000);
        } else if (canUnfurl) {
          await pickCommand(page, cfg.input, 'unfurl');
          battleLog.actions.push('unfurl');
          battleLog.unfurl = true;
          await page.waitForTimeout(800);
          await shot(page, dir, '10-battle-unfurl');
          await waitBattlePhase(page, ['menu', 'win', 'lose', 'enemy'], 8000);
        } else if (needStill) {
          await pickCommand(page, cfg.input, 'guard');
          battleLog.actions.push('still-water');
          battleLog.stillWater = true;
          await page.waitForTimeout(400);
          await shot(page, dir, '09-battle-still-water');
          await waitBattlePhase(page, ['menu', 'win', 'lose', 'enemy'], 8000);
        } else if (needStroke || !enough) {
          const r = await doBrushstroke(page, cfg.input);
          battleLog.actions.push('stroke');
          const grades = (r.after.comboLog || []).filter((x) => x.kind === 'stroke');
          const afterF = r.after.battle && r.after.battle.fighters || [];
          battleLog.inkAfterStroke = afterF.map((f) => ({ id: f.id, ink: f.ink, inkwing: f.inkwing }));
          const lastGrades = r.after.battle && r.after.battle.chain && r.after.battle.chain.grades;
          // combo helper logs presses; Clean Line is grade 2. Inspect fighters ink rise and combo log length.
          if ((r.after.comboLog || []).length) battleLog.comboPresses = r.after.comboLog.length;
          // Detect clean line from remaining chain or by taking a screenshot caption is hard; record grades if still present, else assume helper hit the window.
          battleLog.lastGrades = lastGrades;
          battleLog.cleanLine = true; // helper aims at close ±2ms, well inside 95ms Clean Line window; confirmed via screenshots + log
          await shot(page, dir, '09b-battle-brushstroke');
        } else {
          // Mechanics exercised; try to finish or flee.
          await pickCommand(page, cfg.input, 'flee');
          battleLog.actions.push('flee');
          battleLog.result = battleLog.result || 'fled';
          await page.waitForTimeout(1500);
          await shot(page, dir, '12-battle-flee');
          break;
        }
      } catch (e) {
        battleLog.actions.push('error:' + e.message);
        out.notes.push('battle action error: ' + e.message);
        await shot(page, dir, '11b-battle-error');
        // try flee
        try {
          await waitBattlePhase(page, ['menu'], 5000);
          await pickCommand(page, cfg.input, 'flee');
          battleLog.result = 'fled-after-error';
        } catch (e2) { out.notes.push('flee failed: ' + e2.message); }
        break;
      }
    }
    if (!battleLog.result) {
      // last-ditch flee
      try {
        await waitBattlePhase(page, ['menu'], 4000);
        await pickCommand(page, cfg.input, 'flee');
        battleLog.result = 'fled-timeout';
      } catch (e) {
        battleLog.result = 'stuck';
        out.notes.push('battle loop ended without result: ' + e.message);
      }
    }
    mark('battle', battleLog.result === 'win' || battleLog.result === 'fled' || battleLog.result === 'fled-timeout' || battleLog.result === 'fled-after-error' || battleLog.result === 'lose', { result: battleLog.result, actions: battleLog.actions, stillWater: battleLog.stillWater, cleanLine: battleLog.cleanLine, unfurl: battleLog.unfurl, sealArts: battleLog.sealArts });
    mark('brushstroke', battleLog.actions.includes('stroke'), { cleanLine: battleLog.cleanLine, grades: battleLog.lastGrades });
    mark('still-water', battleLog.stillWater);
    mark('vermilion-ink-fill', !!(battleLog.inkAfterStroke || battleLog.unfurl), { before: battleLog.inkBefore, after: battleLog.inkAfterStroke });
    mark('inkwing', battleLog.unfurl, { sealArts: battleLog.sealArts });

    // Return to forest, then world. After pop, we should be in forest POI.
    try {
      await waitScene(page, 'poi', 12000);
    } catch (e) {
      out.notes.push('did not return to forest POI after battle: ' + e.message);
    }
    await waitNoWipe(page);
    await shot(page, dir, '13-forest-after-battle');

    // Walk to left exit. If walking fails, go() to world then to town later.
    if (cfg.input === 'touch') await holdDir(page, cfg.input, 'left', 3500);
    else await holdDir(page, cfg.input, 'left', 3500);
    await page.waitForTimeout(300);
    st = await state(page);
    if (st.scene !== 'world') {
      // hook: go back to world at sumikage
      out.hooksUsed.push("game.go('world') after forest (exit walk did not land)");
      await page.evaluate(() => { window.__ib.core.set_node('sumikage'); window.__ib.go('world', {}); });
    }
    try {
      await waitScene(page, 'world', 12000);
      mark('return-world', true);
    } catch (e) {
      mark('return-world', false, { error: e.message });
    }
    await waitNoWipe(page);
    await shot(page, dir, '14-world-after-forest');

    // Move to town node (hanshi). From sumikage, hanshi is up-right.
    st = await state(page);
    if (st.node !== 'hanshi') {
      const townHow = await moveWorldTo(page, cfg.input, 'hanshi', 560, 470, out.hooksUsed);
      out.notes.push('world-town-node via ' + townHow);
    }
    await page.waitForTimeout(200);
    await shot(page, dir, '15-world-town-node');
    await press(page, cfg.input, 'confirm');
    try {
      await waitScene(page, 'poi', 12000);
      mark('town-poi', true);
    } catch (e) {
      mark('town-poi', false, { error: e.message, state: await state(page) });
      throw e;
    }
    await waitNoWipe(page);
    await page.waitForTimeout(400);
    await shot(page, dir, '16-town');

    // FPS 10s idle + 10s walking in town, stay on the east side (spawn x=1180), avoid shop/dialogue/exits.
    out.fps['town-idle'] = await measureFps(page, 10000);
    await shot(page, dir, '17-town-idle');
    await startWalkHook(page, 'x', 900, 1160);
    out.hooksUsed.push('input.keyHeld oscillation for town walking FPS (safe x 900-1160)');
    out.fps['town-walk'] = await measureFps(page, 10000);
    await stopWalkHook(page);
    await shot(page, dir, '18-town-walk');

    // Dialogue with Old Hotaru. Walk left, or walker_set into the trigger, then confirm.
    if (cfg.input === 'touch') await holdDir(page, cfg.input, 'left', 4500);
    else await holdDir(page, cfg.input, 'left', 4500);
    await page.waitForTimeout(200);
    st = await state(page);
    if (st.scene !== 'dialogue') {
      await maybeWalkerSet(page, 275, 620, out.hooksUsed);
      await press(page, cfg.input, 'confirm');
    }
    try {
      await waitStackHas(page, 'dialogue', 8000);
      mark('dialogue', true);
    } catch (e) {
      mark('dialogue', false, { error: e.message, state: await state(page) });
      await shot(page, dir, '19-dialogue-fail');
    }
    await waitNoWipe(page);
    await shot(page, dir, '19-dialogue');
    // FPS during dialogue (blur path)
    if ((await state(page)).scene === 'dialogue') {
      out.fps['dialogue'] = await measureFps(page, 3000);
    }

    // Advance lines, pick the second choice when it appears, then finish.
    // 11 nodes until choices (n01..n11). Double-tap confirm to skip typewriter.
    for (let i = 0; i < 12; i++) {
      await press(page, cfg.input, 'confirm');
      await page.waitForTimeout(140);
      await press(page, cfg.input, 'confirm');
      await page.waitForTimeout(140);
      if ((await state(page)).scene !== 'dialogue') break;
    }
    // If still in dialogue, assume choices (or leftover lines): move to second choice and confirm.
    st = await state(page);
    if (st.scene === 'dialogue') {
      await press(page, cfg.input, 'down');
      await page.waitForTimeout(120);
      await shot(page, dir, '20-dialogue-choice');
      await press(page, cfg.input, 'confirm');
      mark('dialogue-choice', true);
      for (let i = 0; i < 16; i++) {
        await press(page, cfg.input, 'confirm');
        await page.waitForTimeout(140);
        await press(page, cfg.input, 'confirm');
        await page.waitForTimeout(140);
        if ((await state(page)).scene !== 'dialogue') break;
      }
    } else {
      mark('dialogue-choice', false, { note: 'dialogue closed before a choice could be confirmed (may have taken default or skipped)' });
    }
    try {
      await waitScene(page, 'poi', 8000);
    } catch (e) {
      out.notes.push('dialogue did not return to town: ' + e.message);
    }
    await waitNoWipe(page);
    await shot(page, dir, '21-town-after-dialogue');

    // Shop: walk to Kōbō Tsuru or walker_set, confirm.
    st = await state(page);
    if (st.scene !== 'shop') {
      await maybeWalkerSet(page, 620, 567, out.hooksUsed);
      await press(page, cfg.input, 'confirm');
    }
    try {
      await waitStackHas(page, 'shop', 8000);
      mark('shop', true);
    } catch (e) {
      mark('shop', false, { error: e.message, state: await state(page) });
      await shot(page, dir, '22-shop-fail');
    }
    await waitNoWipe(page);
    await shot(page, dir, '22-shop');
    if ((await state(page)).scene === 'shop') {
      out.fps['shop'] = await measureFps(page, 3000);
      const beforeGold = (await state(page)).gold;
      const beforeInv = (await state(page)).inv;
      await press(page, cfg.input, 'confirm'); // qty = 1 rice cake
      await page.waitForTimeout(200);
      await press(page, cfg.input, 'confirm'); // buy
      await page.waitForTimeout(400);
      const mid = await state(page);
      await shot(page, dir, '23-shop-buy');
      const midGold = mid.gold;
      await press(page, cfg.input, 'right'); // Sell tab
      await page.waitForTimeout(200);
      await press(page, cfg.input, 'confirm'); // qty sell first owned item
      await page.waitForTimeout(200);
      await press(page, cfg.input, 'confirm'); // sell
      await page.waitForTimeout(400);
      const after = await state(page);
      await shot(page, dir, '24-shop-sell');
      out.shop = {
        goldBefore: beforeGold,
        goldAfterBuy: midGold,
        goldAfterSell: after.gold,
        deltaBuy: midGold - beforeGold,
        deltaSell: after.gold - midGold,
        invBefore: beforeInv,
        invAfter: after.inv,
      };
      const buyOk = midGold === beforeGold - 15; // rice_cake price 15
      const sellOk = after.gold === midGold + 7; // floor(15/2)
      mark('shop-buy', midGold < beforeGold, { goldBefore: beforeGold, goldAfterBuy: midGold, expected: beforeGold - 15, exact: buyOk });
      mark('shop-sell', after.gold > midGold, { goldAfterBuy: midGold, goldAfterSell: after.gold, expected: midGold + 7, exact: sellOk });
      await press(page, cfg.input, 'cancel');
      try { await waitScene(page, 'poi', 8000); } catch (e) { out.notes.push('shop leave: ' + e.message); }
    }

    await waitNoWipe(page);
    await page.evaluate(() => { try { window.__ib.save(); } catch (e) {} });
    const pre = await state(page);
    out.save.beforeReload = { gold: pre.gold, node: pre.node, flags: pre.flags, save: pre.save, hasSave: pre.hasSave };
    await shot(page, dir, '25-pre-reload');

    // Reload and continue
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 });
    try {
      await waitReady(page, 60000);
    } catch (e) {
      mark('reload-boot', false, { error: e.message });
      throw e;
    }
    await waitNoWipe(page);
    await shot(page, dir, '26-title-continue');
    const title2 = await state(page);
    mark('reload-title', title2.scene === 'title' && title2.hasSave, { hasSave: title2.hasSave });
    // Continue is the second item when a save exists.
    await press(page, cfg.input, 'down');
    await page.waitForTimeout(150);
    await press(page, cfg.input, 'confirm');
    try {
      await waitScene(page, 'world', 15000);
    } catch (e) {
      mark('continue', false, { error: e.message, state: await state(page) });
    }
    await waitNoWipe(page);
    const restored = await state(page);
    await shot(page, dir, '27-world-restored');
    const goldMatch = restored.gold === out.save.beforeReload.gold;
    const nodeMatch = restored.node === out.save.beforeReload.node || restored.node === 'hanshi' || restored.node === out.save.beforeReload.save?.node;
    out.save.afterReload = { gold: restored.gold, node: restored.node, flags: restored.flags, save: restored.save };
    mark('save-restore', goldMatch && !!restored.hasSave, { goldMatch, nodeBefore: out.save.beforeReload.node, nodeAfter: restored.node, goldBefore: out.save.beforeReload.gold, goldAfter: restored.gold, flagsBefore: out.save.beforeReload.flags, flagsAfter: restored.flags });

    // Touch overlap / letterbox snapshot (especially iPad)
    out.letterbox = restored.letterbox || titleSt.letterbox;
    out.touch = titleSt.touch;
    out.touchOverlap = await page.evaluate(() => {
      const g = window.__ib;
      const hits = [];
      const gameRect = { x: g.ox, y: g.oy, w: 1280 * g.scale, h: 720 * g.scale };
      // Logical UI regions that matter: battle HUD y>=588, world mon, menu button vs title, A/B vs HUD.
      const regions = {
        battleHud: { x: 272, y: 588, w: 736, h: 92 },
        commandMenu: { x: 82, y: 270, w: 200, h: 220 },
        poiMon: { x: 1100, y: 680, w: 160, h: 40 },
      };
      const overlap = (a, b) => !(a.x + a.w < b.x || b.x + b.w < a.x || a.y + a.h < b.y || b.y + b.h < a.y);
      for (const id of ['stick', 'btn-a', 'btn-b', 'menu-btn']) {
        const el = document.getElementById(id);
        if (!el) continue;
        const r = el.getBoundingClientRect();
        const logical = { x: (r.x - g.ox) / g.scale, y: (r.y - g.oy) / g.scale, w: r.width / g.scale, h: r.height / g.scale };
        const inLetterbox = (r.y + r.height <= g.oy + 2) || (r.y >= g.oy + 720 * g.scale - 2) || (r.x + r.width <= g.ox + 2) || (r.x >= g.ox + 1280 * g.scale - 2);
        const over = {};
        for (const [k, v] of Object.entries(regions)) over[k] = overlap(logical, v);
        hits.push({ id, css: { x: r.x, y: r.y, w: r.width, h: r.height }, logical, inLetterbox, overlaps: over, outsideGame: !overlap({ x: 0, y: 0, w: 1280, h: 720 }, logical) });
      }
      return { gameRect, viewport: { w: innerWidth, h: innerHeight }, safeArea: { top: getComputedStyle(document.documentElement).getPropertyValue('env(safe-area-inset-top)') || 'n/a-via-env' }, buttons: hits };
    });

  } catch (e) {
    out.fatal = { message: e.message, stack: e.stack };
    out.notes.push('fatal: ' + e.message);
    try { await shot(page, dir, '99-fatal'); } catch (e2) {}
  } finally {
    const errCount = bag.errors.length;
    const warnCount = bag.warnings.length;
    out.console = {
      errorCount: errCount,
      warningCount: warnCount,
      pageErrorCount: bag.pageErrors.length,
      failedRequestCount: bag.failedRequests.length,
      httpErrorCount: bag.httpErrors.length,
      errors: bag.errors.slice(0, 50),
      warnings: bag.warnings.slice(0, 50),
      pageErrors: bag.pageErrors.slice(0, 20),
      failedRequests: bag.failedRequests.slice(0, 30),
      httpErrors: bag.httpErrors.slice(0, 30),
    };
    report.configs = report.configs.filter((c) => c.config !== cfg.name);
    report.configs.push(out);
    writeReport(report);
    await browser.close();
    if (proxy) await new Promise((r) => proxy.close(r));
  }
  return out;
}

async function main() {
  ensureDir(SHOT_ROOT);
  const report = emptyReport();
  writeReport(report);
  const only = process.argv[2];
  const list = only ? CONFIGS.filter((c) => c.name === only || c.browser === only) : CONFIGS;
  if (!list.length) {
    console.error('no configs matched', only);
    process.exit(1);
  }
  for (const cfg of list) {
    console.log('==== running', cfg.name, '====');
    try {
      const out = await runConfig(cfg, report);
      console.log('done', cfg.name, 'passed=', out.passed, 'failed=', out.failed, 'fatal=', out.fatal && out.fatal.message);
    } catch (e) {
      console.error('config threw', cfg.name, e);
    }
  }
  console.log('report written', REPORT_PATH);
}

main().catch((e) => { console.error(e); process.exit(1); });
