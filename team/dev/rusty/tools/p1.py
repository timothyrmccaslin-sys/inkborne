import sys; import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from rep import edits
edits([
("pub struct Hit { pub gap_ms: f64, pub mult: f64 }",
 "pub struct Hit { pub gap_ms: f64, pub mult: f64,\n    /// Optional per-hit window overrides (half-widths, ms).\n    #[serde(default, skip_serializing_if = \"Option::is_none\")] pub clean_ms: Option<f64>,\n    #[serde(default, skip_serializing_if = \"Option::is_none\")] pub good_ms: Option<f64> }"),
("""/// Brushstroke judgement. `delta_ms` = press time - ring-close time.
/// 2 = Clean Line, 1 = good, 0 = miss (chain breaks).
pub const CLEAN_MS: f64 = 95.0;
pub const GOOD_MS: f64 = 150.0;
pub fn judge_delta(delta_ms: f64) -> u8 { let d = delta_ms.abs(); if d <= CLEAN_MS { 2 } else if d <= GOOD_MS { 1 } else { 0 } }""",
"""/// Brushstroke judgement. `delta_ms` = press time - ring-close (target) time.
/// 2 = Clean Line, 1 = good, 0 = miss (chain breaks). Windows are HALF-widths in ms, symmetric early/late.
/// Clean widened 70 -> 95 per Richard's iPad touch findings (core/tests/combo-timing-findings.md).
/// Both are defaults; data can override them (`combo_windows`, see `Game::set_combo_windows`).
pub const CLEAN_MS: f64 = 95.0;
pub const GOOD_MS: f64 = 150.0;
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
#[derive(Clone)]
struct Combo { actor: usize, target: usize, stroke_idx: usize, stroke_id: String, name: String, hits: Vec<(f64, f64, f64)>, next: usize, anchor: f64, grades: Vec<u8>, presses: Vec<f64> }"""),
("    forms: BTreeMap<String, (String, String, [f64; 5])>,\n}",
 "    forms: BTreeMap<String, (String, String, [f64; 5])>,\n    win: Windows, combo: Option<Combo>,\n}"),
("walk: Walker::default(), forms: BTreeMap::new() })",
 "walk: Walker::default(), forms: BTreeMap::new(), win: Windows::default(), combo: None })"),
("""            self.forms.insert(id.clone(), (x["form_name"].as_str().unwrap_or("").into(), x["passive"]["id"].as_str().unwrap_or("").into(), [g("atk"), g("def"), g("mat"), g("mdf"), g("spd")]));
        } }
        true
    }""",
"""            self.forms.insert(id.clone(), (x["form_name"].as_str().unwrap_or("").into(), x["passive"]["id"].as_str().unwrap_or("").into(), [g("atk"), g("def"), g("mat"), g("mdf"), g("spd")]));
        } }
        if v["combo_windows"].is_object() { self.win.apply(&v["combo_windows"]); }
        true
    }
    /// Override combo windows: `{ "clean_ms": 95, "good_ms": 150, "anchor": "press"|"close",
    /// "hits": { "<stroke_id>#<hit index>": { "clean_ms", "good_ms" } } }` (any subset). Half-widths in ms.
    pub fn set_combo_windows(&mut self, cj: &str) -> bool {
        let Ok(v) = serde_json::from_str::<Value>(cj) else { return false };
        if !v.is_object() { return false }
        self.win.apply(&v); true
    }"""),
("""    pub fn judge(&self, delta_ms: f64) -> u8 { judge_delta(delta_ms) }
    pub fn windows_json(&self) -> String { json!({"clean": CLEAN_MS, "good": GOOD_MS}).to_string() }""",
"""    pub fn judge(&self, delta_ms: f64) -> u8 { judge_with(delta_ms, self.win.clean, self.win.good) }
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
    pub fn cancel_combo(&mut self) -> bool { if self.combo.as_ref().map(|c| c.grades.is_empty()).unwrap_or(false) { self.combo = None; true } else { false } }"""),
("        self.fighters.clear(); self.battle_over = None; self.round = 0;",
 "        self.fighters.clear(); self.battle_over = None; self.round = 0; self.combo = None;"),
])
