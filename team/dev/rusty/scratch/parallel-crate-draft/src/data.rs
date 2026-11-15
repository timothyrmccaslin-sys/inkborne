//! Data shapes (SPEC section 7 plus Jake's extensions). Unknown fields are ignored on purpose:
//! never add `deny_unknown_fields` here (Jake's party.json carries growth, stat_table, etc.).
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

fn one() -> u32 { 1 }
fn mat_s() -> String { "mat".into() }
fn weight1() -> u32 { 1 }

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct HitDef {
    pub gap_ms: f64,
    pub mult: f64,
    /// Optional per-hit window overrides (half-widths, ms).
    #[serde(default, skip_serializing_if = "Option::is_none")] pub clean_ms: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")] pub good_ms: Option<f64>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct StrokeDef {
    pub id: String,
    pub name: String,
    pub hits: Vec<HitDef>,
    #[serde(default = "onef")] pub finish_mult: f64,
    #[serde(default = "one")] pub unlock_lv: u32,
}
fn onef() -> f64 { 1.0 }

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SealDef {
    #[serde(default)] pub id: String,
    pub name: String,
    pub seals: u32,
    pub mult: f64,
    pub element: String,
    /// "atk" or "mat" (Jake). Default "mat".
    #[serde(default = "mat_s")] pub stat: String,
}

/// Optional out-of-form Magic (not in SPEC v1.1; costs Vermilion Ink).
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SpellDef {
    pub id: String,
    pub name: String,
    #[serde(default)] pub element: String,
    pub power: f64,
    #[serde(default)] pub ink_cost: f64,
    /// "one" | "all"
    #[serde(default = "one_s")] pub target: String,
    /// "elem" (damage) | "heal"
    #[serde(default = "elem_s")] pub kind: String,
}
fn one_s() -> String { "one".into() }
fn elem_s() -> String { "elem".into() }

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct StatRow { pub lv: u32, pub hp: f64, pub atk: f64, pub def: f64, pub mat: f64, pub mdf: f64, pub spd: f64 }

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct MemberDef {
    pub id: String,
    pub name: String,
    #[serde(default)] pub title: String,
    pub element: String,
    #[serde(default = "one")] pub lv: u32,
    pub hp: f64, pub atk: f64, pub def: f64, pub mat: f64, pub mdf: f64, pub spd: f64,
    #[serde(default)] pub ink: f64,
    pub strokes: Vec<StrokeDef>,
    pub seal: SealDef,
    #[serde(default)] pub spells: Vec<SpellDef>,
    #[serde(default, skip_serializing)] pub stat_table: Vec<StatRow>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct XpRow { pub lv: u32, pub total: u32, #[serde(default)] pub to_next: u32 }
#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct Progression { #[serde(default)] pub level_cap: u32, #[serde(default)] pub xp_table: Vec<XpRow> }

#[derive(Clone, Debug, Deserialize)]
pub struct PartyFile {
    pub members: Vec<MemberDef>,
    #[serde(default)] pub progression: Option<Progression>,
    #[serde(default)] pub combo_windows: Option<serde_json::Value>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct MoveDef {
    pub id: String,
    pub name: String,
    /// "phys" | "elem" | "heal" | "guard"
    pub kind: String,
    #[serde(default = "onef")] pub power: f64,
    #[serde(default)] pub element: Option<String>,
    #[serde(default = "weight1")] pub weight: u32,
    /// AI targeting: "random" (default) | "lowest_hp" | "highest_hp" | "weak" | "all"
    #[serde(default)] pub target: Option<String>,
    /// Only usable while own HP fraction is below this.
    #[serde(default)] pub hp_below: Option<f64>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct EnemyDef {
    pub id: String,
    pub name: String,
    #[serde(default)] pub element: String,
    pub hp: f64, pub atk: f64, pub def: f64, pub mat: f64, pub mdf: f64, pub spd: f64,
    #[serde(default)] pub mon: u32,
    #[serde(default)] pub xp: Option<u32>,
    pub moves: Vec<MoveDef>,
}

#[derive(Clone, Debug, Deserialize)]
pub struct EnemyFile {
    pub enemies: Vec<EnemyDef>,
    #[serde(default)] pub encounters: BTreeMap<String, Vec<String>>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ItemDef {
    pub id: String,
    pub name: String,
    #[serde(default)] pub desc: String,
    /// "heal" | "healall" | "ink" | "bomb"
    pub kind: String,
    #[serde(default)] pub power: f64,
    #[serde(default)] pub element: Option<String>,
    #[serde(default)] pub price: u32,
}

#[derive(Clone, Debug, Deserialize)]
pub struct ItemFile { pub items: Vec<ItemDef> }

/// Jake's suggested enemy XP (DESIGN.md) used when enemies.json has no `xp`.
pub fn default_xp(enemy_id: &str) -> u32 {
    match enemy_id { "blotling" => 12, "hollow_lantern" => 18, "smudge_ronin" => 150, _ => 10 }
}
