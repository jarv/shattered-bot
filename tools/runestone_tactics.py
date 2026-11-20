"""Active, bounded runestone and exotic-consumable tactics from observed geometry."""
try:
    from .consumable_tactics import base_name, unknown_potion, unknown_scroll
except ImportError:
    from consumable_tactics import base_name, unknown_potion, unknown_scroll


def choose_runestone(p, state, enemies, distance, neighbors):
    active = [e for e in enemies if not e.get("sleeping")]
    if not active or p.stone_cooldown or state.get("danger_cells"):
        return None
    pos, width = state["hero"]["cell"], state["map"]["width"]
    hp = state["hero"]["hp"] / max(1, state["hero"]["max_hp"])
    inventory = {base_name(i): i for i in state["inventory"]}
    pressure = len(active) >= 2 or hp < 0.6
    if hp < 0.45:
        blink = blink_escape(p, state, active, distance, neighbors)
        if blink:
            return blink
    fog = inventory.get("potion of shrouding fog")
    if pressure and hp < 0.7 and fog and "THROW" in fog.get("actions", []) \
            and not any(p.harmless_effect(e) for e in p.tiles[pos].get("effects", [])):
        p.stone_cooldown = 8
        return p.use(fog, "THROW", "alchemy: shrouding fog breaks swarm sight without blinding the Mage", target=pos)
    def throw(name, target, reason):
        item = inventory.get(name)
        enemy = next((e for e in active if e["cell"] == target), None)
        if item and "THROW" in item.get("actions", []) and p.shot_clear(state, target) and (not enemy or p.target_allowed(item, enemy)):
            p.stone_cooldown = 8
            return p.use(item, "THROW", reason, target=target)
        return None
    enemy_cells = {e["cell"] for e in active}
    shock = inventory.get("stone of shock")
    if pressure and shock and "THROW" in shock.get("actions", []) and (len(active) >= 3 or not p.charged_magic(state)):
        choices = []
        friend_cells = {o["cell"] for o in state.get("objects", []) if not o.get("top_item") and o["cell"] not in enemy_cells}
        for target, tile in p.tiles.items():
            if not tile.get("visible") or tile["terrain"] not in {1,6,11,14,19,20,29} \
                    or tile.get("plant") or tile.get("effects") or target in p.loot \
                    or distance(pos, target, width) <= 2 or any(distance(target, c, width) <= 2 for c in friend_cells) \
                    or not p.shot_clear(state, target):
                continue
            area = {target}
            for _ in range(2):
                area |= {n for c in area for n in neighbors(c, width, state["map"]["height"])
                         if p.tiles.get(n, {}).get("terrain") in {1,2,3,5,6,9,11,14,15,18,19,20,29,30}}
            hits = sum(e["cell"] in area and p.target_allowed(shock, e) for e in active)
            if hits >= 2:
                choices.append((hits, -distance(pos, target, width), -target, target))
        if choices:
            return throw("stone of shock", max(choices)[3], "stone: shock visible ground to disable pursuing cluster and recharge")
    for enemy in sorted(active, key=lambda e: distance(pos, e["cell"], width), reverse=True):
        target = enemy["cell"]
        dist = distance(pos, target, width)
        others = [o for o in state.get("objects", []) if not o.get("top_item") and o["cell"] not in enemy_cells]
        if pressure and dist >= 3 and not any(distance(target, o["cell"], width) <= 2 for o in others):
            cluster = sum(distance(target, e["cell"], width) <= 2 for e in active)
            area = {y*width+x for x in range(max(0,target%width-2), min(width,target%width+3))
                    for y in range(max(0,target//width-2), min(state["map"]["height"],target//width+3))}
            known_area = all(p.tiles.get(c, {}).get("visible") and p.tiles[c]["terrain"] in {1,4,6,11,14,19,20,29} for c in area)
            if cluster >= 2 and known_area and not any(distance(target, o["cell"], width) <= 2 for o in state.get("objects", []) if o["cell"] not in enemy_cells):
                action = throw("stone of blast", target, "stone: blast distant enemy cluster with no visible allies or loot in radius")
                if action:
                    return action
            if not p.charged_magic(state):
                action = throw("stone of shock", target, "stone: paralyze distant group and recharge wands")
                if action:
                    return action
            if len(active) >= 3 and state["depth"] % 5 != 0:
                action = throw("stone of aggression", target, "stone: redirect swarm onto observed non-boss enemy")
                if action:
                    return action
            # Flock must not seal the hero inside its radius or block every exit.
            escape = [c for c in neighbors(pos, width, state["map"]["height"])
                      if p.walkable(c, enemy_cells) and distance(c, target, width) > 2]
            if hp < 0.5 and escape:
                action = throw("stone of flock", target, "stone: block distant pursuit while retaining an exit")
                if action:
                    return action
        if dist >= 3 and pressure and not any(distance(target, o["cell"], width) <= 1 for o in state.get("objects", [])
                                             if o["cell"] != target):
            action = throw("potion of snap freeze", target, "alchemy: freeze distant threat without freezing hero or allies")
            if action:
                return action
        if hp < 0.6 and enemy["name"].lower() not in {"goo", "tengu", "dm-300", "king of dwarves", "yog-dzewa", "demon spawner"} and "fist" not in enemy["name"].lower():
            for name in ("stone of deep sleep", "stone of fear"):
                action = throw(name, target, "stone: disable pursuit before critical health")
                if action:
                    return action
    if pressure and hp < 0.65:
        buffs = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
        for name, action, buff in (("potion of stamina", "DRINK", "stamina"),
                                   ("potion of earthen armor", "DRINK", "earth"),
                                   ("scroll of dread", "READ", "dread"),
                                   ("scroll of prismatic image", "READ", "prismatic")):
            item = inventory.get(name)
            if item and action in item.get("actions", []) and buff not in buffs:
                p.stone_cooldown = 8
                return p.use(item, action, "alchemy: use known defensive exotic before lethal trades")
    return None


def prepare_intuition(p, state, guess=None, candidate=None):
    stone = next((i for i in state["inventory"] if base_name(i) == "stone of intuition" and "USE" in i.get("actions", [])), None)
    if not stone:
        return None
    # These are explicitly hypotheses; a failed guess does not identify an item.
    unknown = [i for i in state["inventory"] if i["name"] not in p.intuition_attempts
               and not i.get("identified") and (unknown_potion(i) or unknown_scroll(i) or i["name"].lower().endswith(" ring"))]
    if not unknown and candidate is None:
        return None
    item = candidate if candidate is not None else max(unknown, key=lambda i: (unknown_potion(i), i.get("quantity", 1)))
    choice = guess or ("potion of strength" if unknown_potion(item) else "scroll of recharging" if unknown_scroll(item) else "ring of energy")
    p.intuition_attempts.add(item["name"])
    p.intuition_plan = {"item": item["name"].lower(), "guess": choice, "stage": "item", "steps": 0, "bags": set()}
    return p.use(stone, "USE", "stone: test declared identity hypothesis without drinking unknown potion")


def intuition_menu(p, state):
    plan = p.intuition_plan
    plan["steps"] += 1
    buttons = state["ui"]["buttons"]
    if plan["steps"] <= 8:
        label = plan["item"] if plan["stage"] == "item" else plan["guess"]
        if plan["stage"] == "confirm" and not any(t.strip().lower() == plan["guess"] for t in state["ui"].get("texts", [])):
            p.intuition_plan = None
            return p.decision({"type": "back"}, "stone: refuse intuition confirmation without rendered selected guess")
        match = next((b for b in buttons if b["label"].lower() == label), None)
        if match:
            stage = plan["stage"]
            if stage == "confirm":
                p.intuition_plan = None
            else:
                plan["stage"] = "guess" if stage == "item" else "confirm"
            return p.decision({"type": "button", "id": match["id"]}, "stone: confirm public intuition hypothesis" if stage == "confirm" else "stone: select public intuition option")
        if plan["stage"] == "item":
            bag = next((b for b in buttons if b["label"].lower() in {"backpack", "potion bandolier", "scroll holder"}
                        and b["label"] not in plan["bags"]), None)
            if bag:
                plan["bags"].add(bag["label"])
                return p.decision({"type": "button", "id": bag["id"]}, "stone: search observed bag once")
    p.intuition_plan = None
    return p.decision({"type": "back"}, "stone: cancel unavailable intuition hypothesis")


def prepare_mapping(p, state, *, required=False):
    try:
        from .mapping_knowledge import complete
    except ImportError:
        from mapping_knowledge import complete
    if complete(p,state):return None
    if state["depth"] in p.mapping_attempts or state["hero"]["hp"] <= 3:
        return None
    if required and any("magic immun" in b["name"].lower() for b in state["hero"].get("buffs",[])):
        return None
    scroll = next((i for i in state["inventory"] if base_name(i) == "scroll of magic mapping" and "READ" in i.get("actions", [])), None)
    if required and scroll:
        p.mapping_attempts.add(state["depth"])
        return p.use(scroll,"READ","scroll: reveal connecting passages to an observed mandatory strength/upgrade pickup")
    if p.searches < 2:
        return None
    stone = next((i for i in state["inventory"] if base_name(i) == "stone of clairvoyance" and "THROW" in i.get("actions", [])), None)
    if stone:
        p.mapping_attempts.add(state["depth"])
        return p.use(stone, "THROW", "stone: reveal surrounding geometry after bounded unsuccessful search", target=state["hero"]["cell"])
    if scroll:
        p.mapping_attempts.add(state["depth"])
        return p.use(scroll, "READ", "scroll: map missing exit instead of prolonged hunger-cost search")
    return None


def blink_escape(p, state, enemies, distance, neighbors):
    try:
        from .challenge_combat import reach
    except ImportError:
        from challenge_combat import reach
    blink = next((i for i in state["inventory"] if base_name(i) == "stone of blink" and "THROW" in i.get("actions", [])), None)
    if not blink:
        return None
    pos, width = state["hero"]["cell"], state["map"]["width"]
    occupied = {o["cell"] for o in state.get("objects", []) if not o.get("top_item")}
    paths = p.paths(state, occupied)
    choices = []
    for cell in paths:
        tile = p.tiles[cell]
        if cell == pos or not tile.get("visible") or tile["terrain"] not in {1,2,3,11,14,19,20,29} \
                or tile.get("plant") or tile.get("trap") or p.effects_block_movement(tile) or cell in p.loot \
                or cell in state.get("danger_cells", []) or not 2 <= distance(pos, cell, width) <= 6:
            continue
        separation = min((distance(cell, e["cell"], width)-reach(e)
                          - int(any(t in e.get("description", "").lower() for t in ("extremely fast", "double speed")))
                          for e in enemies if not e.get("sleeping")), default=6)
        exits = sum(p.walkable(n, occupied) for n in neighbors(cell, width, state["map"]["height"]))
        if separation >= 2 and exits >= 2 and p.shot_clear(state, cell):
            choices.append((separation, exits, -distance(pos, cell, width), cell))
    if choices:
        p.stone_cooldown = 8
        return p.use(blink, "THROW", "stone: blink to verified visible safe ground with continuing exits", target=max(choices)[3])
    return None


def prepare_inventory_stone(p, state):
    try:
        from .combat_items import stats
        from .artifact_tactics import ARTIFACT_PRIORITY, artifact_name
    except ImportError:
        from combat_items import stats
        from artifact_tactics import ARTIFACT_PRIORITY, artifact_name
    inventory = state["inventory"]
    detect = next((i for i in inventory if base_name(i) == "stone of detect magic" and "USE" in i.get("actions", [])), None)
    targets = [i for i in inventory if not i.get("curse_known") and "EQUIP" in i.get("actions", [])
               and (artifact_name(i) in ARTIFACT_PRIORITY or i["name"].lower().endswith(" ring"))
               and ("detect", i["name"]) not in p.inventory_stone_attempts]
    if detect and targets:
        target = max(targets, key=lambda i: ARTIFACT_PRIORITY.get(artifact_name(i), 4))
        kind, source = "detect", detect
    else:
        source = next((i for i in inventory if base_name(i) == "stone of augmentation" and "USE" in i.get("actions", [])), None)
        target = next((i for i in inventory if i.get("equipped") and i.get("identified") and not i.get("known_cursed")
                       and stats(i) and stats(i)[0] == "armor" and "evasion" not in i.get("description", "").lower()
                       and ("augment", i["name"]) not in p.inventory_stone_attempts), None)
        kind = "augment"
    if source and target:
        p.inventory_stone_attempts.add((kind, target["name"]))
        p.inventory_stone_plan = {"kind": kind, "item": target["name"].lower(), "stage": "item", "steps": 0, "bags": set()}
        return p.use(source, "USE", "stone: inspect unknown equipment magic" if kind == "detect" else "stone: prioritize evasion over reduced challenge armor blocking")
    return None


def inventory_stone_menu(p, state):
    plan = p.inventory_stone_plan
    plan["steps"] += 1
    buttons = state["ui"]["buttons"]
    if plan["steps"] <= 6:
        target = next((b for b in buttons if b["label"].lower() == plan["item"]), None) if plan["stage"] == "item" else \
                 next((b for b in buttons if "evasion" in b["label"].lower()), None)
        if target:
            if plan["kind"] == "detect" or plan["stage"] == "augment":
                p.inventory_stone_plan = None
            else:
                plan["stage"] = "augment"
            return p.decision({"type": "button", "id": target["id"]}, "stone: select validated equipment/augmentation option")
        if plan["stage"] == "item":
            bag = next((b for b in buttons if b["label"].lower() in {"backpack", "magical holster"} and b["label"] not in plan["bags"]), None)
            if bag:
                plan["bags"].add(bag["label"])
                return p.decision({"type": "button", "id": bag["id"]}, "stone: find equipment in observed bag")
    p.inventory_stone_plan = None
    return p.decision({"type": "back"}, "stone: cancel unavailable equipment operation")
