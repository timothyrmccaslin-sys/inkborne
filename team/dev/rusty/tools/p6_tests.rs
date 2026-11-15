
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
