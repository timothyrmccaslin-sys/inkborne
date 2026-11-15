#!/usr/bin/env python3
"""Validate Jane's data against SPEC section 7, Ollie's ids, Jake's gauge rules,
and the 11 live equipment ids. Exit 1 on error."""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
TEAM = os.path.join(HERE, "..", "..", "..")
REPO = os.path.join(TEAM, "..")
LIVE_ITEMS = os.path.join(REPO, "data", "items.json")
RETIRED = os.path.join(HERE, "..", "proposed", "retired", "equipment.json")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


err = []


def fail(msg):
    err.append(msg)


items = load(os.path.join(DATA, "items.json"))["items"]
shops = load(os.path.join(DATA, "shops.json"))
nums = load(os.path.join(DATA, "equipment_numbers.json"))
mon = load(os.path.join(DATA, "enemies.mon.json"))
ollie = load(os.path.join(TEAM, "story", "items.json"))["items"]
tr = load(os.path.join(TEAM, "systems", "jake", "transformation.json"))
el = load(os.path.join(TEAM, "systems", "jake", "elements.json"))["elements"]

if os.path.exists(os.path.join(DATA, "equipment.json")):
    fail("data/equipment.json should be retired; numbers live in data/equipment_numbers.json")

# --- consumables ---
ids = [i["id"] for i in items]
if len(set(ids)) != len(ids):
    fail("duplicate item id")
oid = {i["id"] for i in ollie}
for i in items:
    for k in ("id", "name", "desc", "kind", "power", "price"):
        if k not in i:
            fail(f"{i.get('id')}: missing {k}")
    if i["id"] not in oid:
        fail(f"{i['id']}: not an Ollie id")
    if i["kind"] not in ("heal", "healall", "ink", "bomb"):
        fail(f"{i['id']}: bad kind")
    if i["kind"] == "bomb" and i.get("element") not in el:
        fail(f"{i['id']}: bad element")
    if not isinstance(i["price"], int) or i["price"] <= 0:
        fail(f"{i['id']}: bad price")
    blob = json.dumps(i)
    if re.search("drag" + "oon", blob, re.I):
        fail("forbidden word")
    if i["kind"] == "ink" and re.search(r"red ink", i.get("desc", ""), re.I):
        fail(f"{i['id']}: desc should say Vermilion Ink, not red ink")

ink_powers = sorted(i["power"] for i in items if i["kind"] == "ink")
if ink_powers != [25, 50]:
    fail(f"ink items must be powers 25 and 50, got {ink_powers}")

if tr["gauge"]["field"] != "ink" or tr["gauge"]["max"] != 100:
    fail("gauge mismatch with transformation.json")
if tr["gauge"].get("display_name") != "Vermilion Ink":
    fail("gauge display_name should be Vermilion Ink")

# --- equipment numbers vs live items.json ---
if not os.path.isfile(LIVE_ITEMS):
    fail(f"live items.json not found: {LIVE_ITEMS}")
    live_eq = []
else:
    live_eq = load(LIVE_ITEMS).get("equipment") or []

live_by_id = {e["id"]: e for e in live_eq}
num_eq = nums.get("equipment") or []
num_by_id = {e["id"]: e for e in num_eq}
if len(num_by_id) != len(num_eq):
    fail("duplicate id in equipment_numbers.json")

live_ids = set(live_by_id)
num_ids = set(num_by_id)
for missing in sorted(live_ids - num_ids):
    fail(f"{missing}: in live items.json but missing from equipment_numbers.json")
for extra in sorted(num_ids - live_ids):
    fail(f"{extra}: in equipment_numbers.json but not a live equipment id")

slots = set(nums.get("slots") or [])
stat_keys = set(nums.get("stat_keys") or [])
expected_slots = {"weapon", "armor", "accessory"}
if slots != expected_slots:
    fail(f"slots should be {sorted(expected_slots)}, got {sorted(slots)}")

ink_accessories = 0
for eid, e in num_by_id.items():
    live = live_by_id.get(eid)
    for k in ("id", "slot", "tier", "mods", "price", "sell_price", "sellable", "in_shop", "equippable_by", "status"):
        if k not in e:
            fail(f"{eid}: missing {k}")
    if e.get("status") not in ("PROPOSED", "APPROVED by Jake"):
        fail(f"{eid}: status must be PROPOSED or APPROVED by Jake")
    if e.get("slot") not in slots:
        fail(f"{eid}: bad slot {e.get('slot')}")
    if e.get("element") is not None and e["element"] not in el:
        fail(f"{eid}: bad element")
    mods = e.get("mods") or {}
    if not isinstance(mods, dict):
        fail(f"{eid}: mods must be an object")
    else:
        for k, v in mods.items():
            if k not in stat_keys:
                fail(f"{eid}: bad stat key {k}")
            if not isinstance(v, int):
                fail(f"{eid}: mod {k} must be a flat int, got {v!r}")
            if v <= 0:
                fail(f"{eid}: mod {k} should be a positive flat bonus")
        if mods.get("atk", 0) > 8:
            fail(f"{eid}: atk mod {mods['atk']} exceeds Jake's +8 cap")
        if mods.get("spd", 0) > 2:
            fail(f"{eid}: spd mod {mods['spd']} exceeds Jake's +2 cap")
    if not isinstance(e.get("price"), int) or e["price"] <= 0:
        fail(f"{eid}: bad price")
    sellable = e.get("sellable")
    sell_price = e.get("sell_price")
    if sellable is True:
        expected_sell = e["price"] // 2
        if sell_price != expected_sell:
            fail(f"{eid}: sell_price should be floor(price/2)={expected_sell}, got {sell_price}")
        if not e.get("in_shop"):
            fail(f"{eid}: unsellable unique/out-of-shop gear should not be sellable")
    elif sellable is False:
        if sell_price != 0:
            fail(f"{eid}: unsellable sell_price should be 0, got {sell_price}")
    else:
        fail(f"{eid}: sellable must be true or false")
    if e.get("starting_for") and sellable is not False:
        fail(f"{eid}: starter gear must be unsellable")
    if e.get("starting_for") and e["starting_for"] not in e.get("equippable_by", []):
        fail(f"{eid}: starting_for {e['starting_for']} not in equippable_by")
    if "ink" in e:
        ink_accessories += 1
        ink = e["ink"]
        if ink.get("on_stroke_hit_landed") != 1:
            fail(f"{eid}: ink accessory should be +1 per Stroke hit landed")
        if ink.get("on_battle_start", 0) != 0:
            fail(f"{eid}: no flat ink at the start of battle")
    if "resist" in e:
        resist = e["resist"]
        if resist.get("element") not in el:
            fail(f"{eid}: bad resist element")
        if resist.get("mult") != 0.75:
            fail(f"{eid}: resist mult should be 0.75, got {resist.get('mult')}")
        apply_after = str(resist.get("apply_after", ""))
        if "elements.json" not in apply_after:
            fail(f"{eid}: resist must be applied after the elements.json chart")
    if re.search("drag" + "oon", json.dumps(e), re.I):
        fail(f"{eid}: forbidden word")
    if live:
        for k in ("slot", "tier", "in_shop", "equippable_by"):
            if e.get(k) != live.get(k):
                fail(f"{eid}: {k}={e.get(k)!r} does not match live {live.get(k)!r}")
        live_start = live.get("starting_for") or None
        num_start = e.get("starting_for") or None
        if live_start != num_start:
            fail(f"{eid}: starting_for={num_start!r} does not match live {live_start!r}")
        if e.get("name") and e["name"] != live.get("name"):
            fail(f"{eid}: name {e['name']!r} does not match live {live.get('name')!r}")

if ink_accessories > 1:
    fail(f"at most one ink accessory, found {ink_accessories}")
if not any(k in nums.get("_status", "") for k in ("PROPOSED", "APPROVED")):
    fail("equipment_numbers.json _status must say PROPOSED or APPROVED")

# --- shops ---
known = set(ids) | num_ids
for n, s in shops.items():
    for k in ("name", "keeper", "stock"):
        if k not in s:
            fail(f"shop {n}: missing {k}")
    for x in s.get("stock", []):
        if x not in known:
            fail(f"shop {n}: unknown item {x}")
    for eid, e in num_by_id.items():
        listed = eid in s.get("stock", [])
        if e.get("in_shop") and not listed:
            fail(f"shop {n}: in_shop equipment {eid} missing from stock")
        if listed and not e.get("in_shop") and eid not in set(ids):
            fail(f"shop {n}: {eid} is in stock but in_shop is false")

# --- mon ---
for k, v in mon.get("mon", {}).items():
    if not isinstance(v, int) or v <= 0:
        fail(f"bad mon {k}")

# --- retired file should still exist as an archive, not as live data ---
if not os.path.isfile(RETIRED):
    fail(f"retired null-id file missing: {RETIRED}")

for m in err:
    print("ERROR", m)
print(
    f"{len(items)} items, {len(shops)} shop(s), {len(num_eq)} equipment numbers "
    f"(live ids matched: {len(live_ids & num_ids)}/{len(live_ids)}), {len(err)} error(s)"
)
sys.exit(1 if err else 0)
