import sys; import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from rep import edits, P
edits([
("    fn var(&mut self) -> f64 { 0.94 + self.rng.next() * 0.12 }",
 "    /// Damage variance, uniform VAR_MIN..VAR_MAX from the seeded RNG (Jake DESIGN.md: 0.95..1.05).\n    fn var(&mut self) -> f64 { VAR_MIN + self.rng.next() * (VAR_MAX - VAR_MIN) }"),
("pub fn judge_delta(delta_ms: f64) -> u8 {",
 "/// Damage variance bounds (Jake, DESIGN.md section 2).\npub const VAR_MIN: f64 = 0.95;\npub const VAR_MAX: f64 = 1.05;\npub fn judge_delta(delta_ms: f64) -> u8 {"),
("            let dstat = if m.seal.stat == \"atk\" { self.st(t, 1) } else { self.st(t, 3) };",
 "            // Seal Arts always hit the defender's mdf; seal.stat only picks the attacker's stat (Jake, DESIGN.md).\n            let dstat = self.st(t, 3);"),
])
open(P,'a').write(r'''
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
''')
