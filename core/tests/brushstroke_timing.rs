//! Brushstroke timing tests against Rusty's battle core (`judge_delta`)
//! and Jake's stroke data (`team/systems/jake/party.json`).
//!
//! Windows come from the core and are absolute milliseconds, not a fraction
//! of `gap_ms`:
//!   Clean Line (grade 2): |delta_ms| <= CLEAN_MS (95, Richard iPad windows)
//!   good        (grade 1): CLEAN_MS < |delta_ms| <= GOOD_MS (150)
//!   miss        (grade 0): |delta_ms| > GOOD_MS
//! Early and late are the same grade; the sign of `delta_ms` is press time
//! minus ring-close time (core docs). There is no separate early/late grade.
//!
//! Aligns with June's CMB-01/CMB-02/CMB-03 (time-based early/good/clean/late
//! presses) and Sam's note that combo judging should use timestamps, not
//! frame counts. Tightness for iPad touch is reported in
//! `combo-timing-findings.md` next to this file, not asserted here, so a
//! data tweak does not fail the judge tests.

use inkborne_core::{judge_delta, CLEAN_MS, GOOD_MS};
use serde::Deserialize;
use std::path::PathBuf;

#[derive(Deserialize)]
struct PartyFile {
    members: Vec<MemberStrokes>,
}

#[derive(Deserialize)]
struct MemberStrokes {
    id: String,
    name: String,
    strokes: Vec<StrokeHits>,
}

#[derive(Deserialize)]
struct StrokeHits {
    id: String,
    name: String,
    hits: Vec<HitGap>,
}

#[derive(Deserialize)]
struct HitGap {
    gap_ms: f64,
}

fn jake_party_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../team/systems/jake/party.json")
}

fn load_jake_party() -> PartyFile {
    let path = jake_party_path();
    let raw = std::fs::read_to_string(&path)
        .unwrap_or_else(|e| panic!("failed to read {}: {e}", path.display()));
    serde_json::from_str(&raw).unwrap_or_else(|e| panic!("party.json parse: {e}"))
}

/// Representative offsets for the four press classes Jake asked to cover.
/// Values are derived from the core constants, not invented windows.
fn press_cases() -> [(&'static str, f64, u8); 4] {
    let clean = 0.0;
    let good = (CLEAN_MS + GOOD_MS) / 2.0; // midpoint of the good-only band, late side
    let early = -(GOOD_MS + 40.0); // just outside the early good edge
    let late = GOOD_MS + 40.0; // just outside the late good edge
    [
        ("early", early, 0),
        ("good", good, 1),
        ("clean", clean, 2),
        ("late", late, 0),
    ]
}

#[test]
fn windows_are_the_documented_absolute_ms() {
    assert_eq!(CLEAN_MS, 95.0); // Richard iPad windows: clean ±95, good ±150
    assert_eq!(GOOD_MS, 150.0);
    assert!(CLEAN_MS < GOOD_MS);
}

#[test]
fn judge_boundaries_match_core_constants() {
    assert_eq!(judge_delta(0.0), 2);
    assert_eq!(judge_delta(CLEAN_MS), 2);
    assert_eq!(judge_delta(-CLEAN_MS), 2);
    assert_eq!(judge_delta(CLEAN_MS + 1.0), 1);
    assert_eq!(judge_delta(-(CLEAN_MS + 1.0)), 1);
    assert_eq!(judge_delta(GOOD_MS), 1);
    assert_eq!(judge_delta(-GOOD_MS), 1);
    assert_eq!(judge_delta(GOOD_MS + 1.0), 0);
    assert_eq!(judge_delta(-(GOOD_MS + 1.0)), 0);
}

#[test]
fn every_jake_hit_judges_early_good_clean_late() {
    let party = load_jake_party();
    let cases = press_cases();
    let mut hits = 0u32;

    for member in &party.members {
        for stroke in &member.strokes {
            assert!(
                !stroke.hits.is_empty(),
                "{}/{} has no hits",
                member.id,
                stroke.id
            );
            for (hi, hit) in stroke.hits.iter().enumerate() {
                assert!(
                    hit.gap_ms > 0.0,
                    "{}/{}/hit{} gap_ms must be positive, got {}",
                    member.id,
                    stroke.id,
                    hi,
                    hit.gap_ms
                );
                for (label, delta, expect) in cases {
                    let got = judge_delta(delta);
                    assert_eq!(
                        got, expect,
                        "{} {} / {} hit{} (gap_ms={}): {} press at {:+} ms judged {} want {}",
                        member.name,
                        member.id,
                        stroke.name,
                        hi,
                        hit.gap_ms,
                        label,
                        delta,
                        got,
                        expect
                    );
                }
                // Good exists on the early side as well (same grade, opposite sign).
                assert_eq!(
                    judge_delta(-((CLEAN_MS + GOOD_MS) / 2.0)),
                    1,
                    "{}/{}/hit{} early-side good",
                    member.id,
                    stroke.id,
                    hi
                );
                hits += 1;
            }
        }
    }

    assert!(
        hits >= 1,
        "expected at least one hit in {}",
        jake_party_path().display()
    );
    eprintln!("judged {hits} hits × 4 press classes from Jake's party.json");
}

#[test]
fn game_judge_matches_judge_delta() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..");
    let party = std::fs::read_to_string(root.join("data/party.json")).unwrap();
    let enemies = std::fs::read_to_string(root.join("data/enemies.json")).unwrap();
    let items = std::fs::read_to_string(root.join("data/items.json")).unwrap();
    let game = inkborne_core::Game::new(&party, &enemies, &items, 7).expect("Game::new");

    for (label, delta, expect) in press_cases() {
        assert_eq!(game.judge(delta), expect, "Game::judge {label} at {delta}");
        assert_eq!(game.judge(delta), judge_delta(delta));
    }

    let windows: serde_json::Value =
        serde_json::from_str(&game.windows_json()).expect("windows_json");
    assert_eq!(windows["clean"].as_f64(), Some(CLEAN_MS));
    assert_eq!(windows["good"].as_f64(), Some(GOOD_MS));
}

/// A miss (early or late) at any hit index breaks the chain: later hits
/// are not applied. Covers June CMB-02 against `Game::stroke`.
#[test]
fn miss_breaks_chain_at_that_hit() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..");
    let party = std::fs::read_to_string(root.join("data/party.json")).unwrap();
    let enemies = std::fs::read_to_string(root.join("data/enemies.json")).unwrap();
    let items = std::fs::read_to_string(root.join("data/items.json")).unwrap();

    // Itsuki / Falling Pine is 3 hits in both live data and Jake's drop.
    // sumikage_c is a live encounter in data/enemies.json (blotling, hollow_lantern, blotling).
    let mut game = inkborne_core::Game::new(&party, &enemies, &items, 7).expect("Game::new");
    let battle: serde_json::Value =
        serde_json::from_str(&game.start_battle("sumikage_c")).expect("battle json");
    let fighters = battle["fighters"].as_array().expect("fighters");
    let actor = fighters
        .iter()
        .position(|f| f["id"] == "itsuki")
        .expect("itsuki in party");
    let target = fighters
        .iter()
        .position(|f| f["side"].as_u64() == Some(1))
        .expect("sumikage_c must spawn at least one enemy");
    assert_eq!(fighters[target]["side"].as_u64(), Some(1), "target must be an enemy");
    assert_eq!(fighters[actor]["side"].as_u64(), Some(0), "actor must be a party member");
    let result: serde_json::Value =
        serde_json::from_str(&game.stroke(actor, target, 0, &[2, 0, 2])).unwrap();
    let events = result["events"]
        .as_array()
        .expect("stroke returns events");
    assert_eq!(events.len(), 2, "chain should stop at the first miss: {result}");
    assert_eq!(events[0]["grade"].as_u64(), Some(2));
    assert_eq!(events[1]["grade"].as_u64(), Some(0));
    assert!(events[0].get("dmg").is_some());
    assert!(events[1].get("dmg").is_none());
    assert_eq!(
        events[0]["target"].as_u64(),
        Some(target as u64),
        "clean hit must land on the enemy target: {result}"
    );
}
