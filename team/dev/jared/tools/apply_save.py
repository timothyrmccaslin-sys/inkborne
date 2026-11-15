#!/usr/bin/env python3
"""Plug the save module into a copy of core/: copies save.rs into <core>/src/ and edits <core>/src/lib.rs.
Usage: python3 apply_save.py <path-to-core>
Base: live core/ + Rusty's 0007-0009 (his 0008 adds `xp`/`lv` to Save and a level-restoring load_json;
save.rs keeps both and moves that logic into the validated loader). Only two spots in lib.rs change:
the `Save` struct (moved to save.rs) and `load_json` (now delegates to `load_save`)."""
import pathlib, re, shutil, sys
core = pathlib.Path(sys.argv[1]); here = pathlib.Path(__file__).resolve().parent.parent
lib = core / "src/lib.rs"; s = lib.read_text()
struct_re = re.compile(r"#\[derive\(Serialize, Deserialize, Clone, Default\)\]\nstruct Save \{.*?\}\n", re.S)
load_re = re.compile(r"    pub fn load_json\(&mut self, s: &str\) -> bool \{\n?.*?\n    \}\n(?=    /// Set member)", re.S)
assert len(struct_re.findall(s)) == 1, "Save struct anchor not found (has lib.rs changed?)"
assert len(load_re.findall(s)) == 1, "load_json anchor not found (needs Rusty's 0008 load_json; has lib.rs changed?)"
s = struct_re.sub(lambda m: "// Save state lives in save.rs (Jared): schema `version`, `equipped`, validated load, `load_warnings()`.\nmod save;\nuse save::Save;\n", s)
s = load_re.sub(lambda m: "    /// Lenient, validated load (save.rs). `false` only for unreadable input, and then state is untouched.\n"
                          "    pub fn load_json(&mut self, s: &str) -> bool { self.load_save(s) }\n", s)
lib.write_text(s)
shutil.copy(here / "core/src/save.rs", core / "src/save.rs")
print("ok", lib)
