#!/usr/bin/env python3
"""No-dependency consistency check for Jake's Inkborne systems drop.
    python3 tools/validate.py      (exit 0 = OK)"""
import json, math, os, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
errs = []
def err(m): errs.append(m)
def load(n):
    with open(os.path.join(ROOT, n), encoding="utf-8") as f:
        return json.load(f)

party, tf, el = load("party.json"), load("transformation.json"), load("elements.json")
STATS = ["hp", "atk", "def", "mat", "mdf", "spd"]
ELEMS = set(el["elements"])

# --- elements: SPEC Six Inks rule
for a in el["elements"]:
    if el["opposite"][el["opposite"][a]] != a: err(f"opposite not symmetric: {a}")
    for d in el["elements"]:
        want = 2.0 if el["opposite"][a] == d else 0.5 if a == d else 1.0
        if el["chart"][a][d] != want: err(f"chart {a}->{d}={el['chart'][a][d]} want {want}")

# --- party: SPEC v1 section 7 fields
SPEC_MEMBER = ["id", "name", "title", "element", "lv", "hp", "atk", "def", "mat", "mdf", "spd", "ink", "strokes", "seal"]
prog = party["progression"]; cap = prog["level_cap"]
if len(party["members"]) != 3: err("need exactly 3 members")
ids = set()
for m in party["members"]:
    mid = m.get("id", "?")
    for k in SPEC_MEMBER:
        if k not in m: err(f"{mid}: missing SPEC field {k}")
    if mid in ids: err(f"duplicate id {mid}")
    ids.add(mid)
    if m["element"] not in ELEMS: err(f"{mid}: bad element {m['element']}")
    if not (1 <= m["lv"] <= cap): err(f"{mid}: lv out of range")
    if not (0 <= m["ink"] <= tf["gauge"]["max"]): err(f"{mid}: ink out of range")
    for s in STATS:
        if not isinstance(m[s], int) or m[s] <= 0: err(f"{mid}: {s} must be positive int")
    tab = m["stat_table"]
    if [r["lv"] for r in tab] != list(range(1, cap + 1)): err(f"{mid}: stat_table levels")
    for r in tab:
        for s in STATS:
            want = m["base"][s] + math.floor(m["growth"][s] * (r["lv"] - 1) + 0.5)
            if r[s] != want: err(f"{mid} L{r['lv']} {s}={r[s]} want {want}")
    for s in STATS:
        if m[s] != tab[m["lv"] - 1][s]: err(f"{mid}: current {s} != stat_table at lv {m['lv']}")
    sids = set()
    for st in m["strokes"]:
        if st["id"] in sids: err(f"{mid}: dup stroke {st['id']}")
        sids.add(st["id"])
        if not st["hits"]: err(f"{mid}/{st['id']}: no hits")
        for h in st["hits"]:
            if not (250 <= h["gap_ms"] <= 1200): err(f"{mid}/{st['id']}: gap_ms {h['gap_ms']} outside 250..1200")
            if h["mult"] <= 0: err(f"{mid}/{st['id']}: mult <= 0")
        if st["finish_mult"] < 1: err(f"{mid}/{st['id']}: finish_mult < 1")
        if not (1 <= st.get("unlock_lv", 1) <= cap): err(f"{mid}/{st['id']}: unlock_lv")
    if not any(st.get("unlock_lv", 1) <= m["lv"] for st in m["strokes"]): err(f"{mid}: no stroke usable at start")
    sl = m["seal"]
    if sl["element"] not in ELEMS or sl["seals"] < 1 or sl["mult"] <= 0: err(f"{mid}: bad seal")
    if sl.get("stat", "mat") not in ("atk", "mat"): err(f"{mid}: seal.stat must be atk|mat")

xt = prog["xp_table"]
if [r["lv"] for r in xt] != list(range(1, cap + 1)): err("xp_table levels")
tot = 0
for i, r in enumerate(xt):
    if r["total"] != tot: err(f"xp total at L{r['lv']}")
    if r["lv"] < cap and (r["to_next"] <= 0 or (i and r["to_next"] <= xt[i-1]["to_next"])): err(f"xp to_next not increasing at L{r['lv']}")
    if r["lv"] == cap and r["to_next"] != 0: err("to_next at cap must be 0")
    tot += r["to_next"]

# --- transformation
g, f, u = tf["gauge"], tf["fill"], tf["unfurl"]
if g["max"] != 100: err("SPEC: gauge max must be 100")
if u["cost"] != g["max"]: err("SPEC: Unfurl costs a full gauge")
if u["duration_turns"] != 3: err("SPEC: Inkwing lasts 3 turns")
if set(tf["forms"]) != ids: err("forms must cover exactly the party ids")
for mid, fm in tf["forms"].items():
    if fm["element"] != next(m["element"] for m in party["members"] if m["id"] == mid): err(f"{mid}: form element != member element")
    for s, v in fm["mult"].items():
        if s not in STATS: err(f"{mid}: unknown mult stat {s}")
        if not (1.0 <= v <= 2.0): err(f"{mid}: mult {s}={v} outside 1..2")
    for s in ("atk", "def"):
        if fm["mult"].get(s, 1) <= 1: err(f"SPEC: {mid} Inkwing must raise {s}")
dt = f["damage_taken"]
if not (dt["min_if_damaged"] <= dt["max_per_hit"] < g["max"]): err("damage_taken clamp")

# --- gauge pacing sanity: turns to fill with only the starter Stroke
for m in party["members"]:
    st = m["strokes"][0]; n = len(st["hits"])
    good = n * f["stroke_hit"] + f["chain_complete_bonus"]
    perfect = n * (f["stroke_hit"] + f["clean_line_bonus"]) + f["perfect_chain_bonus"]
    tg, tp = math.ceil(100 / good), math.ceil(100 / perfect)
    print(f"  {m['id']:7s} {st['name']:20s} good chain +{good:2d} ({tg} turns)  perfect +{perfect:2d} ({tp} turns)  [attack-only, no damage taken]")
    if not (2 <= tp <= 8 and tg <= 10): err(f"{m['id']}: gauge pacing out of band")

# --- IP check: banned words anywhere in the drop
BANNED = ["dragoon", "wingly", "addition"]
for dp, _, fs in os.walk(ROOT):
    for fn in fs:
        if fn.endswith((".json", ".md", ".py", ".rs")):
            txt = open(os.path.join(dp, fn), encoding="utf-8").read().lower()
            for w in BANNED:
                # validate.py itself lists the words; skip only this file
                if w in txt and fn != "validate.py": err(f"banned word '{w}' in {fn}")
for n in ("party.json", "transformation.json", "elements.json"):
    if "spirit" in open(os.path.join(ROOT, n), encoding="utf-8").read().lower(): err(f"canon: avoid 'spirit' in {n}")

if errs:
    print("FAIL"); [print(" -", e) for e in errs]; sys.exit(1)
print("OK: party.json, transformation.json, elements.json are consistent")
