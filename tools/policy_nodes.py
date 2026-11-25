"""Reactive policy leaves. The priority tree is declared in policy_tree.py.

Leaves never submit inputs. They may update local intent, but only return one
decision; the runner owns execution and rejection rollback.
"""
try:
    from .policy_decision import Finished, Intent
    from .policy_geometry import distance, neighbors, line_clear
    from .combat_items import equipment_upgrade, known_cursed, stats
    from .combat_positioning import (rinse_ooze, close_zapper, skeleton_spacing,
                                    invisible_withdrawal, CombatPositioningBlocked,
                                    SkeletonSpacingBlocked)
    from .boss_strategies import BossEscapeBlocked
    from .shop_tactics import visit_entrance_shop, choose_shop, ShopVisitBlocked
    from .resource_tactics import choose_well, choose_meat, choose_enchantment
    from .consumable_tactics import choose_consumable, identify_retry_allowed
    from .necromancer_tactics import choose_necromancer, NecromancerStalemate
    from .wand_tactics import choose_wand_probe
    from .seed_tactics import choose_seed
    from .upgrade_tactics import choose_upgrade
except ImportError:
    from policy_decision import Finished, Intent
    from policy_geometry import distance, neighbors, line_clear
    from combat_items import equipment_upgrade, known_cursed, stats
    from combat_positioning import (rinse_ooze, close_zapper, skeleton_spacing,
                                   invisible_withdrawal, CombatPositioningBlocked,
                                   SkeletonSpacingBlocked)
    from boss_strategies import BossEscapeBlocked
    from shop_tactics import visit_entrance_shop, choose_shop, ShopVisitBlocked
    from resource_tactics import choose_well, choose_meat, choose_enchantment
    from consumable_tactics import choose_consumable, identify_retry_allowed
    from necromancer_tactics import choose_necromancer, NecromancerStalemate
    from wand_tactics import choose_wand_probe
    from seed_tactics import choose_seed
    from upgrade_tactics import choose_upgrade


def rinse(c):
    return rinse_ooze(c.policy, c.state, c.enemies, distance, neighbors)


def rooted_recovery(c):
    try:
        from .rooted_recovery import choose
    except ImportError:
        from rooted_recovery import choose
    return choose(c)


def vertigo_response(c):
    try:
        from .vertigo_tactics import choose
    except ImportError:
        from vertigo_tactics import choose
    return choose(c.policy, c.state)


def toxic_gas(c):
    try:
        from .toxic_escape import escape
    except ImportError:
        from toxic_escape import escape
    return escape(c.policy, c.state)


def burning(c):
    # Burning recovery precedes generic room hazards, but not a boss telegraph.
    if getattr(c.policy,'wood_burn_plan',None) and c.pos not in c.danger:
        try:
            from .wooden_barrier import recover
        except ImportError:
            from wooden_barrier import recover
        wood=recover(c.policy,c.state,c.enemies)
        if wood:return wood
    if "burning" in c.buffs and c.pos not in c.danger:
        return rinse(c)


def ordinary_flight_recovery(c):
    if getattr(getattr(c.policy, "profile", None), "name", None) != "simple-bot":
        return None
    try:
        from .simple_flight import recover
    except ImportError:
        from simple_flight import recover
    return recover(c.policy, c.state, c.enemies)


def boss_escape(c):
    if not c.boss:
        return None
    try:
        return c.boss.evade(c.policy, c.state, c.enemies, distance, neighbors)
    except BossEscapeBlocked as error:
        transport = c.policy.emergency_transport(c.state, c.enemies)
        if transport:
            return transport
        c.policy.stop_no_safe_action(str(error))


def warned_cell(c):
    if c.pos in c.danger:
        return c.policy.retreat(c.state, c.enemies, c.danger)


def harmful_effect(c):
    if c.policy.effects_block_movement(c.policy.tiles[c.pos]):
        return c.policy.retreat(c.state, c.enemies, danger={c.pos})


def dm100_door_escape(c):
    if c.boss or not getattr(c.policy,'unit_strategies_enabled',False):return None
    # This early leaf can attack adjacent casters as well as move. Do not
    # preempt the shared low-HP invisibility withdrawal with an attack or lure.
    # Healing and the existing bounded withdrawal retain their normal order.
    if c.hp<.5 and any(b in c.buffs for b in ('invisib','cloaked')):return None
    try:
        from .dm100_escape import choose,exposed_memory
        from .ranged_tactics import choose as ranged
    except ImportError:
        from dm100_escape import choose,exposed_memory
        from ranged_tactics import choose as ranged
    present=any(e['name'].lower()=='dm-100' and not e.get('sleeping') for e in c.enemies)
    if not present and not exposed_memory(c.policy,c.state) and not (
            c.policy.ranged_plan and c.policy.ranged_plan.get('name')=='dm-100'):return None
    if c.hp<.3 and present:
        rescue=critical_transport(c) or healing(c)
        if rescue:return rescue
    # Retain the established wall-backed bank flow without allowing its damage
    # fallback to preempt immediate flight toward a newly visible doorway.
    plan=c.policy.ranged_plan
    if plan and plan.get('name')=='dm-100' and plan.get('mode')=='cover':
        return ranged(c.policy,c.state,c.enemies,escape_only=True)
    action=choose(c.policy,c.state,c.enemies)
    if action:return action
    if not present and exposed_memory(c.policy,c.state):
        c.policy.stop_no_safe_action('Recent DM-100 lightning lane remains unverified; no ordinary recovery wait or guessed blind attack')
    return None


def well(c):
    return choose_well(c.policy, c.state, c.enemies, distance, neighbors)


def healing(c):
    p = c.policy
    threshold = c.boss.healing_threshold(c.state) if c.boss and c.active else 0.48 if c.active else 0.3
    if c.hp >= threshold:
        return None
    heal = next((i for i in c.inventory if "potion of healing" in i["name"].lower()
                 and "DRINK" in i["actions"] and p.item_action_allowed(i, "DRINK")), None)
    water = next((i for i in c.inventory if "waterskin" in i["name"].lower() and "DRINK" in i["actions"]), None)
    if heal:
        return p.use(heal, "DRINK", "survival: healing potion")
    if water:
        return p.use(water, "DRINK", "survival: drink dew")


def critical_transport(c):
    p = c.policy
    if not getattr(p,'unit_strategies_enabled',False) or not c.active or c.boss:
        return None
    if c.hp < .3 or (c.hp < .5 and p.critical_retreats >= 3 and not p.charged_magic(c.state)):
        return p.emergency_transport(c.state,c.enemies)


def corruption(c):
    try:
        from .corruption_tactics import choose
    except ImportError:
        from corruption_tactics import choose
    return choose(c.policy,c.state,c.enemies)


def cleanse(c):
    equipped = any(i.get("equipped") and known_cursed(i) for i in c.inventory)
    p = c.policy
    tile = p.tiles.get(c.pos, {})
    # Wands do not need equipping to be useful. Restore a publicly proven
    # cursed spare during quiet preparation, never by spending a combat turn
    # or treating the read/menu selection as evidence of successful cleansing.
    spare = not equipped and not c.enemies and not getattr(p, "recent_threats", {}) \
        and not getattr(p, "unseen_damage_turns", 0) and not c.danger \
        and c.state.get("status") == "ready" and not c.state.get("modal") \
        and tile.get("visible") and tile.get("observed") \
        and not tile.get("effects") and not tile.get("trap") and not tile.get("plant") \
        and not any(b in c.buffs for b in ("blind", "burn", "poison", "bleed", "ooze", "paral", "vertigo")) \
        and any(i["name"].lower().startswith("wand of ") and i.get("curse_known")
                and known_cursed(i) and "ZAP" in i.get("actions", []) for i in c.inventory)
    if equipped or spare:
        scroll = next((i for i in c.inventory if "scroll of remove curse" in i["name"].lower()
                       and "READ" in i.get("actions", [])), None)
        if scroll:
            c.policy.menu_plan = "discover-scroll"
            c.policy.consumable_menu_bags = set()
            return c.policy.use(scroll, "READ", "survival: cleanse cursed equipped item first" if equipped
                                else "prepare: cleanse known cursed spare wand")


def invisible_escape(c):
    try:
        return invisible_withdrawal(c.policy, c.state, c.enemies, distance, line_clear)
    except CombatPositioningBlocked as error:
        c.policy.stop_tactical("invisible-stall",str(error))


def starvation(c):
    if getattr(c.policy,'unit_strategies_enabled',False) and not c.enemies \
            and any(t in c.buffs for t in ('hungry','starving')):
        try:
            from .hungry_cooking import choose
        except ImportError:
            from hungry_cooking import choose
        cooked=choose(c.policy,c.state,c.enemies)
        if cooked:return cooked
    food = c.policy.food_items(c.state)
    if not c.active and "starving" in c.buffs and food:
        c.policy.rests = 0
        return c.policy.use(food[0], "EAT", "survival: eat while starving")


def priority_resource(c):
    if getattr(c.policy,'unit_strategies_enabled',False):
        try:
            from .priority_resources import choose
        except ImportError:
            from priority_resources import choose
        return choose(c.policy,c.state,c.enemies)


def ghost_reward(c):
    if getattr(c.policy,'unit_strategies_enabled',False) and c.policy.ghost_quest.get('stage') in {'reward','collect_dropped'}:
        try:
            from .ghost_quest import visit_ghost
        except ImportError:
            from ghost_quest import visit_ghost
        return visit_ghost(c.policy,c.state,c.enemies,distance,neighbors)


def piranha_supplies(c):
    if c.active:return None
    try:
        from .piranha_tactics import choose
    except ImportError:
        from piranha_tactics import choose
    return choose(c.policy,c.state,c.enemies)


def exhausted_room_descent(c):
    try:
        from .room_supplies import descend
    except ImportError:
        from room_supplies import descend
    return descend(c.policy,c.state,c.enemies)


def wandmaker(c):
    if not hasattr(c.policy,'wandmaker_quest'):return None
    try:
        from .wandmaker_quest import choose
    except ImportError:
        from wandmaker_quest import choose
    return choose(c.policy,c.state,c.enemies)


def blandfruit(c):
    if not hasattr(c.policy,'wandmaker_quest'):return None
    try:
        from .blandfruit_tactics import choose
    except ImportError:
        from blandfruit_tactics import choose
    return choose(c.policy,c.state,c.enemies)


def peaceful_preparation(c):
    if c.active:
        return None
    p, state = c.policy, c.state
    if getattr(p,'unit_strategies_enabled',False):
        try:
            from .inventory_tactics import choose
        except ImportError:
            from inventory_tactics import choose
        cleanup=choose(p,state,c.enemies)
        if cleanup:return cleanup
    previous = p.paths(state, {e["cell"] for e in c.enemies})
    p.exhausted.add(c.pos)
    try:
        visit = visit_entrance_shop(p, state, previous, neighbors)
    except ShopVisitBlocked as error:
        p.stop_gameplay(str(error))
    if visit:
        return visit
    shopping = choose_shop(p, state, previous)
    if shopping:
        return shopping
    if p.engine == "legacy" and not c.enemies and p.combat_approach_target is not None:
        target = p.combat_approach_target
        if target in p.enemy_sightings and p.combat_approach_steps < 12:
            approach = p.toward(state, target, "explore: continue last-seen combat approach", previous,
                                intent=Intent.EXPLORE)
            if approach and approach.action["cell"] != c.pos:
                p.combat_approach_steps += 1
                return approach
        p.combat_approach_target = None
        p.combat_approach_steps = 0
    equipment = equipment_upgrade(state)
    if equipment:
        return p.use(equipment, "EQUIP", "prepare: stronger usable equipment")
    enchant = choose_enchantment(p, state)
    if enchant:
        return enchant
    meat = choose_meat(p, state, c.enemies, distance, neighbors)
    if meat:
        return meat
    if p.engine == "planner":
        recovery = p.planner.recover(p, state, c.enemies)
        if recovery:
            return recovery
        return p.planner.continue_navigation(p, state, c.enemies)


def emergency_consumable(c):
    if c.active and c.hp < 0.35 and not c.danger:
        return consumable(c)


def select_combat_mode(c):
    c.planning_combat = c.policy.engine == "planner" and not c.boss and c.policy.planner.eligible(c.state, c.enemies)


def funnel(c):
    if getattr(c.policy,'unit_strategies_enabled',False):return None
    if c.policy.necro_escape_target is None and not c.planning_combat:
        return c.policy.single_enemy_position(c.state, c.enemies)


def necromancer(c):
    if getattr(c.policy,'unit_strategies_enabled',False):return None
    try:
        return choose_necromancer(c.policy, c.state, c.enemies, distance, neighbors, line_clear)
    except NecromancerStalemate as error:
        c.policy.stop_gameplay(str(error))


def skeleton(c):
    try:
        return skeleton_spacing(c.policy, c.state, c.enemies, distance, neighbors)
    except SkeletonSpacingBlocked as error:
        c.policy.stop_no_safe_action(str(error))


def zapper(c):
    if getattr(c.policy,'unit_strategies_enabled',False):return None
    if not c.planning_combat:
        return close_zapper(c.policy, c.state, c.enemies, distance)


def consumable(c):
    return choose_consumable(c.policy, c.state, c.enemies, distance, neighbors)


def critical_withdrawal(c):
    p = c.policy
    close = [e for e in c.active if distance(c.pos, e["cell"], c.width) == 1]
    finisher = None
    if not c.planning_combat and len(close) == 1 and 0.25 <= c.hp < 0.5 and not p.charged_magic(c.state) \
            and close[0]["name"].lower() in {"marsupial rat", "albino rat", "gnoll scout", "slime", "caustic slime", "swarm of flies"}:
        bar = close[0].get("health_bar")
        key = ("critical-finisher", p.depth, close[0]["cell"], close[0]["name"])
        if bar and bar[1] > 0 and bar[0] / bar[1] <= 0.15 and p.snake_melee_attempts[key] < 2:
            finisher = close[0]
            p.snake_melee_attempts[key] += 1
    if not c.planning_combat and c.active and c.hp < 0.5 and not p.charged_magic(c.state) and not finisher:
        escape = p.retreat(c.state, c.enemies)
        if escape:
            if p.critical_retreats >= 12:
                p.stop_no_safe_action("Critical-health withdrawal exhausted its budget without recovery or usable magic")
            p.critical_retreats += 1
            escape.reason = "combat: retreat at low health with exhausted magic"
            return escape
    else:
        p.critical_retreats = 0


def wand_probe(c):
    return choose_wand_probe(c.policy, c.state, c.enemies, distance, neighbors)


def seed(c):
    if getattr(c.policy,'unit_strategies_enabled',False):return None
    # A two-input setup is unsafe while a charged boss attack is advertised.
    if not (c.boss and c.danger):
        return choose_seed(c.policy, c.state, c.enemies, distance, neighbors)


def seed_preparation(c):
    if getattr(c.policy,'unit_strategies_enabled',False) and c.active and not c.boss:
        if c.policy.ambush_plan or c.policy.multi_door_plan or c.policy.ranged_plan:return None
        return choose_seed(c.policy,c.state,c.enemies,distance,neighbors)


def tactical(c):
    if c.planning_combat and not any(t.get("available", 0) > 0 for t in c.hero.get("talents", [])):
        return c.policy.planner.tactical(c.policy, c.state, c.enemies, distance, neighbors, line_clear)


def continue_ambush(c):
    if not c.enemies and c.policy.ambush_plan:
        return c.policy.door_ambush(c.state, c.enemies, [], c.policy.ambush_plan["kind"])


def select_engagement(c):
    # Sleepers behind cover must not preempt recovery or a loot route.
    c.engage = c.active
    if not c.active and (c.hp > 0.8 or ("starving" in c.buffs and c.hp >= 0.5)):
        magic = c.policy.charged_magic(c.state)
        c.engage = [e for e in c.enemies if distance(c.pos, e["cell"], c.width) == 1
                    or (magic and c.policy.shot_clear(c.state, e["cell"]))]


def cursed_combat(c):
    p = c.policy
    if c.engage and any(i.get("equipped") and known_cursed(i) and stats(i)
                        and stats(i)[0] == "melee" for i in c.inventory):
        enemy = min(c.engage, key=lambda e: distance(c.pos, e["cell"], c.width))
        attack = p.best_attack(c.state, enemy)
        if attack:
            return attack
        escape = p.retreat(c.state, c.enemies)
        if escape:
            return escape
        p.stop_no_safe_action("Known cursed melee weapon equipped; no safe alternative attack or retreat")


def wraith(c):
    if getattr(c.policy,'unit_strategies_enabled',False):return None
    if any(e["name"].lower() in {"wraith", "tormented spirit"} for e in c.engage):
        return c.policy.wraith_combat(c.state, c.enemies, c.buffs)


def snake(c):
    if getattr(c.policy,'unit_strategies_enabled',False):return None
    nearest = min((distance(c.pos, e["cell"], c.width) for e in c.engage), default=99)
    if any(e["name"].lower() == "sewer snake" and distance(c.pos, e["cell"], c.width) <= nearest for e in c.engage):
        return c.policy.snake_combat(c.state, c.enemies, c.buffs)


def talent(c):
    for name in c.policy.talent_priority(c.state):
        available = next((t for t in c.hero.get("talents", []) if t["name"].lower() == name
                          and t["available"] > 0 and t["points"] < t["max_points"]), None)
        if available:
            return c.policy.decision({"type": "talent", "name": available["name"]}, f"talent: {name}")


def require_staff(c):
    if c.policy.staff(c.state) is None:
        c.policy.stop_gameplay("Mage staff missing")


def boss_combat(c):
    if c.boss:
        preparation = c.boss.prepare(c.policy, c.state, c.enemies)
        if preparation:
            return preparation
        return c.boss.choose(c.policy, c.state, c.engage, distance, neighbors)


def ordinary_combat(c):
    if not c.engage:
        return None
    p, state = c.policy, c.state
    try:
        from .incoming_damage import priority
    except ImportError:
        from incoming_damage import priority

    def visible_health(enemy):
        bar = enemy.get("health_bar")
        return bar[0] / bar[1] if bar and bar[1] > 0 else 1

    enemy = min(c.engage, key=lambda e: (-priority(p,state,c.active,e),distance(c.pos, e["cell"], c.width),
                                        e["name"].lower() != "goo", visible_health(e)))
    if getattr(p,'unit_strategies_enabled',False):
        selected=p.planner.report.get('unit_target')
        enemy=next((e for e in c.engage if e['cell']==selected),enemy)
        if selected is None:
            profile=p.unit_strategies.profile(enemy)
            p.planner.report['unit_strategy_selection']={'name':enemy['name'],'cell':enemy['cell'],
                'strategy':profile.strategy,'movement':profile.movement,'status':'shared attack on admitted sleeper'}
    dist = distance(c.pos, enemy["cell"], c.width)
    is_goo = enemy["name"].lower() == "goo"
    bar = enemy.get("health_bar")
    weak = bar and bar[1] > 0 and bar[0] / bar[1] < 0.22
    crowded = sum(distance(c.pos, e["cell"], c.width) <= 2 for e in c.active) > 1
    charges = (p.staff(state).get("status") or "").split("/")
    # Do not wait for an ordinary enemy to approach while other awake enemies
    # are converging too. A distant second front is missed by the local radius.
    # Lone-enemy conservation and the separate queued-snake reserve remain.
    reserve = (not enemy.get("sleeping") and len(c.active) <= 1 and not crowded and charges[0].isdigit() and int(charges[0]) <= 2 and c.hp > 0.6
               and enemy["name"].lower() in {"marsupial rat", "albino rat", "gnoll scout"})
    adjacent = sum(distance(c.pos, e["cell"], c.width) == 1 for e in c.active)
    queued = [e for e in c.active if e["name"].lower() == "sewer snake" and distance(c.pos, e["cell"], c.width) > 1]
    occupied = {e["cell"] for e in c.enemies}
    flank = any(p.walkable(cell, occupied) and distance(cell, snake["cell"], c.width) <= 1
                for cell in neighbors(c.pos, c.width, state["map"]["height"]) for snake in queued)
    magic_budget = sum(int((i.get("status") or "0").split("/")[0])
                       if (i.get("status") or "").split("/")[0].isdigit() else 1 for i in p.charged_magic(state))
    reserve_for_snake = (dist == 1 and adjacent == 1 and c.hp >= 0.65
                         and enemy["name"].lower() in {"marsupial rat", "albino rat", "gnoll scout"}
                         and bar and bar[1] > 0 and bar[0] / bar[1] <= 0.65
                         and queued and not flank and 0 < magic_budget <= 2)
    blocker_key = ("blocker", p.depth, enemy["cell"])
    emergency_reserve = (dist == 1 and c.hp >= 0.35 and magic_budget == 1 and queued and not flank
                         and enemy["name"].lower() in {"marsupial rat", "albino rat", "gnoll scout"}
                         and bar and bar[1] > 0 and bar[0] / bar[1] <= 0.2 and p.snake_melee_attempts[blocker_key] < 2)
    if emergency_reserve and not reserve_for_snake:
        p.snake_melee_attempts[blocker_key] += 1
        reserve_for_snake = True
    attack = p.best_attack(state, enemy, reserve=reserve or (weak and dist == 1 and not is_goo and not crowded),
                           reserve_magic=reserve_for_snake)
    if attack:
        if reserve_for_snake and attack.action["type"] == "cell":
            attack.reason = "combat: preserve magic for queued snake"
        return attack
    if enemy.get("sleeping"):
        p.planner.report["sleeper_engagement"] = {
            "cell": enemy["cell"], "status": "no admitted attack; resume ordinary work, not a lure wait"}
        return None
    if getattr(p,'unit_strategies_enabled',False) and any(distance(c.pos,e['cell'],c.width)==1 for e in c.active):
        p.stop_tactical('attack-position','Adjacent observed attacker while selected target has no admitted attack; recover/reselect instead of passive recharge')
    key = (p.depth, c.pos, enemy["cell"])
    if not p.attack_approach_allowed(state,enemy):
        p.stop_tactical('attack-position','No non-splitting fly attack available; re-evaluate pressure instead of walking into melee')
    p.combat_waits[key] += 1
    if p.combat_waits[key] > 12:
        p.stop_gameplay("Ordinary combat stalled without an attack or reachable approach; refusing indefinite waiting")
    if p.combat_waits[key] > 2:
        approach = p.toward(state, enemy["cell"], "combat: improve line of fire", intent=Intent.APPROACH)
        if approach:
            if p.combat_approach_target != enemy["cell"]:
                p.combat_approach_steps = 0
            p.combat_approach_target = enemy["cell"]
            p.combat_approach_steps += 1
            return approach
    if getattr(p,'unit_strategies_enabled',False):
        try:
            from .ranged_tactics import exposed_wait
        except ImportError:
            from ranged_tactics import exposed_wait
        if exposed_wait(p,state,c.enemies):p.stop_no_safe_action('Ordinary combat cannot wait for recharge in a ranged firing lane')
    return p.decision({"type": "wait"}, "combat: wait for approach/recharge")


def unit_engagement(c):
    if not getattr(c.policy,'unit_strategies_enabled',False):return None
    try:
        from .unit_strategies import choose
    except ImportError:
        from unit_strategies import choose
    return choose(c.policy,c.state,c.enemies)


def ranged_survival(c):
    if c.boss or not getattr(c.policy,'unit_strategies_enabled',False):return None
    try:
        from .ranged_tactics import choose
    except ImportError:
        from ranged_tactics import choose
    return choose(c.policy,c.state,c.enemies)


def multi_threat_retreat(c):
    if not getattr(c.policy,'unit_strategies_enabled',False):return None
    try:
        from .multi_enemy_tactics import choose
    except ImportError:
        from multi_enemy_tactics import choose
    return choose(c.policy,c.state,c.enemies)


def preparation_and_recovery(c):
    if c.active:
        return None
    p, state = c.policy, c.state
    try:
        from .ranged_tactics import exposed_wait
    except ImportError:
        from ranged_tactics import exposed_wait
    if exposed_wait(p,state,c.enemies):return None
    strength = next((i for i in c.inventory if "potion of strength" in i["name"].lower() and "DRINK" in i["actions"]), None)
    if strength:
        return p.use(strength, "DRINK", "prepare: strength potion")
    upgrade = next((i for i in c.inventory if "scroll of upgrade" in i["name"].lower() and "READ" in i["actions"]), None)
    # READ is still advertised while blinded, but fails without spending time.
    # Defer allocation intent as well as the input until reading is possible.
    allocation = choose_upgrade(state) if upgrade and "blind" not in c.buffs else None
    if allocation:
        p.menu_plan = "upgrade-select"
        p.upgrade_target = allocation[0]["name"]
        return p.use(upgrade, "READ", "prepare: upgrade allocation: " + allocation[1])
    identify = next((i for i in c.inventory if "scroll of identify" in i["name"].lower() and "READ" in i["actions"]), None)
    unknown_potions = [i for i in c.inventory if "potion" in i["name"].lower() and "potion of " not in i["name"].lower()]
    if identify and unknown_potions and identify_retry_allowed(p, state):
        p.menu_plan = "discover-scroll"
        p.consumable_menu_bags = set()
        return p.use(identify, "READ", "prepare: identify a potion")
    budget = p.recovery_limit(state, "hungry" in c.buffs)
    if p.engine == "legacy" and c.hp < p.recovery_target(state) and "starving" not in c.buffs and "locked" not in c.buffs \
            and not any(effect in c.buffs for effect in ("burning","poison","bleed","ooze")) \
            and ("hungry" not in c.buffs or p.food_items(state)
                 or p.food_recovery_until>getattr(p,"floor_recovery",0)) and p.rests < budget:
        p.rests += 1
        return p.decision({"type": "wait"}, "recover: natural healing", intent=Intent.RECOVER)


def exploration(c):
    c.policy.rests = 0
    return c.policy.explore(c.state, c.enemies)
