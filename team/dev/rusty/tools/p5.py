import sys; import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from rep import edits, P
s=open(P).read()
a=s.index("    /// Enemy acts (call when current() is an enemy).") if "    /// Enemy acts (call when current() is an enemy)." in s else s.index("    pub fn enemy_turn(&mut self) -> String {")
b=s.index("        self.advance(); out.to_string()\n    }\n", s.index("pub fn enemy_turn"))+len("        self.advance(); out.to_string()\n    }\n")
new='''    /// Enemy acts (call when current() is an enemy). Data-driven AI (enemies.json, all fields optional):
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
            let f = &mut self.fighters[t]; let h = (mv.power * self.fighters[me].mat.max(1.0)).round();
            let f = { let _ = f; &mut self.fighters[t] };
            let h = h.min(f.max_hp - f.hp).max(0.0); f.hp += h;
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
'''
s=s[:a]+new+s[b:]
open(P,'w').write(s)
edits([
("pub struct Move { pub id: String, pub name: String, pub kind: String, pub power: f64, #[serde(default)] pub element: Option<String>, pub weight: u32 }",
 "pub struct Move { pub id: String, pub name: String, pub kind: String, #[serde(default = \"one_f\")] pub power: f64, #[serde(default)] pub element: Option<String>, #[serde(default = \"one_u\")] pub weight: u32,\n    /// AI: target rule (see `enemy_turn`) and HP gate. Optional.\n    #[serde(default, skip_serializing_if = \"Option::is_none\")] pub target: Option<String>,\n    #[serde(default, skip_serializing_if = \"Option::is_none\")] pub hp_below: Option<f64> }\nfn one_f() -> f64 { 1.0 }\nfn one_u() -> u32 { 1 }"),
("pub mon: u32, pub moves: Vec<Move> }",
 "pub mon: u32, pub moves: Vec<Move>,\n    /// Default AI target rule for this enemy's moves (optional).\n    #[serde(default, skip_serializing_if = \"Option::is_none\")] pub ai: Option<String> }"),
("    chart: Option<BTreeMap<String, BTreeMap<String, f64>>>,\n    guard_rules: GuardRules,\n}",
 "    chart: Option<BTreeMap<String, BTreeMap<String, f64>>>,\n    guard_rules: GuardRules,\n    enemy_dmg_mult: f64,\n}"),
("guard_rules: GuardRules::default() })", "guard_rules: GuardRules::default(), enemy_dmg_mult: 0.8 })"),
("        let ids = self.encounters.get(encounter).cloned().unwrap_or_default();",
 "        let mut ids = self.encounters.get(encounter).cloned().unwrap_or_default();\n        ids.truncate(3); // the battle stage holds 1-3 enemies"),
])
