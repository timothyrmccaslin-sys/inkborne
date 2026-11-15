//! Inkborne core: battle rules, Brushstroke timing judgement, Vermilion Ink / Inkwing,
//! Six Inks elements, Still Water guard, items, inventory + mon, POI walker collision, saves.
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::BTreeMap;
use wasm_bindgen::prelude::*;

// ---------- data ----------
#[derive(Clone, Serialize, Deserialize)]
pub struct Hit { pub gap_ms: f64, pub mult: f64 }
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
}
#[derive(Clone, Serialize, Deserialize)]
pub struct Move { pub id: String, pub name: String, pub kind: String, pub power: f64, #[serde(default)] pub element: Option<String>, pub weight: u32 }
#[derive(Clone, Serialize, Deserialize)]
pub struct EnemyDef { pub id: String, pub name: String, pub element: String, pub hp: f64, pub atk: f64, pub def: f64, pub mat: f64, pub mdf: f64, pub spd: f64, pub mon: u32, pub moves: Vec<Move> }
#[derive(Clone, Serialize, Deserialize)]
pub struct Item { pub id: String, pub name: String, pub desc: String, pub kind: String, pub power: f64, #[serde(default)] pub element: Option<String>, pub price: u32 }

#[derive(Deserialize)] struct PartyFile { members: Vec<Member> }
#[derive(Deserialize)] struct EnemyFile { enemies: Vec<EnemyDef>, encounters: BTreeMap<String, Vec<String>> }
#[derive(Deserialize)] struct ItemFile { items: Vec<Item> }

/// Six Inks: opposite pairs deal x2, same element x0.5.
pub fn elem_mod(atk: &str, def: &str) -> f64 {
    let opp = |a: &str| match a { "ember" => "tide", "tide" => "ember", "gale" => "stone", "stone" => "gale", "dawn" => "dusk", "dusk" => "dawn", _ => "" };
    if atk.is_empty() || def.is_empty() { 1.0 } else if opp(atk) == def { 2.0 } else if atk == def { 0.5 } else { 1.0 }
}

/// Brushstroke judgement. `delta_ms` = press time - ring-close time.
/// 2 = Clean Line, 1 = good, 0 = miss (chain breaks).
pub const CLEAN_MS: f64 = 95.0;
pub const GOOD_MS: f64 = 150.0;
pub fn judge_delta(delta_ms: f64) -> u8 { let d = delta_ms.abs(); if d <= CLEAN_MS { 2 } else if d <= GOOD_MS { 1 } else { 0 } }

struct Rng(u64);
impl Rng { fn next(&mut self) -> f64 { self.0 ^= self.0 << 13; self.0 ^= self.0 >> 7; self.0 ^= self.0 << 17; (self.0 >> 11) as f64 / (1u64 << 53) as f64 } }

#[derive(Clone, Serialize)]
struct Fighter { side: u8, idx: usize, id: String, name: String, element: String, hp: f64, max_hp: f64, atk: f64, def: f64, mat: f64, mdf: f64, spd: f64,
    ink: f64, guarding: bool, inkwing: u32, alive: bool, mon: u32, #[serde(skip)] fm: [f64; 5], form: String }

#[derive(Serialize, Deserialize, Clone, Default)]
struct Save { gold: u32, inv: BTreeMap<String, u32>, hp: BTreeMap<String, f64>, ink: BTreeMap<String, f64>, flags: BTreeMap<String, bool>, node: String }

#[wasm_bindgen]
pub struct Game {
    party: Vec<Member>, enemies: Vec<EnemyDef>, encounters: BTreeMap<String, Vec<String>>, items: Vec<Item>,
    st: Save, rng: Rng,
    // battle
    fighters: Vec<Fighter>, order: Vec<usize>, turn_pos: usize, round: u32, battle_over: Option<String>,
    // walker
    walk: Walker,
    forms: BTreeMap<String, (String, String, [f64; 5])>,
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
        for m in &p.members { st.hp.insert(m.id.clone(), m.hp); st.ink.insert(m.id.clone(), m.ink); }
        Ok(Game { party: p.members, enemies: e.enemies, encounters: e.encounters, items: i.items, st, rng: Rng(seed as u64 * 2654435761 + 1),
            fighters: vec![], order: vec![], turn_pos: 0, round: 0, battle_over: None, walk: Walker::default(), forms: BTreeMap::new() })
    }

    /// Load Inkwing forms from transformation.json (optional; defaults otherwise).
    pub fn set_rules(&mut self, tj: &str) -> bool {
        let Ok(v) = serde_json::from_str::<Value>(tj) else { return false };
        if let Some(f) = v["forms"].as_object() { for (id, x) in f {
            let m = &x["mult"]; let g = |k: &str| m[k].as_f64().unwrap_or(1.0);
            self.forms.insert(id.clone(), (x["form_name"].as_str().unwrap_or("").into(), x["passive"]["id"].as_str().unwrap_or("").into(), [g("atk"), g("def"), g("mat"), g("mdf"), g("spd")]));
        } }
        true
    }
    fn passive_on(&self, pid: &str) -> bool { self.fighters.iter().any(|f| f.side == 0 && f.alive && f.inkwing > 0 && self.forms.get(&f.id).map(|x| x.1 == pid).unwrap_or(false)) }
    fn st(&self, i: usize, k: usize) -> f64 { let f = &self.fighters[i]; let b = [f.atk, f.def, f.mat, f.mdf, f.spd][k]; if f.inkwing > 0 { b * f.fm[k] } else { b } }
    fn add_ink(&mut self, i: usize, n: f64) { let f = &mut self.fighters[i]; if f.side == 0 && f.alive && f.inkwing == 0 { f.ink = (f.ink + n).clamp(0.0, 100.0); } }
    // ---------- save / economy ----------
    pub fn save_json(&self) -> String { serde_json::to_string(&self.st).unwrap() }
    pub fn load_json(&mut self, s: &str) -> bool { match serde_json::from_str::<Save>(s) { Ok(v) => { self.st = v; true } Err(_) => false } }
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
        let v: Vec<Value> = self.party.iter().map(|m| json!({"id": m.id, "name": m.name, "title": m.title, "element": m.element, "lv": m.lv,
            "hp": self.st.hp[&m.id], "maxHp": m.hp, "ink": self.st.ink[&m.id], "strokes": m.strokes, "seal": m.seal})).collect();
        Value::Array(v).to_string()
    }
    pub fn rest(&mut self) { for m in &self.party { self.st.hp.insert(m.id.clone(), m.hp); } }

    /// Timed-press judgement exposed to the renderer (single source of truth for windows).
    pub fn judge(&self, delta_ms: f64) -> u8 { judge_delta(delta_ms) }
    pub fn windows_json(&self) -> String { json!({"clean": CLEAN_MS, "good": GOOD_MS}).to_string() }

    // ---------- battle ----------
    pub fn start_battle(&mut self, encounter: &str) -> String {
        self.fighters.clear(); self.battle_over = None; self.round = 0;
        for (i, m) in self.party.iter().enumerate() {
            let hp = self.st.hp[&m.id].max(1.0);
            self.fighters.push(Fighter { side: 0, idx: i, id: m.id.clone(), name: m.name.clone(), element: m.element.clone(), hp, max_hp: m.hp, atk: m.atk, def: m.def,
                mat: m.mat, mdf: m.mdf, spd: m.spd, ink: self.st.ink[&m.id], guarding: false, inkwing: 0, alive: true, mon: 0, fm: forms_of(&self.forms, &m.id), form: self.forms.get(&m.id).map(|f| f.0.clone()).unwrap_or_default() });
        }
        let ids = self.encounters.get(encounter).cloned().unwrap_or_default();
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
        self.order = o; self.turn_pos = 0;
    }
    pub fn battle_json(&self) -> String {
        json!({"fighters": self.fighters, "turn": self.current(), "round": self.round, "over": self.battle_over}).to_string()
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
        if win { let m: u32 = self.fighters.iter().filter(|f| f.side == 1).map(|f| f.mon).sum(); self.st.gold += m; }
    }
    pub fn spoils(&self) -> u32 { self.fighters.iter().filter(|f| f.side == 1).map(|f| f.mon).sum() }
    fn var(&mut self) -> f64 { 0.94 + self.rng.next() * 0.12 }
    fn hurt(&mut self, t: usize, raw: f64) -> f64 {
        let mantle = self.fighters[t].side == 0 && self.passive_on("slate_mantle");
        let f = &mut self.fighters[t];
        let mut d = raw.max(1.0);
        if f.guarding { d *= 0.5 }
        if mantle { d *= 0.85 }
        let d = d.round();
        f.hp = (f.hp - d).max(0.0); if f.hp <= 0.0 { f.alive = false; f.inkwing = 0; if f.side == 0 { f.ink = 0.0 } }
        if f.side == 0 && f.alive && f.inkwing == 0 { // Vermilion Ink from damage taken (Jake): round(30*dmg/max), 1..15, x1.5 in Still Water
            let mut g = (30.0 * d / f.max_hp).round().clamp(1.0, 15.0); if f.guarding { g = (g * 1.5).round() }
            f.ink = (f.ink + g).min(100.0);
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
        let em = elem_mod(&elem, &self.fighters[target].element);
        for (k, h) in s.hits.iter().enumerate() {
            let g = *grades.get(k).unwrap_or(&0);
            if g == 0 { events.push(json!({"hit": k, "grade": 0})); break }
            landed += 1; if g == 2 { cleans += 1 }
            let mut r = raw(atk, def) * h.mult * em * self.var();
            if g == 2 { r *= 1.25 }
            if landed == s.hits.len() { r *= s.finish_mult }
            let d = self.hurt(target, r);
            self.add_ink(actor, if g == 2 { 8.0 } else { 4.0 });
            let killed = !self.fighters[target].alive; if killed { self.add_ink(actor, 3.0) }
            events.push(json!({"hit": k, "grade": g, "dmg": d, "target": target, "killed": killed}));
            if killed { break }
        }
        let full = landed == s.hits.len(); let perfect = full && cleans == s.hits.len();
        if perfect { self.add_ink(actor, 10.0) } else if full { self.add_ink(actor, 6.0) }
        if landed == 0 { let v = self.var(); let d = self.hurt(target, raw(atk, def) * 0.3 * v); events.push(json!({"glance": true, "dmg": d, "target": target})); }
        let out = json!({"kind": "stroke", "name": s.name, "events": events, "full": full, "perfect": perfect, "elem": em, "ink": self.fighters[actor].ink});
        self.tick_inkwing(actor); self.advance(); out.to_string()
    }
    /// Inkwing: needs a full gauge, lasts 3 of this character's turns. Uses this turn.
    pub fn inkwing(&mut self, actor: usize) -> String {
        let a = &mut self.fighters[actor];
        if a.side != 0 || a.ink < 100.0 || a.inkwing > 0 { return json!({"ok": false}).to_string() }
        a.ink = 0.0; a.inkwing = 4; // decremented at end of this turn -> 3 Inkwing turns
        let heal = (a.max_hp * 0.15).round().min(a.max_hp - a.hp); a.hp += heal;
        let out = json!({"kind": "inkwing", "ok": true, "actor": actor, "heal": heal, "form": a.form});
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
            let em = elem_mod(&m.seal.element, &self.fighters[t].element);
            let dstat = if m.seal.stat == "atk" { self.st(t, 1) } else { self.st(t, 3) };
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
    fn tick_inkwing(&mut self, actor: usize) { let a = &mut self.fighters[actor]; if a.inkwing > 0 { a.inkwing -= 1; } }
    /// Still Water: halve damage until next turn and restore 10% max HP.
    pub fn guard(&mut self, actor: usize) -> String {
        let a = &mut self.fighters[actor];
        let heal = (a.max_hp * if a.inkwing > 0 { 0.15 } else { 0.1 }).round().min(a.max_hp - a.hp); a.hp += heal; a.guarding = true;
        if a.inkwing == 0 { a.ink = (a.ink + 6.0).min(100.0) }
        let out = json!({"kind": "guard", "actor": actor, "heal": heal});
        self.tick_inkwing(actor); self.advance_keep_guard(actor); out.to_string()
    }
    fn advance_keep_guard(&mut self, actor: usize) { self.advance(); if self.current() as usize != actor { self.fighters[actor].guarding = true; } }
    pub fn use_item(&mut self, actor: usize, item: &str, target: usize) -> String {
        let have = self.st.inv.get(item).copied().unwrap_or(0);
        let Some(it) = self.items.iter().find(|i| i.id == item).cloned() else { return json!({"ok": false}).to_string() };
        if have == 0 { return json!({"ok": false}).to_string() }
        self.st.inv.insert(item.into(), have - 1);
        let mut events = vec![];
        match it.kind.as_str() {
            "heal" => { let f = &mut self.fighters[target]; let h = it.power.min(f.max_hp - f.hp); f.hp += h; events.push(json!({"target": target, "heal": h})); }
            "healall" => for i in 0..self.fighters.len() { let f = &mut self.fighters[i]; if f.side == 0 && f.alive { let h = it.power.min(f.max_hp - f.hp); f.hp += h; events.push(json!({"target": i, "heal": h})); } },
            "ink" => { let f = &mut self.fighters[target]; f.ink = (f.ink + it.power).min(100.0); events.push(json!({"target": target, "ink": f.ink})); }
            "bomb" => { let e = it.element.clone().unwrap_or_default(); let em = elem_mod(&e, &self.fighters[target].element); let v = self.var(); let d = self.hurt(target, it.power * em * v); events.push(json!({"target": target, "dmg": d, "elem": em, "killed": !self.fighters[target].alive})); }
            _ => {}
        }
        let out = json!({"kind": "item", "ok": true, "item": it.name, "itemKind": it.kind, "events": events});
        self.tick_inkwing(actor); self.advance(); out.to_string()
    }
    /// Enemy acts (call when current() is an enemy). Picks a weighted move and a living party target.
    pub fn enemy_turn(&mut self) -> String {
        let me = self.current(); if me < 0 { return "{}".into() } let me = me as usize;
        if self.fighters[me].side != 1 { return "{}".into() }
        let def = match self.enemies.iter().find(|e| e.id == self.fighters[me].id).cloned() { Some(d) if !d.moves.is_empty() => d, _ => { self.advance(); return json!({"kind": "enemy", "actor": me, "move": "hesitates", "target": -1, "dmg": 0}).to_string() } };
        let total: u32 = def.moves.iter().map(|m| m.weight).sum();
        let mut r = (self.rng.next() * total as f64) as u32; let mut mv = def.moves[0].clone();
        for m in &def.moves { if r < m.weight { mv = m.clone(); break } r -= m.weight; }
        let alive: Vec<usize> = (0..self.fighters.len()).filter(|&i| self.fighters[i].side == 0 && self.fighters[i].alive).collect();
        if alive.is_empty() { self.advance(); return "{}".into() }
        let t = alive[(self.rng.next() * alive.len() as f64) as usize % alive.len()];
        let (raw, em) = if mv.kind == "elem" {
            let e = mv.element.clone().unwrap_or_default(); let em = elem_mod(&e, &self.fighters[t].element);
            { let v = self.var(); (raw(self.st(me, 2), self.st(t, 3)) * mv.power * em * v * 0.8, em) }
        } else { let v = self.var(); (raw(self.st(me, 0), self.st(t, 1)) * mv.power * v * 0.8, 1.0) };
        let guarded = self.fighters[t].guarding;
        let d = self.hurt(t, raw);
        let out = json!({"kind": "enemy", "actor": me, "move": mv.name, "moveKind": mv.kind, "element": mv.element, "target": t, "dmg": d, "elem": em, "guarded": guarded, "killed": !self.fighters[t].alive});
        self.advance(); out.to_string()
    }
    /// Demo/debug: set a party member's Vermilion Ink.
    pub fn debug_ink(&mut self, actor: usize, v: f64) { if let Some(f) = self.fighters.get_mut(actor) { f.ink = v.clamp(0.0, 100.0) } }

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
