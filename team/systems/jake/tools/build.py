#!/usr/bin/env python3
"""Generates party.json, transformation.json and elements.json from the
constants below. Python 3 stdlib only. Run from anywhere:
    python3 tools/build.py
Edit numbers HERE, rebuild, then run tools/validate.py."""
import json, math, os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

LEVEL_CAP = 20
START_LV = 5   # demo opens mid-journey, like the integrator placeholder (lv 5)
START_INK = {"itsuki": 60}  # demo showcase: Itsuki can Unfurl in the first fight
STATS = ["hp", "atk", "def", "mat", "mdf", "spd"]

# XP needed to go from level L to L+1.
XP_A, XP_P, XP_B = 20, 1.5, 10
def xp_to_next(lv):
    return math.floor(XP_A * lv ** XP_P + XP_B)

def stat_at(base, growth, lv):
    return base + math.floor(growth * (lv - 1) + 0.5)

MEMBERS = [
    {
        "id": "itsuki", "name": "Itsuki Hane", "title": "Wandering Swordsman",
        "role": "physical_dps", "element": "gale",
        "base":   {"hp": 150, "atk": 22, "def": 12, "mat": 10, "mdf": 10, "spd": 14},
        "growth": {"hp": 16,  "atk": 2.6, "def": 1.4, "mat": 1.0, "mdf": 1.1, "spd": 0.8},
        "strokes": [
            {"id": "falling_pine", "name": "Falling Pine", "unlock_lv": 1,
             "hits": [{"gap_ms": 700, "mult": 0.7}, {"gap_ms": 520, "mult": 0.8}, {"gap_ms": 460, "mult": 1.0}],
             "finish_mult": 1.3},
            {"id": "wet_edge", "name": "Wet Edge", "unlock_lv": 5,
             "hits": [{"gap_ms": 650, "mult": 0.5}, {"gap_ms": 450, "mult": 0.6}, {"gap_ms": 380, "mult": 0.7}, {"gap_ms": 340, "mult": 1.1}],
             "finish_mult": 1.5},
        ],
        "seal": {"id": "crane_gale_script", "name": "Gale Crane Script", "seals": 4, "mult": 0.55, "element": "gale", "stat": "atk"},
    },
    {
        "id": "benika", "name": "Benika Matsuo", "title": "Shrine Archer",
        "role": "healer_support", "element": "ember",
        "base":   {"hp": 125, "atk": 15, "def": 10, "mat": 22, "mdf": 16, "spd": 16},
        "growth": {"hp": 13,  "atk": 1.8, "def": 1.1, "mat": 2.8, "mdf": 1.9, "spd": 0.9},
        "strokes": [
            {"id": "three_prayer_slips", "name": "Three Prayer Slips", "unlock_lv": 1,
             "hits": [{"gap_ms": 760, "mult": 0.6}, {"gap_ms": 560, "mult": 0.6}, {"gap_ms": 520, "mult": 0.9}],
             "finish_mult": 1.25},
            {"id": "lantern_volley", "name": "Lantern Volley", "unlock_lv": 6,
             "hits": [{"gap_ms": 700, "mult": 0.5}, {"gap_ms": 500, "mult": 0.5}, {"gap_ms": 440, "mult": 0.6}, {"gap_ms": 400, "mult": 0.9}],
             "finish_mult": 1.4},
        ],
        "seal": {"id": "ember_kite_litany", "name": "Ember Kite Litany", "seals": 5, "mult": 0.4, "element": "ember", "stat": "mat"},
    },
    {
        "id": "gonzo", "name": "Gonzō Kuraishi", "title": "Retired Temple Monk",
        "role": "tank", "element": "stone",
        "base":   {"hp": 200, "atk": 20, "def": 18, "mat": 8,  "mdf": 14, "spd": 8},
        "growth": {"hp": 22,  "atk": 2.4, "def": 2.2, "mat": 0.7, "mdf": 1.6, "spd": 0.5},
        "strokes": [
            {"id": "temple_bell", "name": "Temple Bell", "unlock_lv": 1,
             "hits": [{"gap_ms": 820, "mult": 1.0}, {"gap_ms": 640, "mult": 1.3}],
             "finish_mult": 1.4},
            {"id": "mountain_gong", "name": "Mountain Gong", "unlock_lv": 7,
             "hits": [{"gap_ms": 800, "mult": 0.9}, {"gap_ms": 600, "mult": 1.0}, {"gap_ms": 560, "mult": 1.4}],
             "finish_mult": 1.6},
        ],
        "seal": {"id": "stone_owl_verse", "name": "Stone Owl Verse", "seals": 3, "mult": 0.8, "element": "stone", "stat": "atk"},
    },
]

INKWING = {
    "itsuki": {
        "form_name": "Gale Crane", "element": "gale",
        "mult": {"atk": 1.5, "def": 1.25, "mat": 1.3, "mdf": 1.25, "spd": 1.2},
        "passive": {"id": "tailwind", "name": "Tailwind",
                    "desc": "Acts first each round while in Inkwing, regardless of speed.",
                    "effect": {"kind": "act_first"}},
        "strokes_element": "gale",
    },
    "benika": {
        "form_name": "Ember Kite", "element": "ember",
        "mult": {"atk": 1.25, "def": 1.25, "mat": 1.5, "mdf": 1.4, "spd": 1.15},
        "passive": {"id": "kindling_prayer", "name": "Kindling Prayer",
                    "desc": "Each Clean seal in her Seal Art also heals every living ally for 5% of their max HP.",
                    "effect": {"kind": "heal_party_per_clean_seal", "pct_max_hp": 5}},
        "strokes_element": "ember",
    },
    "gonzo": {
        "form_name": "Stone Owl", "element": "stone",
        "mult": {"atk": 1.4, "def": 1.6, "mat": 1.2, "mdf": 1.4, "spd": 1.0},
        "passive": {"id": "slate_mantle", "name": "Slate Mantle",
                    "desc": "All allies take 15% less damage while Gonzō is in Inkwing.",
                    "effect": {"kind": "party_damage_taken_mult", "value": 0.85}},
        "strokes_element": "stone",
    },
}

def build_party():
    xp_table = []
    total = 0
    for lv in range(1, LEVEL_CAP + 1):
        nxt = xp_to_next(lv) if lv < LEVEL_CAP else 0
        xp_table.append({"lv": lv, "total": total, "to_next": nxt})
        total += nxt
    members = []
    for m in MEMBERS:
        cur = {s: stat_at(m["base"][s], m["growth"][s], START_LV) for s in STATS}
        table = [{"lv": lv, **{s: stat_at(m["base"][s], m["growth"][s], lv) for s in STATS}}
                 for lv in range(1, LEVEL_CAP + 1)]
        members.append({
            # ---- SPEC v1 section 7 fields (exact names) ----
            "id": m["id"], "name": m["name"], "title": m["title"], "element": m["element"],
            "lv": START_LV, **cur, "ink": START_INK.get(m["id"], 0),
            "strokes": m["strokes"], "seal": m["seal"],
            # ---- extensions (ignored by a serde struct that doesn't declare them) ----
            "role": m["role"], "base": m["base"], "growth": m["growth"], "stat_table": table,
        })
    return {
        "members": members,
        "progression": {
            "level_cap": LEVEL_CAP,
            "stat_formula": "stat(lv) = base + floor(growth * (lv - 1) + 0.5)",
            "xp_formula": f"to_next(lv) = floor({XP_A} * lv^{XP_P} + {XP_B}); 0 at level_cap",
            "xp_share": "every member alive at victory gets the full encounter XP; KO'd members get 0",
            "on_level_up": "max stats recomputed from stat_table; current HP rises by the max HP gained",
            "xp_table": xp_table,
        },
    }

def build_transformation():
    return {
        "gauge": {
            "display_name": "Vermilion Gauge", "field": "ink", "max": 100,
            "ui_pulse_at": [25, 50, 75, 100],
            "persists_between_battles": True, "saved": True,
            "decay_per_turn": 0,
        },
        "fill": {
            "stroke_hit": 5,
            "clean_line_bonus": 4,
            "chain_complete_bonus": 4,
            "perfect_chain_bonus": 8,
            "perfect_chain_replaces_complete": True,
            "kill_bonus": 3,
            "damage_taken": {"per_pct_hp_lost": 0.3, "min_if_damaged": 1, "max_per_hit": 15,
                             "formula": "round(0.3 * 100 * dmg / max_hp), clamped 1..15"},
            "still_water_use": 6,
            "still_water_damage_taken_mult": 1.5,
            "seal_arts_fill": False,
            "gain_while_inkwing": False,
            "items": "items.json kind 'ink' adds `power` (owned by Jane)",
        },
        "reset": {
            "on_ko": "keep",
            "on_unfurl": 0,
            "on_battle_end": "keep",
            "on_flee": "keep",
            "clamp": [0, 100],
        },
        "unfurl": {
            "command": "Unfurl",
            "cost": 100,
            "requires_full": True,
            "uses_turn": True,
            "heal_pct_max_hp": 15,
            "duration_turns": 3,
            "duration_counts": "the character's own turns AFTER the Unfurl turn",
            "one_active_per_character": True,
            "tiers": 1,
        },
        "inkwing_rules": {
            "commands": ["seal_art", "stroke", "still_water", "item"],
            "stroke_element": "form element (normal-form Strokes are neutral)",
            "still_water_heal_pct": 15,
            "max_hp_unchanged": True,
            "revert": "at the end of the 3rd Inkwing turn, on KO, or when the battle ends; stats return to normal, current HP kept (clamped to max), ink stays 0 (it was spent)",
            "early_cancel": False,
        },
        "forms": INKWING,
    }

ELEMENTS = ["ember", "tide", "gale", "stone", "dawn", "dusk"]
OPPOSITE = {"ember": "tide", "tide": "ember", "gale": "stone", "stone": "gale", "dawn": "dusk", "dusk": "dawn"}

def build_elements():
    chart = {a: {d: (2.0 if OPPOSITE[a] == d else 0.5 if a == d else 1.0) for d in ELEMENTS} for a in ELEMENTS}
    return {
        "source": "SPEC v1 section 2 (Six Inks). This file only spells out the matrix.",
        "elements": ELEMENTS,
        "display": {"ember": "Ember", "tide": "Tide", "gale": "Gale", "stone": "Stone", "dawn": "Dawn", "dusk": "Dusk"},
        "opposite": OPPOSITE,
        "neutral": "none",
        "rule": "attack element vs defender element: opposite x2.0, same x0.5, otherwise x1.0; 'none' on either side x1.0",
        "chart": chart,
    }

def dump(name, obj):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")

if __name__ == "__main__":
    dump("party.json", build_party())
    dump("transformation.json", build_transformation())
    dump("elements.json", build_elements())
    print("wrote party.json, transformation.json, elements.json")
