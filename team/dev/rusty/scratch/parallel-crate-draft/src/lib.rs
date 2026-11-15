//! inkborne_core: Inkborne's game core (Rust -> WebAssembly).
//! Battle rules, Brushstroke Chain timing, Vermilion Ink / Unfurl / Inkwing, Seal Arts, Six Inks,
//! Still Water, items, enemy AI, plus the integrator's inventory/mon, POI walker and save (kept for compat).
//! See ../API.md for the full contract.
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::BTreeMap;
use wasm_bindgen::prelude::*;

pub mod data;
pub mod rules;
mod battle;

pub use data::*;
pub use rules::{elem_mod, judge_delta, judge_with, raw, Rng, Rules, CLEAN_MS, GOOD_MS};
pub use battle::{Fighter, Phase};

#[derive(Serialize, Deserialize, Clone, Default)]
pub(crate) struct Save {
    gold: u32,
    inv: BTreeMap<String, u32>,
    hp: BTreeMap<String, f64>,
    ink: BTreeMap<String, f64>,
    flags: BTreeMap<String, bool>,
    node: String,
    #[serde(default)] xp: BTreeMap<String, u32>,
    #[serde(default)] lv: BTreeMap<String, u32>,
}

#[derive(Default)]
struct Walker { x: f64, y: f64, w: f64, h: f64, solids: Vec<[f64; 4]>, triggers: Vec<(String, [f64; 4])>, r: f64 }
fn overlap(x: f64, y: f64, r: f64, s: &[f64; 4]) -> bool { x + r > s[0] && x - r < s[0] + s[2] && y + r * 0.5 > s[1] && y - r * 0.5 < s[1] + s[3] }

fn err(ctx: &str, e: serde_json::Error) -> JsValue { JsValue::from_str(&format!("{ctx}: {e}")) }

#[wasm_bindgen]
pub struct Game {
    pub(crate) party: Vec<MemberDef>,
    pub(crate) progression: Progression,
    pub(crate) enemies: Vec<EnemyDef>,
    pub(crate) encounters: BTreeMap<String, Vec<String>>,
    pub(crate) items: Vec<ItemDef>,
    pub(crate) rules: Rules,
    pub(crate) st: Save,
    pub(crate) rng: Rng,
    pub(crate) b: battle::Battle,
    walk: Walker,
}

impl Game {
    /// Pure-Rust constructor (tests / native tools). Errors are plain strings.
    pub fn from_json(party_json: &str, enemies_json: &str, items_json: &str, seed: u32) -> Result<Game, String> {
        let p: PartyFile = serde_json::from_str(party_json).map_err(|e| format!("party.json: {e}"))?;
        let e: EnemyFile = serde_json::from_str(enemies_json).map_err(|e| format!("enemies.json: {e}"))?;
        let i: ItemFile = serde_json::from_str(items_json).map_err(|e| format!("items.json: {e}"))?;
        let mut rules = Rules::default();
        if let Some(cw) = &p.combo_windows { rules.apply_windows(cw); }
        let mut st = Save { gold: 120, ..Default::default() };
        for id in ["rice_cake", "paper_cracker", "inkstone_chip"] {
            if i.items.iter().any(|x| x.id == id) { st.inv.insert(id.into(), if id == "rice_cake" { 3 } else { 1 }); }
        }
        if st.inv.is_empty() { // different item set (e.g. Jane's): a small starter kit by kind
            for (kind, n) in [("heal", 3u32), ("ink", 1), ("bomb", 1)] {
                if let Some(x) = i.items.iter().find(|x| x.kind == kind) { st.inv.insert(x.id.clone(), n); }
            }
        }
        for m in &p.members {
            st.hp.insert(m.id.clone(), m.hp); st.ink.insert(m.id.clone(), m.ink.clamp(0.0, 100.0));
            st.lv.insert(m.id.clone(), m.lv);
            let xp0 = p.progression.as_ref().and_then(|pr| pr.xp_table.iter().find(|r| r.lv == m.lv)).map(|r| r.total).unwrap_or(0);
            st.xp.insert(m.id.clone(), xp0);
        }
        Ok(Game { party: p.members, progression: p.progression.unwrap_or_default(), enemies: e.enemies, encounters: e.encounters, items: i.items,
            rules, st, rng: Rng::new(seed), b: battle::Battle::default(), walk: Walker::default() })
    }
    pub fn fighters(&self) -> &[Fighter] { &self.b.fighters }
    pub fn fighters_mut(&mut self) -> &mut Vec<Fighter> { &mut self.b.fighters }
    pub fn inv_count(&self, id: &str) -> u32 { self.st.inv.get(id).copied().unwrap_or(0) }
}

#[wasm_bindgen]
impl Game {
    // ================= construction / data =================
    #[wasm_bindgen(constructor)]
    pub fn new(party_json: &str, enemies_json: &str, items_json: &str, seed: u32) -> Result<Game, JsValue> {
        Game::from_json(party_json, enemies_json, items_json, seed).map_err(|e| JsValue::from_str(&e))
    }
    /// Jake's transformation.json (fill, unfurl, forms, passives) and optional `combo_windows`.
    pub fn set_rules(&mut self, tj: &str) -> bool {
        match serde_json::from_str::<Value>(tj) { Ok(v) => { self.rules.apply_transformation(&v); true } Err(_) => false }
    }
    /// Jake's elements.json (`chart`). Optional; the SPEC rule is built in.
    pub fn set_elements(&mut self, ej: &str) -> bool {
        match serde_json::from_str::<Value>(ej) { Ok(v) => self.rules.apply_elements(&v), Err(_) => false }
    }
    /// `{ clean_ms, good_ms, anchor, seal_gap_ms, hits: { "<stroke_id>#<n>": { clean_ms, good_ms } } }`
    pub fn set_combo_windows(&mut self, cj: &str) -> bool {
        match serde_json::from_str::<Value>(cj) { Ok(v) => { self.rules.apply_windows(&v); true } Err(_) => false }
    }
    /// `{ enemy_damage_mult, seal_gap_ms, flee_base, var_min, var_max, combo_windows }`
    pub fn set_config(&mut self, cj: &str) -> bool {
        match serde_json::from_str::<Value>(cj) { Ok(v) => { self.rules.apply_config(&v); true } Err(_) => false }
    }
    pub fn version(&self) -> String { env!("CARGO_PKG_VERSION").into() }

    // ================= timing =================
    /// Grade with the current default windows (2 Clean Line, 1 good, 0 miss).
    pub fn judge(&self, delta_ms: f64) -> u8 { judge_with(delta_ms, self.rules.clean_ms, self.rules.good_ms) }
    pub fn windows_json(&self) -> String {
        json!({"clean": self.rules.clean_ms, "good": self.rules.good_ms, "clean_ms": self.rules.clean_ms, "good_ms": self.rules.good_ms,
               "anchor": if self.rules.anchor_close { "close" } else { "press" }, "seal_gap_ms": self.rules.seal_gap_ms}).to_string()
    }

    // ================= battle: lifecycle & queries =================
    pub fn start_battle(&mut self, encounter: &str) -> String { self.start_battle_opts(encounter, "{}") }
    /// opts: `{ can_flee, first: "enemy"|"party"|null, enemies: [ids] }`
    pub fn start_battle_opts(&mut self, encounter: &str, opts_json: &str) -> String {
        let o: Value = serde_json::from_str(opts_json).unwrap_or(Value::Null);
        self.begin_battle(encounter, &o); self.state_json()
    }
    pub fn current(&self) -> i32 { self.b.current() }
    pub fn phase(&self) -> String { self.b.phase.name().into() }
    pub fn outcome(&self) -> String { self.b.outcome.clone().unwrap_or_default() }
    pub fn state_json(&self) -> String { self.state_value().to_string() }
    pub fn battle_json(&self) -> String { self.state_json() }
    pub fn drain_events(&mut self) -> String { Value::Array(std::mem::take(&mut self.b.events)).to_string() }
    pub fn actions_json(&self) -> String { self.actions_value().to_string() }
    pub fn targets_json(&self, kind: &str, r#ref: &str) -> String { self.targets_value(kind, r#ref).to_string() }
    pub fn spoils(&self) -> u32 { self.b.fighters.iter().filter(|f| f.side == 1).map(|f| f.mon).sum() }
    pub fn rewards_json(&self) -> String { self.b.rewards.clone().unwrap_or(Value::Null).to_string() }
    pub fn combo_json(&self) -> String { self.combo_value().to_string() }

    // ================= battle: timed =================
    pub fn begin_stroke(&mut self, actor: usize, target: usize, stroke_idx: usize, t0_ms: f64) -> String { self.do_begin_stroke(actor, target, stroke_idx, t0_ms).to_string() }
    pub fn begin_seal(&mut self, actor: usize, t0_ms: f64) -> String { self.do_begin_seal(actor, t0_ms).to_string() }
    pub fn press(&mut self, t_ms: f64) -> String { self.do_press(t_ms, false).to_string() }
    pub fn combo_tick(&mut self, now_ms: f64) -> String { self.do_tick(now_ms).to_string() }
    pub fn cancel_combo(&mut self) -> bool { self.do_cancel_combo() }

    // ================= battle: commands =================
    pub fn act(&mut self, action_json: &str) -> String {
        match serde_json::from_str::<Value>(action_json) { Ok(v) => self.do_act(&v).to_string(), Err(e) => json!({"ok": false, "reason": format!("bad json: {e}")}).to_string() }
    }
    pub fn step(&mut self) -> String {
        if self.b.phase != Phase::Enemy { return json!({"ok": false, "reason": if self.b.phase == Phase::Over { "over" } else { "party_turn" }}).to_string() }
        self.enemy_turn()
    }
    pub fn enemy_turn(&mut self) -> String { self.do_enemy_turn().to_string() }
    /// Pre-judged Brushstroke Chain (compat / tests). `grades` per hit (2/1/0); stops at the first 0.
    pub fn stroke(&mut self, actor: usize, target: usize, stroke_idx: usize, grades: &[u8]) -> String { self.do_stroke_prejudged(actor, target, stroke_idx, grades).to_string() }
    /// Unfurl into Inkwing (compat name).
    pub fn inkwing(&mut self, actor: usize) -> String { self.do_unfurl(actor).to_string() }
    pub fn unfurl(&mut self, actor: usize) -> String { self.do_unfurl(actor).to_string() }
    /// Pre-judged Seal Art: `hits` seals struck (of the member's seal count), `clean` of those Clean.
    pub fn seal_art(&mut self, actor: usize, hits: u32, clean: u32) -> String {
        let n = self.b.fighters.get(actor).and_then(|f| self.party.get(f.slot)).map(|m| m.seal.seals.max(1)).unwrap_or(1);
        let hits = hits.min(n); let clean = clean.min(hits);
        let grades: Vec<u8> = (0..n).map(|i| if i < clean { 2 } else if i < hits { 1 } else { 0 }).collect();
        self.do_seal_prejudged(actor, &grades).to_string()
    }
    /// Still Water.
    pub fn guard(&mut self, actor: usize) -> String { self.do_guard(actor).to_string() }
    pub fn use_item(&mut self, actor: usize, item: &str, target: usize) -> String { self.do_item(actor, item, target).to_string() }
    pub fn cast(&mut self, actor: usize, spell_idx: usize, target: usize) -> String { self.do_magic(actor, spell_idx, target).to_string() }
    pub fn flee(&mut self, actor: usize) -> String { self.do_flee(actor).to_string() }
    /// Demo/debug: set a fighter's Vermilion Ink.
    pub fn debug_ink(&mut self, actor: usize, v: f64) { if let Some(f) = self.b.fighters.get_mut(actor) { f.ink = v.clamp(0.0, self.rules.ink_max) } }

    // ================= save / economy (integrator compat) =================
    pub fn save_json(&self) -> String { serde_json::to_string(&self.st).unwrap_or_else(|_| "{}".into()) }
    pub fn load_json(&mut self, s: &str) -> bool {
        match serde_json::from_str::<Save>(s) {
            Ok(mut v) => {
                for m in &self.party { // clamp tampered values (John's save-tamper notes)
                    let h = v.hp.entry(m.id.clone()).or_insert(m.hp); if !h.is_finite() { *h = m.hp }
                    let k = v.ink.entry(m.id.clone()).or_insert(0.0); *k = if k.is_finite() { k.clamp(0.0, 100.0) } else { 0.0 };
                }
                self.st = v;
                for i in 0..self.party.len() { let lv = self.st.lv.get(&self.party[i].id).copied().unwrap_or(self.party[i].lv); self.apply_level(i, lv); }
                for m in &self.party { let h = self.st.hp.get_mut(&m.id).unwrap(); *h = h.clamp(1.0, m.hp); }
                true
            }
            Err(_) => false,
        }
    }
    pub fn gold(&self) -> u32 { self.st.gold }
    pub fn set_flag(&mut self, k: &str, v: bool) { self.st.flags.insert(k.into(), v); }
    pub fn flag(&self, k: &str) -> bool { *self.st.flags.get(k).unwrap_or(&false) }
    pub fn set_node(&mut self, n: &str) { self.st.node = n.into(); }
    pub fn node(&self) -> String { self.st.node.clone() }
    pub fn inventory_json(&self) -> String {
        let v: Vec<Value> = self.items.iter().map(|it| json!({"id": it.id, "name": it.name, "desc": it.desc, "kind": it.kind, "price": it.price, "sell": it.price / 2, "count": self.inv_count(&it.id)})).collect();
        json!({"gold": self.st.gold, "items": v}).to_string()
    }
    pub fn buy(&mut self, id: &str, qty: u32) -> bool {
        let Some(it) = self.items.iter().find(|i| i.id == id) else { return false };
        let Some(cost) = it.price.checked_mul(qty) else { return false };
        if cost > self.st.gold || qty == 0 { return false }
        self.st.gold -= cost; *self.st.inv.entry(id.into()).or_insert(0) += qty; true
    }
    pub fn sell(&mut self, id: &str, qty: u32) -> bool {
        let Some(it) = self.items.iter().find(|i| i.id == id) else { return false };
        let have = self.inv_count(id); if have < qty || qty == 0 { return false }
        self.st.inv.insert(id.into(), have - qty); self.st.gold = self.st.gold.saturating_add(it.price / 2 * qty); true
    }
    pub fn party_json(&self) -> String {
        let v: Vec<Value> = self.party.iter().map(|m| json!({"id": m.id, "name": m.name, "title": m.title, "element": m.element,
            "lv": self.st.lv.get(&m.id).copied().unwrap_or(m.lv), "xp": self.st.xp.get(&m.id).copied().unwrap_or(0),
            "hp": self.st.hp.get(&m.id).copied().unwrap_or(m.hp), "maxHp": m.hp, "ink": self.st.ink.get(&m.id).copied().unwrap_or(0.0),
            "atk": m.atk, "def": m.def, "mat": m.mat, "mdf": m.mdf, "spd": m.spd, "strokes": m.strokes, "seal": m.seal})).collect();
        Value::Array(v).to_string()
    }
    pub fn rest(&mut self) { for m in &self.party { self.st.hp.insert(m.id.clone(), m.hp); } }

    // ================= POI walker (integrator compat, unchanged) =================
    pub fn walker_load(&mut self, poi_json: &str, x: f64, y: f64) -> bool {
        let Ok(v) = serde_json::from_str::<Value>(poi_json) else { return false };
        let arr4 = |a: &Value| -> [f64; 4] { let a = a.as_array().cloned().unwrap_or_default(); let g = |i: usize| a.get(i).and_then(|x| x.as_f64()).unwrap_or(0.0); [g(0), g(1), g(2), g(3)] };
        self.walk = Walker { x, y, w: v["w"].as_f64().unwrap_or(1280.0), h: v["h"].as_f64().unwrap_or(720.0), r: 18.0,
            solids: v["solids"].as_array().map(|a| a.iter().map(arr4).collect()).unwrap_or_default(), triggers: vec![] };
        if let Some(t) = v["triggers"].as_array() { for t in t { self.walk.triggers.push((t["id"].as_str().unwrap_or("").into(), arr4(&t["rect"]))); } }
        if let Some(t) = v["exits"].as_array() { for (k, t) in t.iter().enumerate() { self.walk.triggers.push((format!("exit:{k}"), arr4(&t["rect"]))); } }
        true
    }
    pub fn walker_step(&mut self, vx: f64, vy: f64, dt: f64) -> Vec<f64> {
        let w = &mut self.walk; let r = w.r;
        let nx = (w.x + vx * dt).clamp(r, (w.w - r).max(r));
        if !w.solids.iter().any(|s| overlap(nx, w.y, r, s)) { w.x = nx; }
        let ny = (w.y + vy * dt).clamp(r, (w.h - 4.0).max(r));
        if !w.solids.iter().any(|s| overlap(w.x, ny, r, s)) { w.y = ny; }
        vec![w.x, w.y]
    }
    pub fn walker_set(&mut self, x: f64, y: f64) { self.walk.x = x; self.walk.y = y; }
    pub fn walker_triggers(&self) -> String {
        let w = &self.walk;
        w.triggers.iter().filter(|(_, s)| w.x > s[0] && w.x < s[0] + s[2] && w.y > s[1] && w.y < s[1] + s[3]).map(|(id, _)| id.clone()).collect::<Vec<_>>().join(",")
    }
}

#[allow(dead_code)]
fn _unused(e: serde_json::Error) -> JsValue { err("", e) }
