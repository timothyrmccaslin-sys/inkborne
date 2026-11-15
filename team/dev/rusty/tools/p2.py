import sys; import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from rep import edits
edits([
("#[derive(Clone)]\nstruct Combo {",
"""/// Vermilion Ink + Unfurl rules. Fallback defaults mirror Jake's team/systems/jake/transformation.json (2026-11-15 3:36 PM);
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

#[derive(Clone)]
struct Combo {"""),
("    win: Windows, combo: Option<Combo>,\n}", "    win: Windows, combo: Option<Combo>, ink: InkRules,\n}"),
("win: Windows::default(), combo: None })", "win: Windows::default(), combo: None, ink: InkRules::default() })"),
("        if v[\"combo_windows\"].is_object() { self.win.apply(&v[\"combo_windows\"]); }\n        true",
 "        if v[\"combo_windows\"].is_object() { self.win.apply(&v[\"combo_windows\"]); }\n        self.ink.apply(&v);\n        true"),
("if f.side == 0 && f.alive && f.inkwing == 0 { f.ink = (f.ink + n).clamp(0.0, 100.0); } }",
 "if f.side == 0 && f.alive && (f.inkwing == 0 || self.ink.gain_while_inkwing) { f.ink = (f.ink + n).clamp(0.0, self.ink.max); } }"),
("""        let mantle = self.fighters[t].side == 0 && self.passive_on("slate_mantle");
        let f = &mut self.fighters[t];""",
"""        let mantle = self.fighters[t].side == 0 && self.passive_on("slate_mantle");
        let ir = self.ink.clone();
        let f = &mut self.fighters[t];"""),
("""if f.hp <= 0.0 { f.alive = false; f.inkwing = 0; if f.side == 0 { f.ink = 0.0 } }
        if f.side == 0 && f.alive && f.inkwing == 0 { // Vermilion Ink from damage taken (Jake): round(30*dmg/max), 1..15, x1.5 in Still Water
            let mut g = (30.0 * d / f.max_hp).round().clamp(1.0, 15.0); if f.guarding { g = (g * 1.5).round() }
            f.ink = (f.ink + g).min(100.0);""",
"""if f.hp <= 0.0 { f.alive = false; f.inkwing = 0; if f.side == 0 && ir.ko_reset { f.ink = 0.0 } }
        if f.side == 0 && f.alive && (f.inkwing == 0 || ir.gain_while_inkwing) { // Vermilion Ink from damage taken (Jake, transformation.json fill.damage_taken)
            let g = ir.from_damage(d, f.max_hp, f.guarding);
            f.ink = (f.ink + g).min(ir.max);"""),
("""            self.add_ink(actor, if g == 2 { 8.0 } else { 4.0 });
            let killed = !self.fighters[target].alive; if killed { self.add_ink(actor, 3.0) }""",
"""            self.add_ink(actor, self.ink.stroke_hit + if g == 2 { self.ink.clean_bonus } else { 0.0 });
            let killed = !self.fighters[target].alive; if killed { self.add_ink(actor, self.ink.kill) }"""),
("        if perfect { self.add_ink(actor, 10.0) } else if full { self.add_ink(actor, 6.0) }",
 """        if perfect { let b = self.ink.perfect_chain + if self.ink.perfect_replaces { 0.0 } else { self.ink.chain_complete }; self.add_ink(actor, b) }
        else if full { self.add_ink(actor, self.ink.chain_complete) }"""),
("""    /// Inkwing: needs a full gauge, lasts 3 of this character's turns. Uses this turn.
    pub fn inkwing(&mut self, actor: usize) -> String {
        let a = &mut self.fighters[actor];
        if a.side != 0 || a.ink < 100.0 || a.inkwing > 0 { return json!({"ok": false}).to_string() }
        a.ink = 0.0; a.inkwing = 4; // decremented at end of this turn -> 3 Inkwing turns
        let heal = (a.max_hp * 0.15).round().min(a.max_hp - a.hp); a.hp += heal;
        let out = json!({"kind": "inkwing", "ok": true, "actor": actor, "heal": heal, "form": a.form});""",
"""    /// Unfurl (the battle command) into Inkwing form. Needs ink >= unfurl.cost (a full gauge), not already Inkwing.
    /// Uses this turn; the next `unfurl.duration_turns` (3) own turns are Inkwing. Heals unfurl.heal_pct_max_hp.
    pub fn inkwing(&mut self, actor: usize) -> String {
        let ir = self.ink.clone();
        let Some(a) = self.fighters.get_mut(actor) else { return json!({"ok": false, "reason": "bad_index"}).to_string() };
        if a.side != 0 || !a.alive { return json!({"ok": false, "reason": "not_party_actor"}).to_string() }
        if a.inkwing > 0 { return json!({"ok": false, "reason": "already_inkwing"}).to_string() }
        if a.ink < ir.unfurl_cost { return json!({"ok": false, "reason": "ink_not_full", "ink": a.ink, "cost": ir.unfurl_cost}).to_string() }
        a.ink = 0.0; a.inkwing = ir.unfurl_turns + 1; // decremented at end of this turn -> unfurl_turns Inkwing turns
        let heal = (a.max_hp * ir.unfurl_heal_pct / 100.0).round().min(a.max_hp - a.hp); a.hp += heal;
        let out = json!({"kind": "inkwing", "ok": true, "actor": actor, "heal": heal, "form": a.form, "turns": ir.unfurl_turns});"""),
("    fn tick_inkwing(&mut self, actor: usize) {",
 "    /// Alias of `inkwing` under the command's name (SPEC section 2: the command is Unfurl, the form is Inkwing).\n    pub fn unfurl(&mut self, actor: usize) -> String { self.inkwing(actor) }\n    /// Whether `actor` may Unfurl right now.\n    pub fn can_unfurl(&self, actor: usize) -> bool { self.fighters.get(actor).map(|a| a.side == 0 && a.alive && a.inkwing == 0 && a.ink >= self.ink.unfurl_cost).unwrap_or(false) }\n    /// Gauge rules in effect: `{max, unfurl_cost, unfurl_turns}`.\n    pub fn ink_rules_json(&self) -> String { json!({\"max\": self.ink.max, \"unfurl_cost\": self.ink.unfurl_cost, \"unfurl_turns\": self.ink.unfurl_turns, \"stroke_hit\": self.ink.stroke_hit, \"clean_bonus\": self.ink.clean_bonus}).to_string() }\n    fn tick_inkwing(&mut self, actor: usize) {"),
("        if a.inkwing == 0 { a.ink = (a.ink + 6.0).min(100.0) }",
 "        if a.inkwing == 0 { a.ink = (a.ink + self.ink.still_water_use).min(self.ink.max) }"),
("\"ink\" => { let f = &mut self.fighters[target]; f.ink = (f.ink + it.power).min(100.0);",
 "\"ink\" => { let mx = self.ink.max; let f = &mut self.fighters[target]; if f.inkwing == 0 { f.ink = (f.ink + it.power).min(mx); }"),
("f.ink = v.clamp(0.0, 100.0) } }", "f.ink = v.clamp(0.0, self.ink.max) } }"),
])
