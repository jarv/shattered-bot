"""Prioritize visible summoners; remembered sightings are navigation clues only."""

CASTERS = {"necromancer", "spectral necromancer"}
SUMMON = "necromancer's skeleton"


class NecromancerStalemate(RuntimeError):
    pass


def haste_withdrawal(p, state, enemies, distance):
    target = p.necro_escape_target
    if target is None:
        return None
    hero, width = state["hero"], state["map"]["width"]
    buffs = " ".join(b["name"].lower() for b in hero.get("buffs", []))
    previous = p.paths(state, {e["cell"] for e in enemies})
    if "haste" in buffs and not any(s in buffs for s in ("crippled", "slowed", "rooted")) \
            and target in previous and target != hero["cell"] and p.necro_moves < 24:
        route = p.route(previous, target)
        threats = [e for e in enemies if e["name"].lower() not in CASTERS and not e.get("sleeping")]
        if len(route) <= 4 and all(distance(target, e["cell"], width) > 1 for e in threats) \
                and all(p.tiles[c]["terrain"] not in {5, 7, 8, 10, 21, 22, 31, 37, 38}
                        and not p.tiles[c].get("plant") and not p.tiles[c].get("effects")
                        and c not in p.loot and c not in state.get("danger_cells", []) for c in route[1:]):
            p.necro_moves += 1
            return p.cell(route[1], "necro: haste withdrawal before linked skeleton explosion")
    p.necro_escape_target = None
    return None


def choose_necromancer(p, state, enemies, distance, neighbors, line_clear):
    pos, width, height = state["hero"]["cell"], state["map"]["width"], state["map"]["height"]
    withdrawal = haste_withdrawal(p, state, enemies, distance)
    if withdrawal:
        return withdrawal
    visible = [e for e in enemies if e["name"].lower() in CASTERS and not e.get("sleeping")]
    minions = [e for e in enemies if e["name"].lower() == SUMMON and not e.get("sleeping")]
    if not visible and not minions:
        p.necro_moves = p.necro_blocker_attacks = 0
        return None
    hero = state["hero"]
    buffs = " ".join(b["name"].lower() for b in hero.get("buffs", []))
    threats = [e for e in enemies if e["name"].lower() not in CASTERS and not e.get("sleeping")]
    if threats and hero["hp"] < 0.5 * hero["max_hp"]:
        for name, action, active_buff in (("potion of invisibility", "DRINK", "invisib"),
                                          ("scroll of teleportation", "READ", ""),
                                          ("scroll of terror", "READ", ""),
                                          ("potion of haste", "DRINK", "haste")):
            item = next((i for i in state["inventory"] if name in i["name"].lower()
                         and action in i.get("actions", [])), None)
            if item and (not active_buff or active_buff not in buffs):
                return p.use(item, action, "necro: escape supported minion attrition")
    # Killing the caster also kills its minion via Skeleton.die(), which still
    # explodes. At low HP, don't turn a nearly-won caster fight into self-death.
    wounded_caster = any(e.get("health_bar") and e["health_bar"][1] > 0
                         and e["health_bar"][0] / e["health_bar"][1] <= 0.4 for e in visible)
    adjacent_minions = [e for e in minions if distance(pos, e["cell"], width) == 1]
    if wounded_caster and adjacent_minions and hero["hp"] <= 12:
        occupied = {e["cell"] for e in enemies}
        escapes = [c for c in neighbors(pos, width, height) if p.walkable(c, occupied)
                   and p.tiles[c]["terrain"] not in {5, 7, 8, 10, 21, 22, 31, 37, 38}
                   and not p.tiles[c].get("plant") and not p.loot.get(c, {}).get("for_sale")
                   and all(distance(c, e["cell"], width) > 1 for e in enemies if not e.get("sleeping") and e["name"].lower() not in CASTERS)]
        if escapes and p.necro_moves < 24:
            p.necro_moves += 1
            return p.cell(min(escapes, key=lambda c: p.visits[c]), "necro: gain distance before linked skeleton explosion")
        if "haste" in buffs and not any(s in buffs for s in ("crippled", "slowed", "rooted")):
            previous = p.paths(state, occupied)
            targets = [c for c in previous if 2 < len(p.route(previous, c)) <= 4
                       and all(distance(c, e["cell"], width) > 1 for e in threats)]
            for target in sorted(targets, key=lambda c: len(p.route(previous, c))):
                p.necro_escape_target = target
                withdrawal = haste_withdrawal(p, state, enemies, distance)
                if withdrawal:
                    return withdrawal
        raise NecromancerStalemate("Finishing this necromancer risks a fatal adjacent bone explosion; no safe spacing or usable escape")
    # Summoner priority must not grant a nearly-dead ordinary attacker many
    # free hits. Do not apply this to skeletons: their death blast needs spacing.
    finishers = [e for e in threats if distance(pos, e["cell"], width) == 1
                 and e["name"].lower() not in {SUMMON, "skeleton", "wraith", "tormented spirit"}
                 and e.get("health_bar") and e["health_bar"][1] > 0
                 and e["health_bar"][0] / e["health_bar"][1] <= 0.25]
    for target in finishers:
        magic = p.charged_magic(state)
        if magic and p.shot_clear(state, target["cell"]):
            return p.use(magic[0], "ZAP", "necro: finish wounded adjacent attacker first", target=target["cell"])
        attack = p.best_attack(state, target)
        if attack:
            attack.reason = "necro: finish wounded adjacent attacker first"
            return attack
    # A caster is a support target, not a melee threat. Killing it also kills
    # its own summons, but never infer which offscreen minion belongs to whom.
    for caster in sorted(visible, key=lambda e: distance(pos, e["cell"], width)):
        attack = p.best_attack(state, caster)
        if attack:
            attack.reason = "necro: focus visible summoner"
            return attack

    memories = [e for e in p.enemy_sightings.values() if e["name"].lower() in CASTERS]
    targets = (visible or memories) if (minions or visible) else []
    occupied = {e["cell"] for e in enemies}
    previous = p.paths(state, occupied)
    can_zap = bool(p.charged_magic(state))

    if p.necro_moves < 24:
        choices = []
        for target in targets:
            is_visible = target in visible
            for cell in previous:
                if cell == pos or p.tiles[cell]["terrain"] in {5, 7, 8, 10, 21, 22, 31, 37, 38} \
                        or p.loot.get(cell, {}).get("for_sale") or p.tiles[cell].get("plant"):
                    continue
                route = p.route(previous, cell)
                if len(route) > 13:
                    continue
                near = distance(cell, target["cell"], width) <= 1
                firing = False
                if is_visible and can_zap:
                    hypothetical = dict(state, hero=dict(state["hero"], cell=cell))
                    firing = p.shot_clear(hypothetical, target["cell"])
                if not near and not firing:
                    continue
                step = route[1]
                if sum(distance(step, e["cell"], width) <= 1 for e in threats) > 1:
                    continue
                exposure = sum(distance(c, e["cell"], width) <= 1 for c in route[1:] for e in threats)
                choices.append((len(route) + 2*exposure, len(route), step, is_visible))
        if choices:
            _, _, step, visible_target = min(choices)
            p.necro_moves += 1
            return p.cell(step, "necro: bypass minion toward summoner" if visible_target
                          else "necro: investigate last visible summoner position")

    # If the caster cannot be reached, withdraw around cover so it loses sight
    # of the hero instead of continuously healing/empowering its minion.
    if minions and p.necro_moves < 24:
        steps = [c for c in neighbors(pos, width, height) if p.walkable(c, occupied)
                 and p.tiles[c]["terrain"] not in {5, 7, 8, 10, 21, 22, 31, 37, 38}
                 and not p.loot.get(c, {}).get("for_sale") and not p.tiles[c].get("plant")
                 and all(distance(c, e["cell"], width) > 1 for e in threats)]
        if steps:
            def score(cell):
                cover = any(not line_clear(cell, t["cell"], width, p.tiles) for t in targets)
                return cover, min(distance(cell, e["cell"], width) for e in minions), -p.visits[cell]
            p.necro_moves += 1
            return p.cell(max(steps, key=score), "necro: break contact with supported skeleton")
    # Sometimes the summon is the only blocker. Permit a small number of
    # attacks to open an escape, never dozens of stationary resource trades.
    if minions and p.necro_blocker_attacks < 4:
        target = min(minions, key=lambda e: distance(pos, e["cell"], width))
        attack = p.best_attack(state, target)
        if attack:
            p.necro_blocker_attacks += 1
            attack.reason = "necro: bounded attack on blocking summon"
            return attack
    if minions:
        raise NecromancerStalemate("Necromancer summon: no reachable caster, safe withdrawal, or usable escape; refusing indefinite attrition")
    return None
