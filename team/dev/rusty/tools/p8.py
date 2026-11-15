import sys; import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from rep import edits, P
edits([
("    #[serde(default)] pub cur_hp: Option<f64>,",
 "    #[serde(default)] pub cur_hp: Option<f64>,\n    /// Jake's precomputed per-level stats (index = lv - 1). Optional; needed for level-ups.\n    #[serde(default, skip_serializing)] pub stat_table: Vec<StatRow>,"),
("pub mon: u32, pub moves: Vec<Move>,",
 "pub mon: u32, pub moves: Vec<Move>,\n    /// XP awarded at victory (SPEC section 7, optional, default 0).\n    #[serde(default)] pub xp: u32,"),
("#[derive(Deserialize)] struct PartyFile { members: Vec<Member> }",
 """#[derive(Deserialize)] struct PartyFile { members: Vec<Member>, #[serde(default)] progression: Progression }
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
}"""),
("flags: BTreeMap<String, bool>, node: String }",
 "flags: BTreeMap<String, bool>, node: String,\n    /// Per-member cumulative XP and level (0008). Older saves load with these empty.\n    #[serde(default)] xp: BTreeMap<String, u32>, #[serde(default)] lv: BTreeMap<String, u32> }"),
("        for m in &p.members { st.hp.insert(m.id.clone(), m.hp); st.ink.insert(m.id.clone(), m.ink); }",
 "        for m in &p.members { st.hp.insert(m.id.clone(), m.hp); st.ink.insert(m.id.clone(), m.ink);\n            st.lv.insert(m.id.clone(), m.lv.max(1)); st.xp.insert(m.id.clone(), p.progression.total_at(m.lv).unwrap_or(0)); }\n        let progression = p.progression;"),
("can_flee: true, first: None, flee_fails: 0, flee_rules: FleeRules::default() })",
 "can_flee: true, first: None, flee_fails: 0, flee_rules: FleeRules::default(), progression, rewards: None })"),
("    can_flee: bool, first: Option<String>, flee_fails: u32, flee_rules: FleeRules,\n}",
 "    can_flee: bool, first: Option<String>, flee_fails: u32, flee_rules: FleeRules,\n    progression: Progression, rewards: Option<Value>,\n}"),
("    pub fn load_json(&mut self, s: &str) -> bool { match serde_json::from_str::<Save>(s) { Ok(v) => { self.st = v; true } Err(_) => false } }",
 """    pub fn load_json(&mut self, s: &str) -> bool {
        match serde_json::from_str::<Save>(s) {
            Ok(v) => {
                self.st = v;
                for i in 0..self.party.len() { // restore level (clamped 1..cap) and its stat_table row
                    let id = self.party[i].id.clone();
                    let lv = self.st.lv.get(&id).copied().unwrap_or(self.party[i].lv).clamp(1, self.progression.cap().max(self.party[i].lv));
                    self.st.lv.insert(id.clone(), lv); self.st.xp.entry(id.clone()).or_insert(0);
                    self.st.ink.entry(id.clone()).or_insert(0.0); // partial/old saves: avoid the map-index panic in party_json/start_battle
                    self.apply_level(i, lv);
                    let mx = self.party[i].hp; self.st.hp.entry(id).or_insert(mx);
                }
                true
            }
            Err(_) => false,
        }
    }
    /// Set member `i`'s stats from `stat_table[lv-1]` (no-op without a table). Returns the max-HP gain.
    fn apply_level(&mut self, i: usize, lv: u32) -> f64 {
        let m = &mut self.party[i];
        let Some(r) = m.stat_table.iter().find(|r| r.lv == lv).cloned() else { return 0.0 };
        let gain = r.hp - m.hp;
        m.lv = lv; m.hp = r.hp; m.atk = r.atk; m.def = r.def; m.mat = r.mat; m.mdf = r.mdf; m.spd = r.spd;
        gain
    }
    /// XP/level-ups from the last victory: `{mon, xp, members:[{id, name, alive, gained, xp, lv_before, lv, leveled_up, next_total, stats?}]}` or null.
    pub fn rewards_json(&self) -> String { self.rewards.clone().unwrap_or(Value::Null).to_string() }"""),
("\"element\": m.element, \"lv\": m.lv,",
 "\"element\": m.element, \"lv\": self.st.lv.get(&m.id).copied().unwrap_or(m.lv), \"xp\": self.st.xp.get(&m.id).copied().unwrap_or(0), \"nextXp\": self.progression.total_at(self.st.lv.get(&m.id).copied().unwrap_or(m.lv) + 1),"),
("        self.can_flee = can_flee; self.first = first; self.flee_fails = 0;",
 "        self.can_flee = can_flee; self.first = first; self.flee_fails = 0; self.rewards = None;"),
("        if win { let m: u32 = self.fighters.iter().filter(|f| f.side == 1).map(|f| f.mon).sum(); self.st.gold += m; }",
 "        if win { let m: u32 = self.fighters.iter().filter(|f| f.side == 1).map(|f| f.mon).sum(); self.st.gold += m; self.award_xp(m); }"),
("    pub fn spoils(&self) -> u32 {",
 """    /// Jake's XP rule: every member alive at victory gets the full encounter XP (sum of enemy `xp`); KO'd members get 0.
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
    pub fn spoils(&self) -> u32 {"""),
("               \"canFlee\": self.can_flee, \"first\": self.first, \"fleeChance\": self.flee_chance()}).to_string()",
 "               \"canFlee\": self.can_flee, \"first\": self.first, \"fleeChance\": self.flee_chance(), \"rewards\": self.rewards}).to_string()"),
])
open(P,'a').write(r'''
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
        let mut g = Game::new(&rd("../data/party.json"), &rd("../data/enemies.json"), &rd("../data/items.json"), 4).unwrap();
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
''')
