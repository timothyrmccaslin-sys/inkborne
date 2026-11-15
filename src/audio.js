// Audio: James's synthesized SFX + ambience loops and Rita's formant voices (team/audio), all
// generated in-house (no outside samples). One shared AudioContext unlocked on the first gesture
// (iOS), audioSession 'playback'. Loops skip ~25 ms MP3 padding at each end (James's README).
// Music: Cody's synthesized cues (team/audio/music); POI ambience loops from James play underneath.
import BLIPS from './blips.js';
const SFX = ['step', 'step-dirt-02', 'step-dirt-03', 'step-dirt-04', 'step-wood-01', 'step-wood-02', 'confirm', 'cancel', 'move', 'ring', 'hit', 'hit-heavy', 'hit-crit',
  'clean', 'miss', 'combo-finish', 'guard', 'heal', 'inkwing', 'seal', 'coin', 'text', 'wipe', 'enemy-hit', 'enemy-defeat', 'lantern', 'wind', 'amb-forest', 'amb-town'];
const GAIN = { step: 0.35, confirm: 0.6, cancel: 0.6, move: 0.4, ring: 0.5, hit: 0.75, 'hit-heavy': 0.8, 'hit-crit': 0.8, clean: 0.75, miss: 0.7, 'combo-finish': 0.8, guard: 0.65, heal: 0.6,
  inkwing: 0.9, seal: 0.75, coin: 0.6, text: 0.25, wipe: 0.5, 'enemy-hit': 0.75, 'enemy-defeat': 0.7, lantern: 0.35, wind: 0.45, 'amb-forest': 0.55, 'amb-town': 0.5 };
const PAD = 0.025;
export class Audio {
  constructor(base) {
    this.base = base; this.buf = {}; this.ctx = null; this.loopSrc = null; this.loopKey = null; this.vol = { sfx: 0.8, amb: 0.7, voice: 0.9, music: 0.8 };
    try { if (navigator.audioSession) navigator.audioSession.type = 'playback'; } catch (e) {}
    const unlock = () => this.unlock();
    for (const ev of ['touchend', 'pointerup', 'click', 'keydown']) addEventListener(ev, unlock, { passive: true });
  }
  unlock() {
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
      this.ctx = new AC(); this.out = this.ctx.createGain(); this.out.connect(this.ctx.destination);
      const b = this.ctx.createBuffer(1, 1, 22050), s = this.ctx.createBufferSource(); s.buffer = b; s.connect(this.out); s.start(0);
      this.loadAll();
    }
    if (this.ctx.state !== 'running') this.ctx.resume().catch(() => {});
    if (this.wantLoop && !this.loopSrc) this.ambience(this.wantLoop);
    if (this.wantMusic && !this.musicSrc) this.music(this.wantMusic);
  }
  async load(key, path) {
    if (this.buf[key] || !this.ctx) return this.buf[key];
    if (this.miss && this.miss[key]) return null;
    try { const r = await fetch(path); if (!r.ok) throw 0; const a = await r.arrayBuffer(); this.buf[key] = await this.ctx.decodeAudioData(a); } catch (e) { (this.miss ||= {})[key] = 1; /* missing file: silent */ }
    return this.buf[key];
  }
  loadAll() { for (const k of SFX) this.load(k, `${this.base}assets/sfx/${k}.mp3`); }
  play(key, o = {}) {
    if (!this.ctx || this.ctx.state !== 'running') return;
    if (key === 'step') key = o.wood ? `step-wood-0${1 + (Math.random() * 2 | 0)}` : ['step', 'step-dirt-02', 'step-dirt-03', 'step-dirt-04'][Math.random() * 4 | 0];
    const b = this.buf[key]; if (!b) return;
    const s = this.ctx.createBufferSource(), g = this.ctx.createGain(); s.buffer = b;
    s.playbackRate.value = o.rate ?? (key.startsWith('step') ? 0.95 + Math.random() * 0.1 : 1);
    g.gain.value = (o.gain ?? GAIN[key] ?? 0.7) * this.vol.sfx; s.connect(g); g.connect(this.out); s.start(0, key.startsWith('amb') ? PAD : 0);
  }
  /** loop an ambience key with the MP3 padding trimmed (loopStart/loopEnd) and a short fade */
  async ambience(key) {
    this.wantLoop = key;
    if (!this.ctx) return; if (this.loopKey === key && this.loopSrc) return;
    this.stopAmbience();
    const b = await this.load(key, `${this.base}assets/sfx/${key}.mp3`); if (!b || this.wantLoop !== key) return;
    const s = this.ctx.createBufferSource(), g = this.ctx.createGain(); s.buffer = b; s.loop = true; s.loopStart = PAD; s.loopEnd = b.duration - PAD;
    g.gain.setValueAtTime(0, this.ctx.currentTime); g.gain.linearRampToValueAtTime((GAIN[key] ?? 0.5) * this.vol.amb, this.ctx.currentTime + 1.2);
    s.connect(g); g.connect(this.out); s.start(0, PAD); this.loopSrc = s; this.loopGain = g; this.loopKey = key;
  }
  stopAmbience() {
    if (!this.loopSrc) return; const s = this.loopSrc, g = this.loopGain, t = this.ctx.currentTime;
    g.gain.cancelScheduledValues(t); g.gain.setValueAtTime(g.gain.value, t); g.gain.linearRampToValueAtTime(0, t + 0.6); s.stop(t + 0.65); this.loopSrc = null; this.loopKey = null;
  }
  setScene(kind) { // 'forest' | 'town' | 'world' | 'battle' | null
    this.wantLoop = kind === 'forest' ? 'amb-forest' : kind === 'town' ? 'amb-town' : null;
    if (this.wantLoop) this.ambience(this.wantLoop); else this.stopAmbience();
    const M = { title: 'title', world: 'world', forest: 'forest', town: 'town', battle: 'battle', shop: 'extra-shop' };
    if (kind in M) this.music(M[kind]);
    if (kind === 'world') this.play('wind', { gain: 0.35 });
  }
  voice(who, kind) { // Rita's voice one-shots: voice-<id>-<kind>[-n]
    if (!this.ctx) return; if (kind === 'talk') kind = 'blip'; if (!['itsuki', 'benika', 'gonzo'].includes(who)) return this.blip(who); const n = { grunt: 3, attack: 3, blip: 3 }[kind]; const key = `voice-${who}-${kind}${n ? '-' + (1 + (Math.random() * n | 0)) : ''}`;
    this.load(key, `${this.base}assets/voice/${key}.mp3`).then((b) => { if (!b || this.ctx.state !== 'running') return; const s = this.ctx.createBufferSource(), g = this.ctx.createGain(); s.buffer = b; g.gain.value = 0.85 * this.vol.voice; s.connect(g); g.connect(this.out); s.start(); });
  }
  blip(who) { if (!this.ctx || this.ctx.state !== 'running') return; const f = BLIPS[`blip-${who}`]; if (f) f(this.ctx, this.out, this.ctx.currentTime); else this.play('text'); }
  // --- music: Cody's cues (team/audio/music, synthesized in-house), loop points from its manifest ---
  async loadMusicMeta() { if (this.mmeta) return this.mmeta; try { const m = await (await fetch(this.base + 'assets/music/manifest.json')).json(); this.mmeta = Object.fromEntries(m.tracks.map((t) => [t.key, t])); } catch (e) { this.mmeta = {}; } return this.mmeta; }
  async music(key, o = {}) {
    this.wantMusic = key; if (!this.ctx) return; if (this.musicKey === key && this.musicSrc) return;
    this.stopMusic(o.fade ?? 0.8);
    if (!key) return;
    const meta = (await this.loadMusicMeta())[key] || {}; const b = await this.load('m-' + key, `${this.base}assets/music/${meta.file || key + '.mp3'}`);
    if (!b || this.wantMusic !== key) return;
    const s = this.ctx.createBufferSource(), g = this.ctx.createGain(); s.buffer = b;
    const loop = o.loop ?? meta.loop ?? true; s.loop = loop; if (loop) { s.loopStart = meta.loopStart ?? PAD; s.loopEnd = Math.min(b.duration, meta.loopEnd ?? b.duration - PAD); }
    const t = this.ctx.currentTime, v = (o.gain ?? 0.5) * this.vol.music;
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(v, t + (o.fadeIn ?? 1.0)); s.connect(g); g.connect(this.out); s.start(0, PAD);
    if (!loop) s.onended = () => { if (this.musicSrc === s) { this.musicSrc = null; this.musicKey = null; if (o.then) this.music(o.then); } };
    this.musicSrc = s; this.musicGain = g; this.musicKey = key;
  }
  stopMusic(f = 0.8) { if (!this.musicSrc) return; const s = this.musicSrc, g = this.musicGain, t = this.ctx.currentTime; g.gain.cancelScheduledValues(t); g.gain.setValueAtTime(g.gain.value, t); g.gain.linearRampToValueAtTime(0, t + f); try { s.stop(t + f + 0.05); } catch (e) {} this.musicSrc = null; this.musicKey = null; }
  /** one-shot sting over the current music (transform sting, victory fanfare) */
  async sting(key, gain = 0.7) { const meta = (await this.loadMusicMeta())[key] || {}; const b = await this.load('m-' + key, `${this.base}assets/music/${meta.file || key + '.mp3'}`); if (!b || this.ctx.state !== 'running') return; const s = this.ctx.createBufferSource(), g = this.ctx.createGain(); s.buffer = b; g.gain.value = gain * this.vol.music; s.connect(g); g.connect(this.out); s.start(0, PAD); }
}
