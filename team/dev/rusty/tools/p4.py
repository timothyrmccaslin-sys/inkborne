import sys; import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from rep import edits
edits([
("#[derive(Clone)]\nstruct Combo {",
"""/// Still Water (guard): damage taken x`damage_mult` until the guarder's next turn, heal `heal_pct`% max HP
/// (`heal_pct_inkwing`% in Inkwing). SPEC section 2: halves damage, heals 10%. Jake: 15% in Inkwing.
/// Data: transformation.json `inkwing_rules.still_water_heal_pct`, optional `still_water { damage_mult, heal_pct }`.
#[derive(Clone)]
struct GuardRules { damage_mult: f64, heal_pct: f64, heal_pct_inkwing: f64 }
impl Default for GuardRules { fn default() -> Self { GuardRules { damage_mult: 0.5, heal_pct: 10.0, heal_pct_inkwing: 15.0 } } }

#[derive(Clone)]
struct Combo {"""),
("    chart: Option<BTreeMap<String, BTreeMap<String, f64>>>,\n}", "    chart: Option<BTreeMap<String, BTreeMap<String, f64>>>,\n    guard_rules: GuardRules,\n}"),
("chart: None })", "chart: None, guard_rules: GuardRules::default() })"),
("        self.ink.apply(&v);\n        true",
 """        self.ink.apply(&v);
        if let Some(x) = v["inkwing_rules"]["still_water_heal_pct"].as_f64() { self.guard_rules.heal_pct_inkwing = x.max(0.0) }
        if let Some(x) = v["still_water"]["heal_pct"].as_f64() { self.guard_rules.heal_pct = x.max(0.0) }
        if let Some(x) = v["still_water"]["damage_mult"].as_f64() { self.guard_rules.damage_mult = x.clamp(0.0, 1.0) }
        true"""),
("        let ir = self.ink.clone();\n        let f = &mut self.fighters[t];",
 "        let ir = self.ink.clone(); let gm = self.guard_rules.damage_mult;\n        let f = &mut self.fighters[t];"),
("        if f.guarding { d *= 0.5 }", "        if f.guarding { d *= gm }"),
("""    pub fn guard(&mut self, actor: usize) -> String {
        let a = &mut self.fighters[actor];
        let heal = (a.max_hp * if a.inkwing > 0 { 0.15 } else { 0.1 }).round().min(a.max_hp - a.hp); a.hp += heal; a.guarding = true;
        if a.inkwing == 0 { a.ink = (a.ink + self.ink.still_water_use).min(self.ink.max) }
        let out = json!({"kind": "guard", "actor": actor, "heal": heal});""",
"""    /// Still Water: damage x0.5 until this fighter's next turn, heals 10% max HP (15% in Inkwing), +6 Vermilion Ink
    /// (not in Inkwing); Ink from damage taken while guarding is x1.5. Uses the turn.
    pub fn guard(&mut self, actor: usize) -> String {
        if self.battle_over.is_some() { return json!({"ok": false, "reason": "over"}).to_string() }
        let gr = self.guard_rules.clone();
        let Some(a) = self.fighters.get_mut(actor) else { return json!({"ok": false, "reason": "bad_index"}).to_string() };
        if !a.alive { return json!({"ok": false, "reason": "down"}).to_string() }
        let pct = if a.inkwing > 0 { gr.heal_pct_inkwing } else { gr.heal_pct };
        let heal = (a.max_hp * pct / 100.0).round().min(a.max_hp - a.hp).max(0.0); a.hp += heal; a.guarding = true;
        if a.side == 0 && a.inkwing == 0 { a.ink = (a.ink + self.ink.still_water_use).min(self.ink.max) }
        let out = json!({"kind": "guard", "ok": true, "actor": actor, "heal": heal, "hp": a.hp, "ink": a.ink, "damage_mult": gr.damage_mult});"""),
])
