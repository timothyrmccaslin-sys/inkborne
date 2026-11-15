import sys; import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from rep import edits
edits([
("impl Rng { fn next(&mut self) -> f64 {", "impl Rng {\n    /// Uniform index in 0..n (0 when n == 0).\n    fn below(&mut self, n: usize) -> usize { if n == 0 { 0 } else { ((self.next() * n as f64) as usize).min(n - 1) } }\n    fn next(&mut self) -> f64 {"),
("""            let f = &mut self.fighters[t]; let h = (mv.power * self.fighters[me].mat.max(1.0)).round();
            let f = { let _ = f; &mut self.fighters[t] };
            let h = h.min(f.max_hp - f.hp).max(0.0); f.hp += h;""",
"""            let h = (mv.power * self.fighters[me].mat.max(1.0)).round();
            let f = &mut self.fighters[t]; let h = h.min(f.max_hp - f.hp).max(0.0); f.hp += h;"""),
])
