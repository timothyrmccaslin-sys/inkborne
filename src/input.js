// Unified input (SPEC section 4): keyboard, Gamepad API (standard mapping) and on-screen touch.
// Touch controls hide after gamepad input and return on the next touch.
const KEYS = { ArrowUp: 'up', KeyW: 'up', ArrowDown: 'down', KeyS: 'down', ArrowLeft: 'left', KeyA: 'left', ArrowRight: 'right', KeyD: 'right',
  Space: 'confirm', Enter: 'confirm', KeyJ: 'confirm', Escape: 'cancel', Backspace: 'cancel', KeyK: 'cancel', Tab: 'menu', KeyM: 'menu' };
const ACTIONS = ['up', 'down', 'left', 'right', 'confirm', 'cancel', 'menu'];
export class Input {
  constructor(root) {
    this.held = {}; this.edge = {}; this.edgeAt = {}; this.ax = 0; this.ay = 0; this.source = 'keyboard';
    this.stick = { id: null, ox: 0, oy: 0, x: 0, y: 0 }; this.touchHeld = {}; this.padHeld = {}; this.keyHeld = {};
    this.root = root; this.pointerTaps = [];
    addEventListener('keydown', (e) => { const a = KEYS[e.code]; if (!a) return; e.preventDefault(); if (!this.keyHeld[a]) this.press(a, e.timeStamp); this.keyHeld[a] = true; this.source = 'keyboard'; });
    addEventListener('keyup', (e) => { const a = KEYS[e.code]; if (a) this.keyHeld[a] = false; });
    this.bindTouch();
  }
  press(a, ts) { this.edge[a] = true; this.edgeAt[a] = ts ?? performance.now(); }
  bindTouch() {
    const el = (id) => document.getElementById(id);
    const stickEl = el('stick'), knob = el('knob');
    const showTouch = () => { if (this.source !== 'touch') { this.source = 'touch'; document.body.classList.remove('pad'); } };
    stickEl.addEventListener('pointerdown', (e) => { showTouch(); stickEl.setPointerCapture(e.pointerId); const r = stickEl.getBoundingClientRect(); this.stick = { id: e.pointerId, ox: r.left + r.width / 2, oy: r.top + r.height / 2, x: e.clientX, y: e.clientY, r: r.width / 2 }; this.moveStick(e, knob); e.preventDefault(); });
    stickEl.addEventListener('pointermove', (e) => { if (e.pointerId === this.stick.id) this.moveStick(e, knob); });
    const end = (e) => { if (e.pointerId === this.stick.id) { this.stick.id = null; this.ax = this.ay = 0; knob.style.transform = ''; for (const d of ['up', 'down', 'left', 'right']) this.touchHeld[d] = false; } };
    stickEl.addEventListener('pointerup', end); stickEl.addEventListener('pointercancel', end);
    for (const b of document.querySelectorAll('[data-act]')) {
      const a = b.dataset.act;
      b.addEventListener('pointerdown', (e) => { showTouch(); e.preventDefault(); this.press(a, e.timeStamp); this.touchHeld[a] = true; b.classList.add('on'); });
      const up = () => { this.touchHeld[a] = false; b.classList.remove('on'); };
      b.addEventListener('pointerup', up); b.addEventListener('pointercancel', up); b.addEventListener('pointerleave', up);
    }
    // taps on the canvas (menus) are reported as positions for scenes that want them
    document.getElementById('c').addEventListener('pointerdown', (e) => { if (e.pointerType === 'touch') showTouch(); this.pointerTaps.push({ x: e.clientX, y: e.clientY, t: e.timeStamp }); });
  }
  moveStick(e, knob) {
    const s = this.stick; let dx = e.clientX - s.ox, dy = e.clientY - s.oy; const m = Math.hypot(dx, dy), r = s.r || 60;
    if (m > r) { dx *= r / m; dy *= r / m; }
    knob.style.transform = `translate(${dx}px, ${dy}px)`;
    const nx = dx / r, ny = dy / r, dead = 0.25;
    this.ax = Math.abs(nx) > dead ? nx : 0; this.ay = Math.abs(ny) > dead ? ny : 0;
    const prev = { ...this.touchHeld };
    this.touchHeld.left = nx < -0.5; this.touchHeld.right = nx > 0.5; this.touchHeld.up = ny < -0.5; this.touchHeld.down = ny > 0.5;
    for (const d of ['up', 'down', 'left', 'right']) if (this.touchHeld[d] && !prev[d]) this.press(d, e.timeStamp);
  }
  pollPad() {
    const pads = navigator.getGamepads ? navigator.getGamepads() : []; let p = null; for (const g of pads) if (g && g.connected) { p = g; break; }
    if (!p) return;
    const b = (i) => !!(p.buttons[i] && p.buttons[i].pressed);
    const map = { confirm: b(0), cancel: b(1), menu: b(9), up: b(12), down: b(13), left: b(14), right: b(15) };
    let ax = p.axes[0] || 0, ay = p.axes[1] || 0; if (Math.abs(ax) < 0.25) ax = 0; if (Math.abs(ay) < 0.25) ay = 0;
    map.left ||= ax < -0.5; map.right ||= ax > 0.5; map.up ||= ay < -0.5; map.down ||= ay > 0.5;
    let any = ax || ay;
    for (const a of ACTIONS) { if (map[a] && !this.padHeld[a]) this.press(a); if (map[a]) any = true; this.padHeld[a] = map[a]; }
    if (any) { this.padAx = ax; this.padAy = ay; if (this.source !== 'pad') { this.source = 'pad'; document.body.classList.add('pad'); } } else { this.padAx = this.padAy = 0; }
  }
  /** call once per frame before scene update */
  begin() {
    this.pollPad();
    for (const a of ACTIONS) this.held[a] = !!(this.keyHeld[a] || this.touchHeld[a] || this.padHeld[a]);
  }
  /** call once per frame after scene update */
  end() { this.edge = {}; this.pointerTaps.length = 0; }
  pressed(a) { return !!this.edge[a]; }
  pressedAt(a) { return this.edgeAt[a]; }
  down(a) { return !!this.held[a]; }
  /** analog move vector, -1..1 */
  move() {
    let x = (this.held.right ? 1 : 0) - (this.held.left ? 1 : 0), y = (this.held.down ? 1 : 0) - (this.held.up ? 1 : 0);
    if (this.stick.id !== null && (this.ax || this.ay)) { x = this.ax; y = this.ay; }
    if (this.padAx || this.padAy) { x = this.padAx; y = this.padAy; }
    const m = Math.hypot(x, y); if (m > 1) { x /= m; y /= m; }
    return [x, y];
  }
}
