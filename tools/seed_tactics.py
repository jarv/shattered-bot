"""Conservative plant setup using only observed items, terrain, and threats."""


PLANTABLE = {1, 2, 3, 5, 6, 11, 14, 15, 19, 20, 29}


def choose_seed(p, state, enemies, distance, neighbors):
    if getattr(p,'unit_strategies_enabled',False):
        try:
            from .seed_strategies import choose
        except ImportError:
            from seed_strategies import choose
        return choose(p,state,enemies)
    if getattr(p, "barren_land", False):
        p.seed_plan = None
        return None
    hero = state["hero"]
    pos, width, height = hero["cell"], state["map"]["width"], state["map"]["height"]
    buffs = " ".join(b["name"].lower() for b in hero.get("buffs", []))
    active = [e for e in enemies if not e.get("sleeping")]
    close = min((distance(pos, e["cell"], width) for e in active), default=99)
    hp = hero["hp"] / max(1, hero["max_hp"])
    tile = p.tiles[pos]
    safe_recovery = not active and not any(distance(pos, e["cell"], width) <= 3 for e in enemies)
    safe_recovery = safe_recovery and not any(distance(pos, a["cell"], width) <= 3 for a in p.room_actors.values())
    affordable = "starving" not in buffs and ("hungry" not in buffs or p.food_items(state))
    plan = p.seed_plan
    if plan:
        if plan["cell"] != pos or pos in p.room_blocked or p.effects_block_movement(tile):
            p.seed_plan = None
        elif plan["stage"] == "activate":
            plant = tile.get("plant", "").lower()
            allowed = safe_recovery if plan["kind"] == "sungrass" else close >= 2
            if plan["kind"] in plant and allowed:
                p.seed_plan = dict(plan, stage="recover", waits=0)
                return p.cell(pos, f"seed: activate {plan['kind']}")
            p.seed_plan = None
        elif plan["kind"] == "sungrass" and "herbal healing" in buffs and safe_recovery \
                and affordable and hp < 0.95 and plan["waits"] < 80:
            plan["waits"] += 1
            return p.decision({"type": "wait"}, "seed: sheltered sungrass recovery")
        else:
            p.seed_plan = None
    if p.seed_cooldown:
        p.seed_cooldown -= 1
        return None

    def seed(kind):
        return next((i for i in state["inventory"] if f"seed of {kind}" in i["name"].lower()
                      and "PLANT" in i.get("actions", []) and not i.get("known_cursed")
                      and p.item_action_allowed(i,"PLANT")), None)

    def plantable(cell):
        t = p.tiles.get(cell, {})
        return t.get("terrain") in PLANTABLE and not t.get("plant") and not t.get("trap") \
                and not p.effects_block_movement(t) and cell not in p.room_blocked and cell not in state.get("danger_cells", [])

    def plant_self(kind):
        item = seed(kind)
        if item and plantable(pos):
            p.seed_plan = {"kind": kind, "cell": pos, "stage": "activate"}
            p.seed_cooldown = 20
            return p.use(item, "PLANT", f"seed: prepare {kind}")
        return None

    if safe_recovery and affordable and hp < 0.8 and "herbal healing" not in buffs:
        action = plant_self("sungrass")
        if action:
            return action
    if close >= 3 and any(condition in buffs for condition in ("poison", "bleeding", "weakness", "blindness")):
        action = plant_self("mageroyal")
        if action:
            return action
    # Two ordinary inputs must complete before a known walking-only foe arrives.
    # Do not assume a ranged/fast enemy or a boss will patiently approach.
    walking={'marsupial rat','albino rat','gnoll scout','slime','caustic slime'}
    if len(active)==1 and active[0]['name'].lower() in walking and 4<=close<=5 \
            and 'champion' not in active[0].get('description','').lower() and not state.get('danger_cells'):
        if hp<.65 and not any(b in buffs for b in ('time bubble','time freeze')):
            action=plant_self('swiftthistle')
            if action:return action
        if hp>=.5 and not any(b in buffs for b in ('blessed','recharging')):
            action=plant_self('starflower')
            if action:return action
    degree = lambda cell: sum(p.walkable(n) for n in neighbors(cell, width, height))
    if len(active) == 1 and close >= 3 and close <= 5 and hp >= 0.5 and degree(pos) <= 3 \
            and "herbal armor" not in buffs:
        action = plant_self("earthroot")
        if action:
            return action
    # Lead a durable pursuer onto a narrow approach tile. Never throw a seed
    # under a stationary attacker and assume it immediately applies its effect.
    durable = [e for e in active if e["name"].lower() in {"sewer crab", "gnoll scout", "goo", "slime", "caustic slime"}
                or "mimic" in e["name"].lower()]
    if getattr(p,'unit_strategies_enabled',False):
        durable=[e for e in durable if p.unit_strategies.profile(e).triggers_ground_plants]
    if close >= 2 and durable:
        enemy = min(durable, key=lambda e: distance(pos, e["cell"], width))
        dist = distance(pos, enemy["cell"], width)
        bar = enemy.get("health_bar")
        if bar and bar[1] > 0 and bar[0] / bar[1] < 0.3:
            return None
        occupied = {o["cell"] for o in state.get("objects", []) if "top_item" not in o}
        candidates = [c for c in neighbors(pos, width, height) if c not in occupied and plantable(c)
                      and p.walkable(c) and degree(c) <= 3 and distance(c, enemy["cell"], width) < dist
                      and p.shot_clear(state, c)]
        if candidates:
            kind = "blindweed" if len(active) > 1 else "sorrowmoss"
            item = seed(kind)
            if item and "THROW" in item["actions"]:
                p.seed_cooldown = 20
                target = min(candidates, key=lambda c: (degree(c), distance(c, enemy["cell"], width)))
                return p.use(item, "THROW", f"seed: {kind} pursuit trap", target=target)
    return None
