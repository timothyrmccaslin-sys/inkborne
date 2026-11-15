export class Game {
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        GameFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_game_free(ptr, 0);
    }
    /**
     * UI hint for one fighter: `{element, weak:[...x>1], resist:[...x<1]}` over the six inks.
     * @param {number} target
     * @returns {string}
     */
    affinity_json(target) {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_affinity_json(this.__wbg_ptr, target);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {string}
     */
    battle_json() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_battle_json(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * Start a timed chain at `t0_ms` (performance.now()). Hit 0's target is t0 + gap_ms[0]; hit n's target is
     * the press that landed hit n-1 + gap_ms[n] (or the previous target with anchor "close").
     * Returns `{ok, actor, target, stroke, name, anchor, hits:[{hit,gap_ms,mult,clean_ms,good_ms}], next}`.
     * @param {number} actor
     * @param {number} target
     * @param {number} stroke_idx
     * @param {number} t0_ms
     * @returns {string}
     */
    begin_stroke(actor, target, stroke_idx, t0_ms) {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_begin_stroke(this.__wbg_ptr, actor, target, stroke_idx, t0_ms);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @param {string} id
     * @param {number} qty
     * @returns {boolean}
     */
    buy(id, qty) {
        const val2 = +qty;
        const ptr0 = passStringToWasm0(id, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.game_buy(this.__wbg_ptr, ptr0, len0, val2);
        return ret !== 0;
    }
    /**
     * Whether Flee is allowed in this battle (false for `canFlee:false` encounters or when over).
     * @returns {boolean}
     */
    can_flee() {
        const ret = wasm.game_can_flee(this.__wbg_ptr);
        return ret !== 0;
    }
    /**
     * Whether `actor` may Unfurl right now.
     * @param {number} actor
     * @returns {boolean}
     */
    can_unfurl(actor) {
        const ret = wasm.game_can_unfurl(this.__wbg_ptr, actor);
        return ret !== 0;
    }
    /**
     * Abort a chain before its first press (back to the command menu). False once a press has been judged.
     * @returns {boolean}
     */
    cancel_combo() {
        const ret = wasm.game_cancel_combo(this.__wbg_ptr);
        return ret !== 0;
    }
    /**
     * The running chain (`null` if none).
     * @returns {string}
     */
    combo_json() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_combo_json(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * Call every frame while a chain is running. If `now_ms` is past the pending hit's good window,
     * that hit is judged a miss (no press) and the chain ends. Returns `{timeout:false}` otherwise.
     * @param {number} now_ms
     * @returns {string}
     */
    combo_tick(now_ms) {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_combo_tick(this.__wbg_ptr, now_ms);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * Index of the fighter whose turn it is (-1 when over).
     * @returns {number}
     */
    current() {
        const ret = wasm.game_current(this.__wbg_ptr);
        return ret;
    }
    /**
     * Demo/debug: set a party member's Vermilion Ink.
     * @param {number} actor
     * @param {number} v
     */
    debug_ink(actor, v) {
        wasm.game_debug_ink(this.__wbg_ptr, actor, v);
    }
    /**
     * Element multiplier attack element -> defender element (chart if loaded, else the SPEC rule).
     * @param {string} atk
     * @param {string} def
     * @returns {number}
     */
    elem(atk, def) {
        let ptr0, len0, ptr1, len1;
        try {
            ptr0 = passStringToWasm0(atk, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            len0 = WASM_VECTOR_LEN;
            ptr1 = passStringToWasm0(def, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            len1 = WASM_VECTOR_LEN;
        } catch (e) {
            if (ptr1) { wasm.__wbindgen_free(ptr1, len1 * 1, 1); }
            if (ptr0) { wasm.__wbindgen_free(ptr0, len0 * 1, 1); }
            throw e;
        }
        const ret = wasm.game_elem(this.__wbg_ptr, ptr0, len0, ptr1, len1);
        return ret;
    }
    /**
     * Enemy acts (call when current() is an enemy). Data-driven AI (enemies.json, all fields optional):
     * - move `weight`: weighted pick among eligible moves (seeded RNG).
     * - move `hp_below` (0..1): only eligible while the enemy's own HP fraction is below it (e.g. a desperation move).
     * - move `kind`: "phys" (atk vs def), "elem" (mat vs mdf, x element), "heal" (heals the most-hurt living enemy
     *   by power x mat), "guard" (the enemy takes Still Water: damage x0.5 until its next turn).
     * - move `target` (else enemy `ai`, else "random"): "random" | "lowest_hp" | "lowest_hp_pct" | "highest_hp" |
     *   "weak" (prefers a member weak to the move's element) | "all" (hits every living party member).
     * @returns {string}
     */
    enemy_turn() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_enemy_turn(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * Put `id` in `member`'s `slot` (empty `id` clears it). Validates member, slot and id/slot match.
     * Stat mods and inventory accounting are not applied yet (pending Jane/Jake).
     * @param {string} member
     * @param {string} slot
     * @param {string} id
     * @returns {boolean}
     */
    equip(member, slot, id) {
        let ptr0, len0, ptr1, len1, ptr2, len2;
        try {
            ptr0 = passStringToWasm0(member, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            len0 = WASM_VECTOR_LEN;
            ptr1 = passStringToWasm0(slot, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            len1 = WASM_VECTOR_LEN;
            ptr2 = passStringToWasm0(id, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            len2 = WASM_VECTOR_LEN;
        } catch (e) {
            if (ptr2) { wasm.__wbindgen_free(ptr2, len2 * 1, 1); }
            if (ptr1) { wasm.__wbindgen_free(ptr1, len1 * 1, 1); }
            if (ptr0) { wasm.__wbindgen_free(ptr0, len0 * 1, 1); }
            throw e;
        }
        const ret = wasm.game_equip(this.__wbg_ptr, ptr0, len0, ptr1, len1, ptr2, len2);
        return ret !== 0;
    }
    /**
     * `{ "<member>": { "<slot>": id|null } }`
     * @returns {string}
     */
    equipped_json() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_equipped_json(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @param {string} k
     * @returns {boolean}
     */
    flag(k) {
        const ptr0 = passStringToWasm0(k, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.game_flag(this.__wbg_ptr, ptr0, len0);
        return ret !== 0;
    }
    /**
     * Flee (party command, uses the turn). Refuses with `reason`: "over", "cannot_flee", "bad_index", "not_party_actor",
     * "not_your_turn". On success the battle ends with outcome "fled" (HP and Vermilion Ink kept, no mon/XP);
     * on failure the turn passes and the next attempt gets +per_fail. Returns `{kind:"flee", ok, fled, chance, roll}`.
     * @param {number} actor
     * @returns {string}
     */
    flee(actor) {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_flee(this.__wbg_ptr, actor);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * Current flee success chance 0..1 (what the next `flee()` rolls against).
     * @returns {number}
     */
    flee_chance() {
        const ret = wasm.game_flee_chance(this.__wbg_ptr);
        return ret;
    }
    /**
     * @returns {number}
     */
    gold() {
        const ret = wasm.game_gold(this.__wbg_ptr);
        return ret >>> 0;
    }
    /**
     * Still Water: halve damage until next turn and restore 10% max HP.
     * Still Water: damage x0.5 until this fighter's next turn, heals 10% max HP (15% in Inkwing), +6 Vermilion Ink
     * (not in Inkwing); Ink from damage taken while guarding is x1.5. Uses the turn.
     * @param {number} actor
     * @returns {string}
     */
    guard(actor) {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_guard(this.__wbg_ptr, actor);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * Gauge rules in effect: `{max, unfurl_cost, unfurl_turns}`.
     * @returns {string}
     */
    ink_rules_json() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_ink_rules_json(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * Unfurl (the battle command) into Inkwing form. Needs ink >= unfurl.cost (a full gauge), not already Inkwing.
     * Uses this turn; the next `unfurl.duration_turns` (3) own turns are Inkwing. Heals unfurl.heal_pct_max_hp.
     * @param {number} actor
     * @returns {string}
     */
    inkwing(actor) {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_inkwing(this.__wbg_ptr, actor);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {string}
     */
    inventory_json() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_inventory_json(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * Timed-press judgement exposed to the renderer (single source of truth for windows).
     * @param {number} delta_ms
     * @returns {number}
     */
    judge(delta_ms) {
        const ret = wasm.game_judge(this.__wbg_ptr, delta_ms);
        return ret;
    }
    /**
     * Lenient, validated load (save.rs). `false` only for unreadable input, and then state is untouched.
     * @param {string} s
     * @returns {boolean}
     */
    load_json(s) {
        const ptr0 = passStringToWasm0(s, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.game_load_json(this.__wbg_ptr, ptr0, len0);
        return ret !== 0;
    }
    /**
     * Warnings from the last `load_json`: `[{ "code", "path", "detail" }]` (empty after a clean load).
     * Codes: malformed_json, not_object, too_large, version_too_new (load returned false), migrated,
     * unknown_field, unknown_item, unknown_member, unknown_slot, unknown_equipment, wrong_slot,
     * not_equippable, bad_type, clamped, defaulted.
     * @returns {string}
     */
    load_warnings() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_load_warnings(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @param {string} party_json
     * @param {string} enemies_json
     * @param {string} items_json
     * @param {number} seed
     */
    constructor(party_json, enemies_json, items_json, seed) {
        const val4 = +seed;
        let ptr0, len0, ptr1, len1, ptr2, len2;
        try {
            ptr0 = passStringToWasm0(party_json, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            len0 = WASM_VECTOR_LEN;
            ptr1 = passStringToWasm0(enemies_json, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            len1 = WASM_VECTOR_LEN;
            ptr2 = passStringToWasm0(items_json, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            len2 = WASM_VECTOR_LEN;
        } catch (e) {
            if (ptr2) { wasm.__wbindgen_free(ptr2, len2 * 1, 1); }
            if (ptr1) { wasm.__wbindgen_free(ptr1, len1 * 1, 1); }
            if (ptr0) { wasm.__wbindgen_free(ptr0, len0 * 1, 1); }
            throw e;
        }
        const ret = wasm.game_new(ptr0, len0, ptr1, len1, ptr2, len2, val4);
        if (ret[2]) {
            throw takeFromExternrefTable0(ret[1]);
        }
        this.__wbg_ptr = ret[0];
        GameFinalization.register(this, this.__wbg_ptr, this);
        return this;
    }
    /**
     * @returns {string}
     */
    node() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_node(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {string}
     */
    party_json() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_party_json(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * Grade a press at `t_ms` against the pending hit. Returns `{ok, hit, grade, delta_ms, timeout, done, next?, result?}`.
     * A miss (early or late) ends the chain. When `done`, `result` is the `stroke()` result and the turn has advanced.
     * @param {number} t_ms
     * @returns {string}
     */
    press(t_ms) {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_press(this.__wbg_ptr, t_ms);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    rest() {
        wasm.game_rest(this.__wbg_ptr);
    }
    /**
     * XP/level-ups from the last victory: `{mon, xp, members:[{id, name, alive, gained, xp, lv_before, lv, leveled_up, next_total, stats?}]}` or null.
     * @returns {string}
     */
    rewards_json() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_rewards_json(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {string}
     */
    save_json() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_save_json(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * Schema version this build writes.
     * @returns {number}
     */
    save_version() {
        const ret = wasm.game_save_version(this.__wbg_ptr);
        return ret >>> 0;
    }
    /**
     * Seal Arts (Inkwing only): `hits` seals struck of the member's seal count, `clean` of those perfect.
     * Missed seals still land at half (Jake: magic is forgiving).
     * @param {number} actor
     * @param {number} hits
     * @param {number} clean
     * @returns {string}
     */
    seal_art(actor, hits, clean) {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_seal_art(this.__wbg_ptr, actor, hits, clean);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @param {string} id
     * @param {number} qty
     * @returns {boolean}
     */
    sell(id, qty) {
        const val2 = +qty;
        const ptr0 = passStringToWasm0(id, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.game_sell(this.__wbg_ptr, ptr0, len0, val2);
        return ret !== 0;
    }
    /**
     * Override combo windows: `{ "clean_ms": 95, "good_ms": 150, "anchor": "press"|"close",
     * "hits": { "<stroke_id>#<hit index>": { "clean_ms", "good_ms" } } }` (any subset). Half-widths in ms.
     * @param {string} cj
     * @returns {boolean}
     */
    set_combo_windows(cj) {
        const ptr0 = passStringToWasm0(cj, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.game_set_combo_windows(this.__wbg_ptr, ptr0, len0);
        return ret !== 0;
    }
    /**
     * Load Jake's elements.json (`{"chart": {"ember": {"tide": 2.0, ...}, ...}}`). Optional: without it the
     * SPEC section 2 rule (opposite x2, same x0.5, else x1) is used. Pairs missing from the chart also fall back.
     * @param {string} ej
     * @returns {boolean}
     */
    set_elements(ej) {
        const ptr0 = passStringToWasm0(ej, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.game_set_elements(this.__wbg_ptr, ptr0, len0);
        return ret !== 0;
    }
    /**
     * Damage multiplier on all enemy attacks (default 0.8, the integrator's tuning).
     * @param {number} m
     */
    set_enemy_damage_mult(m) {
        wasm.game_set_enemy_damage_mult(this.__wbg_ptr, m);
    }
    /**
     * Load the equipment catalog: pass the live `data/items.json` text (its `equipment` array) or Jane's
     * `equipment.json`. Call it right after the constructor and before `load_json`, or every equipped id
     * in the save is dropped as unknown. Also puts `starting_for` gear into empty slots (new game).
     * @param {string} equipment_json
     * @returns {boolean}
     */
    set_equipment(equipment_json) {
        const ptr0 = passStringToWasm0(equipment_json, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.game_set_equipment(this.__wbg_ptr, ptr0, len0);
        return ret !== 0;
    }
    /**
     * @param {string} k
     * @param {boolean} v
     */
    set_flag(k, v) {
        const val2 = +v;
        const ptr0 = passStringToWasm0(k, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        wasm.game_set_flag(this.__wbg_ptr, ptr0, len0, val2);
    }
    /**
     * Override the flee formula: `{ base, per_spd, per_fail, min, max }` (any subset).
     * @param {string} j
     * @returns {boolean}
     */
    set_flee_rules(j) {
        const ptr0 = passStringToWasm0(j, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.game_set_flee_rules(this.__wbg_ptr, ptr0, len0);
        return ret !== 0;
    }
    /**
     * @param {string} n
     */
    set_node(n) {
        const ptr0 = passStringToWasm0(n, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        wasm.game_set_node(this.__wbg_ptr, ptr0, len0);
    }
    /**
     * Load Inkwing forms from transformation.json (optional; defaults otherwise).
     * @param {string} tj
     * @returns {boolean}
     */
    set_rules(tj) {
        const ptr0 = passStringToWasm0(tj, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.game_set_rules(this.__wbg_ptr, ptr0, len0);
        return ret !== 0;
    }
    /**
     * @returns {number}
     */
    spoils() {
        const ret = wasm.game_spoils(this.__wbg_ptr);
        return ret >>> 0;
    }
    /**
     * @param {string} encounter
     * @returns {string}
     */
    start_battle(encounter) {
        let deferred2_0;
        let deferred2_1;
        try {
            const ptr0 = passStringToWasm0(encounter, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            const len0 = WASM_VECTOR_LEN;
            const ret = wasm.game_start_battle(this.__wbg_ptr, ptr0, len0);
            deferred2_0 = ret[0];
            deferred2_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred2_0, deferred2_1, 1);
        }
    }
    /**
     * Start a battle with optional encounter flags: `{ "first": "enemy"|"party"|null, "canFlee": bool }`
     * (`can_flee` also accepted). `first` reorders round 1 only (ambush: that side acts first, each side by speed).
     * `canFlee:false` makes `flee()` refuse with reason "cannot_flee" (bosses). Missing flags = normal start, Flee allowed.
     * @param {string} encounter
     * @param {string} opts_json
     * @returns {string}
     */
    start_battle_opts(encounter, opts_json) {
        let deferred3_0;
        let deferred3_1;
        try {
            let ptr0, len0, ptr1, len1;
            try {
                ptr0 = passStringToWasm0(encounter, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
                len0 = WASM_VECTOR_LEN;
                ptr1 = passStringToWasm0(opts_json, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
                len1 = WASM_VECTOR_LEN;
            } catch (e) {
                if (ptr1) { wasm.__wbindgen_free(ptr1, len1 * 1, 1); }
                if (ptr0) { wasm.__wbindgen_free(ptr0, len0 * 1, 1); }
                throw e;
            }
            const ret = wasm.game_start_battle_opts(this.__wbg_ptr, ptr0, len0, ptr1, len1);
            deferred3_0 = ret[0];
            deferred3_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred3_0, deferred3_1, 1);
        }
    }
    /**
     * Renderer step: if it is an enemy's turn, run its AI (same as `enemy_turn`); otherwise `{"ok":false}`.
     * @returns {string}
     */
    step() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_step(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * Party attack with a Brushstroke Chain. `grades` = per-hit judgement (2/1/0); stops at first 0.
     * @param {number} actor
     * @param {number} target
     * @param {number} stroke_idx
     * @param {Uint8Array | number[]} grades
     * @returns {string}
     */
    stroke(actor, target, stroke_idx, grades) {
        let deferred5_0;
        let deferred5_1;
        try {
            const val2 = +actor;
            const val3 = +target;
            const val4 = +stroke_idx;
            const ptr0 = passArray8ToWasm0(grades, wasm.__wbindgen_malloc);
            const len0 = WASM_VECTOR_LEN;
            const ret = wasm.game_stroke(this.__wbg_ptr, val2, val3, val4, ptr0, len0);
            deferred5_0 = ret[0];
            deferred5_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred5_0, deferred5_1, 1);
        }
    }
    /**
     * Alias of `inkwing` under the command's name (SPEC section 2: the command is Unfurl, the form is Inkwing).
     * @param {number} actor
     * @returns {string}
     */
    unfurl(actor) {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_unfurl(this.__wbg_ptr, actor);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @param {number} actor
     * @param {string} item
     * @param {number} target
     * @returns {string}
     */
    use_item(actor, item, target) {
        let deferred4_0;
        let deferred4_1;
        try {
            const val2 = +actor;
            const val3 = +target;
            const ptr0 = passStringToWasm0(item, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            const len0 = WASM_VECTOR_LEN;
            const ret = wasm.game_use_item(this.__wbg_ptr, val2, ptr0, len0, val3);
            deferred4_0 = ret[0];
            deferred4_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred4_0, deferred4_1, 1);
        }
    }
    /**
     * @param {string} poi_json
     * @param {number} x
     * @param {number} y
     * @returns {boolean}
     */
    walker_load(poi_json, x, y) {
        const val2 = +x;
        const val3 = +y;
        const ptr0 = passStringToWasm0(poi_json, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.game_walker_load(this.__wbg_ptr, ptr0, len0, val2, val3);
        return ret !== 0;
    }
    /**
     * @param {number} x
     * @param {number} y
     */
    walker_set(x, y) {
        wasm.game_walker_set(this.__wbg_ptr, x, y);
    }
    /**
     * Move by (vx, vy) px/s for dt seconds with axis-separated collision. Returns [x, y].
     * @param {number} vx
     * @param {number} vy
     * @param {number} dt
     * @returns {Float64Array}
     */
    walker_step(vx, vy, dt) {
        const ret = wasm.game_walker_step(this.__wbg_ptr, vx, vy, dt);
        var v1 = getArrayF64FromWasm0(ret[0], ret[1]).slice();
        wasm.__wbindgen_free(ret[0], ret[1] * 8, 8);
        return v1;
    }
    /**
     * Ids of triggers the walker currently stands in, comma separated.
     * @returns {string}
     */
    walker_triggers() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_walker_triggers(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * `clean`/`good` (and the same values as `clean_ms`/`good_ms`) are half-widths in ms.
     * @returns {string}
     */
    windows_json() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.game_windows_json(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
}
if (Symbol.dispose) Game.prototype[Symbol.dispose] = Game.prototype.free;
function __wbg_get_imports() {
    const import0 = {
        __proto__: null,
        __wbg___wbindgen_throw_4c88d8bf264fd984: function(arg0, arg1) {
            throw new Error(getStringFromWasm0(arg0, arg1));
        },
        __wbindgen_generic_0000000000000001: function(arg0, arg1) {
            // Cast intrinsic for `Ref(String) -> Externref`.
            const ret = getStringFromWasm0(arg0, arg1);
            return ret;
        },
        __wbindgen_init_externref_table: function() {
            const table = wasm.__wbindgen_externrefs;
            table.set(0, undefined);
            table.set(1024, undefined);
            table.set(1025, null);
            table.set(1026, true);
            table.set(1027, false);
        },
    };
    return {
        __proto__: null,
        "./inkborne_core_bg.js": import0,
    };
}

const GameFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_game_free(ptr, 1));

function getArrayF64FromWasm0(ptr, len) {
    ptr = ptr >>> 0;
    return getFloat64ArrayMemory0().subarray(ptr / 8, ptr / 8 + len);
}

let cachedFloat64ArrayMemory0 = null;
function getFloat64ArrayMemory0() {
    if (cachedFloat64ArrayMemory0 === null || cachedFloat64ArrayMemory0.byteLength === 0) {
        cachedFloat64ArrayMemory0 = new Float64Array(wasm.memory.buffer);
    }
    return cachedFloat64ArrayMemory0;
}

function getStringFromWasm0(ptr, len) {
    ptr = ptr >>> 0;
    return decodeText(getUint8ArrayMemory0().subarray(ptr, ptr + len));
}

let cachedUint8ArrayMemory0 = null;
function getUint8ArrayMemory0() {
    if (cachedUint8ArrayMemory0 === null || cachedUint8ArrayMemory0.byteLength === 0) {
        cachedUint8ArrayMemory0 = new Uint8Array(wasm.memory.buffer);
    }
    return cachedUint8ArrayMemory0;
}

function passArray8ToWasm0(arg, malloc) {
    const ptr = malloc(arg.length * 1, 1) >>> 0;
    getUint8ArrayMemory0().set(arg, ptr / 1);
    WASM_VECTOR_LEN = arg.length;
    return ptr;
}

function passStringToWasm0(arg, malloc, realloc) {
    if (realloc === undefined) {
        const buf = cachedTextEncoder.encode(arg);
        const ptr = malloc(buf.length, 1) >>> 0;
        getUint8ArrayMemory0().subarray(ptr, ptr + buf.length).set(buf);
        WASM_VECTOR_LEN = buf.length;
        return ptr;
    }

    let len = arg.length;
    let ptr = malloc(len, 1) >>> 0;

    const mem = getUint8ArrayMemory0();

    let offset = 0;

    for (; offset < len; offset++) {
        const code = arg.charCodeAt(offset);
        if (code > 0x7F) break;
        mem[ptr + offset] = code;
    }
    if (offset !== len) {
        if (offset !== 0) {
            arg = arg.slice(offset);
        }
        ptr = realloc(ptr, len, len = offset + arg.length * 3, 1) >>> 0;
        const view = getUint8ArrayMemory0().subarray(ptr + offset, ptr + len);
        const ret = cachedTextEncoder.encodeInto(arg, view);

        offset += ret.written;
        ptr = realloc(ptr, len, offset, 1) >>> 0;
    }

    WASM_VECTOR_LEN = offset;
    return ptr;
}

function takeFromExternrefTable0(idx) {
    const value = wasm.__wbindgen_externrefs.get(idx);
    wasm.__externref_table_dealloc(idx);
    return value;
}

let cachedTextDecoder = new TextDecoder('utf-8', { ignoreBOM: true });
cachedTextDecoder.decode();
const MAX_SAFARI_DECODE_BYTES = 2146435072;
let numBytesDecoded = 0;
function decodeText(bytes) {
    numBytesDecoded += bytes.length;
    if (numBytesDecoded >= MAX_SAFARI_DECODE_BYTES) {
        cachedTextDecoder = new TextDecoder('utf-8', { ignoreBOM: true });
        cachedTextDecoder.decode();
        numBytesDecoded = bytes.length;
    }
    return cachedTextDecoder.decode(bytes);
}

const cachedTextEncoder = new TextEncoder();

if (!('encodeInto' in cachedTextEncoder)) {
    cachedTextEncoder.encodeInto = function (arg, view) {
        const buf = cachedTextEncoder.encode(arg);
        view.set(buf);
        return {
            read: arg.length,
            written: buf.length
        };
    };
}

let WASM_VECTOR_LEN = 0;

let wasmModule, wasmInstance, wasm;
function __wbg_finalize_init(instance, module) {
    wasmInstance = instance;
    wasm = instance.exports;
    wasmModule = module;
    cachedFloat64ArrayMemory0 = null;
    cachedUint8ArrayMemory0 = null;
    wasm.__wbindgen_start();
    return wasm;
}

async function __wbg_load(module, imports) {
    if (typeof Response === 'function' && module instanceof Response) {
        if (!module.ok) {
            throw new Error(`failed to fetch Wasm: ${module.status} ${module.statusText} fetching '${module.url}'`);
        }

        if (typeof WebAssembly.instantiateStreaming === 'function') {
            try {
                return await WebAssembly.instantiateStreaming(module, imports);
            } catch (e) {
                const validResponse = expectedResponseType(module.type);

                if (validResponse && module.headers.get('Content-Type') !== 'application/wasm') {
                    console.warn("`WebAssembly.instantiateStreaming` failed because your server does not serve Wasm with `application/wasm` MIME type. Falling back to `WebAssembly.instantiate` which is slower. Original error:\n", e);

                } else { throw e; }
            }
        }

        const bytes = await module.arrayBuffer();
        return await WebAssembly.instantiate(bytes, imports);
    } else {
        const instance = await WebAssembly.instantiate(module, imports);

        if (instance instanceof WebAssembly.Instance) {
            return { instance, module };
        } else {
            return instance;
        }
    }

    function expectedResponseType(type) {
        switch (type) {
            case 'basic': case 'cors': case 'default': return true;
        }
        return false;
    }
}

function initSync(module) {
    if (wasm !== undefined) return wasm;


    if (module !== undefined) {
        if (Object.getPrototypeOf(module) === Object.prototype) {
            ({module} = module)
        } else {
            console.warn('using deprecated parameters for `initSync()`; pass a single object instead')
        }
    }

    const imports = __wbg_get_imports();
    if (!(module instanceof WebAssembly.Module)) {
        module = new WebAssembly.Module(module);
    }
    const instance = new WebAssembly.Instance(module, imports);
    return __wbg_finalize_init(instance, module);
}

let __wbg_init_promise;
async function __wbg_init(module_or_path) {
    if (wasm !== undefined) return wasm;
    if (__wbg_init_promise === undefined) {
        __wbg_init_promise = __wbg_init_once(module_or_path);
        __wbg_init_promise.catch(() => { __wbg_init_promise = undefined; });
    }
    return __wbg_init_promise;
}

async function __wbg_init_once(module_or_path) {

    if (module_or_path !== undefined) {
        if (Object.getPrototypeOf(module_or_path) === Object.prototype) {
            ({module_or_path} = module_or_path)
        } else {
            console.warn('using deprecated parameters for the initialization function; pass a single object instead')
        }
    }

    if (module_or_path === undefined) {
        module_or_path = new URL('inkborne_core_bg.wasm', import.meta.url);
    }
    const imports = __wbg_get_imports();

    if (typeof module_or_path === 'string' || (typeof Request === 'function' && module_or_path instanceof Request) || (typeof URL === 'function' && module_or_path instanceof URL)) {
        module_or_path = fetch(module_or_path);
    }

    const { instance, module } = await __wbg_load(await module_or_path, imports);

    return __wbg_finalize_init(instance, module);
}

export { initSync, __wbg_init as default };
