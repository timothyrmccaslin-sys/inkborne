//! Inkborne core: battle rules, Brushstroke timing judgement, Vermilion Ink / Inkwing,
//! Six Inks elements, Still Water guard, items, inventory + mon, POI walker collision, saves.
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::BTreeMap;
use wasm_bindgen::prelude::*;

// ---------- data ----------
#[derive(Clone, Serialize, Deserialize)]
pub struct Hit { pub gap_ms: f64, pub mult: f64,
    /// Optional per-hit window overrides (half-widths, ms).
    #[serde(default, skip_serializing_if = "Option::is_none")] pub clean_ms: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")] pub good_ms: Option<f64> }
#[derive(Clone, Serialize, Deserialize)]
pub struct Stroke { pub id: String, pub name: String, pub hits: Vec<Hit>, pub finish_mult: f64 }
#[derive(Clone, Serialize, Deserialize)]
pub struct Seal { pub name: String, pub seals: u32, pub mult: f64, pub element: String, #[serde(default = "mat_s")] pub stat: String }
fn mat_s() -> String { "mat".into() }
#[derive(Clone, Serialize, Deserialize)]
pub struct Member {
    pub id: String, pub name: String, #[serde(default)] pub title: String, pub element: String, pub lv: u32,
    pub hp: f64, pub atk: f64, pub def: f64, pub mat: f64, pub mdf: f64, pub spd: f64, pub ink: f64,
    pub strokes: Vec<Stroke>, pub seal: Seal,
    #[serde(default)] pub cur_hp: Option<f64>,
    /// Jake's precomputed per-level stats (index = lv - 1). Optional; needed for level-ups.
    #[serde(default, skip_serializing)] pub stat_table: Vec<StatRow>,
}
#[derive(Clone, Serialize, Deserialize)]
pub struct Move { pub id: String, pub name: String, pub kind: String, #[serde(default = "one_f")] pub power: f64, #[serde(default)] pub element: Option<String>, #[serde(default = "one_u")] pub weight: u32,
    /// AI: target rule (see `enemy_turn`) and HP gate. Optional.
    #[serde(default, skip_serializing_if = "Option::is_none")] pub target: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")] pub hp_below: Option<f64> }
fn one_f() -> f64 { 1.0 }
fn one_u() -> u32 { 1 }
#[derive(Clone, Serialize, Deserialize)]
pub struct EnemyDef { pub id: String, pub name: String, pub element: String, pub hp: f64, pub atk: f64, pub def: f64, pub mat: f64, pub mdf: f64, pub spd: f64, pub mon: u32, pub moves: Vec<Move>,
    /// XP awarded at victory (SPEC section 7, optional, default 0).
    #[serde(default)] pub xp: u32,
    /// Default AI target rule for this enemy's moves (optional).
    #[serde(default, skip_serializing_if = "Option::is_none")] pub ai: Option<String> }
#[derive(Clone, Serialize, Deserialize)]
pub struct Item { pub id: String, pub name: String, pub desc: String, pub kind: String, pub power: f64, #[serde(default)] pub element: Option<String>, pub price: u32 }

#[derive(Deserialize)] struct PartyFile { members: Vec<Member>, #[serde(default)] progression: Progression }
#[derive(Clone, Serialize, Deserialize)]
pub struct StatRow { pub lv: u32, pub hp: f64, pub atk: f64, pub def: f64, pub mat: f64, pub mdf: f64, pub spd: f64 }
#[derive(Clone, Serialize, Deserialize)]
pub struct XpRow { pub lv: u32, pub total: u32, #[serde(default)] pub to_next: u32 }
/// Jake's party.json `progression` (level_cap, xp_table with cumulative `total` per level). Optional.
#[derive(Clone, Default, Deserialize)]
struct Progression { #[serde(default)] level_cap: u32, #[serde(default)] xp_table: Vec<XpRow> }
impl Progression {
    fn total_at(&self, lv: u32) -> Option<u32> { self.xp_table.iter().find(|r| r.lv == lv).map(|r| r.total) }
    fn cap(&self) -> u32 { if self.level_cap > 0 { self.level_cap } else { self.xp_table.iter().map(|r| r.lv).max().unwrap_or(1) } }
    /// Level for a cumulative XP total (never below `floor`).
    fn level_for(&self, xp: u32, floor: u32) -> u32 { let mut lv = floor.max(1); while lv < self.cap() { match self.total_at(lv + 1) { Some(t) if xp >= t => lv += 1, _ => break } } lv }
}
#[derive(Deserialize)] struct EnemyFile { enemies: Vec<EnemyDef>, encounters: BTreeMap<String, Vec<String>> }
#[derive(Deserialize)] struct ItemFile { items: Vec<Item> }

/// Six Inks: opposite pairs deal x2, same element x0.5.
pub fn elem_mod(atk: &str, def: &str) -> f64 {
    let opp = |a: &str| match a { "ember" => "tide", "tide" => "ember", "gale" => "stone", "stone" => "gale", "dawn" => "dusk", "dusk" => "dawn", _ => "" };
    if atk.is_empty() || def.is_empty() || atk == "none" || def == "none" { 1.0 } else if opp(atk) == def { 2.0 } else if atk == def { 0.5 } else { 1.0 }
}

/// Brushstroke judgement. `delta_ms` = press time - ring-close (target) time.
/// 2 = Clean Line, 1 = good, 0 = miss (chain breaks). Windows are HALF-widths in ms, symmetric early/late.
/// Clean widened 70 -> 95 per Richard's iPad touch findings (core/tests/combo-timing-findings.md).
/// Both are defaults; data can override them (`combo_windows`, see `Game::set_combo_windows`).
pub const CLEAN_MS: f64 = 95.0;
pub const GOOD_MS: f64 = 150.0;
/// Damage variance bounds (Jake, DESIGN.md section 2).
pub const VAR_MIN: f64 = 0.95;
pub const VAR_MAX: f64 = 1.05;
pub fn judge_delta(delta_ms: f64) -> u8 { judge_with(delta_ms, CLEAN_MS, GOOD_MS) }
/// Judgement with explicit half-widths. Non-finite input is a miss.
pub fn judge_with(delta_ms: f64, clean_ms: f64, good_ms: f64) -> u8 {
    if !delta_ms.is_finite() { return 0 }
    let d = delta_ms.abs(); if d <= clean_ms { 2 } else if d <= good_ms.max(clean_ms) { 1 } else { 0 }
}

/// Combo timing windows (data-overridable). `anchor_close`: hit n+1 is measured from hit n's target
/// time instead of from the actual press (default: from the press, agreed with Jake/Tim).
#[derive(Clone)]
struct Windows { clean: f64, good: f64, anchor_close: bool, per_hit: BTreeMap<String, (Option<f64>, Option<f64>)> }
impl Default for Windows { fn default() -> Self { Windows { clean: CLEAN_MS, good: GOOD_MS, anchor_close: false, per_hit: BTreeMap::new() } } }
impl Windows {
    fn apply(&mut self, v: &Value) {
        if let Some(x) = v["clean_ms"].as_f64() { self.clean = x.max(0.0) }
        if let Some(x) = v["good_ms"].as_f64() { self.good = x.max(0.0) }
        self.good = self.good.max(self.clean);
        if let Some(a) = v["anchor"].as_str() { self.anchor_close = a == "close" }
        if let Some(h) = v["hits"].as_object() { for (k, x) in h { self.per_hit.insert(k.clone(), (x["clean_ms"].as_f64(), x["good_ms"].as_f64())); } }
    }
    /// Windows for hit `n` of stroke `sid`: defaults < combo_windows < combo_windows.hits["sid#n"] < party.json hit fields.
    fn for_hit(&self, sid: &str, n: usize, h: &Hit) -> (f64, f64) {
        let (mut c, mut g) = (self.clean, self.good);
        if let Some((oc, og)) = self.per_hit.get(&format!("{sid}#{n}")) { if let Some(x) = oc { c = *x } if let Some(x) = og { g = *x } }
        if let Some(x) = h.clean_ms { c = x } if let Some(x) = h.good_ms { g = x }
        (c, g.max(c))
    }
}

/// An in-progress timed Brushstroke Chain (renderer-driven, see `begin_stroke`/`press`/`combo_tick`).
/// Vermilion Ink + Unfurl rules. Fallback defaults mirror Jake's team/systems/jake/transformation.json (2026-11-15 3:36 PM);
/// `set_rules(transformation.json)` overrides any subset.
#[derive(Clone)]
struct InkRules {
    max: f64, stroke_hit: f64, clean_bonus: f64, chain_complete: f64, perfect_chain: f64, perfect_replaces: bool, kill: f64,
    dmg_per_pct: f64, dmg_min: f64, dmg_max: f64, still_water_use: f64, still_water_dmg_mult: f64, gain_while_inkwing: bool,
    ko_reset: bool, unfurl_cost: f64, unfurl_heal_pct: f64, unfurl_turns: u32,
}
impl Default for InkRules {
    fn default() -> Self {
        InkRules { max: 100.0, stroke_hit: 4.0, clean_bonus: 4.0, chain_complete: 6.0, perfect_chain: 10.0, perfect_replaces: true, kill: 3.0,
            dmg_per_pct: 0.3, dmg_min: 1.0, dmg_max: 15.0, still_water_use: 6.0, still_water_dmg_mult: 1.5, gain_while_inkwing: false,
            ko_reset: true, unfurl_cost: 100.0, unfurl_heal_pct: 15.0, unfurl_turns: 3 }
    }
}
impl InkRules {
    fn apply(&mut self, v: &Value) {
        let f = |x: &Value, d: f64| x.as_f64().unwrap_or(d);
        self.max = f(&v["gauge"]["max"], self.max).max(1.0);
        let fl = &v["fill"];
        self.stroke_hit = f(&fl["stroke_hit"], self.stroke_hit);
        self.clean_bonus = f(&fl["clean_line_bonus"], self.clean_bonus);
        self.chain_complete = f(&fl["chain_complete_bonus"], self.chain_complete);
        self.perfect_chain = f(&fl["perfect_chain_bonus"], self.perfect_chain);
        if let Some(b) = fl["perfect_chain_replaces_complete"].as_bool() { self.perfect_replaces = b }
        self.kill = f(&fl["kill_bonus"], self.kill);
        let dt = &fl["damage_taken"];
        self.dmg_per_pct = f(&dt["per_pct_hp_lost"], self.dmg_per_pct);
        self.dmg_min = f(&dt["min_if_damaged"], self.dmg_min);
        self.dmg_max = f(&dt["max_per_hit"], self.dmg_max).max(self.dmg_min);
        self.still_water_use = f(&fl["still_water_use"], self.still_water_use);
        self.still_water_dmg_mult = f(&fl["still_water_damage_taken_mult"], self.still_water_dmg_mult);
        if let Some(b) = fl["gain_while_inkwing"].as_bool() { self.gain_while_inkwing = b }
        // on_ko: a number (Jake: 0 = ink resets) or the legacy strings "keep"/"reset"
        match &v["reset"]["on_ko"] { Value::String(s) => self.ko_reset = s != "keep", Value::Number(_) => self.ko_reset = true, _ => {} }
        let u = &v["unfurl"];
        self.unfurl_cost = f(&u["cost"], self.unfurl_cost).min(self.max);
        self.unfurl_heal_pct = f(&u["heal_pct_max_hp"], self.unfurl_heal_pct);
        if let Some(t) = u["duration_turns"].as_u64() { self.unfurl_turns = (t as u32).max(1) }
    }
    /// Ink from damage taken: round_half_up(per_pct*100*dmg/max_hp [x1.5 in Still Water]) clamped to min..max.
    fn from_damage(&self, dmg: f64, max_hp: f64, guarding: bool) -> f64 {
        if dmg <= 0.0 || max_hp <= 0.0 { return 0.0 }
        let mut g = self.dmg_per_pct * 100.0 * dmg / max_hp;
        if guarding { g *= self.still_water_dmg_mult }
        (g + 0.5).floor().clamp(self.dmg_min, self.dmg_max)
    }
}

/// Still Water (guard): damage taken x`damage_mult` until the guarder's next turn, heal `heal_pct`% max HP
/// (`heal_pct_inkwing`% in Inkwing). SPEC section 2: halves damage, heals 10%. Jake: 15% in Inkwing.
/// Data: transformation.json `inkwing_rules.still_water_heal_pct`, optional `still_water { damage_mult, heal_pct }`.
#[derive(Clone)]
struct GuardRules { damage_mult: f64, heal_pct: f64, heal_pct_inkwing: f64 }
impl Default for GuardRules { fn default() -> Self { GuardRules { damage_mult: 0.5, heal_pct: 10.0, heal_pct_inkwing: 15.0 } } }

/// Flee chance (seeded, deterministic): p = clamp(base + per_spd * (avg party SPD - avg enemy SPD)
/// + per_fail * failed_attempts_this_battle, min, max), using living fighters' effective SPD (Inkwing applied).
/// Success iff rng.next() < p. Data: optional `flee {base, per_spd, per_fail, min, max}` in set_rules / set_flee_rules.
#[derive(Clone)]
struct FleeRules { base: f64, per_spd: f64, per_fail: f64, min: f64, max: f64 }
impl Default for FleeRules { fn default() -> Self { FleeRules { base: 0.5, per_spd: 0.05, per_fail: 0.25, min: 0.25, max: 0.95 } } }
impl FleeRules {
    fn apply(&mut self, v: &Value) {
        let f = |k: &str, d: f64| v[k].as_f64().filter(|x| x.is_finite()).unwrap_or(d);
        self.base = f("base", self.base); self.per_spd = f("per_spd", self.per_spd); self.per_fail = f("per_fail", self.per_fail);
        self.min = f("min", self.min).clamp(0.0, 1.0); self.max = f("max", self.max).clamp(self.min, 1.0);
    }
}

#[derive(Clone)]
struct Combo { actor: usize, target: usize, stroke_idx: usize, stroke_id: String, name: String, hits: Vec<(f64, f64, f64)>, next: usize, anchor: f64, grades: Vec<u8>, presses: Vec<f64> }

struct Rng(u64);
impl Rng {
    /// Uniform index in 0..n (0 when n == 0).
    fn below(&mut self, n: usize) -> usize { if n == 0 { 0 } else { ((self.next() * n as f64) as usize).min(n - 1) } }
    fn next(&mut self) -> f64 { self.0 ^= self.0 << 13; self.0 ^= self.0 >> 7; self.0 ^= self.0 << 17; (self.0 >> 11) as f64 / (1u64 << 53) as f64 } }

#[derive(Clone, Serialize)]
struct Fighter { side: u8, idx: usize, id: String, name: String, element: String, hp: f64, max_hp: f64, atk: f64, def: f64, mat: f64, mdf: f64, spd: f64,
    ink: f64, guarding: bool, inkwing: u32, alive: bool, mon: u32, #[serde(skip)] fm: [f64; 5], form: String }

// Save state lives in save.rs (Jared): schema `version`, `equipped`, validated load, `load_warnings()`.
mod save;
use save::Save;

#[wasm_bindgen]
pub struct Game {
    party: Vec<Member>, enemies: Vec<EnemyDef>, encounters: BTreeMap<String, Vec<String>>, items: Vec<Item>,
    st: Save, rng: Rng,
    // battle
    fighters: Vec<Fighter>, order: Vec<usize>, turn_pos: usize, round: u32, battle_over: Option<String>,
    // walker
    walk: Walker,
    forms: BTreeMap<String, (String, String, [f64; 5])>,
    win: Windows, combo: Option<Combo>, ink: InkRules,
    /// Optional Six Inks chart from Jake's elements.json (`chart[attack][defend]`); falls back to `elem_mod`.
    chart: Option<BTreeMap<String, BTreeMap<String, f64>>>,
    guard_rules: GuardRules,
    enemy_dmg_mult: f64,
    // encounter flags (Ashley's zones.json `fixed.<id>.canFlee`, encounters.js `first`)
    can_flee: bool, first: Option<String>, flee_fails: u32, flee_rules: FleeRules,
    progression: Progression, rewards: Option<Value>,
}
/// Inkwing multipliers [atk, def, mat, mdf, spd] from transformation.json (Jake).
fn forms_of(f: &BTreeMap<String, (String, String, [f64; 5])>, id: &str) -> [f64; 5] { f.get(id).map(|x| x.2).unwrap_or([1.5, 1.25, 1.3, 1.25, 1.0]) }
/// Jake's damage curve: never below a quarter of attack.
pub fn raw(a: f64, d: f64) -> f64 { (a * 2.0 - d).max(a * 0.25) }

#[derive(Default)]
struct Walker { x: f64, y: f64, w: f64, h: f64, solids: Vec<[f64; 4]>, triggers: Vec<(String, [f64; 4])>, r: f64 }
fn overlap(x: f64, y: f64, r: f64, s: &[f64; 4]) -> bool { x + r > s[0] && x - r < s[0] + s[2] && y + r * 0.5 > s[1] && y - r * 0.5 < s[1] + s[3] }

#[wasm_bindgen]
impl Game {
    #[wasm_bindgen(constructor)]
    pub fn new(party_json: &str, enemies_json: &str, items_json: &str, seed: u32) -> Result<Game, JsValue> {
        let p: PartyFile = serde_json::from_str(party_json).map_err(|e| JsValue::from_str(&format!("party.json: {e}")))?;
        let e: EnemyFile = serde_json::from_str(enemies_json).map_err(|e| JsValue::from_str(&format!("enemies.json: {e}")))?;
        let i: ItemFile = serde_json::from_str(items_json).map_err(|e| JsValue::from_str(&format!("items.json: {e}")))?;
        let mut st = Save { gold: 120, node: String::new(), ..Default::default() };
        st.inv.insert("rice_cake".into(), 3); st.inv.insert("paper_cracker".into(), 1); st.inv.insert("inkstone_chip".into(), 1);
        for m in &p.members { st.hp.insert(m.id.clone(), m.hp); st.ink.insert(m.id.clone(), m.ink);
            st.lv.insert(m.id.clone(), m.lv.max(1)); st.xp.insert(m.id.clone(), p.progression.total_at(m.lv).unwrap_or(0)); }
        let progression = p.progression;
        Ok(Game { party: p.members, enemies: e.enemies, encounters: e.encounters, items: i.items, st, rng: Rng(seed as u64 * 2654435761 + 1),
            fighters: vec![], order: vec![], turn_pos: 0, round: 0, battle_over: None, walk: Walker::default(), forms: BTreeMap::new(), win: Windows::default(), combo: None, ink: InkRules::default(), chart: None, guard_rules: GuardRules::default(), enemy_dmg_mult: 0.8, can_flee: true, first: None, flee_fails: 0, flee_rules: FleeRules::default(), progression, rewards: None })
    }

    /// Load Inkwing forms from transformation.json (optional; defaults otherwise).
    pub fn set_rules(&mut self, tj: &str) -> bool {
        let Ok(v) = serde_json::from_str::<Value>(tj) else { return false };
        if let Some(f) = v["forms"].as_object() { for (id, x) in f {
            let m = &x["mult"]; let g = |k: &str| m[k].as_f64().unwrap_or(1.0);
            self.forms.insert(id.clone(), (x["form_name"].as_str().unwrap_or("").into(), x["passive"]["id"].as_str().unwrap_or("").into(), [g("atk"), g("def"), g("mat"), g("mdf"), g("spd")]));
        } }
        if v["combo_windows"].is_object() { self.win.apply(&v["combo_windows"]); }
        if v["flee"].is_object() { self.flee_rules.apply(&v["flee"]); }
        self.ink.apply(&v);
        if let Some(x) = v["inkwing_rules"]["still_water_heal_pct"].as_f64() { self.guard_rules.heal_pct_inkwing = x.max(0.0) }
        if let Some(x) = v["still_water"]["heal_pct"].as_f64() { self.guard_rules.heal_pct = x.max(0.0) }
        if let Some(x) = v["still_water"]["damage_mult"].as_f64() { self.guard_rules.damage_mult = x.clamp(0.0, 1.0) }
        true
    }
    /// Load Jake's elements.json (`{"chart": {"ember": {"tide": 2.0, ...}, ...}}`). Optional: without it the
    /// SPEC section 2 rule (opposite x2, same x0.5, else x1) is used. Pairs missing from the chart also fall back.
    pub fn set_elements(&mut self, ej: &str) -> bool {
        let Ok(v) = serde_json::from_str::<Value>(ej) else { return false };
        let Some(c) = v["chart"].as_object() else { return false };
        let mut out = BTreeMap::new();
        for (a, row) in c { let mut r = BTreeMap::new(); if let Some(o) = row.as_object() { for (d, m) in o { if let Some(m) = m.as_f64() { r.insert(d.clone(), m); } } } out.insert(a.clone(), r); }
        self.chart = Some(out); true
    }
    /// Element multiplier attack element -> defender element (chart if loaded, else the SPEC rule).
    pub fn elem(&self, atk: &str, def: &str) -> f64 {
        if let Some(m) = self.chart.as_ref().and_then(|c| c.get(atk)).and_then(|r| r.get(def)) { return *m }
        elem_mod(atk, def)
    }
    /// UI hint for one fighter: `{element, weak:[...x>1], resist:[...x<1]}` over the six inks.
    pub fn affinity_json(&self, target: usize) -> String {
        let Some(f) = self.fighters.get(target) else { return "null".into() };
        let all = ["ember", "tide", "gale", "stone", "dawn", "dusk"];
        let weak: Vec<&str> = all.iter().copied().filter(|a| self.elem(a, &f.element) > 1.0).collect();
        let resist: Vec<&str> = all.iter().copied().filter(|a| self.elem(a, &f.element) < 1.0).collect();
        json!({"element": f.element, "weak": weak, "resist": resist}).to_string()
    }
    /// Override combo windows: `{ "clean_ms": 95, "good_ms": 150, "anchor": "press"|"close",
    /// "hits": { "<stroke_id>#<hit index>": { "clean_ms", "good_ms" } } }` (any subset). Half-widths in ms.
    pub fn set_combo_windows(&mut self, cj: &str) -> bool {
        let Ok(v) = serde_json::from_str::<Value>(cj) else { return false };
        if !v.is_object() { return false }
        self.win.apply(&v); true
    }
    fn passive_on(&self, pid: &str) -> bool { self.fighters.iter().any(|f| f.side == 0 && f.alive && f.inkwing > 0 && self.forms.get(&f.id).map(|x| x.1 == pid).unwrap_or(false)) }
    fn st(&self, i: usize, k: usize) -> f64 { let f = &self.fighters[i]; let b = [f.atk, f.def, f.mat, f.mdf, f.spd][k]; if f.inkwing > 0 { b * f.fm[k] } else { b } }
    fn add_ink(&mut self, i: usize, n: f64) { let f = &mut self.fighters[i]; if f.side == 0 && f.alive && (f.inkwing == 0 || self.ink.gain_while_inkwing) { f.ink = (f.ink + n).clamp(0.0, self.ink.max); } }
    // ---------- save / economy ----------
    pub fn save_json(&self) -> String { serde_json::to_string(&self.st).unwrap() }
    /// Lenient, validated load (save.rs). `false` only for unreadable input, and then state is untouched.
    pub fn load_json(&mut self, s: &str) -> bool { self.load_save(s) }
    /// Set member `i`'s stats from `stat_table[lv-1]` (no-op without a table). Returns the max-HP gain.
    fn apply_level(&mut self, i: usize, lv: u32) -> f64 {
        let m = &mut self.party[i];
        let Some(r) = m.stat_table.iter().find(|r| r.lv == lv).cloned() else { return 0.0 };
        let gain = r.hp - m.hp;
        m.lv = lv; m.hp = r.hp; m.atk = r.atk; m.def = r.def; m.mat = r.mat; m.mdf = r.mdf; m.spd = r.spd;
        gain
    }
    /// XP/level-ups from the last victory: `{mon, xp, members:[{id, name, alive, gained, xp, lv_before, lv, leveled_up, next_total, stats?}]}` or null.
    pub fn rewards_json(&self) -> String { self.rewards.clone().unwrap_or(Value::Null).to_string() }
    pub fn gold(&self) -> u32 { self.st.gold }
    pub fn set_flag(&mut self, k: &str, v: bool) { self.st.flags.insert(k.into(), v); }
    pub fn flag(&self, k: &str) -> bool { *self.st.flags.get(k).unwrap_or(&false) }
    pub fn set_node(&mut self, n: &str) { self.st.node = n.into(); }
    pub fn node(&self) -> String { self.st.node.clone() }
    pub fn inventory_json(&self) -> String {
        let v: Vec<Value> = self.items.iter().map(|it| json!({"id": it.id, "name": it.name, "desc": it.desc, "kind": it.kind, "price": it.price, "sell": it.price / 2, "count": self.st.inv.get(&it.id).copied().unwrap_or(0)})).collect();
        json!({"gold": self.st.gold, "items": v}).to_string()
    }
    pub fn buy(&mut self, id: &str, qty: u32) -> bool {
        let Some(it) = self.items.iter().find(|i| i.id == id) else { return false };
        let cost = it.price * qty; if cost > self.st.gold || qty == 0 { return false }
        self.st.gold -= cost; *self.st.inv.entry(id.into()).or_insert(0) += qty; true
    }
    pub fn sell(&mut self, id: &str, qty: u32) -> bool {
        let Some(it) = self.items.iter().find(|i| i.id == id) else { return false };
        let have = self.st.inv.get(id).copied().unwrap_or(0); if have < qty || qty == 0 { return false }
        self.st.inv.insert(id.into(), have - qty); self.st.gold += it.price / 2 * qty; true
    }
    pub fn party_json(&self) -> String {
        let v: Vec<Value> = self.party.iter().map(|m| json!({"id": m.id, "name": m.name, "title": m.title, "element": m.element, "lv": self.st.lv.get(&m.id).copied().unwrap_or(m.lv), "xp": self.st.xp.get(&m.id).copied().unwrap_or(0), "nextXp": self.progression.total_at(self.st.lv.get(&m.id).copied().unwrap_or(m.lv) + 1),
            "hp": self.st.hp[&m.id], "maxHp": m.hp, "ink": self.st.ink[&m.id], "strokes": m.strokes, "seal": m.seal})).collect();
        Value::Array(v).to_string()
    }
    pub fn rest(&mut self) { for m in &self.party { self.st.hp.insert(m.id.clone(), m.hp); } }

    /// Timed-press judgement exposed to the renderer (single source of truth for windows).
    pub fn judge(&self, delta_ms: f64) -> u8 { judge_with(delta_ms, self.win.clean, self.win.good) }
    /// `clean`/`good` (and the same values as `clean_ms`/`good_ms`) are half-widths in ms.
    pub fn windows_json(&self) -> String {
        json!({"clean": self.win.clean, "good": self.win.good, "clean_ms": self.win.clean, "good_ms": self.win.good,
               "anchor": if self.win.anchor_close { "close" } else { "press" }}).to_string()
    }

    // ---------- timed Brushstroke Chain (renderer-driven) ----------
    /// Start a timed chain at `t0_ms` (performance.now()). Hit 0's target is t0 + gap_ms[0]; hit n's target is
    /// the press that landed hit n-1 + gap_ms[n] (or the previous target with anchor "close").
    /// Returns `{ok, actor, target, stroke, name, anchor, hits:[{hit,gap_ms,mult,clean_ms,good_ms}], next}`.
    pub fn begin_stroke(&mut self, actor: usize, target: usize, stroke_idx: usize, t0_ms: f64) -> String {
        let bad = |r: &str| json!({"ok": false, "reason": r}).to_string();
        if self.battle_over.is_some() { return bad("over") }
        if self.combo.is_some() { return bad("combo_in_progress") }
        if actor >= self.fighters.len() || target >= self.fighters.len() { return bad("bad_index") }
        if self.fighters[actor].side != 0 || !self.fighters[actor].alive { return bad("not_party_actor") }
        if !self.fighters[target].alive { return bad("target_down") }
        if !t0_ms.is_finite() { return bad("bad_time") }
        let Some(m) = self.party.get(self.fighters[actor].idx) else { return bad("no_member") };
        if m.strokes.is_empty() { return bad("no_strokes") }
        let si = stroke_idx.min(m.strokes.len() - 1); let s = &m.strokes[si];
        if s.hits.is_empty() { return bad("no_hits") }
        let hits: Vec<(f64, f64, f64)> = s.hits.iter().enumerate().map(|(n, h)| { let (c, g) = self.win.for_hit(&s.id, n, h); (h.gap_ms, c, g) }).collect();
        let hj: Vec<Value> = s.hits.iter().zip(&hits).enumerate().map(|(n, (h, w))| json!({"hit": n, "gap_ms": h.gap_ms, "mult": h.mult, "clean_ms": w.1, "good_ms": w.2})).collect();
        let c = Combo { actor, target, stroke_idx: si, stroke_id: s.id.clone(), name: s.name.clone(), hits, next: 0, anchor: t0_ms, grades: vec![], presses: vec![] };
        let out = json!({"ok": true, "actor": actor, "target": target, "stroke": c.stroke_id, "name": c.name,
            "anchor": if self.win.anchor_close { "close" } else { "press" }, "hits": hj, "next": Self::next_json(&c)});
        self.combo = Some(c); out.to_string()
    }
    fn next_json(c: &Combo) -> Value {
        match c.hits.get(c.next) {
            Some(&(gap, cl, gd)) => { let t = c.anchor + gap; json!({"hit": c.next, "start_ms": c.anchor, "target_ms": t, "clean_ms": cl, "good_ms": gd, "open_ms": t - gd, "close_ms": t + gd}) }
            None => Value::Null,
        }
    }
    /// Grade a press at `t_ms` against the pending hit. Returns `{ok, hit, grade, delta_ms, timeout, done, next?, result?}`.
    /// A miss (early or late) ends the chain. When `done`, `result` is the `stroke()` result and the turn has advanced.
    pub fn press(&mut self, t_ms: f64) -> String { self.press_inner(t_ms, false).to_string() }
    /// Call every frame while a chain is running. If `now_ms` is past the pending hit's good window,
    /// that hit is judged a miss (no press) and the chain ends. Returns `{timeout:false}` otherwise.
    pub fn combo_tick(&mut self, now_ms: f64) -> String {
        let Some(c) = &self.combo else { return json!({"ok": false, "timeout": false}).to_string() };
        let Some(&(gap, _, gd)) = c.hits.get(c.next) else { return json!({"ok": false, "timeout": false}).to_string() };
        if now_ms > c.anchor + gap + gd { self.press_inner(now_ms, true).to_string() } else { json!({"ok": true, "timeout": false}).to_string() }
    }
    fn press_inner(&mut self, t_ms: f64, timeout: bool) -> Value {
        let Some(mut c) = self.combo.take() else { return json!({"ok": false, "reason": "no_combo"}) };
        let (gap, cl, gd) = c.hits[c.next];
        let target = c.anchor + gap;
        let delta = t_ms - target;
        let grade = if timeout { 0 } else { judge_with(delta, cl, gd) };
        let hit = c.next;
        c.grades.push(grade); c.presses.push(t_ms);
        c.anchor = if self.win.anchor_close { target } else { t_ms };
        c.next += 1;
        if grade == 0 || c.next >= c.hits.len() {
            let res: Value = serde_json::from_str(&self.stroke(c.actor, c.target, c.stroke_idx, &c.grades)).unwrap_or(Value::Null);
            json!({"ok": true, "hit": hit, "grade": grade, "delta_ms": delta, "timeout": timeout, "done": true, "result": res})
        } else {
            let nx = Self::next_json(&c); self.combo = Some(c);
            json!({"ok": true, "hit": hit, "grade": grade, "delta_ms": delta, "timeout": timeout, "done": false, "next": nx})
        }
    }
    /// The running chain (`null` if none).
    pub fn combo_json(&self) -> String {
        match &self.combo { Some(c) => json!({"actor": c.actor, "target": c.target, "stroke": c.stroke_id, "name": c.name, "grades": c.grades, "presses": c.presses, "next": Self::next_json(c)}).to_string(), None => "null".into() }
    }
    /// Abort a chain before its first press (back to the command menu). False once a press has been judged.
    pub fn cancel_combo(&mut self) -> bool { if self.combo.as_ref().map(|c| c.grades.is_empty()).unwrap_or(false) { self.combo = None; true } else { false } }

    // ---------- battle ----------
    /// Start a battle with optional encounter flags: `{ "first": "enemy"|"party"|null, "canFlee": bool }`
    /// (`can_flee` also accepted). `first` reorders round 1 only (ambush: that side acts first, each side by speed).
    /// `canFlee:false` makes `flee()` refuse with reason "cannot_flee" (bosses). Missing flags = normal start, Flee allowed.
    pub fn start_battle_opts(&mut self, encounter: &str, opts_json: &str) -> String {
        let o: Value = serde_json::from_str(opts_json).unwrap_or(Value::Null);
        let can = o["canFlee"].as_bool().or(o["can_flee"].as_bool()).unwrap_or(true);
        let first = o["first"].as_str().filter(|s| *s == "enemy" || *s == "party").map(|s| s.to_string());
        self.start_inner(encounter, can, first)
    }
    /// Override the flee formula: `{ base, per_spd, per_fail, min, max }` (any subset).
    pub fn set_flee_rules(&mut self, j: &str) -> bool {
        let Ok(v) = serde_json::from_str::<Value>(j) else { return false };
        if !v.is_object() { return false } self.flee_rules.apply(&v); true
    }
    /// Whether Flee is allowed in this battle (false for `canFlee:false` encounters or when over).
    pub fn can_flee(&self) -> bool { self.can_flee && self.battle_over.is_none() }
    /// Current flee success chance 0..1 (what the next `flee()` rolls against).
    pub fn flee_chance(&self) -> f64 {
        let avg = |side: u8| { let v: Vec<f64> = (0..self.fighters.len()).filter(|&i| self.fighters[i].side == side && self.fighters[i].alive).map(|i| self.st(i, 4)).collect(); if v.is_empty() { 0.0 } else { v.iter().sum::<f64>() / v.len() as f64 } };
        let r = &self.flee_rules;
        (r.base + r.per_spd * (avg(0) - avg(1)) + r.per_fail * self.flee_fails as f64).clamp(r.min, r.max)
    }
    /// Flee (party command, uses the turn). Refuses with `reason`: "over", "cannot_flee", "bad_index", "not_party_actor",
    /// "not_your_turn". On success the battle ends with outcome "fled" (HP and Vermilion Ink kept, no mon/XP);
    /// on failure the turn passes and the next attempt gets +per_fail. Returns `{kind:"flee", ok, fled, chance, roll}`.
    pub fn flee(&mut self, actor: usize) -> String {
        let bad = |r: &str| json!({"kind": "flee", "ok": false, "reason": r}).to_string();
        if self.battle_over.is_some() { return bad("over") }
        if !self.can_flee { return bad("cannot_flee") }
        let Some(a) = self.fighters.get(actor) else { return bad("bad_index") };
        if a.side != 0 || !a.alive { return bad("not_party_actor") }
        if self.current() != actor as i32 { return bad("not_your_turn") }
        if self.combo.is_some() { return bad("combo_in_progress") }
        let chance = self.flee_chance(); let roll = self.rng.next();
        if roll < chance {
            self.battle_over = Some("fled".into());
            for f in self.fighters.iter().filter(|f| f.side == 0) { self.st.hp.insert(f.id.clone(), f.hp.max(1.0)); self.st.ink.insert(f.id.clone(), f.ink); }
            json!({"kind": "flee", "ok": true, "fled": true, "actor": actor, "chance": chance, "roll": roll}).to_string()
        } else {
            self.flee_fails += 1;
            let out = json!({"kind": "flee", "ok": true, "fled": false, "actor": actor, "chance": chance, "roll": roll});
            self.tick_inkwing(actor); self.advance(); out.to_string()
        }
    }
    pub fn start_battle(&mut self, encounter: &str) -> String { self.start_inner(encounter, true, None) }
    fn start_inner(&mut self, encounter: &str, can_flee: bool, first: Option<String>) -> String {
        self.can_flee = can_flee; self.first = first; self.flee_fails = 0; self.rewards = None;
        self.fighters.clear(); self.battle_over = None; self.round = 0; self.combo = None;
        for (i, m) in self.party.iter().enumerate() {
            let hp = self.st.hp[&m.id].max(1.0);
            self.fighters.push(Fighter { side: 0, idx: i, id: m.id.clone(), name: m.name.clone(), element: m.element.clone(), hp, max_hp: m.hp, atk: m.atk, def: m.def,
                mat: m.mat, mdf: m.mdf, spd: m.spd, ink: self.st.ink[&m.id], guarding: false, inkwing: 0, alive: true, mon: 0, fm: forms_of(&self.forms, &m.id), form: self.forms.get(&m.id).map(|f| f.0.clone()).unwrap_or_default() });
        }
        let mut ids = self.encounters.get(encounter).cloned().unwrap_or_default();
        ids.truncate(3); // the battle stage holds 1-3 enemies
        for (k, id) in ids.iter().enumerate() {
            if let Some(d) = self.enemies.iter().find(|e| &e.id == id) {
                self.fighters.push(Fighter { side: 1, idx: k, id: d.id.clone(), name: d.name.clone(), element: d.element.clone(), hp: d.hp, max_hp: d.hp, atk: d.atk, def: d.def,
                    mat: d.mat, mdf: d.mdf, spd: d.spd, ink: 0.0, guarding: false, inkwing: 0, alive: true, mon: d.mon, fm: [1.0; 5], form: String::new() });
            }
        }
        self.new_round();
        self.battle_json()
    }
    fn new_round(&mut self) {
        self.round += 1;
        let mut o: Vec<usize> = (0..self.fighters.len()).filter(|&i| self.fighters[i].alive).collect();
        let key = |i: usize| { let f = &self.fighters[i]; let tw = f.inkwing > 0 && self.forms.get(&f.id).map(|x| x.1 == "tailwind").unwrap_or(false); if tw { 1e6 } else { self.st(i, 4) } };
        o.sort_by(|&a, &b| key(b).partial_cmp(&key(a)).unwrap().then(a.cmp(&b)));
        if self.round == 1 { if let Some(side) = self.first.as_deref() { // ambush: that side acts first in round 1 (stable, keeps speed order)
            let s = if side == "enemy" { 1 } else { 0 };
            let (mut a, b): (Vec<usize>, Vec<usize>) = o.iter().partition(|&&i| self.fighters[i].side == s); a.extend(b); o = a;
        } }
        self.order = o; self.turn_pos = 0;
    }
    pub fn battle_json(&self) -> String {
        json!({"fighters": self.fighters, "turn": self.current(), "round": self.round, "over": self.battle_over,
               "canFlee": self.can_flee, "first": self.first, "fleeChance": self.flee_chance(), "rewards": self.rewards}).to_string()
    }
    /// Index of the fighter whose turn it is (-1 when over).
    pub fn current(&self) -> i32 {
        if self.battle_over.is_some() { return -1 }
        self.order.get(self.turn_pos).map(|&i| i as i32).unwrap_or(-1)
    }
    fn advance(&mut self) {
        self.check_over();
        if self.battle_over.is_some() { return }
        loop {
            self.turn_pos += 1;
            if self.turn_pos >= self.order.len() { self.new_round(); }
            let i = self.order[self.turn_pos];
            if self.fighters[i].alive { break }
        }
        let i = self.order[self.turn_pos];
        self.fighters[i].guarding = false; // Still Water lasts until your next turn
    }
    fn check_over(&mut self) {
        let pa = self.fighters.iter().any(|f| f.side == 0 && f.alive);
        let ea = self.fighters.iter().any(|f| f.side == 1 && f.alive);
        if !ea { self.battle_over = Some("win".into()); self.commit(true) } else if !pa { self.battle_over = Some("lose".into()); self.commit(false) }
    }
    fn commit(&mut self, win: bool) {
        for f in self.fighters.iter().filter(|f| f.side == 0) { self.st.hp.insert(f.id.clone(), if win { f.hp.max(1.0) } else { f.max_hp * 0.5 }); self.st.ink.insert(f.id.clone(), f.ink); }
        if win { let m: u32 = self.fighters.iter().filter(|f| f.side == 1).map(|f| f.mon).sum(); self.st.gold += m; self.award_xp(m); }
    }
    /// Jake's XP rule: every member alive at victory gets the full encounter XP (sum of enemy `xp`); KO'd members get 0.
    /// Level-up when cumulative XP reaches progression.xp_table[lv+1].total (cap level_cap); max stats come from
    /// stat_table and current HP rises by the max HP gained.
    fn award_xp(&mut self, mon: u32) {
        let total: u32 = self.fighters.iter().filter(|f| f.side == 1).map(|f| self.enemies.iter().find(|e| e.id == f.id).map(|e| e.xp).unwrap_or(0)).sum();
        let mut out = vec![];
        for k in 0..self.fighters.len() {
            if self.fighters[k].side != 0 { continue }
            let (i, id, alive) = (self.fighters[k].idx, self.fighters[k].id.clone(), self.fighters[k].alive);
            let gained = if alive { total } else { 0 };
            let before = self.st.lv.get(&id).copied().unwrap_or(self.party[i].lv);
            let xp = self.st.xp.get(&id).copied().unwrap_or(0).saturating_add(gained);
            self.st.xp.insert(id.clone(), xp);
            let lv = if self.progression.xp_table.is_empty() { before } else { self.progression.level_for(xp, before) };
            let mut stats = Value::Null;
            if lv > before {
                let gain = self.apply_level(i, lv);
                if self.party[i].lv == lv { // stat_table had the row
                    let h = self.st.hp.entry(id.clone()).or_insert(0.0); *h = (*h + gain.max(0.0)).min(self.party[i].hp);
                    let m = &self.party[i]; stats = json!({"hp": m.hp, "atk": m.atk, "def": m.def, "mat": m.mat, "mdf": m.mdf, "spd": m.spd});
                }
                self.st.lv.insert(id.clone(), lv);
            }
            out.push(json!({"id": id, "name": self.party[i].name, "alive": alive, "gained": gained, "xp": xp, "lv_before": before, "lv": lv,
                "leveled_up": lv > before, "next_total": self.progression.total_at(lv + 1), "stats": stats}));
        }
        self.rewards = Some(json!({"mon": mon, "xp": total, "members": out}));
    }
    pub fn spoils(&self) -> u32 { self.fighters.iter().filter(|f| f.side == 1).map(|f| f.mon).sum() }
    /// Damage variance, uniform VAR_MIN..VAR_MAX from the seeded RNG (Jake DESIGN.md: 0.95..1.05).
    fn var(&mut self) -> f64 { VAR_MIN + self.rng.next() * (VAR_MAX - VAR_MIN) }
    fn hurt(&mut self, t: usize, raw: f64) -> f64 {
        let mantle = self.fighters[t].side == 0 && self.passive_on("slate_mantle");
        let ir = self.ink.clone(); let gm = self.guard_rules.damage_mult;
        let f = &mut self.fighters[t];
        let mut d = raw.max(1.0);
        if f.guarding { d *= gm }
        if mantle { d *= 0.85 }
        let d = d.round();
        f.hp = (f.hp - d).max(0.0); if f.hp <= 0.0 { f.alive = false; f.inkwing = 0; if f.side == 0 && ir.ko_reset { f.ink = 0.0 } }
        if f.side == 0 && f.alive && (f.inkwing == 0 || ir.gain_while_inkwing) { // Vermilion Ink from damage taken (Jake, transformation.json fill.damage_taken)
            let g = ir.from_damage(d, f.max_hp, f.guarding);
            f.ink = (f.ink + g).min(ir.max);
        }
        d
    }

    /// Party attack with a Brushstroke Chain. `grades` = per-hit judgement (2/1/0); stops at first 0.
    pub fn stroke(&mut self, actor: usize, target: usize, stroke_idx: usize, grades: &[u8]) -> String {
        let Some(m) = self.party.get(self.fighters[actor].idx).cloned() else { return "{}".into() };
        let s = m.strokes[stroke_idx.min(m.strokes.len() - 1)].clone();
        let mut events = vec![]; let mut landed = 0; let mut cleans = 0;
        let (atk, def) = (self.st(actor, 0), self.st(target, 1));
        let elem = if self.fighters[actor].inkwing > 0 { self.fighters[actor].element.clone() } else { String::new() };
        let em = self.elem(&elem, &self.fighters[target].element);
        for (k, h) in s.hits.iter().enumerate() {
            let g = *grades.get(k).unwrap_or(&0);
            if g == 0 { events.push(json!({"hit": k, "grade": 0})); break }
            landed += 1; if g == 2 { cleans += 1 }
            let mut r = raw(atk, def) * h.mult * em * self.var();
            if g == 2 { r *= 1.25 }
            if landed == s.hits.len() { r *= s.finish_mult }
            let d = self.hurt(target, r);
            self.add_ink(actor, self.ink.stroke_hit + if g == 2 { self.ink.clean_bonus } else { 0.0 });
            let killed = !self.fighters[target].alive; if killed { self.add_ink(actor, self.ink.kill) }
            events.push(json!({"hit": k, "grade": g, "dmg": d, "target": target, "killed": killed}));
            if killed { break }
        }
        let full = landed == s.hits.len(); let perfect = full && cleans == s.hits.len();
        if perfect { let b = self.ink.perfect_chain + if self.ink.perfect_replaces { 0.0 } else { self.ink.chain_complete }; self.add_ink(actor, b) }
        else if full { self.add_ink(actor, self.ink.chain_complete) }
        if landed == 0 { let v = self.var(); let d = self.hurt(target, raw(atk, def) * 0.3 * v); events.push(json!({"glance": true, "dmg": d, "target": target})); }
        let out = json!({"kind": "stroke", "name": s.name, "events": events, "full": full, "perfect": perfect, "elem": em, "ink": self.fighters[actor].ink});
        self.tick_inkwing(actor); self.advance(); out.to_string()
    }
    /// Unfurl (the battle command) into Inkwing form. Needs ink >= unfurl.cost (a full gauge), not already Inkwing.
    /// Uses this turn; the next `unfurl.duration_turns` (3) own turns are Inkwing. Heals unfurl.heal_pct_max_hp.
    pub fn inkwing(&mut self, actor: usize) -> String {
        let ir = self.ink.clone();
        let Some(a) = self.fighters.get_mut(actor) else { return json!({"ok": false, "reason": "bad_index"}).to_string() };
        if a.side != 0 || !a.alive { return json!({"ok": false, "reason": "not_party_actor"}).to_string() }
        if a.inkwing > 0 { return json!({"ok": false, "reason": "already_inkwing"}).to_string() }
        if a.ink < ir.unfurl_cost { return json!({"ok": false, "reason": "ink_not_full", "ink": a.ink, "cost": ir.unfurl_cost}).to_string() }
        a.ink = 0.0; a.inkwing = ir.unfurl_turns + 1; // decremented at end of this turn -> unfurl_turns Inkwing turns
        let heal = (a.max_hp * ir.unfurl_heal_pct / 100.0).round().min(a.max_hp - a.hp); a.hp += heal;
        let out = json!({"kind": "inkwing", "ok": true, "actor": actor, "heal": heal, "form": a.form, "turns": ir.unfurl_turns});
        self.tick_inkwing(actor); self.advance(); out.to_string()
    }
    /// Seal Arts (Inkwing only): `hits` seals struck of the member's seal count, `clean` of those perfect.
    /// Missed seals still land at half (Jake: magic is forgiving).
    pub fn seal_art(&mut self, actor: usize, hits: u32, clean: u32) -> String {
        if self.fighters[actor].inkwing == 0 { return json!({"ok": false}).to_string() }
        let m = self.party[self.fighters[actor].idx].clone();
        let n = m.seal.seals.max(1); let hits = hits.min(n); let clean = clean.min(hits);
        let power = (clean as f64 * 1.25 + (hits - clean) as f64 + (n - hits) as f64 * 0.5) / n as f64;
        let a = if m.seal.stat == "atk" { self.st(actor, 0) } else { self.st(actor, 2) };
        let mut events = vec![];
        let targets: Vec<usize> = (0..self.fighters.len()).filter(|&i| self.fighters[i].side == 1 && self.fighters[i].alive).collect();
        for t in targets {
            let em = self.elem(&m.seal.element, &self.fighters[t].element);
            // Seal Arts always hit the defender's mdf; seal.stat only picks the attacker's stat (Jake, DESIGN.md).
            let dstat = self.st(t, 3);
            let v = self.var();
            let d = self.hurt(t, raw(a, dstat) * m.seal.mult * power * 1.6 * em * v);
            events.push(json!({"target": t, "dmg": d, "elem": em, "killed": !self.fighters[t].alive}));
        }
        let mut heals = vec![];
        if clean > 0 && self.forms.get(&m.id).map(|x| x.1 == "kindling_prayer").unwrap_or(false) {
            for i in 0..self.fighters.len() { let f = &mut self.fighters[i]; if f.side == 0 && f.alive { let h = (f.max_hp * 0.05 * clean as f64).round().min(f.max_hp - f.hp); f.hp += h; heals.push(json!({"target": i, "heal": h})); } }
        }
        let out = json!({"kind": "seal", "ok": true, "name": m.seal.name, "element": m.seal.element, "events": events, "heals": heals, "power": power});
        self.tick_inkwing(actor); self.advance(); out.to_string()
    }
    /// Alias of `inkwing` under the command's name (SPEC section 2: the command is Unfurl, the form is Inkwing).
    pub fn unfurl(&mut self, actor: usize) -> String { self.inkwing(actor) }
    /// Whether `actor` may Unfurl right now.
    pub fn can_unfurl(&self, actor: usize) -> bool { self.fighters.get(actor).map(|a| a.side == 0 && a.alive && a.inkwing == 0 && a.ink >= self.ink.unfurl_cost).unwrap_or(false) }
    /// Gauge rules in effect: `{max, unfurl_cost, unfurl_turns}`.
    pub fn ink_rules_json(&self) -> String { json!({"max": self.ink.max, "unfurl_cost": self.ink.unfurl_cost, "unfurl_turns": self.ink.unfurl_turns, "stroke_hit": self.ink.stroke_hit, "clean_bonus": self.ink.clean_bonus}).to_string() }
    fn tick_inkwing(&mut self, actor: usize) { let a = &mut self.fighters[actor]; if a.inkwing > 0 { a.inkwing -= 1; } }
    /// Still Water: halve damage until next turn and restore 10% max HP.
    /// Still Water: damage x0.5 until this fighter's next turn, heals 10% max HP (15% in Inkwing), +6 Vermilion Ink
    /// (not in Inkwing); Ink from damage taken while guarding is x1.5. Uses the turn.
    pub fn guard(&mut self, actor: usize) -> String {
        if self.battle_over.is_some() { return json!({"ok": false, "reason": "over"}).to_string() }
        let gr = self.guard_rules.clone();
        let Some(a) = self.fighters.get_mut(actor) else { return json!({"ok": false, "reason": "bad_index"}).to_string() };
        if !a.alive { return json!({"ok": false, "reason": "down"}).to_string() }
        let pct = if a.inkwing > 0 { gr.heal_pct_inkwing } else { gr.heal_pct };
        let heal = (a.max_hp * pct / 100.0).round().min(a.max_hp - a.hp).max(0.0); a.hp += heal; a.guarding = true;
        if a.side == 0 && a.inkwing == 0 { a.ink = (a.ink + self.ink.still_water_use).min(self.ink.max) }
        let out = json!({"kind": "guard", "ok": true, "actor": actor, "heal": heal, "hp": a.hp, "ink": a.ink, "damage_mult": gr.damage_mult});
        self.tick_inkwing(actor); self.advance_keep_guard(actor); out.to_string()
    }
    fn advance_keep_guard(&mut self, actor: usize) { self.advance(); if self.current() as usize != actor { self.fighters[actor].guarding = true; } }
    pub fn use_item(&mut self, actor: usize, item: &str, target: usize) -> String {
        let have = self.st.inv.get(item).copied().unwrap_or(0);
        let Some(it) = self.items.iter().find(|i| i.id == item).cloned() else { return json!({"ok": false}).to_string() };
        if have == 0 { return json!({"ok": false}).to_string() }
        if it.kind == "gear" { return json!({"ok": false}).to_string() }
        if it.kind == "ink" && self.fighters.get(target).map(|f| f.inkwing > 0 || !f.alive).unwrap_or(true) { return json!({"ok": false, "reason": "inkwing"}).to_string() }
        self.st.inv.insert(item.into(), have - 1);
        let mut events = vec![];
        match it.kind.as_str() {
            "heal" => { let f = &mut self.fighters[target]; let h = it.power.min(f.max_hp - f.hp); f.hp += h; events.push(json!({"target": target, "heal": h})); }
            "healall" => for i in 0..self.fighters.len() { let f = &mut self.fighters[i]; if f.side == 0 && f.alive { let h = it.power.min(f.max_hp - f.hp); f.hp += h; events.push(json!({"target": i, "heal": h})); } },
            "ink" => { let mx = self.ink.max; let f = &mut self.fighters[target]; if f.inkwing == 0 { f.ink = (f.ink + it.power).min(mx); } events.push(json!({"target": target, "ink": f.ink})); }
            "bomb" => { let e = it.element.clone().unwrap_or_default(); let em = self.elem(&e, &self.fighters[target].element); let v = self.var(); let d = self.hurt(target, it.power * em * v); events.push(json!({"target": target, "dmg": d, "elem": em, "killed": !self.fighters[target].alive})); }
            _ => {}
        }
        let out = json!({"kind": "item", "ok": true, "item": it.name, "itemKind": it.kind, "events": events});
        self.tick_inkwing(actor); self.advance(); out.to_string()
    }
    /// Enemy acts (call when current() is an enemy). Data-driven AI (enemies.json, all fields optional):
    /// - move `weight`: weighted pick among eligible moves (seeded RNG).
    /// - move `hp_below` (0..1): only eligible while the enemy's own HP fraction is below it (e.g. a desperation move).
    /// - move `kind`: "phys" (atk vs def), "elem" (mat vs mdf, x element), "heal" (heals the most-hurt living enemy
    ///   by power x mat), "guard" (the enemy takes Still Water: damage x0.5 until its next turn).
    /// - move `target` (else enemy `ai`, else "random"): "random" | "lowest_hp" | "lowest_hp_pct" | "highest_hp" |
    ///   "weak" (prefers a member weak to the move's element) | "all" (hits every living party member).
    pub fn enemy_turn(&mut self) -> String {
        let me = self.current(); if me < 0 { return "{}".into() } let me = me as usize;
        if self.fighters[me].side != 1 { return "{}".into() }
        let def = match self.enemies.iter().find(|e| e.id == self.fighters[me].id).cloned() { Some(d) if !d.moves.is_empty() => d, _ => { self.advance(); return json!({"kind": "enemy", "actor": me, "move": "hesitates", "target": -1, "dmg": 0}).to_string() } };
        let alive: Vec<usize> = (0..self.fighters.len()).filter(|&i| self.fighters[i].side == 0 && self.fighters[i].alive).collect();
        if alive.is_empty() { self.advance(); return "{}".into() }
        let hp_frac = self.fighters[me].hp / self.fighters[me].max_hp.max(1.0);
        let hurt_ally = (0..self.fighters.len()).filter(|&i| self.fighters[i].side == 1 && self.fighters[i].alive && self.fighters[i].hp < self.fighters[i].max_hp * 0.7)
            .min_by(|&a, &b| (self.fighters[a].hp / self.fighters[a].max_hp).partial_cmp(&(self.fighters[b].hp / self.fighters[b].max_hp)).unwrap_or(std::cmp::Ordering::Equal));
        let eligible: Vec<Move> = def.moves.iter().filter(|m| m.weight > 0 && m.hp_below.map(|h| hp_frac < h).unwrap_or(true) && (m.kind != "heal" || hurt_ally.is_some())).cloned().collect();
        let pool = if eligible.is_empty() { def.moves.clone() } else { eligible };
        let total: u32 = pool.iter().map(|m| m.weight.max(1)).sum();
        let mut r = ((self.rng.next() * total as f64) as u32).min(total.saturating_sub(1)); let mut mv = pool[0].clone();
        for m in &pool { let w = m.weight.max(1); if r < w { mv = m.clone(); break } r -= w; }
        if mv.kind == "guard" {
            self.fighters[me].guarding = true;
            let out = json!({"kind": "enemy", "actor": me, "move": mv.name, "moveKind": "guard", "element": Value::Null, "target": me, "dmg": 0, "elem": 1.0, "guarded": false, "killed": false, "targets": [me], "hits": []});
            self.advance_keep_guard(me); return out.to_string()
        }
        if mv.kind == "heal" {
            let t = hurt_ally.unwrap_or(me);
            let h = (mv.power * self.fighters[me].mat.max(1.0)).round();
            let f = &mut self.fighters[t]; let h = h.min(f.max_hp - f.hp).max(0.0); f.hp += h;
            let out = json!({"kind": "enemy", "actor": me, "move": mv.name, "moveKind": "heal", "element": Value::Null, "target": t, "dmg": 0, "heal": h, "elem": 1.0, "guarded": false, "killed": false, "targets": [t], "hits": []});
            self.advance(); return out.to_string()
        }
        let elem_s = if mv.kind == "elem" { mv.element.clone().unwrap_or_else(|| self.fighters[me].element.clone()) } else { String::new() };
        let rule = mv.target.clone().or(def.ai.clone()).unwrap_or_else(|| "random".into());
        let by = |k: &dyn Fn(usize) -> f64, lo: bool| -> usize { *alive.iter().min_by(|&&a, &&b| { let (x, y) = (k(a), k(b)); let o = x.partial_cmp(&y).unwrap_or(std::cmp::Ordering::Equal); if lo { o } else { o.reverse() } }).unwrap() };
        let targets: Vec<usize> = match rule.as_str() {
            "all" => alive.clone(),
            "lowest_hp" => vec![by(&|i| self.fighters[i].hp, true)],
            "lowest_hp_pct" => vec![by(&|i| self.fighters[i].hp / self.fighters[i].max_hp.max(1.0), true)],
            "highest_hp" => vec![by(&|i| self.fighters[i].hp, false)],
            "weak" => { let w: Vec<usize> = alive.iter().copied().filter(|&i| self.elem(&elem_s, &self.fighters[i].element) > 1.0).collect();
                        let p = if w.is_empty() { &alive } else { &w }; vec![p[self.rng.below(p.len())]] }
            _ => vec![alive[self.rng.below(alive.len())]],
        };
        let mut hits = vec![];
        for &t in &targets {
            if !self.fighters[t].alive { continue }
            let em = if mv.kind == "elem" { self.elem(&elem_s, &self.fighters[t].element) } else { 1.0 };
            let v = self.var();
            let rw = if mv.kind == "elem" { raw(self.st(me, 2), self.st(t, 3)) * em } else { raw(self.st(me, 0), self.st(t, 1)) } * mv.power * v * self.enemy_dmg_mult;
            let guarded = self.fighters[t].guarding;
            let d = self.hurt(t, rw);
            hits.push(json!({"target": t, "dmg": d, "elem": em, "guarded": guarded, "killed": !self.fighters[t].alive}));
        }
        let h0 = hits.first().cloned().unwrap_or(json!({"target": -1, "dmg": 0, "elem": 1.0, "guarded": false, "killed": false}));
        let out = json!({"kind": "enemy", "actor": me, "move": mv.name, "moveId": mv.id, "moveKind": mv.kind, "element": mv.element, "target": h0["target"], "dmg": h0["dmg"],
            "elem": h0["elem"], "guarded": h0["guarded"], "killed": h0["killed"], "targets": targets, "hits": hits, "ai": rule});
        self.advance(); out.to_string()
    }
    /// Renderer step: if it is an enemy's turn, run its AI (same as `enemy_turn`); otherwise `{"ok":false}`.
    pub fn step(&mut self) -> String {
        let c = self.current();
        if c < 0 { return json!({"ok": false, "reason": "over"}).to_string() }
        if self.fighters[c as usize].side != 1 { return json!({"ok": false, "reason": "party_turn"}).to_string() }
        self.enemy_turn()
    }
    /// Damage multiplier on all enemy attacks (default 0.8, the integrator's tuning).
    pub fn set_enemy_damage_mult(&mut self, m: f64) { if m.is_finite() && m >= 0.0 { self.enemy_dmg_mult = m } }
    /// Demo/debug: set a party member's Vermilion Ink.
    pub fn debug_ink(&mut self, actor: usize, v: f64) { if let Some(f) = self.fighters.get_mut(actor) { f.ink = v.clamp(0.0, self.ink.max) } }

    // ---------- POI walker ----------
    pub fn walker_load(&mut self, poi_json: &str, x: f64, y: f64) -> bool {
        let Ok(v) = serde_json::from_str::<Value>(poi_json) else { return false };
        let arr4 = |a: &Value| -> [f64; 4] { let a = a.as_array().cloned().unwrap_or_default(); let g = |i: usize| a.get(i).and_then(|x| x.as_f64()).unwrap_or(0.0); [g(0), g(1), g(2), g(3)] };
        self.walk = Walker { x, y, w: v["w"].as_f64().unwrap_or(1280.0), h: v["h"].as_f64().unwrap_or(720.0), r: 18.0,
            solids: v["solids"].as_array().map(|a| a.iter().map(arr4).collect()).unwrap_or_default(), triggers: vec![] };
        if let Some(t) = v["triggers"].as_array() { for t in t { self.walk.triggers.push((t["id"].as_str().unwrap_or("").into(), arr4(&t["rect"]))); } }
        if let Some(t) = v["exits"].as_array() { for (k, t) in t.iter().enumerate() { self.walk.triggers.push((format!("exit:{k}"), arr4(&t["rect"]))); } }
        true
    }
    /// Move by (vx, vy) px/s for dt seconds with axis-separated collision. Returns [x, y].
    pub fn walker_step(&mut self, vx: f64, vy: f64, dt: f64) -> Vec<f64> {
        let w = &mut self.walk; let r = w.r;
        let nx = (w.x + vx * dt).clamp(r, w.w - r);
        if !w.solids.iter().any(|s| overlap(nx, w.y, r, s)) { w.x = nx; }
        let ny = (w.y + vy * dt).clamp(r, w.h - 4.0);
        if !w.solids.iter().any(|s| overlap(w.x, ny, r, s)) { w.y = ny; }
        vec![w.x, w.y]
    }
    pub fn walker_set(&mut self, x: f64, y: f64) { self.walk.x = x; self.walk.y = y; }
    /// Ids of triggers the walker currently stands in, comma separated.
    pub fn walker_triggers(&self) -> String {
        let w = &self.walk;
        w.triggers.iter().filter(|(_, s)| w.x > s[0] && w.x < s[0] + s[2] && w.y > s[1] && w.y < s[1] + s[3]).map(|(id, _)| id.clone()).collect::<Vec<_>>().join(",")
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn g() -> Game {
        let p = std::fs::read_to_string("../data/party.json").unwrap();
        let e = std::fs::read_to_string("../data/enemies.json").unwrap();
        let i = std::fs::read_to_string("../data/items.json").unwrap();
        { let mut g = Game::new(&p, &e, &i, 7).unwrap(); g.set_rules(&std::fs::read_to_string("../data/transformation.json").unwrap()); g }
    }
    #[test] fn elements() { assert_eq!(elem_mod("ember", "tide"), 2.0); assert_eq!(elem_mod("gale", "gale"), 0.5); assert_eq!(elem_mod("dawn", "ember"), 1.0); }
    #[test] fn timing() { assert_eq!(judge_delta(30.0), 2); assert_eq!(judge_delta(-120.0), 1); assert_eq!(judge_delta(200.0), 0); }
    #[test] fn full_battle() {
        let mut g = g(); g.start_battle("sumikage_c");
        let mut guard = 0;
        while g.current() >= 0 && guard < 500 {
            guard += 1; let c = g.current() as usize;
            if g.fighters[c].side == 1 { g.enemy_turn(); continue }
            let t = (0..g.fighters.len()).find(|&i| g.fighters[i].side == 1 && g.fighters[i].alive).unwrap();
            if g.fighters[c].ink >= 100.0 && g.fighters[c].inkwing == 0 { g.inkwing(c); }
            else if g.fighters[c].inkwing > 0 { g.seal_art(c, 5, 3); }
            else { g.stroke(c, t, 0, &[2, 2, 2, 2]); }
        }
        assert_eq!(g.battle_over.as_deref(), Some("win"));
        assert!(g.gold() > 120);
    }
    #[test] fn shop() { let mut g = g(); assert!(g.buy("rice_cake", 2)); assert_eq!(g.gold(), 90); assert!(g.sell("rice_cake", 1)); assert_eq!(g.gold(), 97); assert!(!g.buy("thunder_jar", 1)); }
    #[test] fn guard_heals() { let mut g = g(); g.start_battle("sumikage_c"); let c = g.current() as usize; g.fighters[c].hp = 100.0; let r: Value = serde_json::from_str(&g.guard(c)).unwrap(); assert!(r["heal"].as_f64().unwrap() > 0.0); }
}

/// Rusty's battle-rule tests (patches 0001-0005). Read live data from ../data like the integrator's tests.
#[cfg(test)]
mod rusty_tests {
    use super::*;
    fn rd(p: &str) -> String { std::fs::read_to_string(p).unwrap() }
    fn game_with(enemies: &str) -> Game {
        let mut g = Game::new(&rd("../data/party.json"), enemies, &rd("../data/items.json"), 11).unwrap();
        g.set_rules(&rd("../data/transformation.json")); g
    }
    fn fresh() -> Game { game_with(&rd("../data/enemies.json")) }
    fn v(s: &str) -> Value { serde_json::from_str(s).unwrap() }
    fn first_enemy(g: &Game) -> usize { (0..g.fighters.len()).find(|&i| g.fighters[i].side == 1 && g.fighters[i].alive).unwrap() }
    /// Start sumikage_c and make it Itsuki's turn against a very tanky first enemy, ink 0.
    fn itsuki_turn(g: &mut Game) -> (usize, usize) {
        g.start_battle("sumikage_c");
        let a = (0..g.fighters.len()).find(|&i| g.fighters[i].id == "itsuki").unwrap();
        let t = first_enemy(g);
        g.fighters[t].hp = 1e6; g.fighters[t].max_hp = 1e6; g.fighters[a].ink = 0.0;
        g.order = vec![a]; g.turn_pos = 0;
        (a, t)
    }

    // ---- turn order ----
    #[test] fn turn_order_is_by_speed_and_deterministic() {
        let mut g1 = fresh(); g1.start_battle("sumikage_c");
        let spd: Vec<f64> = g1.order.iter().map(|&i| g1.st(i, 4)).collect();
        assert!(spd.windows(2).all(|w| w[0] >= w[1]), "order not by speed: {spd:?}");
        let mut g2 = fresh(); g2.start_battle("sumikage_c");
        assert_eq!(g1.order, g2.order);
    }
    #[test] fn tailwind_inkwing_acts_first() {
        let mut g = fresh(); let (a, _) = itsuki_turn(&mut g);
        g.fighters[a].ink = 100.0; assert_eq!(v(&g.unfurl(a))["ok"], true);
        g.new_round(); assert_eq!(g.order[0], a);
    }
    #[test] fn encounter_capped_at_three_enemies() {
        let e = r#"{"enemies":[{"id":"blotling","name":"Blotling","element":"dusk","hp":50,"atk":10,"def":5,"mat":5,"mdf":5,"spd":5,"mon":1,"moves":[{"id":"s","name":"S","kind":"phys","power":1,"weight":1}]}],
                   "encounters":{"four":["blotling","blotling","blotling","blotling"]}}"#;
        let mut g = game_with(e); g.start_battle("four");
        assert_eq!(g.fighters.iter().filter(|f| f.side == 1).count(), 3);
    }

    // ---- combo timing (0001) ----
    #[test] fn default_windows_are_half_widths_95_150() {
        let g = fresh();
        assert_eq!((g.judge(95.0), g.judge(-95.0), g.judge(95.5), g.judge(150.0), g.judge(-150.5)), (2, 2, 1, 1, 0));
        let w = v(&g.windows_json()); assert_eq!(w["clean_ms"], 95.0); assert_eq!(w["good_ms"], 150.0); assert_eq!(w["anchor"], "press");
        assert_eq!(judge_with(f64::NAN, 95.0, 150.0), 0);
    }
    #[test] fn windows_are_data_overridable() {
        let mut g = fresh();
        assert!(g.set_combo_windows(r#"{"clean_ms":80,"good_ms":120,"hits":{"falling_pine#1":{"clean_ms":40}}}"#));
        assert_eq!(g.judge(85.0), 1); assert_eq!(g.judge(125.0), 0);
        let (a, t) = itsuki_turn(&mut g);
        let w = v(&g.begin_stroke(a, t, 0, 0.0));
        assert_eq!(w["hits"][0]["clean_ms"], 80.0); assert_eq!(w["hits"][1]["clean_ms"], 40.0); assert_eq!(w["hits"][1]["good_ms"], 120.0);
        // transformation.json-style combo_windows block via set_rules
        let mut g2 = fresh(); g2.set_rules(r#"{"combo_windows":{"clean_ms":99}}"#); assert_eq!(g2.judge(99.0), 2);
    }
    #[test] fn timed_chain_targets_follow_previous_press() {
        let mut g = fresh(); let (a, t) = itsuki_turn(&mut g);
        let gaps: Vec<f64> = g.party[g.fighters[a].idx].strokes[0].hits.iter().map(|h| h.gap_ms).collect();
        let w = v(&g.begin_stroke(a, t, 0, 1000.0));
        assert_eq!(w["next"]["target_ms"], 1000.0 + gaps[0]);
        let p1 = 1000.0 + gaps[0] + 60.0; // late but Clean
        let r1 = v(&g.press(p1)); assert_eq!(r1["grade"], 2); assert_eq!(r1["done"], false);
        assert_eq!(r1["next"]["target_ms"], p1 + gaps[1]); // anchored on the press, not the ring close
        let r2 = v(&g.press(p1 + gaps[1] - 120.0)); assert_eq!(r2["grade"], 1);
        let mut last = r2;
        while last["done"] == false { let tm = last["next"]["target_ms"].as_f64().unwrap(); last = v(&g.press(tm)); }
        assert_eq!(last["result"]["full"], true); assert_eq!(last["result"]["perfect"], false);
        assert!(g.combo.is_none());
    }
    #[test] fn anchor_close_measures_from_previous_target() {
        let mut g = fresh(); g.set_combo_windows(r#"{"anchor":"close"}"#); let (a, t) = itsuki_turn(&mut g);
        let gaps: Vec<f64> = g.party[g.fighters[a].idx].strokes[0].hits.iter().map(|h| h.gap_ms).collect();
        g.begin_stroke(a, t, 0, 0.0);
        let r1 = v(&g.press(gaps[0] + 50.0)); assert_eq!(r1["next"]["target_ms"], gaps[0] + gaps[1]);
    }
    #[test] fn miss_ends_timed_chain_early_or_late() {
        for off in [-200.0, 200.0] {
            let mut g = fresh(); let (a, t) = itsuki_turn(&mut g);
            let w = v(&g.begin_stroke(a, t, 0, 0.0));
            let r = v(&g.press(w["next"]["target_ms"].as_f64().unwrap() + off));
            assert_eq!(r["grade"], 0); assert_eq!(r["done"], true);
            let ev = r["result"]["events"].as_array().unwrap();
            assert_eq!(ev[0]["grade"], 0); assert!(ev[0].get("dmg").is_none(), "the missed hit itself deals no damage");
            // integrator rule kept: a chain with zero landed hits still glances for 30% (separate `glance` event)
            assert!(ev.iter().skip(1).all(|e| e["glance"] == true));
        }
    }
    #[test] fn no_press_times_out_as_miss() {
        let mut g = fresh(); let (a, t) = itsuki_turn(&mut g);
        let w = v(&g.begin_stroke(a, t, 0, 0.0)); let tm = w["next"]["target_ms"].as_f64().unwrap();
        assert_eq!(v(&g.combo_tick(tm + 150.0))["timeout"], false);
        let r = v(&g.combo_tick(tm + 151.0)); assert_eq!(r["timeout"], true); assert_eq!(r["grade"], 0); assert_eq!(r["done"], true);
    }
    #[test] fn begin_stroke_rejects_bad_calls_and_cancel_works() {
        let mut g = fresh(); let (a, t) = itsuki_turn(&mut g);
        assert_eq!(v(&g.begin_stroke(t, a, 0, 0.0))["ok"], false); // enemy can't stroke
        assert_eq!(v(&g.begin_stroke(a, 99, 0, 0.0))["ok"], false);
        assert_eq!(v(&g.begin_stroke(a, t, 0, 0.0))["ok"], true);
        assert_eq!(v(&g.begin_stroke(a, t, 0, 0.0))["reason"], "combo_in_progress");
        assert!(g.cancel_combo()); assert_eq!(g.combo_json(), "null");
        assert_eq!(v(&g.press(10.0))["ok"], false);
    }

    // ---- Vermilion Ink + Unfurl (0002) ----
    #[test] fn ink_fill_follows_transformation_json() {
        let mut g = fresh(); let (a, t) = itsuki_turn(&mut g);
        let n = g.party[g.fighters[a].idx].strokes[0].hits.len();
        let r = v(&g.stroke(a, t, 0, &vec![2u8; n]));
        assert_eq!(r["perfect"], true);
        // values come from the loaded transformation.json; the perfect bonus replaces the complete bonus
        let ir = g.ink.clone(); assert!(ir.perfect_replaces);
        assert_eq!(g.fighters[a].ink, (ir.stroke_hit + ir.clean_bonus) * n as f64 + ir.perfect_chain);
        let mut g = fresh(); let (a, t) = itsuki_turn(&mut g);
        g.stroke(a, t, 0, &vec![1u8; n]);
        assert_eq!(g.fighters[a].ink, ir.stroke_hit * n as f64 + ir.chain_complete);
        // Jake's current file (4 / +4 / complete 6 / perfect 10 replaces): perfect 3-hit chain = 34, all-good = 18
        let mut g = fresh(); g.set_rules(&rd("../team/systems/jake/transformation.json")); let (a, t) = itsuki_turn(&mut g);
        g.stroke(a, t, 0, &[2, 2, 2]); assert_eq!(g.fighters[a].ink, 34.0);
        let mut g = fresh(); g.set_rules(&rd("../team/systems/jake/transformation.json")); let (a, t) = itsuki_turn(&mut g);
        g.stroke(a, t, 0, &[1, 1, 1]); assert_eq!(g.fighters[a].ink, 18.0);
    }
    #[test] fn ink_from_damage_taken_matches_jake_example() {
        let ir = InkRules::default();
        assert_eq!(ir.from_damage(10.0, 160.0, true), 3.0); // Gonzō example in DESIGN.md
        assert_eq!(ir.from_damage(10.0, 160.0, false), 2.0);
        assert_eq!(ir.from_damage(0.4, 500.0, false), 1.0);  // min 1 if damaged
        assert_eq!(ir.from_damage(400.0, 100.0, false), 15.0); // cap 15
    }
    #[test] fn unfurl_needs_full_gauge_and_lasts_three_own_turns() {
        let mut g = fresh(); let (a, t) = itsuki_turn(&mut g);
        g.fighters[a].ink = 99.0;
        assert!(!g.can_unfurl(a)); let r = v(&g.unfurl(a)); assert_eq!(r["ok"], false); assert_eq!(r["reason"], "ink_not_full");
        g.fighters[a].ink = 100.0; assert!(g.can_unfurl(a));
        let r = v(&g.unfurl(a)); assert_eq!(r["ok"], true); assert_eq!(r["turns"], 3);
        assert_eq!(g.fighters[a].ink, 0.0); assert_eq!(v(&g.unfurl(a))["ok"], false);
        let mut own_turns = 0;
        while g.fighters[a].inkwing > 0 && own_turns < 10 { g.fighters[t].hp = 1e6; g.guard(a); own_turns += 1; }
        assert_eq!(own_turns, 3, "Inkwing should cover exactly 3 own turns after the Unfurl turn");
        // no Ink gain while in Inkwing
        let mut g = fresh(); let (a, t) = itsuki_turn(&mut g); g.fighters[a].ink = 100.0; g.unfurl(a); g.stroke(a, t, 0, &[2, 2, 2]);
        assert_eq!(g.fighters[a].ink, 0.0);
    }
    #[test] fn ko_ink_reset_follows_data() {
        let mut g = fresh(); g.set_rules(r#"{"reset":{"on_ko":"keep"}}"#); let (a, _) = itsuki_turn(&mut g); g.fighters[a].ink = 40.0; g.fighters[a].hp = 1.0;
        g.hurt(a, 50.0); assert!(!g.fighters[a].alive); assert_eq!(g.fighters[a].ink, 40.0);
        let mut g = fresh(); g.set_rules(r#"{"reset":{"on_ko":"reset"}}"#); let (a, _) = itsuki_turn(&mut g); g.fighters[a].ink = 40.0; g.fighters[a].hp = 1.0;
        g.hurt(a, 50.0); assert_eq!(g.fighters[a].ink, 0.0);
        let mut g = fresh(); g.set_rules(&rd("../team/systems/jake/transformation.json")); /* on_ko: 0 (integer) */ let (a, _) = itsuki_turn(&mut g); g.fighters[a].ink = 40.0; g.fighters[a].hp = 1.0;
        g.hurt(a, 50.0); assert_eq!(g.fighters[a].ink, 0.0);
    }

    // ---- elements (0003) ----
    #[test] fn six_inks_rule_and_chart() {
        let mut g = fresh();
        assert_eq!(g.elem("gale", "stone"), 2.0); assert_eq!(g.elem("ember", "ember"), 0.5); assert_eq!(g.elem("none", "tide"), 1.0); assert_eq!(g.elem("", "tide"), 1.0);
        assert!(g.set_elements(&rd("../team/systems/jake/elements.json")));
        assert_eq!(g.elem("dawn", "dusk"), 2.0); assert_eq!(g.elem("tide", "gale"), 1.0);
        assert!(g.set_elements(r#"{"chart":{"gale":{"stone":3.0}}}"#)); assert_eq!(g.elem("gale", "stone"), 3.0); assert_eq!(g.elem("ember", "tide"), 2.0);
        g.start_battle("sumikage_c"); let e = first_enemy(&g);
        let a = v(&g.affinity_json(e)); assert_eq!(a["element"], g.fighters[e].element.as_str());
    }
    #[test] fn inkwing_strokes_carry_form_element() {
        let mut g = fresh(); g.start_battle("sumikage_boss");
        let a = (0..g.fighters.len()).find(|&i| g.fighters[i].id == "itsuki").unwrap(); let t = first_enemy(&g);
        assert_eq!(g.fighters[t].element, "stone");
        let r = v(&g.stroke(a, t, 0, &[1])); assert_eq!(r["elem"], 1.0, "normal-form Strokes are neutral");
        g.fighters[a].ink = 100.0; g.unfurl(a);
        let r = v(&g.stroke(a, t, 0, &[1])); assert_eq!(r["elem"], 2.0, "Gale Crane vs Stone");
    }

    // ---- Still Water (0004) ----
    #[test] fn still_water_halves_damage_and_heals() {
        let mut g = fresh(); let (a, _) = itsuki_turn(&mut g);
        let mx = g.fighters[a].max_hp; g.fighters[a].hp = mx / 2.0;
        let r = v(&g.guard(a)); assert_eq!(r["ok"], true);
        assert_eq!(r["heal"].as_f64().unwrap(), (mx * 0.10).round());
        assert_eq!(g.fighters[a].ink, 6.0); assert!(g.fighters[a].guarding);
        let hp0 = g.fighters[a].hp; let d = g.hurt(a, 40.0); assert_eq!(d, 20.0); assert_eq!(g.fighters[a].hp, hp0 - 20.0);
        g.fighters[a].guarding = false; assert_eq!(g.hurt(a, 40.0), 40.0);
        // 15% in Inkwing, no ink gain
        let mut g = fresh(); let (a, _) = itsuki_turn(&mut g); g.fighters[a].ink = 100.0; g.unfurl(a);
        let mx = g.fighters[a].max_hp; g.fighters[a].hp = mx / 2.0; g.order = vec![a]; g.turn_pos = 0;
        let r = v(&g.guard(a)); assert_eq!(r["heal"].as_f64().unwrap(), (mx * 0.15).round()); assert_eq!(g.fighters[a].ink, 0.0);
        // a downed fighter can't guard
        let mut g = fresh(); let (a, _) = itsuki_turn(&mut g); g.fighters[a].alive = false; assert_eq!(v(&g.guard(a))["ok"], false);
    }
    #[test] fn still_water_lasts_until_own_next_turn() {
        let mut g = fresh(); g.start_battle("sumikage_c");
        let a = g.current() as usize; assert_eq!(g.fighters[a].side, 0);
        g.guard(a); assert!(g.fighters[a].guarding);
        let mut guard = 0; while g.current() as usize != a && g.current() >= 0 && guard < 20 {
            let c = g.current() as usize; if g.fighters[c].side == 1 { g.enemy_turn(); } else { g.guard(c); } guard += 1;
            if g.current() as usize != a { assert!(g.fighters[a].guarding || !g.fighters[a].alive); }
        }
        if g.current() as usize == a { assert!(!g.fighters[a].guarding, "guard ends when the guarder's turn comes back"); }
    }

    // ---- enemy AI (0005) ----
    const AI: &str = r#"{"enemies":[
      {"id":"blotling","name":"Blotling","element":"dusk","hp":100,"atk":20,"def":5,"mat":10,"mdf":5,"spd":99,"mon":5,
       "moves":[{"id":"focus","name":"Focus","kind":"phys","power":1,"weight":1,"target":"lowest_hp"}]},
      {"id":"hollow_lantern","name":"Hollow Lantern","element":"gale","hp":100,"atk":20,"def":5,"mat":12,"mdf":5,"spd":99,"mon":5,"ai":"all",
       "moves":[{"id":"sweep","name":"Sweep","kind":"elem","element":"gale","power":0.5,"weight":1}]},
      {"id":"smudge_ronin","name":"Smudge Ronin","element":"stone","hp":100,"atk":20,"def":5,"mat":10,"mdf":5,"spd":99,"mon":5,
       "moves":[{"id":"cut","name":"Cut","kind":"phys","power":1,"weight":1000},
                {"id":"last","name":"Last Stand","kind":"guard","weight":1000000,"hp_below":0.3},
                {"id":"mend","name":"Mend","kind":"heal","power":2,"weight":0}]},
      {"id":"medic","name":"Ink Medic","element":"dawn","hp":100,"atk":5,"def":5,"mat":10,"mdf":5,"spd":99,"mon":5,
       "moves":[{"id":"mend","name":"Mend","kind":"heal","power":2,"weight":5},{"id":"poke","name":"Poke","kind":"phys","power":0.1,"weight":1}]}],
      "encounters":{"a":["blotling"],"b":["hollow_lantern"],"c":["smudge_ronin"],"d":["medic","blotling"]}}"#;
    fn enemy_now(g: &mut Game, id: &str) -> usize { let e = (0..g.fighters.len()).find(|&i| g.fighters[i].id == id).unwrap(); g.order = vec![e]; g.turn_pos = 0; e }
    #[test] fn ai_lowest_hp_target() {
        let mut g = game_with(AI); g.start_battle("a"); enemy_now(&mut g, "blotling");
        let gz = (0..3).find(|&i| g.fighters[i].id == "gonzo").unwrap(); g.fighters[gz].hp = 5.0;
        let r = v(&g.step()); assert_eq!(r["target"], gz); assert_eq!(r["ai"], "lowest_hp");
    }
    #[test] fn ai_all_hits_every_member_with_element() {
        let mut g = game_with(AI); g.start_battle("b"); enemy_now(&mut g, "hollow_lantern");
        let r = v(&g.enemy_turn()); assert_eq!(r["hits"].as_array().unwrap().len(), 3);
        let gz = (0..3).find(|&i| g.fighters[i].id == "gonzo").unwrap();
        let h = r["hits"].as_array().unwrap().iter().find(|h| h["target"] == gz).unwrap(); assert_eq!(h["elem"], 2.0, "Gale vs Gonzō (Stone)");
    }
    #[test] fn ai_hp_gate_and_guard() {
        let mut g = game_with(AI); g.start_battle("c"); let e = enemy_now(&mut g, "smudge_ronin");
        assert_eq!(v(&g.enemy_turn())["moveId"], "cut"); // full HP: gated move not eligible, weight-0 heal never
        g.start_battle("c"); let e2 = enemy_now(&mut g, "smudge_ronin"); assert_eq!(e, e2); g.fighters[e].hp = 20.0; g.order = vec![e, 0];
        let r = v(&g.enemy_turn()); assert_eq!(r["moveKind"], "guard"); assert!(g.fighters[e].guarding);
    }
    #[test] fn ai_heals_hurt_ally() {
        let mut g = game_with(AI); g.start_battle("d"); enemy_now(&mut g, "medic");
        let b = (0..g.fighters.len()).find(|&i| g.fighters[i].id == "blotling").unwrap(); g.fighters[b].hp = 10.0;
        let r = v(&g.enemy_turn()); assert_eq!(r["moveKind"], "heal"); assert_eq!(r["target"], b); assert_eq!(g.fighters[b].hp, 30.0);
        g.start_battle("d"); enemy_now(&mut g, "medic"); // nobody hurt: heal not eligible
        assert_eq!(v(&g.enemy_turn())["moveKind"], "phys");
    }
    #[test] fn step_only_runs_enemy_turns() {
        let mut g = fresh(); g.start_battle("sumikage_c");
        while g.current() >= 0 && g.fighters[g.current() as usize].side == 1 { g.step(); }
        assert_eq!(v(&g.step())["reason"], "party_turn");
    }

    // ---- win / lose ----
    #[test] fn win_by_timed_chains() {
        let mut g = fresh(); g.start_battle("sumikage_c"); let mut n = 0;
        while g.current() >= 0 && n < 500 {
            n += 1; let c = g.current() as usize;
            if g.fighters[c].side == 1 { g.step(); continue }
            let t = first_enemy(&g);
            let mut r = v(&g.begin_stroke(c, t, 0, 0.0));
            while r["next"].is_object() { let tm = r["next"]["target_ms"].as_f64().unwrap(); r = v(&g.press(tm + 10.0)); }
        }
        assert_eq!(g.battle_over.as_deref(), Some("win"));
    }
    #[test] fn lose_when_party_falls() {
        let mut g = fresh(); g.start_battle("sumikage_boss");
        for i in 0..3 { g.fighters[i].hp = 1.0; }
        let mut n = 0;
        while g.current() >= 0 && n < 100 { n += 1; let c = g.current() as usize; if g.fighters[c].side == 1 { g.step(); } else { g.inkwing(c); g.stroke(c, 3, 0, &[0]); } }
        assert_eq!(g.battle_over.as_deref(), Some("lose")); assert_eq!(g.current(), -1);
    }
}

/// Patch 0007 tests: Flee + ambush flags.
#[cfg(test)]
mod flee_tests {
    use super::*;
    fn rd(p: &str) -> String { std::fs::read_to_string(p).unwrap() }
    fn fresh(seed: u32) -> Game { let mut g = Game::new(&rd("../data/party.json"), &rd("../data/enemies.json"), &rd("../data/items.json"), seed).unwrap(); g.set_rules(&rd("../data/transformation.json")); g }
    fn v(s: &str) -> Value { serde_json::from_str(s).unwrap() }
    fn party_turn(g: &mut Game) -> usize { while g.current() >= 0 && g.fighters[g.current() as usize].side == 1 { g.enemy_turn(); } g.current() as usize }
    #[test] fn ambush_enemy_first_then_speed_order() {
        let mut g = fresh(3); g.start_battle_opts("sumikage_c", r#"{"first":"enemy","canFlee":true}"#);
        let sides: Vec<u8> = g.order.iter().map(|&i| g.fighters[i].side).collect();
        let k = sides.iter().position(|&s| s == 0).unwrap(); assert!(sides[k..].iter().all(|&s| s == 0), "enemies all before party: {sides:?}");
        assert_eq!(g.fighters[g.current() as usize].side, 1);
        let e: Vec<f64> = g.order[..k].iter().map(|&i| g.st(i, 4)).collect(); assert!(e.windows(2).all(|w| w[0] >= w[1]));
        assert_eq!(v(&g.battle_json())["first"], "enemy");
        // round 2 goes back to pure speed order
        g.order = vec![g.order[0]]; g.turn_pos = 0; g.new_round(); assert_eq!(g.round, 2);
        let spd: Vec<f64> = g.order.iter().map(|&i| g.st(i, 4)).collect(); assert!(spd.windows(2).all(|w| w[0] >= w[1]));
    }
    #[test] fn party_first_and_bad_flag_ignored() {
        let mut g = fresh(3); g.start_battle_opts("sumikage_c", r#"{"first":"party"}"#);
        assert!(g.order[..3].iter().all(|&i| g.fighters[i].side == 0));
        let mut g2 = fresh(3); g2.start_battle_opts("sumikage_c", r#"{"first":"sideways"}"#); let mut g3 = fresh(3); g3.start_battle("sumikage_c");
        assert_eq!(g2.order, g3.order); assert!(g2.first.is_none());
        let mut g4 = fresh(3); g4.start_battle_opts("sumikage_c", "not json"); assert!(g4.can_flee());
    }
    #[test] fn cannot_flee_blocks_with_reason() {
        let mut g = fresh(5); g.start_battle_opts("sumikage_boss", r#"{"canFlee":false}"#);
        let a = party_turn(&mut g); assert!(!g.can_flee());
        let r = v(&g.flee(a)); assert_eq!(r["ok"], false); assert_eq!(r["reason"], "cannot_flee"); assert_eq!(g.current(), a as i32);
        assert_eq!(v(&g.battle_json())["canFlee"], false);
    }
    #[test] fn flee_rejects_wrong_actor() {
        let mut g = fresh(5); g.start_battle("sumikage_c"); let a = party_turn(&mut g);
        let other = (0..3).find(|&i| i != a).unwrap(); assert_eq!(v(&g.flee(other))["reason"], "not_your_turn");
        let e = (0..g.fighters.len()).find(|&i| g.fighters[i].side == 1).unwrap(); assert_eq!(v(&g.flee(e))["reason"], "not_party_actor");
    }
    #[test] fn flee_success_ends_battle_keeps_hp_ink_no_rewards() {
        let mut g = fresh(5); g.set_flee_rules(r#"{"min":1,"max":1}"#); g.start_battle("sumikage_c"); let a = party_turn(&mut g);
        g.fighters[a].hp = 50.0; g.fighters[a].ink = 42.0; let gold = g.gold();
        let r = v(&g.flee(a)); assert_eq!(r["fled"], true); assert_eq!(g.current(), -1);
        assert_eq!(g.battle_over.as_deref(), Some("fled")); assert_eq!(g.gold(), gold);
        assert_eq!(g.st.hp[&g.fighters[a].id], 50.0); assert_eq!(g.st.ink[&g.fighters[a].id], 42.0);
        assert_eq!(v(&g.flee(a))["reason"], "over");
    }
    #[test] fn flee_failure_passes_turn_and_raises_chance() {
        let mut g = fresh(5); g.set_flee_rules(r#"{"base":0,"per_spd":0,"per_fail":0.1,"min":0,"max":1}"#); g.start_battle("sumikage_c");
        let a = party_turn(&mut g); assert_eq!(g.flee_chance(), 0.0);
        let r = v(&g.flee(a)); assert_eq!(r["fled"], false); assert_ne!(g.current(), a as i32);
        assert!((g.flee_chance() - 0.1).abs() < 1e-9);
    }
    #[test] fn flee_formula_and_determinism() {
        let mut g = fresh(9); g.start_battle("sumikage_c");
        let avg = |s: u8| { let v: Vec<f64> = (0..g.fighters.len()).filter(|&i| g.fighters[i].side == s).map(|i| g.st(i, 4)).collect(); v.iter().sum::<f64>() / v.len() as f64 };
        let want = (0.5 + 0.05 * (avg(0) - avg(1))).clamp(0.25, 0.95); assert!((g.flee_chance() - want).abs() < 1e-9);
        let run = |seed| { let mut g = fresh(seed); g.start_battle("sumikage_c"); let a = party_turn(&mut g); g.flee(a) };
        assert_eq!(run(77), run(77));
        g.set_rules(r#"{"flee":{"base":0.1,"per_spd":0,"min":0,"max":1}}"#); assert!((g.flee_chance() - 0.1).abs() < 1e-9);
    }
}

/// Patch 0008 tests: enemy XP and level-ups (Jake's progression rules).
#[cfg(test)]
mod xp_tests {
    use super::*;
    fn rd(p: &str) -> String { std::fs::read_to_string(p).unwrap() }
    fn v(s: &str) -> Value { serde_json::from_str(s).unwrap() }
    /// Jake's full party.json (stat_table + progression) and live enemies with xp added by test.
    fn jake(xp: [u32; 3]) -> Game {
        let mut e: Value = v(&rd("../data/enemies.json"));
        for (k, x) in e["enemies"].as_array_mut().unwrap().iter_mut().enumerate() { x["xp"] = json!(xp[k.min(2)]); }
        let mut g = Game::new(&rd("../team/systems/jake/party.json"), &e.to_string(), &rd("../data/items.json"), 4).unwrap();
        g.set_rules(&rd("../team/systems/jake/transformation.json")); g
    }
    fn win_now(g: &mut Game) { for f in g.fighters.iter_mut().filter(|f| f.side == 1) { f.hp = 0.0; f.alive = false; } g.check_over(); }
    #[test] fn xp_defaults_to_zero_when_absent() {
        // live enemies.json now carries xp (0.1.1), so strip it to exercise the serde default
        let mut ej: serde_json::Value = serde_json::from_str(&rd("../data/enemies.json")).unwrap();
        for e in ej["enemies"].as_array_mut().unwrap() { e.as_object_mut().unwrap().remove("xp"); }
        let mut g = Game::new(&rd("../data/party.json"), &ej.to_string(), &rd("../data/items.json"), 4).unwrap();
        assert!(g.enemies.iter().all(|e| e.xp == 0));
        g.start_battle("sumikage_c"); win_now(&mut g);
        let r = v(&g.rewards_json()); assert_eq!(r["xp"], 0); assert_eq!(r["members"][0]["gained"], 0);
        assert_eq!(v(&g.battle_json())["rewards"]["mon"], g.spoils());
    }
    #[test] fn starting_xp_matches_level_total() {
        let g = jake([0, 0, 0]); let p = v(&g.party_json());
        assert_eq!(p[0]["lv"], 5); assert_eq!(p[0]["xp"], 379); assert_eq!(p[0]["nextXp"], 612); // xp_table L5 total 379, L6 612
    }
    #[test] fn alive_members_get_full_xp_kod_get_none() {
        let mut g = jake([12, 18, 150]); g.start_battle("sumikage_c"); // blotling, hollow_lantern, blotling = 42
        let b = (0..3).find(|&i| g.fighters[i].id == "benika").unwrap(); g.fighters[b].alive = false; g.fighters[b].hp = 0.0;
        win_now(&mut g);
        let r = v(&g.rewards_json()); assert_eq!(r["xp"], 42);
        for m in r["members"].as_array().unwrap() { if m["id"] == "benika" { assert_eq!(m["gained"], 0); assert_eq!(m["xp"], 379); } else { assert_eq!(m["gained"], 42); assert_eq!(m["xp"], 421); } }
    }
    #[test] fn level_up_uses_stat_table_and_raises_hp_by_gain() {
        let mut g = jake([12, 18, 300]); g.start_battle("sumikage_boss"); // 300 xp: 379 -> 679 >= 612 (L6), < L7 total
        let it = (0..3).find(|&i| g.fighters[i].id == "itsuki").unwrap(); g.fighters[it].hp = 100.0;
        let row5 = g.party[it].stat_table[4].clone(); let row6 = g.party[it].stat_table[5].clone();
        win_now(&mut g);
        let m = v(&g.rewards_json())["members"].as_array().unwrap().iter().find(|m| m["id"] == "itsuki").cloned().unwrap();
        assert_eq!(m["lv_before"], 5); assert_eq!(m["lv"], 6); assert_eq!(m["leveled_up"], true);
        assert_eq!(g.party[it].hp, row6.hp); assert_eq!(g.party[it].atk, row6.atk);
        assert_eq!(g.st.hp["itsuki"], 100.0 + (row6.hp - row5.hp));
        // persists through save/load
        let s = g.save_json(); let mut g2 = jake([0, 0, 0]); assert!(g2.load_json(&s));
        assert_eq!(g2.party[it].atk, row6.atk); assert_eq!(v(&g2.party_json())[it]["lv"], 6);
    }
    #[test] fn multi_level_and_cap() {
        let mut g = jake([0, 0, 100000]); g.start_battle("sumikage_boss"); win_now(&mut g);
        let m = &v(&g.rewards_json())["members"][0]; assert_eq!(m["lv"], 20); assert_eq!(m["next_total"], Value::Null);
    }
    #[test] fn no_rewards_on_lose_or_flee() {
        let mut g = jake([12, 18, 150]); g.start_battle("sumikage_c");
        for i in 0..3 { g.fighters[i].alive = false; g.fighters[i].hp = 0.0; } g.check_over();
        assert_eq!(g.battle_over.as_deref(), Some("lose")); assert_eq!(g.rewards_json(), "null");
    }
    #[test] fn old_save_without_xp_fields_loads() {
        let mut g = jake([0, 0, 0]);
        assert!(g.load_json(r#"{"gold":5,"inv":{},"hp":{"itsuki":10},"ink":{},"flags":{},"node":""}"#));
        assert_eq!(v(&g.party_json())[0]["lv"], 5);
    }
}

/// Patch 0009 tests: Jake's balance fixes (variance, Seal Arts vs mdf, on_ko integer).
#[cfg(test)]
mod balance_tests {
    use super::*;
    fn rd(p: &str) -> String { std::fs::read_to_string(p).unwrap() }
    fn v(s: &str) -> Value { serde_json::from_str(s).unwrap() }
    #[test] fn variance_is_095_to_105() {
        let mut g = Game::new(&rd("../data/party.json"), &rd("../data/enemies.json"), &rd("../data/items.json"), 1).unwrap();
        let (mut lo, mut hi) = (f64::MAX, f64::MIN);
        for _ in 0..20000 { let x = g.var(); lo = lo.min(x); hi = hi.max(x); }
        assert!(lo >= VAR_MIN && hi <= VAR_MAX, "{lo}..{hi}"); assert!(lo < 0.951 && hi > 1.049, "spans the range: {lo}..{hi}");
    }
    /// One enemy with a given def/mdf; Itsuki (seal.stat atk) casts a fixed all-Clean Seal Art.
    fn seal_dmg(def: f64, mdf: f64) -> f64 {
        let e = format!(r#"{{"enemies":[{{"id":"post","name":"Post","element":"","hp":100000,"atk":1,"def":{def},"mat":1,"mdf":{mdf},"spd":1,"mon":0,"moves":[{{"id":"w","name":"W","kind":"phys","power":1,"weight":1}}]}}],"encounters":{{"t":["post"]}}}}"#);
        let mut g = Game::new(&rd("../data/party.json"), &e, &rd("../data/items.json"), 2).unwrap();
        g.set_rules(&rd("../team/systems/jake/transformation.json")); g.start_battle("t");
        let a = (0..3).find(|&i| g.fighters[i].id == "itsuki").unwrap(); assert_eq!(g.party[a].seal.stat, "atk");
        g.fighters[a].inkwing = 3;
        let r = v(&g.seal_art(a, 4, 4)); r["events"][0]["dmg"].as_f64().unwrap()
    }
    #[test] fn seal_arts_always_use_mdf() {
        let base = seal_dmg(5.0, 5.0);
        assert_eq!(seal_dmg(500.0, 5.0), base, "defender def must not matter for a Seal Art");
        assert!(seal_dmg(5.0, 60.0) < base, "defender mdf must reduce Seal Art damage");
    }
    #[test] fn on_ko_integer_resets_ink() {
        let mut g = Game::new(&rd("../data/party.json"), &rd("../data/enemies.json"), &rd("../data/items.json"), 2).unwrap();
        g.set_rules(r#"{"reset":{"on_ko":0}}"#); g.start_battle("sumikage_c");
        g.fighters[0].ink = 50.0; g.fighters[0].hp = 1.0; g.hurt(0, 99.0); assert!(!g.fighters[0].alive); assert_eq!(g.fighters[0].ink, 0.0);
    }
}
