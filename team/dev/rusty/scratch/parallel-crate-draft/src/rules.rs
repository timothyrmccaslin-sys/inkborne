//! Pure rules: timing judgement, Six Inks, damage curve, seeded RNG, tunables loaded from JSON.
use serde_json::Value;
use std::collections::BTreeMap;

/// Clean Line half-width in ms: |press - target| <= CLEAN_MS. Widened from 70 per Richard's iPad findings.
pub const CLEAN_MS: f64 = 95.0;
/// Good half-width in ms: CLEAN_MS < |delta| <= GOOD_MS. Outside = miss (chain ends).
pub const GOOD_MS: f64 = 150.0;

/// Grade a press with the default windows. `delta_ms` = press time - target time.
/// 2 = Clean Line, 1 = good, 0 = miss.
pub fn judge_delta(delta_ms: f64) -> u8 { judge_with(delta_ms, CLEAN_MS, GOOD_MS) }
pub fn judge_with(delta_ms: f64, clean: f64, good: f64) -> u8 {
    if !delta_ms.is_finite() { return 0 }
    let d = delta_ms.abs();
    if d <= clean { 2 } else if d <= good { 1 } else { 0 }
}

/// Six Inks (SPEC section 2): opposite pair x2, same x0.5, else x1. Empty or "none" = x1.
pub fn elem_mod(atk: &str, def: &str) -> f64 {
    let opp = |a: &str| match a { "ember" => "tide", "tide" => "ember", "gale" => "stone", "stone" => "gale", "dawn" => "dusk", "dusk" => "dawn", _ => "" };
    if atk.is_empty() || def.is_empty() || atk == "none" || def == "none" { 1.0 }
    else if opp(atk) == def { 2.0 } else if atk == def { 0.5 } else { 1.0 }
}

/// Jake's damage curve: never below a quarter of attack.
pub fn raw(a: f64, d: f64) -> f64 { (a * 2.0 - d).max(a * 0.25) }

/// xorshift64, deterministic and WASM-safe (no clock, no OS entropy).
#[derive(Clone, Debug)]
pub struct Rng(pub u64);
impl Rng {
    pub fn new(seed: u32) -> Rng { Rng((seed as u64).wrapping_mul(2654435761).wrapping_add(0x9E37_79B9_7F4A_7C15) | 1) }
    pub fn next(&mut self) -> f64 { self.0 ^= self.0 << 13; self.0 ^= self.0 >> 7; self.0 ^= self.0 << 17; (self.0 >> 11) as f64 / (1u64 << 53) as f64 }
    pub fn below(&mut self, n: usize) -> usize { if n == 0 { 0 } else { ((self.next() * n as f64) as usize).min(n - 1) } }
}

#[derive(Clone, Debug)]
pub struct Form { pub name: String, pub element: String, pub stroke_element: String, pub passive: String, pub mult: [f64; 5] }

/// Everything tunable. Defaults equal Jake's transformation.json as of 2026-11-15.
#[derive(Clone, Debug)]
pub struct Rules {
    pub ink_max: f64,
    pub fill_stroke_hit: f64, pub fill_clean_bonus: f64, pub fill_chain_complete: f64, pub fill_perfect: f64,
    pub perfect_replaces_complete: bool, pub fill_kill: f64,
    pub dmg_per_pct: f64, pub dmg_min: f64, pub dmg_max: f64,
    pub still_water_fill: f64, pub still_water_dmg_mult: f64, pub gain_while_inkwing: bool,
    pub ko_resets_ink: bool,
    pub unfurl_cost: f64, pub unfurl_heal_pct: f64, pub unfurl_turns: u32,
    pub guard_heal_pct: f64, pub guard_heal_pct_inkwing: f64, pub guard_mult: f64,
    pub clean_mult: f64, pub seal_miss_mult: f64,
    pub forms: BTreeMap<String, Form>,
    // timing
    pub clean_ms: f64, pub good_ms: f64, pub anchor_close: bool, pub hit_windows: BTreeMap<String, (Option<f64>, Option<f64>)>,
    pub seal_gap_ms: f64,
    // misc config
    pub enemy_damage_mult: f64, pub flee_base: f64, pub var_min: f64, pub var_max: f64,
    pub chart: Option<BTreeMap<String, BTreeMap<String, f64>>>,
}

impl Default for Rules {
    fn default() -> Self {
        Rules {
            ink_max: 100.0, fill_stroke_hit: 5.0, fill_clean_bonus: 4.0, fill_chain_complete: 4.0, fill_perfect: 8.0,
            perfect_replaces_complete: true, fill_kill: 3.0, dmg_per_pct: 0.3, dmg_min: 1.0, dmg_max: 15.0,
            still_water_fill: 6.0, still_water_dmg_mult: 1.5, gain_while_inkwing: false, ko_resets_ink: false,
            unfurl_cost: 100.0, unfurl_heal_pct: 15.0, unfurl_turns: 3,
            guard_heal_pct: 10.0, guard_heal_pct_inkwing: 15.0, guard_mult: 0.5, clean_mult: 1.25, seal_miss_mult: 0.5,
            forms: BTreeMap::new(),
            clean_ms: CLEAN_MS, good_ms: GOOD_MS, anchor_close: false, hit_windows: BTreeMap::new(), seal_gap_ms: 600.0,
            enemy_damage_mult: 0.8, flee_base: 0.5, var_min: 0.95, var_max: 1.05, chart: None,
        }
    }
}

fn f(v: &Value, k: &str, d: f64) -> f64 { v.get(k).and_then(|x| x.as_f64()).unwrap_or(d) }

impl Rules {
    /// Read Jake's transformation.json (any subset).
    pub fn apply_transformation(&mut self, v: &Value) {
        if let Some(g) = v.get("gauge") { self.ink_max = f(g, "max", self.ink_max); }
        if let Some(x) = v.get("fill") {
            self.fill_stroke_hit = f(x, "stroke_hit", self.fill_stroke_hit);
            self.fill_clean_bonus = f(x, "clean_line_bonus", self.fill_clean_bonus);
            self.fill_chain_complete = f(x, "chain_complete_bonus", self.fill_chain_complete);
            self.fill_perfect = f(x, "perfect_chain_bonus", self.fill_perfect);
            if let Some(b) = x.get("perfect_chain_replaces_complete").and_then(|b| b.as_bool()) { self.perfect_replaces_complete = b }
            self.fill_kill = f(x, "kill_bonus", self.fill_kill);
            if let Some(d) = x.get("damage_taken") {
                self.dmg_per_pct = f(d, "per_pct_hp_lost", self.dmg_per_pct);
                self.dmg_min = f(d, "min_if_damaged", self.dmg_min);
                self.dmg_max = f(d, "max_per_hit", self.dmg_max);
            }
            self.still_water_fill = f(x, "still_water_use", self.still_water_fill);
            self.still_water_dmg_mult = f(x, "still_water_damage_taken_mult", self.still_water_dmg_mult);
            if let Some(b) = x.get("gain_while_inkwing").and_then(|b| b.as_bool()) { self.gain_while_inkwing = b }
        }
        if let Some(r) = v.get("reset") { if let Some(s) = r.get("on_ko").and_then(|s| s.as_str()) { self.ko_resets_ink = s != "keep"; } }
        if let Some(u) = v.get("unfurl") {
            self.unfurl_cost = f(u, "cost", self.unfurl_cost);
            self.unfurl_heal_pct = f(u, "heal_pct_max_hp", self.unfurl_heal_pct);
            self.unfurl_turns = f(u, "duration_turns", self.unfurl_turns as f64) as u32;
        }
        if let Some(r) = v.get("inkwing_rules") { self.guard_heal_pct_inkwing = f(r, "still_water_heal_pct", self.guard_heal_pct_inkwing); }
        if let Some(fs) = v.get("forms").and_then(|x| x.as_object()) {
            for (id, x) in fs {
                let m = x.get("mult").cloned().unwrap_or(Value::Null);
                let g = |k: &str| m.get(k).and_then(|y| y.as_f64()).unwrap_or(1.0);
                let el = x.get("element").and_then(|s| s.as_str()).unwrap_or("").to_string();
                self.forms.insert(id.clone(), Form {
                    name: x.get("form_name").and_then(|s| s.as_str()).unwrap_or("").into(),
                    stroke_element: x.get("strokes_element").and_then(|s| s.as_str()).map(|s| s.to_string()).unwrap_or_else(|| el.clone()),
                    element: el,
                    passive: x.get("passive").and_then(|p| p.get("id")).and_then(|s| s.as_str()).unwrap_or("").into(),
                    mult: [g("atk"), g("def"), g("mat"), g("mdf"), g("spd")],
                });
            }
        }
        if let Some(cw) = v.get("combo_windows") { self.apply_windows(cw); }
    }
    /// `{ clean_ms, good_ms, anchor: "press"|"close", seal_gap_ms, hits: { "<stroke_id>#<n>": { clean_ms, good_ms } } }`
    pub fn apply_windows(&mut self, v: &Value) {
        self.clean_ms = f(v, "clean_ms", self.clean_ms);
        self.good_ms = f(v, "good_ms", self.good_ms).max(self.clean_ms);
        self.seal_gap_ms = f(v, "seal_gap_ms", self.seal_gap_ms);
        if let Some(a) = v.get("anchor").and_then(|s| s.as_str()) { self.anchor_close = a == "close"; }
        if let Some(h) = v.get("hits").and_then(|h| h.as_object()) {
            for (k, x) in h { self.hit_windows.insert(k.clone(), (x.get("clean_ms").and_then(|y| y.as_f64()), x.get("good_ms").and_then(|y| y.as_f64()))); }
        }
    }
    pub fn apply_config(&mut self, v: &Value) {
        self.enemy_damage_mult = f(v, "enemy_damage_mult", self.enemy_damage_mult);
        self.seal_gap_ms = f(v, "seal_gap_ms", self.seal_gap_ms);
        self.flee_base = f(v, "flee_base", self.flee_base);
        self.var_min = f(v, "var_min", self.var_min);
        self.var_max = f(v, "var_max", self.var_max).max(self.var_min);
        if let Some(cw) = v.get("combo_windows") { self.apply_windows(cw); }
    }
    /// Jake's elements.json `chart`.
    pub fn apply_elements(&mut self, v: &Value) -> bool {
        let Some(c) = v.get("chart").and_then(|c| c.as_object()) else { return false };
        let mut out = BTreeMap::new();
        for (a, row) in c {
            let mut r = BTreeMap::new();
            if let Some(o) = row.as_object() { for (d, m) in o { if let Some(m) = m.as_f64() { r.insert(d.clone(), m); } } }
            out.insert(a.clone(), r);
        }
        self.chart = Some(out); true
    }
    pub fn elem(&self, atk: &str, def: &str) -> f64 {
        if let Some(c) = &self.chart { if let Some(m) = c.get(atk).and_then(|r| r.get(def)) { return *m } }
        elem_mod(atk, def)
    }
    /// Windows (clean, good) for one hit of a stroke.
    pub fn windows_for(&self, stroke_id: &str, n: usize, hit_clean: Option<f64>, hit_good: Option<f64>) -> (f64, f64) {
        let (mut c, mut g) = (self.clean_ms, self.good_ms);
        if let Some((oc, og)) = self.hit_windows.get(&format!("{stroke_id}#{n}")) { if let Some(x) = oc { c = *x } if let Some(x) = og { g = *x } }
        if let Some(x) = hit_clean { c = x } if let Some(x) = hit_good { g = x }
        (c, g.max(c))
    }
    /// Ink from damage taken: round(per_pct*100*dmg/max) clamped min..max, x mult in Still Water.
    pub fn ink_from_damage(&self, dmg: f64, max_hp: f64, guarding: bool) -> f64 {
        if dmg <= 0.0 || max_hp <= 0.0 { return 0.0 }
        let mut g = self.dmg_per_pct * 100.0 * dmg / max_hp;
        if guarding { g *= self.still_water_dmg_mult }
        (g + 0.5).floor().clamp(self.dmg_min, self.dmg_max)
    }
}
