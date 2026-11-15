import sys; import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from rep import edits, P
edits([
("#[derive(Clone)]\nstruct Combo {",
"""/// Flee chance (seeded, deterministic): p = clamp(base + per_spd * (avg party SPD - avg enemy SPD)
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
struct Combo {"""),
("    enemy_dmg_mult: f64,\n}",
 "    enemy_dmg_mult: f64,\n    // encounter flags (Ashley's zones.json `fixed.<id>.canFlee`, encounters.js `first`)\n    can_flee: bool, first: Option<String>, flee_fails: u32, flee_rules: FleeRules,\n}"),
("enemy_dmg_mult: 0.8 })", "enemy_dmg_mult: 0.8, can_flee: true, first: None, flee_fails: 0, flee_rules: FleeRules::default() })"),
("        if v[\"combo_windows\"].is_object() { self.win.apply(&v[\"combo_windows\"]); }\n        self.ink.apply(&v);",
 "        if v[\"combo_windows\"].is_object() { self.win.apply(&v[\"combo_windows\"]); }\n        if v[\"flee\"].is_object() { self.flee_rules.apply(&v[\"flee\"]); }\n        self.ink.apply(&v);"),
("    pub fn start_battle(&mut self, encounter: &str) -> String {\n        self.fighters.clear();",
 """    /// Start a battle with optional encounter flags: `{ "first": "enemy"|"party"|null, "canFlee": bool }`
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
        self.can_flee = can_flee; self.first = first; self.flee_fails = 0;
        self.fighters.clear();"""),
("""        o.sort_by(|&a, &b| key(b).partial_cmp(&key(a)).unwrap().then(a.cmp(&b)));
        self.order = o; self.turn_pos = 0;""",
"""        o.sort_by(|&a, &b| key(b).partial_cmp(&key(a)).unwrap().then(a.cmp(&b)));
        if self.round == 1 { if let Some(side) = self.first.as_deref() { // ambush: that side acts first in round 1 (stable, keeps speed order)
            let s = if side == "enemy" { 1 } else { 0 };
            let (mut a, b): (Vec<usize>, Vec<usize>) = o.iter().partition(|&&i| self.fighters[i].side == s); a.extend(b); o = a;
        } }
        self.order = o; self.turn_pos = 0;"""),
("""        json!({"fighters": self.fighters, "turn": self.current(), "round": self.round, "over": self.battle_over}).to_string()""",
 """        json!({"fighters": self.fighters, "turn": self.current(), "round": self.round, "over": self.battle_over,
               "canFlee": self.can_flee, "first": self.first, "fleeChance": self.flee_chance()}).to_string()"""),
])
# tests
open(P,'a').write(r'''
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
''')
