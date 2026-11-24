"""Observation memory, navigation/combat primitives, and public policy hooks.

Arbitration lives in policy_tree.py, leaves in policy_nodes.py, UI protocols in
policy_interaction.py, and execution in policy_runner.py. This module never
launches the game or sends inputs.
"""

from collections import deque
import json

try:
    from .policy_decision import Decision, Finished, Intent, TacticalBlocked, NoSafeAction,GameplayBlocked
    from .policy_memory import PolicyMemory, owns_memory
    from .policy_runtime import Context
    from .policy_geometry import distance, neighbors, line_clear
    from .policy_tree import POLICY
    from .policy_interaction import menu as choose_menu
    from .special_rooms import ROOM_ACTORS, CONTAINERS, assess, container_name
    from .combat_items import known_cursed, magic_score, physical_score, stats
    from .hidden_doors import search_coverage, wall_scores, corridor_ends
    from .boss_strategies import create_strategies, strategy_for
    from .wand_tactics import observe_wand_cast
    from .shop_tactics import choose_shop, visit_entrance_shop, ShopVisitBlocked
    from .chest_tactics import eligible_chests
    from .necromancer_tactics import CASTERS
    from .consumable_tactics import learn_sources
    from .combat_positioning import ZAPPERS
    from .resource_tactics import clear_blocking_plant, recheck_hazards
    from .decision_engine import DecisionEngine
    from .mimic_tactics import suspicious_container
    from .combat_observation import compare_options
except ImportError:
    from policy_decision import Decision, Finished, Intent, TacticalBlocked, NoSafeAction,GameplayBlocked
    from policy_memory import PolicyMemory, owns_memory
    from policy_runtime import Context
    from policy_geometry import distance, neighbors, line_clear
    from policy_tree import POLICY
    from policy_interaction import menu as choose_menu
    from special_rooms import ROOM_ACTORS, CONTAINERS, assess, container_name
    from combat_items import known_cursed, magic_score, physical_score, stats
    from hidden_doors import search_coverage, wall_scores, corridor_ends
    from boss_strategies import create_strategies, strategy_for
    from wand_tactics import observe_wand_cast
    from shop_tactics import choose_shop, visit_entrance_shop, ShopVisitBlocked
    from chest_tactics import eligible_chests
    from necromancer_tactics import CASTERS
    from consumable_tactics import learn_sources
    from combat_positioning import ZAPPERS
    from resource_tactics import clear_blocking_plant, recheck_hazards
    from decision_engine import DecisionEngine
    from mimic_tactics import suspicious_container
    from combat_observation import compare_options


FLOOR = {1, 2, 3, 5, 6, 7, 8, 9, 11, 14, 15, 19, 20, 22, 29, 30, 32, 37}
HARMFUL_PLANTS = {"firebloom", "icecap", "sorrowmoss", "blindweed", "stormvine", "fadeleaf", "rotberry"}
AVOID_CONTAINERS = ("crystal chest", "tomb", "skeleton", "sacrificial", "statue")
DOOR_KEYS = {10: "iron", 31: "crystal", 38: "skeleton", 21: "worn"}
TRANSITIONS = {7, 8, 22, 37}
WRAITHS = {"wraith", "tormented spirit"}
ENEMIES = {
    "marsupial rat", "albino rat", "sewer snake", "gnoll scout", "sewer crab", "hermit crab",
    "swarm of flies", "slime", "caustic slime", "fetid rat", "great crab",
    "gnoll trickster", "wraith", "tormented spirit", "mimic", "golden mimic", "crystal mimic", "goo",
    "skeleton", "necromancer's skeleton", "crazy thief", "crazy bandit", "prison guard", "dm-100",
    "necromancer", "spectral necromancer", "tengu", "vampire bat", "gnoll brute", "armored brute",
    "gnoll shaman", "cave spinner", "dm-200", "dm-201", "dm-300", "dwarven ghoul", "dwarf monk",
    "senior monk", "dwarf warlock", "golem", "fire elemental", "newborn fire elemental", "frost elemental",
    "shock elemental", "chaos elemental", "king of dwarves", "succubus", "evil eye", "ripper demon",
    "scorpio", "acidic scorpio", "demon spawner", "yog-dzewa", "god's larva", "burning fist",
    "soiled fist", "rotting fist", "rusted fist", "bright fist", "dark fist", "ebony mimic", "golden bee",
    "greater elemental", "modified dm-100", "modified dm-200", "dwarven skeleton", "captured shaman",
    "crystal guardian", "crystal spire", "crystal wisp", "fungal core", "fungal sentry", "fungal spinner",
    "gnoll exile", "gnoll geomancer", "gnoll guard", "gnoll sapper",
}
TALENTS = ["backup barrier", "empowering meal", "lingering magic", "scholar's intuition", "energizing meal",
           "energizing upgrade", "wand preservation"]


def is_container(obj):
    name = obj["name"].lower()
    living_skeleton = name == "skeleton" and (not obj.get("description") or obj.get("health_bar") is not None
        or obj.get("description", "").lower().startswith("skeletons are composed"))
    return "top_item" in obj or (name in CONTAINERS and not living_skeleton)


def is_passive(obj):
    return obj["name"].lower() == "gnoll exile" and "isn't moving to attack" in obj.get("description", "").lower()


def is_hostile(obj):
    corrupted=any('corrupt' in str(icon).lower() for icon in obj.get('status_icons',[]))
    return obj["name"].lower() in ENEMIES and not corrupted and not is_passive(obj) and not is_container(obj)


class NavigationLoopGuard:
    """Stop repeated navigation without map, loot, key, or coverage progress.

    Visibility flicker, health changes, and passive wand recharging do not count
    as exploration progress: those previously hid retreat/loot oscillations.
    """

    def __init__(self, repetitions=6, window=64):
        self.repetitions = repetitions
        self.history = deque(maxlen=window)
        self.progress = None
        self.visited = set()

    def check(self, state, decision):
        if state.get("scene") != "GameScene" or "map" not in state:
            self.history.clear()
            return
        hero = state["hero"]
        try:
            from .policy_geometry import navigation_terrain
        except ImportError:
            from policy_geometry import navigation_terrain
        progress = (
            state["depth"],
            tuple(sorted((t["cell"], navigation_terrain(t["terrain"]), t.get("trap"), t.get("plant")) for t in state["map"]["cells"])),
            tuple(sorted((i["name"], i.get("quantity", 1), i.get("equipped", False)) for i in state["inventory"])),
            tuple(sorted((k["name"], k["depth"], k["quantity"]) for k in state.get("keys", []))),
            hero.get("level"), hero.get("gold"), hero.get("strength"),
            tuple((t["name"], t["points"]) for t in hero.get("talents", [])),
        )
        position = state["depth"], state.get("branch", 0), hero["cell"]
        if progress != self.progress or position not in self.visited:
            self.history.clear()
            self.progress = progress
        self.visited.add(position)
        if decision.action.get("type") != "cell" or not decision.navigation:
            return
        signature = position, decision.action["cell"], decision.intent
        self.history.append(signature)
        if self.history.count(signature) >= self.repetitions:
            raise TacticalBlocked("navigation-loop",f"No-progress navigation loop at {position}: {decision.reason} -> {decision.action['cell']}")


class MenuLoopGuard:
    """Bound menu/read/cancel cycles even if every individual action is legal."""

    def __init__(self, repetitions=8, window=64):
        self.repetitions = repetitions
        self.history = deque(maxlen=window)
        self.progress = None

    def check(self, state, decision):
        hero = state.get("hero", {})
        progress = (state.get("scene"), state.get("depth"), hero.get("cell"), hero.get("hp"), hero.get("gold"),
                    tuple(sorted((i["name"], i.get("quantity", 1), bool(i.get("identified"))) for i in state.get("inventory", []))))
        if progress != self.progress:
            self.history.clear()
            self.progress = progress
        kind = decision.action.get("type")
        if kind not in {"button", "back"} and not (kind == "item" and decision.action.get("action") in {"READ", "EAT"}):
            return
        semantic = kind
        if kind == "button":
            semantic = next((b["label"] for b in state.get("ui", {}).get("buttons", [])
                             if b["id"] == decision.action.get("id")), decision.action.get("id"))
        signature = (state.get("status"), tuple(state.get("ui", {}).get("texts", [])), semantic, decision.intent)
        self.history.append(signature)
        if self.history.count(signature) >= self.repetitions:
            raise Finished("blocked", f"No-progress menu loop: {decision.reason}; refusing repeated read/select/cancel actions")


@owns_memory
class SurvivalPolicy:
    """Reactive Mage policy with observation-only navigation and tactical hooks."""

    def __init__(self, goal="survival", engine="legacy"):
        if engine not in {"legacy", "planner"}:
            raise ValueError("engine must be legacy or planner")
        self.engine = engine
        self.planner = DecisionEngine()
        self.goal = goal
        self.memory = PolicyMemory()
        self.boss_strategies = create_strategies()

    def decision(self, action, reason, *, intent=Intent.OTHER):
        if self.engine == "planner" and "selection" not in self.planner.report:
            self.planner.report.update(selection=reason, arbitration="dedicated controller or safety override")
        result = Decision(action, reason, intent=intent, controller="interaction")
        self.last_decision = result
        return result

    def cell(self, cell, reason, *, intent=Intent.OTHER):
        return self.decision({"type": "cell", "cell": cell}, reason, intent=intent)

    @property
    def deferred_obligations(self):
        """Compatibility report view; stash quantities have one typed owner."""
        return self.legacy_deferred_obligations + self.physical_ledger.deferred_records()

    def use(self, item, action, reason, target=None, *, intent=Intent.OTHER):
        if not self.item_action_allowed(item, action):
            raise Finished("blocked", f"Policy safety veto: {action} {item['name']}")
        self.target = target
        if action == "ZAP" and "wand of " in item["name"].lower() \
                and (not item.get("curse_known") or not (item.get("status") or "?").split("/")[0].isdigit()):
            self.pending_wand_test = {"id": item["id"], "name": item["name"],"curse_known_before":bool(item.get("curse_known"))}
        if action == "ZAP" and not (item.get("status") or "?").split("/")[0].isdigit():
            self.unknown_magic_cooldowns[item["name"]] = 30
        return self.decision({"type": "item", "id": item["id"], "action": action}, reason, intent=intent)

    def item_action_allowed(self, item, action):
        return True

    def challenge_preparation(self, state, enemies):
        return None

    def preparation(self,state,enemies):
        # Compatibility for older subclasses; regular arbitration uses this hook.
        return self.challenge_preparation(state,enemies)

    def talent_priority(self, state):
        return TALENTS

    def combat_override(self, state, enemies):
        return None

    def emergency_transport(self, state, enemies):
        return None

    def recovery_limit(self, state, hungry):
        return 20 if hungry else 80

    def recovery_target(self,state):
        return 0.95 if state["depth"]==5 else 0.8

    def conserve_descent_allowed(self, state):
        return True

    def attack_score(self, state, enemy, kind, value):
        return value

    def target_allowed(self, item, enemy):
        return True

    def harmless_effect(self, description):
        return False

    def effects_block_movement(self, tile):
        return any(not self.harmless_effect(e) for e in tile.get("effects", []))

    def search_limit(self, state, default, optional):
        try:
            from .hidden_doors import secret_search_allowed
        except ImportError:
            from hidden_doors import secret_search_allowed
        if not secret_search_allowed(state,self):return 0
        return default

    def sweep_limit(self, state):
        return 80

    def stop_unsafe(self, reason):
        raise Finished("blocked", reason)

    def stop_gameplay(self,reason, *, kind="unclassified"):
        raise GameplayBlocked(reason,kind)

    def stop_no_safe_action(self,reason):
        raise NoSafeAction(reason)

    def recover_no_safe_action(self,state,blocked):
        return None

    def stop_tactical(self,code,reason):
        raise TacticalBlocked(code,reason)

    def stop_obligation(self,code,reason):
        raise TacticalBlocked("obligation:"+code,reason)

    def recover_tactical_block(self,state,blocked):
        return None

    def descent_counts_as_clear(self):
        return True

    @staticmethod
    def staff(state):
        return next((i for i in state.get("inventory", []) if "staff" in i["name"].lower()
                     and "IMBUE" in i["actions"]), None)

    @staticmethod
    def food_items(state):
        return [i for i in state.get("inventory", []) if "EAT" in i["actions"]
                and not any(raw in i["name"].lower() for raw in ("seed", "mystery meat", "blandfruit"))]

    def update(self, state):
        learn_sources(self, state)
        depth = state["depth"]
        if depth != self.depth:
            self.planner.reset()
            if self.depth is not None and depth == self.depth + 1 and self.last_decision \
                    and self.last_decision.intent == Intent.DESCEND and self.descent_counts_as_clear():
                self.cleared_floors.append(self.depth)
            self.depth = depth
            self.memory.reset_floor(state["hero"]["cell"])
        self.max_depth = max(self.max_depth, depth)
        pos = state["hero"]["cell"]
        self.previous_position = self.last_state["hero"]["cell"] if self.last_state else None
        if self.last_state is None or self.last_state["hero"]["cell"] != pos:
            self.visits[pos] += 1
        if self.last_state and self.last_decision and self.last_decision.tracks_movement:
            action = self.last_decision.action
            if action["type"] == "cell" and pos == self.last_state["hero"]["cell"]:
                before = [(o["cell"], o["name"]) for o in self.last_state.get("objects", [])]
                after = [(o["cell"], o["name"]) for o in state.get("objects", [])]
                # An immobilized move does not test the destination's terrain.
                # Preserve prior real failures; do not globally clear obstacles.
                rooted_move = action["cell"] != pos and any(
                    b.get("name", "").lower() == "rooted"
                    for b in self.last_state["hero"].get("buffs", []))
                if before == after and not rooted_move:
                    self.failed_moves[action["cell"]] += 1
                    if self.failed_moves[action["cell"]] >= 2:
                        refused_dew = action["cell"] == pos and self.last_decision.intent == Intent.LOOT \
                            and any(o.get("cell") == pos and o.get("name", "").lower() == "dewdrop"
                                    and o.get("top_item") for o in state.get("objects", []))
                        pressure = getattr(self, "inventory_pressure", None)
                        refused_full_pack = False
                        if pressure and action["cell"] == pos and self.last_decision.intent == Intent.LOOT \
                                and pressure["depth"] == depth and pressure["cell"] == pos:
                            try:
                                from .inventory_tactics import signature
                            except ImportError:
                                from inventory_tactics import signature
                            refused_full_pack = pressure["signature"] == signature(state) \
                                and any(o.get("cell") == pos and o.get("top_item")
                                        for o in state.get("objects", []))
                        if refused_dew or refused_full_pack:
                            # A refused underfoot pickup is not evidence that
                            # the occupied floor is impassable. Keep the loot
                            # obligation (including progression resources), but
                            # defer the ordinary tour until inventory changes.
                            try:
                                from .room_loot import inventory_context
                            except ImportError:
                                from room_loot import inventory_context
                            self.room_loot_deferred[pos] = inventory_context(state)
                            self.room_loot_plan = None
                            self.failed_moves.pop(pos, None)
                        else:
                            self.blocked.add(action["cell"])
            elif action["type"] == "cell":
                self.failed_moves.pop(action["cell"], None)
        for tile in state["map"]["cells"]:
            remembered = dict(tile)
            old = self.tiles.get(tile["cell"], {})
            # Same-depth boss transitions can replace previously visited floor
            # with a new door. Historical visits must not hide that new route.
            # Ordinary open/close cycles are not a new exploration obligation.
            if old and tile.get("observed") is not False and old["terrain"] != tile["terrain"] \
                    and {old["terrain"], tile["terrain"]} != {5, 6}:
                self.blocked.discard(tile["cell"])
                self.failed_moves.pop(tile["cell"], None)
                if tile["terrain"] == 5:
                    self.changed_door_cells.add(tile["cell"])
                else:
                    self.exhausted.discard(tile["cell"])
                    self.changed_door_cells.discard(tile["cell"])
            if tile["terrain"] != 5 or tile["cell"] == pos:
                self.changed_door_cells.discard(tile["cell"])
            if not tile["visible"] and "effects" not in tile and old.get("effects"):
                remembered["effects"] = old["effects"]
            self.tiles[tile["cell"]] = remembered
            if tile["visible"] and tile.get("name", "").lower() == "distant well":
                self.drop_room_expected_on.add(depth + 1)
        # Receipt for an entrance-scouting step belongs to observation, not to
        # the next peaceful-preparation selection. Loot or safety can preempt
        # that leaf on arrival; forgetting the arrival then sends us back to
        # the same frontier whenever the interrupt moves us away.
        if self.last_state and self.last_state.get("depth") == depth \
                and self.last_state.get("branch", 0) == state.get("branch", 0) \
                and self.last_state["hero"]["cell"] != pos and self.last_decision \
                and self.last_decision.intent == Intent.SHOP \
                and self.last_decision.reason == "shop: reveal entrance chamber doors" \
                and self.last_decision.action == {"type": "cell", "cell": pos} \
                and any(t["cell"] == pos and t.get("visible") and t.get("observed") is not False
                        for t in state["map"]["cells"]):
            # Only suppress a repeated scouting approach. This is not shop
            # visitation, door-check, loot collection, or floor-clear credit.
            self.exhausted.add(pos)
        counts = {kind: sum(k.get("quantity", 0) for k in state.get("keys", [])
                            if k.get("depth") == depth and f"{kind} key" in k.get("name", "").lower())
                  for kind in ("iron", "golden", "crystal", "worn", "skeleton")}
        if state.get("branch", 0) != 0:
            counts = dict.fromkeys(counts, 0)
        if any(counts[kind] > self.keys.get(kind, 0) for kind in counts):
            # A previously keyless attempt must become available after collecting a key.
            for cell in list(self.blocked):
                if self.tiles.get(cell, {}).get("terrain") in DOOR_KEYS or "chest" in self.loot.get(cell, {}).get("name", "").lower():
                    self.blocked.discard(cell)
                    self.failed_moves.pop(cell, None)
        self.keys = counts
        visible = {t["cell"] for t in state["map"]["cells"] if t["visible"]}
        for cell in visible:
            self.loot.pop(cell, None)
            self.room_actors.pop(cell, None)
            self.enemy_sightings.pop(cell, None)
        for obj in state.get("objects", []):
            name = obj["name"].lower()
            if is_container(obj):
                self.loot[obj["cell"]] = obj
            elif name in ROOM_ACTORS:
                self.room_actors[obj["cell"]] = obj
            elif is_hostile(obj):
                self.enemy_sightings[obj["cell"]] = obj
        self.neutral_actor_cells = {o["cell"] for o in state.get("objects", [])
                                    if "top_item" not in o and (is_passive(o) or o["name"].lower() not in CONTAINERS | ENEMIES)}
        self.friendly_passage_cells={o['cell'] for o in state.get('objects',[]) if o['name'].lower()=='mirror image'}
        if not any(o["name"].lower() == "sheep" for o in state.get("objects", [])):
            self.temporary_block_waits = 0
        self.allowed_chests = eligible_chests(self.loot, self.keys)
        self.room_blocked, self.room_skipped, self.room_notes = assess(
            self.tiles, self.room_actors, {c: o for c, o in self.loot.items() if c not in self.allowed_chests},
            state["map"]["width"], state["map"]["height"], harmless_effect=self.harmless_effect,
            rot_quest=getattr(self,'wandmaker_quest',{}).get('variant')=='berry'
            and getattr(self,'wandmaker_quest',{}).get('stage') in {'active','return'})
        try:
            from .summoning_tactics import quarantine
        except ImportError:
            from summoning_tactics import quarantine
        quarantine(self,state)
        self.crystal_doors_seen.update(c for c, tile in self.tiles.items() if tile["terrain"] == 31)
        opened_crystal_choice = (len(self.crystal_doors_seen) >= 2 and any(
            self.tiles[c]["terrain"] != 31 for c in self.crystal_doors_seen))
        self.optional_locks = {c for c in self.crystal_doors_seen if self.tiles[c]["terrain"] == 31}
        if not opened_crystal_choice or self.keys.get("crystal", 0):
            self.optional_locks.clear()
        if self.optional_locks:
            self.room_notes.append({"kind": "crystal-key room", "cells": sorted(self.optional_locks),
                                    "reason": "Remaining special-room branches deferred with no held crystal keys; not counted as explored"})
        if depth in self.drop_room_expected_on:
            candidates = [c for c, tile in self.tiles.items() if tile["terrain"] == 31]
            self.room_notes.append({"kind": "possible one-way drop-room exit", "cells": candidates,
                                    "reason": "A distant well was seen above; its crystal exit key may be inside the room, not available on this floor"})
        # Successful fly kills often drop healing potions, but the policy does NOT
        # identify them through internal item types. Unknown potions stay unknown.
        if depth == 5 and state.get("boss_health_text"):
            self.boss_seen = True
        self.last_state = state

    def walkable(self, cell, occupied=(), ignored_neutrals=(), ignored_plants=()):
        tile = self.tiles.get(cell)
        if tile and tile['terrain']==31 and getattr(self,'reserve_floor_puzzle_supplies',False):
            try:
                from .keyed_rooms import crystal_keys_ready
            except ImportError:
                from keyed_rooms import crystal_keys_ready
            if not crystal_keys_ready(self):return False
        container = container_name(self.loot.get(cell, {}))
        passable = tile is not None and (tile["terrain"] in FLOOR
                    or self.keys.get(DOOR_KEYS.get(tile["terrain"]), 0) > 0)
        return passable and (not tile.get("trap") or tile["terrain"] == 19) \
            and not suspicious_container(self.loot.get(cell, {})) \
            and not self.effects_block_movement(tile) and (cell in ignored_plants or tile.get("plant", "").lower() not in HARMFUL_PLANTS) \
            and (cell in self.allowed_chests or not any(word in container for word in AVOID_CONTAINERS)) \
            and ("locked chest" not in container or cell in self.allowed_chests) \
            and cell not in self.blocked and cell not in self.room_blocked \
            and (cell not in self.neutral_actor_cells or cell in ignored_neutrals or cell in self.friendly_passage_cells) and cell not in occupied

    def paths(self, state, occupied=(), ignored_neutrals=(), ignored_plants=()):
        start, width, height = state["hero"]["cell"], state["map"]["width"], state["map"]["height"]
        previous = {start: None}
        queue = deque([start])
        while queue:
            cell = queue.popleft()
            for adjacent in neighbors(cell, width, height):
                if adjacent not in previous and self.walkable(adjacent, occupied, ignored_neutrals, ignored_plants):
                    previous[adjacent] = cell
                    # Stairs and locks are action destinations, never transit tiles.
                    # A normal click on stairs would change floors prematurely.
                    if self.tiles[adjacent]["terrain"] not in TRANSITIONS | DOOR_KEYS.keys() \
                            and not self.loot.get(adjacent, {}).get("for_sale") \
                            and "chest" not in self.loot.get(adjacent, {}).get("name", "").lower():
                        queue.append(adjacent)
        return previous

    @staticmethod
    def route(previous, target):
        route = []
        while target is not None:
            route.append(target)
            target = previous[target]
        return list(reversed(route))

    def toward(self, state, target, reason, previous=None, *, intent=Intent.OTHER):
        previous = self.paths(state) if previous is None else previous
        if target not in previous:
            return None
        route = self.route(previous, target)
        forbidden=self.navigation_barriers(state,intent)
        if any(c in forbidden for c in route[1:]):
            start=state["hero"]["cell"]
            safe,queue={start:None},deque([start])
            while queue:
                cell=queue.popleft()
                for n in neighbors(cell,state["map"]["width"],state["map"]["height"]):
                    if n in previous and n not in safe and n not in forbidden:
                        safe[n]=cell
                        queue.append(n)
            if target not in safe:return None
            previous=safe
            route=self.route(previous,target)
        if self.engine == "planner":
            self.planner.track_navigation(state, target, reason, intent)
        decision=self.cell(route[1] if len(route) > 1 else target, reason, intent=intent)
        decision.navigation_route=tuple(route)
        return decision

    def navigation_barriers(self,state,intent):
        return set()

    def menu(self, state):
        return choose_menu(self, state)

    def retreat_preferences(self, state, enemies, candidates):
        return {}

    def retreat(self, state, enemies, danger=(), rinse=False):
        pos, width, height = state["hero"]["cell"], state["map"]["width"], state["map"]["height"]
        occupied = {e["cell"] for e in enemies}
        candidates = [c for c in neighbors(pos, width, height) if self.walkable(c, occupied)
                      and self.tiles[c]["terrain"] not in TRANSITIONS | DOOR_KEYS.keys()]
        if enemies and not danger and not rinse:
            try:
                from .retreat_geometry import onward_exit
            except ImportError:
                from retreat_geometry import onward_exit
            candidates=[c for c in candidates if onward_exit(self,state,c,pos,occupied,enemies)]
        zappers = [e for e in enemies if not e.get('sleeping') and (e['name'].lower() in ZAPPERS or
                   getattr(self,'unit_strategies_enabled',False) and 'ranged-attacks' in self.unit_strategies.profile(e).capabilities)]
        if zappers and not danger:
            exposure = lambda c: sum((self.enemy_can_see(state,e,c) if getattr(self,'unit_strategies_enabled',False)
                                     else self.shot_clear(dict(state, hero=dict(state["hero"], cell=c)), e["cell"]))
                                     for e in zappers)
            current = exposure(pos)
            candidates = [c for c in candidates if exposure(c) <= current]
        if not candidates:
            return None
        preference = self.retreat_preferences(state,enemies,candidates) if not danger and not rinse else {}
        def score(cell):
            closest = min((distance(cell, e["cell"], width) for e in enemies), default=5)
            water = self.tiles[cell]["terrain"] == 29
            return (cell not in danger, water if rinse else True, preference.get(cell,0), min(closest, 4),
                    sum(self.walkable(n, occupied) for n in neighbors(cell, width, height)),
                    -self.visits[cell])
        best = max(candidates, key=score)
        if danger or rinse or min(distance(best, e["cell"], width) for e in enemies) > 1:
            return self.cell(best, "combat: evade telegraph" if danger else "combat: rinse ooze" if rinse else "combat: retreat",
                             intent=Intent.OTHER if danger or rinse else Intent.RETREAT)
        return None

    def shot_clear(self, state, target):
        tiles = dict(self.tiles)
        for obj in state.get("objects", []):
            if obj["cell"] != target and (obj["cell"] in self.neutral_actor_cells
                    or obj["name"].lower() in ENEMIES | ROOM_ACTORS | {"sad ghost", "rat king"}):
                tiles[obj["cell"]] = {"terrain": 4}
        if getattr(self,'unit_strategies_enabled',False):
            try:
                from .policy_geometry import projectile_line_clear
            except ImportError:
                from policy_geometry import projectile_line_clear
            return projectile_line_clear(state['hero']['cell'],target,state['map']['width'],tiles)
        return line_clear(state["hero"]["cell"], target, state["map"]["width"], tiles)

    def single_enemy_position(self, state, enemies):
        """Reduce melee exposure before attacking; prefer a nearby narrow retreat."""
        awake = [e for e in enemies if not e.get("sleeping") and e["name"].lower() not in CASTERS]
        if any(e["name"].lower() in ZAPPERS for e in awake):
            return None  # Melee-only exposure ignores zaps and conflicts with gap closing.
        if len(awake) < 2:
            return None
        pos, width, height = state["hero"]["cell"], state["map"]["width"], state["map"]["height"]
        occupied = {e["cell"] for e in enemies}
        close = lambda cell: sum(distance(cell, e["cell"], width) <= 1 for e in awake)
        degree = lambda cell: sum(self.walkable(n) and self.tiles[n]["terrain"] not in TRANSITIONS
                                   for n in neighbors(cell, width, height))
        mixed_fly=any(e['name'].lower()=='swarm of flies' for e in awake) \
            and any(e['name'].lower()!='swarm of flies' for e in awake)
        def backstep(cell):
            # A low-degree pocket can still expose all of its exits to the
            # pursuing pack on the next turn. Keep one continuation beyond a
            # normal pursuer's immediate reach, rather than cornering ourselves.
            try:
                from .retreat_geometry import onward_runway
            except ImportError:
                from retreat_geometry import onward_runway
            if mixed_fly:return onward_runway(self,state,cell,pos,occupied,awake)
            return any(n != pos and self.walkable(n, occupied)
                       and self.tiles[n]["terrain"] not in TRANSITIONS | DOOR_KEYS.keys()
                       and not self.tiles[n].get("plant") and n not in state.get("danger_cells", [])
                       and all(distance(n, e["cell"], width) > 2 for e in awake)
                       for n in neighbors(cell, width, height))
        current = close(pos)
        # Don't kite indefinitely merely because several enemies are visible.
        if current == 0 and sum(distance(pos, e["cell"], width) <= 2 for e in awake) < 2:
            return None
        candidates = [c for c in neighbors(pos, width, height)
                      if self.walkable(c, occupied) and self.tiles[c]["terrain"] not in TRANSITIONS | DOOR_KEYS.keys()
                      and c not in state.get("danger_cells", [])
                       and not self.tiles[c].get("effects") and close(c) <= 1
                       and backstep(c)
                      and (close(c) < current or (degree(c) <= 3 and degree(c) < degree(pos)))]
        if not candidates:
            return None  # Boxed in: focus fire to create an escape, never wait here.
        routes = self.paths(state, occupied)
        chokes = [c for c in routes if c != pos and degree(c) <= 3
                  and self.tiles[c]["terrain"] not in TRANSITIONS | DOOR_KEYS.keys()
                  and len(self.route(routes, c)) <= 13]
        for choke in sorted(chokes, key=lambda c: len(self.route(routes, c))):
            step = self.route(routes, choke)[1]
            if step in candidates:
                return self.cell(step, "combat: funnel enemies to fight one at a time", intent=Intent.REPOSITION)
        target = min(candidates, key=lambda c: (close(c), degree(c), self.visits[c]))
        return self.cell(target, "combat: funnel enemies to fight one at a time", intent=Intent.REPOSITION)

    def charged_magic(self, state):
        return sorted((i for i in state["inventory"] if magic_score(i) > 0
                       and ((i.get("status") or "?").split("/")[0].isdigit()
                            or not self.unknown_magic_cooldowns[i["name"]])),
                      key=magic_score, reverse=True)

    def attack_kind_allowed(self,state,enemy,kind):
        return True

    def attack_approach_allowed(self,state,enemy):
        return True

    def best_attack(self, state, enemy, reserve=False, reserve_magic=False, *, allowed_kinds=None):
        pos, width = state["hero"]["cell"], state["map"]["width"]
        dist = distance(pos, enemy["cell"], width)
        strength = state["hero"].get("strength", 0)
        options = []
        if dist == 1 and (allowed_kinds is None or 'melee' in allowed_kinds) and self.attack_kind_allowed(state,enemy,'melee'):
            weapon = next((i for i in state["inventory"] if i.get("equipped")
                           and stats(i) and stats(i)[0] == "melee"), None)
            if not weapon or not known_cursed(weapon):
                score = physical_score(weapon, strength) if weapon else 2
                # At low HP, nominal melee damage is a poor trade against a
                # reliable zap: misses and armor can cost the remaining turns.
                if state["hero"]["hp"] <= 0.5 * state["hero"]["max_hp"]:
                    score *= 0.65
                options.append((self.attack_score(state, enemy, "melee", score), None, None))
        if self.shot_clear(state, enemy["cell"]):
            for item in self.charged_magic(state):
                if (allowed_kinds is not None and 'magic' not in allowed_kinds) or not self.attack_kind_allowed(state,enemy,'magic'):
                    continue
                if not self.target_allowed(item, enemy):
                    continue
                if reserve_magic:
                    continue
                if reserve and item == self.staff(state):
                    continue
                score = self.attack_score(state, enemy, "magic", magic_score(item))
                if score > 0:
                    options.append((score, item, "ZAP"))
            for item in state["inventory"]:
                value = stats(item)
                if 'THROW' in item.get('actions',[]) and value and value[0]=='thrown':
                    self.planner.report.setdefault('thrown_weapon_options',[]).append({
                        'name':item['name'],'strength_required':value[2],'hero_strength':strength,
                        'eligible_strength':value[2]<=strength,'known_cursed':known_cursed(item),
                        'caveat':'Still requires clear shot, target and non-splitting admission; not guaranteed damage'})
                if not self.target_allowed(item, enemy):
                    continue
                if "THROW" in item.get("actions", []) and value and value[0] == "thrown" \
                        and (allowed_kinds is None or 'thrown' in allowed_kinds) \
                        and self.attack_kind_allowed(state,enemy,'thrown'):
                    score = physical_score(item, strength)
                    if "force cube" in item["name"].lower():
                        continue
                    if score > 0:
                        options.append((self.attack_score(state, enemy, "thrown", score * (0.5 if dist == 1 else 0.8)), item, "THROW"))
        if not options:
            return None
        self.combat_approach_target = None
        self.combat_approach_steps = 0
        options=compare_options(self,state,enemy,options)
        _, item, action = max(options, key=lambda option: option[0])
        if item:
            return self.use(item, action, "combat: best estimated damage", target=enemy["cell"])
        return self.cell(enemy["cell"], "combat: melee")

    def wraith_combat(self, state, enemies, buffs):
        wraiths = [e for e in enemies if e["name"].lower() in WRAITHS]
        if not wraiths:
            self.ambush_plan = None
            return None
        pos, width = state["hero"]["cell"], state["map"]["width"]
        adjacent = [e for e in wraiths if distance(pos, e["cell"], width) == 1]
        if adjacent and ("invisib" in buffs or adjacent[0].get("sleeping")):
            return self.cell(adjacent[0]["cell"], "wraith: surprise attack")
        targets = sorted(wraiths, key=lambda e: (bool(e.get("sleeping")), distance(pos, e["cell"], width)))
        for target in targets:
            if self.shot_clear(state, target["cell"]):
                magic = [i for i in self.charged_magic(state) if self.target_allowed(i, target)]
                if magic:
                    self.ambush_plan = None
                    return self.use(magic[0], "ZAP", "wraith: guaranteed magic damage", target=target["cell"])
        # Ordinary melee will usually miss. Use a normal doorway surprise setup,
        # or keep moving safely until a wand recharges instead of trading blows.
        ambush = self.door_ambush(state, enemies, targets)
        if ambush:
            return ambush
        recharge = next((i for i in state["inventory"] if "scroll of recharging" in i["name"].lower()
                         and "READ" in i["actions"]), None)
        if recharge and "recharging" not in buffs:
            return self.use(recharge, "READ", "wraith: recharge magic")
        invisible = next((i for i in state["inventory"] if "potion of invisibility" in i["name"].lower()
                           and "DRINK" in i["actions"] and self.item_action_allowed(i,"DRINK")), None)
        if invisible:
            return self.use(invisible, "DRINK", "wraith: enable surprise attack")
        escape = self.retreat(state, enemies)
        if escape:
            escape.reason = "wraith: kite while magic recharges"
            return escape
        self.stop_no_safe_action("Wraiths: no charged magic, doorway ambush, or safe retreat; refusing futile melee")

    def door_ambush_limit(self):
        return 1

    def door_ambush(self, state, enemies, targets, kind="wraith"):
        pos, width, height = state["hero"]["cell"], state["map"]["width"], state["map"]["height"]
        occupied = {e["cell"] for e in enemies}
        plan = self.ambush_plan
        if plan and plan["kind"] != kind:
            plan = self.ambush_plan = None
        if plan and getattr(self,'unit_strategies_enabled',False) and (
                state['hero']['hp']<.5*state['hero']['max_hp'] or
                plan.get('start_hp',state['hero']['hp'])-state['hero']['hp']>.2*state['hero']['max_hp']):
            self.ambush_attempts[plan['door']]+=1
            plan=self.ambush_plan=None
            return None
        # A fresh lure must meet its own continuation health floor too.
        # Otherwise a snake dispatch can start an approach that the next tick
        # immediately aborts, even while an admitted wand shot is available.
        if not plan and getattr(self,'unit_strategies_enabled',False) \
                and state['hero']['hp']<.5*state['hero']['max_hp']:
            return None
        if plan and pos==plan["door"]:
            closed=dict(self.tiles)
            closed[plan["door"]]={"terrain":5}
            if any(line_clear(e["cell"],plan["hide"],width,closed) for e in enemies):
                self.ambush_attempts[plan["door"]]+=1
                plan=self.ambush_plan=None
        if plan:
            door, hide = plan["door"], plan["hide"]
            on_door = next((e for e in targets if e["cell"] == door), None)
            if pos == hide and on_door and (self.previous_position == door or plan.get("last_enemy") != door):
                self.ambush_plan = None
                self.ambush_attempts[door] += 1
                return self.cell(door, f"{kind}: doorway surprise attack")
            if pos == door and self.walkable(hide, occupied):
                if targets:
                    plan["last_enemy"] = targets[0]["cell"]
                return self.cell(hide, f"{kind}: break sight through doorway",intent=Intent.RETREAT)
            wait_budget=plan.get('arrival_budget',3) if getattr(self,'unit_strategies_enabled',False) else 3
            if pos == hide and not any(distance(pos, e["cell"], width) <= 1 for e in enemies) and plan["waits"] < wait_budget:
                plan["waits"] += 1
                if targets:
                    plan["last_enemy"] = targets[0]["cell"]
                return self.decision({"type": "wait"}, f"{kind}: await doorway ambush")
            paths = self.paths(state, occupied)
            if pos != hide and door in paths and plan["waits"] < 6:
                plan["waits"] += 1
                return self.toward(state, door, f"{kind}: reach ambush doorway", paths,intent=Intent.RETREAT)
            self.ambush_attempts[door] += 1
            self.ambush_plan = None
        if not targets:
            return None
        paths = self.paths(state, occupied)
        options = []
        preflights = {}
        scoped_preflight = kind == "doorway" and getattr(self,"unit_strategies_enabled",False)
        for door in paths:
            if self.tiles[door]["terrain"] not in (5, 6) or self.ambush_attempts[door]>=self.door_ambush_limit():
                continue
            route = self.route(paths, door)
            if len(route) > 7 or len(route) - 1 > min(distance(door, e["cell"], width) for e in enemies):
                continue
            for hide in neighbors(door, width, height):
                if scoped_preflight:
                    try:
                        from .escape_commitment import preflight
                    except ImportError:
                        from escape_commitment import preflight
                    witness=preflight(self,state,route,hide)
                    if not witness.allowed:
                        declines=self.planner.report.setdefault("commitment_declines",[])
                        if len(declines)<8:
                            declines.append(dict(door=door,hide=hide,**witness.record()))
                        continue
                    preflights[door,hide]=witness
                if not self.walkable(hide, occupied) or self.tiles[hide]["terrain"] not in FLOOR - TRANSITIONS - {5, 6}:
                    continue
                closed = dict(self.tiles)
                closed[door] = {"terrain": 5}
                if any(line_clear(e["cell"], hide, width, closed) for e in enemies):
                    continue
                options.append((len(route), door, hide))
        if options:
            _, door, hide = min(options)
            self.ambush_plan = {"door": door, "hide": hide, "waits": 0, "kind": kind}
            if scoped_preflight:
                self.ambush_plan["preflight"]=preflights[door,hide].record()
            if getattr(self,'unit_strategies_enabled',False):
                # Observed distance only: no hidden enemy path, position or arrival guarantee.
                self.ambush_plan['arrival_budget']=min(10,max(3,min(distance(door,e['cell'],width) for e in targets)+2))
                self.ambush_plan['start_hp']=state['hero']['hp']
            if pos == door:
                return self.cell(hide, f"{kind}: break sight through doorway",intent=Intent.RETREAT)
            return self.toward(state, door, f"{kind}: reach ambush doorway", paths,intent=Intent.RETREAT)
        return None

    def snake_combat(self, state, enemies, buffs):
        snakes = [e for e in enemies if e["name"].lower() == "sewer snake"]
        if not snakes:
            return None
        pos, width = state["hero"]["cell"], state["map"]["width"]
        target = min(snakes, key=lambda e: (bool(e.get("sleeping")), distance(pos, e["cell"], width)))
        if distance(pos, target["cell"], width) == 1 and (target.get("sleeping") or "invisib" in buffs):
            return self.cell(target["cell"], "snake: surprise attack")
        magic = [i for i in self.charged_magic(state) if self.target_allowed(i, target)]
        if target.get("sleeping") and magic and self.shot_clear(state, target["cell"]):
            return self.use(magic[0], "ZAP", "snake: safe opening shot", target=target["cell"])
        bar = target.get("health_bar")
        wounded = bar and bar[1] > 0 and bar[0] / bar[1] <= 0.35
        hp = state["hero"]["hp"] / max(1, state["hero"]["max_hp"])
        adjacent_threats = [e for e in enemies if not e.get("sleeping")
                            and distance(pos, e["cell"], width) == 1]
        if wounded and magic and self.shot_clear(state, target["cell"]):
            return self.use(magic[0], "ZAP", "snake: finish with magic", target=target["cell"])
        key = (target["cell"], target["name"])
        manageable = len(adjacent_threats) <= 1 or (hp >= 0.85 and len(adjacent_threats) <= 2 and all(
            e["name"].lower() in {"sewer snake", "marsupial rat", "albino rat"} for e in adjacent_threats))
        if distance(pos, target["cell"], width) == 1 and wounded and hp >= 0.65 \
                and manageable and self.snake_melee_attempts[key] < 4:
            self.snake_melee_attempts[key] += 1
            return self.cell(target["cell"], "snake: bounded finishing melee")
        # A new optional lure must not pull us away from owned potion
        # retrieval when the ordinary ranged fallback is already admitted.
        # Keep existing lures, multi-enemy arbitration and shot/charge gates.
        stash = getattr(self, "potion_stash", None)
        if stash and stash.get("phase") == "retrieve" and not self.ambush_plan \
                and len(enemies) == 1 and magic and self.shot_clear(state, target["cell"]):
            return self.use(magic[0], "ZAP", "snake: defend potion retrieval with magic", target=target["cell"])
        ambush = self.door_ambush(state, enemies, snakes, kind="snake")
        if ambush:
            return ambush
        if magic and self.shot_clear(state, target["cell"]):
            return self.use(magic[0], "ZAP", "snake: bypass evasion with magic", target=target["cell"])
        invisible = next((i for i in state["inventory"] if "potion of invisibility" in i["name"].lower()
                           and "DRINK" in i.get("actions", []) and self.item_action_allowed(i,"DRINK")), None)
        if invisible and "invisib" not in buffs:
            return self.use(invisible, "DRINK", "snake: enable surprise attack with known invisibility")
        escape = self.retreat(state, enemies)
        if escape:
            escape.reason = "snake: reposition for surprise/recharge"
            return escape
        onward=self.snake_reposition(state,enemies)
        if onward:
            return onward
        if hp>=0.75 and len([e for e in enemies if not e.get("sleeping")])==1 \
                and distance(pos,target["cell"],width)==1 and "champion" not in target.get("description","").lower() \
                and self.snake_melee_attempts[key]<self.snake_fallback_budget():
            self.snake_melee_attempts[key]+=1
            return self.cell(target["cell"],"snake: bounded healthy isolated fallback after lure and retreat exhausted")
        self.stop_tactical("snake-stall","Snake: no safe surprise setup, magic, or retreat; refusing repeated misses")

    def snake_fallback_budget(self):
        return 0

    def snake_reposition(self,state,enemies):
        return None

    def exploration_report(self, state, previous):
        skipped = self.skipped_special_floor(state, previous)
        coverage = [c for c in previous if not self.visits[c] and self.tiles[c]["terrain"] in FLOOR - TRANSITIONS
                    and c not in skipped and not self.loot.get(c, {}).get("for_sale")]
        locks = [c for c, tile in self.tiles.items() if tile["terrain"] in DOOR_KEYS and c not in self.optional_locks]
        # Known safe floor beyond a lock, hazard, or obstacle is an explicit
        # unfinished obligation, not a reason to silently take the stairs.
        occupied_enemies = {e["cell"] for e in state.get("objects", []) if is_hostile(e)}
        unreachable = [c for c in self.tiles if c not in previous and c not in skipped and c not in occupied_enemies and
                       not self.loot.get(c, {}).get("for_sale") and
                       (self.walkable(c) or (c in self.blocked and self.tiles[c]["terrain"] in FLOOR))
                       and self.tiles[c]["terrain"] not in TRANSITIONS | DOOR_KEYS.keys()]
        frontiers = [c for c in previous if c not in self.exhausted and c not in skipped
                      and not self.loot.get(c, {}).get("for_sale")
                     and self.tiles[c]["terrain"] not in TRANSITIONS | DOOR_KEYS.keys()
                     and ((self.tiles[c].get("mapped") and self.tiles[c].get("observed") is False)
                          or any(n not in self.tiles for n in neighbors(c, state["map"]["width"], state["map"]["height"])))]
        unopened = [c for c in previous if c not in skipped and self.tiles[c]["terrain"] == 5
                    and (not self.visits[c] or c in self.changed_door_cells)]
        return {"known_cells": len(self.tiles), "unvisited_reachable": coverage,
                "unexplored_frontiers": frontiers, "unopened_doors": unopened,
                "unresolved_doors": locks, "unreachable_known_floor": unreachable,
                "held_keys": dict(self.keys), "searches": self.searches,
                "searched_wall_cells": sorted(self.searched_walls),
                "secret_search_steps": self.secret_search_steps,
                "remaining_enemy_sightings": [e for c, e in self.enemy_sightings.items() if c not in skipped],
                "clear_sweep_steps": self.clear_steps,
                "temporary_block_waits": self.temporary_block_waits,
                "hunger": next((b["name"] for b in state["hero"].get("buffs", [])
                                if b["name"].lower() in {"hungry", "starving"}), "not hungry"),
                "food_portions": sum(i.get("quantity", 1) for i in self.food_items(state)),
                "observed_distant_well_floors": sorted(d - 1 for d in self.drop_room_expected_on),
                "drop_room_expected": state["depth"] in self.drop_room_expected_on,
                "skipped_special_cells": sorted(skipped), "skipped_special_rooms": self.room_notes}

    def temporary_blockage(self, state, enemies):
        sheep = {o["cell"] for o in state.get("objects", []) if o["name"].lower() == "sheep"}
        pos, width = state["hero"]["cell"], state["map"]["width"]
        if not sheep or min(distance(pos, c, width) for c in sheep) > 2:
            return None
        if any(not e.get("sleeping") and distance(pos, e["cell"], width) == 1 for e in enemies):
            return None
        occupied = {e["cell"] for e in enemies}
        current = self.paths(state, occupied)
        # Counterfactual planning only: never actually move onto a sheep. Wait if
        # removing these temporary bodies would reconnect more than their tiles.
        after_fade = self.paths(state, occupied, ignored_neutrals=sheep)
        reconnects = len(after_fade) > len(current) + len(sheep)
        blocks_stairs = any(self.tiles.get(c, {}).get("terrain") in TRANSITIONS for c in sheep)
        if not reconnects and not blocks_stairs:
            return None
        if self.temporary_block_waits >= 12:
            self.stop_gameplay("Temporary sheep blockage did not clear within 12 waits")
        self.temporary_block_waits += 1
        return self.decision({"type": "wait"}, "obstacle: wait for magic sheep to fade")

    def skipped_special_floor(self, state, previous):
        """Identify known floor beyond recognized optional hazards, never unknown terrain.

        Ordinary locked doors are not counted as special-room skips. Missing keys
        are reported separately as deferred rooms and do not block descent.
        """
        width, height = state["map"]["width"], state["map"]["height"]
        found = set(previous)
        barriers = self.room_blocked | self.optional_locks
        queue = deque()
        for cell in previous:
            if self.tiles[cell]["terrain"] in TRANSITIONS | DOOR_KEYS.keys():
                continue
            for adjacent in neighbors(cell, width, height):
                if adjacent in barriers and adjacent not in found:
                    found.add(adjacent)
                    queue.append(adjacent)
        while queue:
            for cell in neighbors(queue.popleft(), width, height):
                tile = self.tiles.get(cell)
                if cell in found or tile is None or tile["terrain"] in TRANSITIONS:
                    continue
                if tile["terrain"] in DOOR_KEYS and cell not in self.optional_locks:
                    continue
                if cell in self.blocked and cell not in self.room_blocked:
                    continue
                if cell not in self.room_blocked | self.optional_locks and not self.walkable(cell):
                    continue
                if tile["terrain"] not in FLOOR and cell not in self.room_blocked | self.optional_locks:
                    continue
                found.add(cell)
                queue.append(cell)
        return self.room_skipped | self.optional_locks | (found - set(previous))

    def escape_step_allowed(self,state,cell):
        return True

    def escape_special_room(self, state):
        pos, width, height = state["hero"]["cell"], state["map"]["width"], state["map"]["height"]
        tile = self.tiles.get(pos, {})
        effects = tile.get("effects", [])
        try:
            from .vertigo_tactics import choose as vertigo_response
        except ImportError:
            from vertigo_tactics import choose as vertigo_response
        recovery = vertigo_response(self, state)
        if recovery:
            return recovery
        def cold_only(tile):
            effects = tile.get("effects", [])
            return bool(effects) and all("unnaturally frigid" in effect.lower() for effect in effects)
        def fire_only(tile):
            effects = tile.get("effects", [])
            return bool(effects) and all("a fire is raging here" in effect.lower() for effect in effects)
        def toxic_only(tile):
            effects = tile.get("effects", [])
            return bool(effects) and all("cloud of toxic gas" in effect.lower() for effect in effects)
        escaping_fire = fire_only(self.tiles.get(pos, {}))
        escaping_toxic = toxic_only(self.tiles.get(pos, {}))
        hazard_budget = min(4, max(0, (state["hero"]["hp"] - 7) // 6)) if escaping_fire or escaping_toxic else 0
        if not cold_only(self.tiles.get(pos, {})):
            self.temporary_freeze_waits = 0
        if pos not in self.room_blocked:
            return None
        actors = (self.neutral_actor_cells-self.friendly_passage_cells) | {a["cell"] for a in self.room_actors.values()} | {
            o["cell"] for o in state.get("objects", []) if o["name"].lower() in ENEMIES}
        previous, queue = {pos: None}, deque([pos])
        while queue:
            cell = queue.popleft()
            if cell != pos and cell not in self.room_skipped:
                return self.cell(self.route(previous, cell)[1], "room: retreat to safe ground", intent=Intent.RETREAT)
            for adjacent in neighbors(cell, width, height):
                tile = self.tiles.get(adjacent, {})
                hazard_step = ((escaping_fire and fire_only(tile)) or (escaping_toxic and toxic_only(tile))) \
                    and len(self.route(previous, cell)) <= hazard_budget
                if adjacent not in previous and adjacent not in actors and tile.get("terrain") in FLOOR - TRANSITIONS \
                        and self.escape_step_allowed(state,adjacent) \
                        and (not tile.get("trap") or tile.get("terrain") == 19) \
                        and (not tile.get("effects") or cold_only(tile) or hazard_step) \
                        and tile.get("plant", "").lower() not in HARMFUL_PLANTS:
                    previous[adjacent] = cell
                    queue.append(adjacent)
        nearby = any(distance(pos, o["cell"], width) <= 3 for o in state.get("objects", [])
                     if o["name"].lower() in ENEMIES | ROOM_ACTORS and not o.get("sleeping"))
        if cold_only(self.tiles[pos]) and not nearby and self.temporary_freeze_waits < 16:
            self.temporary_freeze_waits += 1
            return self.decision({"type": "wait"}, "obstacle: wait briefly for isolated freezing air to clear")
        self.stop_tactical("hazard-escape","Inside a hazardous special room without a known safe escape")

    def frontier_cost(self,state,paths,cell):
        return len(self.route(paths,cell))+2*self.visits[cell]

    def exploration_loot_allowed(self,state,cell,paths):
        return True

    def systematic_exploration_enabled(self,state,enemies):
        return False

    def systematic_exploration(self,state,paths,skipped):
        return None

    def explore(self, state, enemies):
        pos, width, height = state["hero"]["cell"], state["map"]["width"], state["map"]["height"]
        previous = self.paths(state, {e["cell"] for e in enemies})
        skipped = self.skipped_special_floor(state, previous)
        self.exhausted.add(pos)
        try:
            visit = visit_entrance_shop(self, state, previous, neighbors)
        except ShopVisitBlocked as error:
            self.stop_gameplay(str(error))
        if visit:
            return visit
        shopping = choose_shop(self, state, previous)
        if shopping:
            return shopping
        previous = {c: parent for c, parent in previous.items()
                    if c == pos or not self.loot.get(c, {}).get("for_sale")}
        systematic=self.systematic_exploration_enabled(state,enemies)
        if getattr(self,'unit_strategies_enabled',False):
            try:
                from .hidden_doors import continue_search_vantage
            except ImportError:
                from hidden_doors import continue_search_vantage
            committed=continue_search_vantage(self,state,enemies,previous)
            if committed:return committed
        if systematic:
            action=self.systematic_exploration(state,previous,skipped)
            if action:return action
        chests = [c for c in self.allowed_chests if not systematic and c in previous and c not in skipped and c not in self.blocked
                  and self.exploration_loot_allowed(state,c,previous)]
        if chests:
            for target in sorted(chests,key=lambda c:len(self.route(previous,c))):
                action=self.toward(state,target,"loot: spend matching key on useful chest",previous,intent=Intent.LOOT)
                if action:return action
        exits = [c for c in previous if self.tiles[c]["terrain"] in {8, 22}]
        if not exits and not enemies:
            plant = clear_blocking_plant(self, state, previous, distance)
            if plant:
                return plant
        buffs = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
        food = self.food_items(state)
        if exits and self.conserve_descent_allowed(state) and (self.depth < 5 or self.goal == "survival") and not food and ("hungry" in buffs or "starving" in buffs):
            nearby_food = [c for c, obj in self.loot.items() if c in previous and c not in skipped
                           and len(self.route(previous, c)) <= 9
                           and any(name in obj["name"].lower() for name in ("ration of food", "pasty", "grilled meat", "frozen carpaccio"))]
            if nearby_food:
                target = min(nearby_food, key=lambda c: len(self.route(previous, c)))
                return self.toward(state, target, "loot: nearby food before descent", previous, intent=Intent.LOOT)
            target = min(exits, key=lambda c: len(self.route(previous, c)))
            return self.toward(state, target, "stairs: conserve food and health", previous, intent=Intent.DESCEND)

        # Keys first. A key stored in the journal is not a lost backpack item.
        loot_targets = []
        for cell, obj in self.loot.items():
            name = obj["name"].lower()
            if systematic:continue
            if obj.get("for_sale"):
                continue  # Purchases require an explicit shop plan and price check.
            if cell not in previous or cell in self.blocked or cell in skipped or self.tiles[cell]["terrain"] in TRANSITIONS:
                continue
            if any(word in container_name(obj) for word in AVOID_CONTAINERS) and cell not in self.allowed_chests:
                continue
            if not self.exploration_loot_allowed(state,cell,previous):
                continue
            if "locked chest" in name and not self.keys.get("golden", 0):
                continue
            loot_targets.append(cell)
        if loot_targets:
            for target in sorted(loot_targets,key=lambda c:("key" not in self.loot[c]["name"].lower(),len(self.route(previous,c)))):
                action=self.toward(state,target,"loot: collect key" if "key" in self.loot[target]["name"].lower()
                                   else "loot: collect/open",previous,intent=Intent.LOOT)
                if action:return action

        locks = [c for c, tile in self.tiles.items() if tile["terrain"] in DOOR_KEYS and c not in self.optional_locks]
        for cell in sorted(locks, key=lambda c: distance(pos, c, width)):
            if systematic:continue
            key = DOOR_KEYS[self.tiles[cell]["terrain"]]
            if cell in previous and cell not in self.blocked and self.keys.get(key, 0) > 0:
                action=self.toward(state,cell,f"explore: unlock {key} door",previous,intent=Intent.EXPLORE)
                if action:return action

        report = self.exploration_report(state, previous)
        frontier = [] if systematic else report["unexplored_frontiers"]
        if frontier:
            for target in sorted(frontier,key=lambda c:self.frontier_cost(state,previous,c)):
                action=self.toward(state,target,"explore: frontier",previous,intent=Intent.EXPLORE)
                if action:return action

        if report["unopened_doors"] and not systematic:
            for target in sorted(report["unopened_doors"],key=lambda c:len(self.route(previous,c))):
                action=self.toward(state,target,"explore: unopened door",previous,intent=Intent.EXPLORE)
                if action:return action

        # Clear known ordinary opponents before leaving, but do not patrol forever
        # for respawns. Last-seen locations are only memories, not hidden live data.
        if self.clear_steps < self.sweep_limit(state):
            targets = []
            for enemy in report["remaining_enemy_sightings"]:
                if getattr(self,'unit_strategies_enabled',False) and enemy.get('sleeping'):
                    continue  # Combat owns sleeper admission; never circle a disabled foe to wake it by proximity.
                for cell in neighbors(enemy["cell"], width, height):
                    if cell in previous and cell != pos and cell not in skipped and self.tiles[cell]["terrain"] not in TRANSITIONS:
                        targets.append(cell)
            if targets:
                for target in sorted(targets,key=lambda c:len(self.route(previous,c))):
                    action=self.toward(state,target,"explore: clear ordinary enemy sighting",previous,intent=Intent.EXPLORE)
                    if action:
                        self.clear_steps+=1
                        return action

        if not exits and not enemies:
            recheck = recheck_hazards(self, state, previous, distance)
            if recheck:
                return recheck
        # Search likely room-wall entrances even with a known exit, but only as
        # a short, well-fed detour. Missing-exit searches retain a larger budget.
        search_budget = 4 if "starving" in buffs else 8 if "hungry" in buffs else 40
        optional = bool(exits) and not getattr(self,'requires_key_search',lambda s:False)(state)
        if optional:
            search_budget = 6 if self.depth > 1 and food and "hungry" not in buffs and "starving" not in buffs \
                and state["hero"]["hp"] >= 0.7 * state["hero"]["max_hp"] else 0
        search_budget = self.search_limit(state, search_budget, optional)
        if self.searches < search_budget and (not optional or self.secret_search_steps < 24):
            try:
                from .hidden_doors import special_room_walls
            except ImportError:
                from hidden_doors import special_room_walls
            excluded=self.searched_walls|special_room_walls(self,state)
            scores = wall_scores(self.tiles, width, height, excluded)
            # A discovered secret only ends optional room hunting. Without a
            # reachable exit, retain the ordinary bounded missing-exit search.
            if self.secret_area_found and exits:
                ends=corridor_ends(self.tiles,width,height,excluded)
                scores={c:s for c,s in scores.items() if c in ends}
            if not optional and (not self.secret_area_found or not exits):
                for wall, tile in self.tiles.items():
                    if tile["terrain"] in (4, 12) and wall not in excluded:
                        scores.setdefault(wall, 1)  # Broad fallback if no exit is known.
            coverage = {c: {wall for wall in scores if distance(c, wall, width) == 1
                            and (c != pos or self.tiles[wall].get("visible"))}
                         for c in previous if self.tiles[c]["terrain"] in FLOOR - TRANSITIONS and c not in skipped
                         and c not in self.completed_maze_cells}
            candidates = [c for c, walls in coverage.items() if walls and self.wall_searches[c] < 1
                          and (not optional or len(self.route(previous, c)) <= 9)]
            if candidates:
                target = max(candidates, key=lambda c: sum(scores[w] for w in coverage[c]) /
                             (1 + len(self.route(previous, c))))
                self.secret_search_steps += 1
                if target != pos:
                    if getattr(self,'unit_strategies_enabled',False):
                        self.secret_search_goal={'cell':target,'walls':set(coverage[target]),'steps':0}
                    return self.toward(state, target, "explore: reach secret-search vantage", previous, intent=Intent.EXPLORE)
                self.searches += 1
                self.wall_searches[pos] += 1
                self.searched_walls.update(search_coverage(self.tiles, pos, width, height))
                return self.decision({"type": "search"}, "explore: search walls for missing rooms/keys")

        if exits and (self.depth < 5 or self.goal == "survival"):
            target = min(exits, key=lambda c: len(self.route(previous, c)))
            reason = "stairs: descend with deferred rooms" if locks or report["unreachable_known_floor"] else "stairs: descend after floor exploration"
            return self.toward(state, target, reason, previous, intent=Intent.DESCEND)
        teleport = next((i for i in state["inventory"] if "scroll of teleportation" in i["name"].lower()
                         and "READ" in i.get("actions", [])), None)
        if not enemies and teleport and self.route_teleports < 1:
            self.route_teleports += 1
            return self.use(teleport, "READ", "explore: teleport after exhausting reachable routes")
        self.stop_gameplay("Exploration exhausted without a reachable exit: " + json.dumps(report))

    def choose(self, state):
        self.planner.begin()
        if state.get("status") == "dead":
            raise Finished("dead", "Hero died")
        if state.get("scene") != "GameScene":
            return self.menu(state)
        if state["hero"].get("hero_class", state["hero"]["name"]).lower() not in {"mage", "warlock", "battlemage"}:
            raise Finished("blocked", "This policy requires a Mage run")
        checkpoint = {"two-floors": 3, "floor-four": 4}.get(self.goal)
        if checkpoint and self.depth is None and state["depth"] != 1:
            raise Finished("blocked", "Start the floor checkpoint on floor 1")
        self.update(state)
        if checkpoint and state["depth"] >= checkpoint:
            if set(range(1, checkpoint)).issubset(self.cleared_floors):
                raise Finished("success", f"Swept ordinary floors and reached floor {checkpoint}")
            raise Finished("blocked", "Checkpoint reached without observing all ordinary-floor descents")
        boss = strategy_for(state, self.boss_strategies)
        if boss and boss.victory(self, state):
            self.defeated_bosses.add(boss.name)
            if self.goal != "survival":
                raise Finished("success", "Goo's displayed boss bar disappeared after engagement")
        if state["depth"] > 5 and self.goal != "survival":
            raise Finished("blocked", "Past milestone area without confirmed Goo defeat")
        if state["status"] == "targeting":
            if self.target is None:
                raise Finished("blocked", "Unexpected targeting prompt")
            target, self.target = self.target, None
            return self.cell(target, "target: selected observed cell")
        if state.get("modal") or state["status"] == "menu":
            return self.menu(state)
        observe_wand_cast(self, state)
        if self.menu_plan in {"discover-scroll", "upgrade-cancel"}:
            self.menu_plan = None  # A non-inventory scroll resolved normally.
        for name in self.unknown_magic_cooldowns:
            self.unknown_magic_cooldowns[name] = max(0, self.unknown_magic_cooldowns[name] - 1)
        if not self.tutorial_read and any("flashing journal" in text.lower() for text in state["ui"]["texts"]):
            journal = next((b for b in state["ui"]["buttons"] if b["label"].lower() == "journal"), None)
            if journal:
                self.tutorial_read = True
                return self.decision({"type": "button", "id": journal["id"]}, "tutorial: read guidebook")
        enemies = [o for o in state.get("objects", []) if is_hostile(o)]
        context = Context(self, state, boss=boss, enemies=enemies,
                          active=[e for e in enemies if not e.get("sleeping")])
        try:
            return POLICY(context)
        finally:
            self.planner.report["controllers"] = context.trace
