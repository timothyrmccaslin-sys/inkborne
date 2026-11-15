import sys; import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from rep import edits
edits([
("""    if atk.is_empty() || def.is_empty() { 1.0 }""",
 """    if atk.is_empty() || def.is_empty() || atk == "none" || def == "none" { 1.0 }"""),
("    win: Windows, combo: Option<Combo>, ink: InkRules,\n}",
 "    win: Windows, combo: Option<Combo>, ink: InkRules,\n    /// Optional Six Inks chart from Jake's elements.json (`chart[attack][defend]`); falls back to `elem_mod`.\n    chart: Option<BTreeMap<String, BTreeMap<String, f64>>>,\n}"),
("ink: InkRules::default() })", "ink: InkRules::default(), chart: None })"),
("    /// Override combo windows:",
"""    /// Load Jake's elements.json (`{"chart": {"ember": {"tide": 2.0, ...}, ...}}`). Optional: without it the
    /// SPEC section 2 rule (opposite x2, same x0.5, else x1) is used. Pairs missing from the chart also fall back.
    pub fn set_elements(&mut self, ej: &str) -> bool {
        let Ok(v) = serde_json::from_str::<Value>(ej) else { return false };
        let Some(c) = v["chart"].as_object() else { return false };
        let mut out = BTreeMap::new();
        for (a, row) in c { let mut r = BTreeMap::new(); if let Some(o) = row.as_object() { for (d, m) in o { if let Some(m) = m.as_f64() { r.insert(d.clone(), m); } } } out.insert(a.clone(), r); }
        self.chart = Some(out); true
    }
    /// Element multiplier attack element -> defender element (chart if loaded, else the SPEC rule).
    pub fn elem(&self, atk: &str, def: &str) -> f64 {
        if let Some(m) = self.chart.as_ref().and_then(|c| c.get(atk)).and_then(|r| r.get(def)) { return *m }
        elem_mod(atk, def)
    }
    /// UI hint for one fighter: `{element, weak:[...x>1], resist:[...x<1]}` over the six inks.
    pub fn affinity_json(&self, target: usize) -> String {
        let Some(f) = self.fighters.get(target) else { return "null".into() };
        let all = ["ember", "tide", "gale", "stone", "dawn", "dusk"];
        let weak: Vec<&str> = all.iter().copied().filter(|a| self.elem(a, &f.element) > 1.0).collect();
        let resist: Vec<&str> = all.iter().copied().filter(|a| self.elem(a, &f.element) < 1.0).collect();
        json!({"element": f.element, "weak": weak, "resist": resist}).to_string()
    }
    /// Override combo windows:"""),
("        let em = elem_mod(&elem, &self.fighters[target].element);", "        let em = self.elem(&elem, &self.fighters[target].element);"),
("            let em = elem_mod(&m.seal.element, &self.fighters[t].element);", "            let em = self.elem(&m.seal.element, &self.fighters[t].element);"),
("let em = elem_mod(&e, &self.fighters[target].element); let v = self.var();", "let em = self.elem(&e, &self.fighters[target].element); let v = self.var();"),
("            let e = mv.element.clone().unwrap_or_default(); let em = elem_mod(&e, &self.fighters[t].element);",
 "            // elem move without its own element uses the enemy's element\n            let e = mv.element.clone().unwrap_or_else(|| self.fighters[me].element.clone()); let em = self.elem(&e, &self.fighters[t].element);"),
])
