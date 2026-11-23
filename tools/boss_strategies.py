"""Boss-specific rules. Strategies receive observations and normal policy actions.

Register each future boss separately: floor number is sufficient for preparation,
but attacks and phase estimates require the visible boss/health bar. Never read
the game's private boss state, charge counter, or generated arena data.
"""
from collections import deque
import re

try:
    from .policy_decision import Intent
except ImportError:
    from policy_decision import Intent

HARD_COVER = {4, 10, 12, 13, 21, 23, 25, 26, 27, 28, 31, 33, 34, 35, 36, 38, 39}


def goo_blast_reaches(source, target, width, tiles):
    """Public radius/solid-cover rules, using observed terrain only.

    Goo checks Ballistica in both directions. Closed ordinary doors and tall
    grass are soft cover and do not protect against this attack. Unknown cells
    never count as a wall. No character positions/private charge state are read.
    """
    dx, dy = target % width-source % width, target // width-source // width
    if max(abs(dx), abs(dy)) > 2:
        return False
    def clear(a, b):
        x, y = b % width-a % width, b // width-a // width
        sx, sy = (1 if x > 0 else -1), (1 if y > 0 else -1)
        x, y = abs(x), abs(y)
        major, minor, da, db = (sx, sy*width, x, y) if x > y else (sy*width, sx, y, x)
        cell, error = a, da//2
        for _ in range(da):
            cell += major
            error += db
            if error >= da:
                cell += minor
                error -= da
            if cell != b and tiles.get(cell, {}).get("terrain") in HARD_COVER:
                return False
        return True
    return clear(source, target) and clear(target, source)


class BossEscapeBlocked(RuntimeError):
    pass


class GooStrategy:
    name = "goo"
    depth = 5

    def __init__(self):
        self.preparation_waits = 0
        self.lure_steps = 0

    @staticmethod
    def health_fraction(state):
        match = re.fullmatch(r"(\d+)/(\d+)", state.get("boss_health_text") or "")
        return int(match[1]) / int(match[2]) if match and int(match[2]) else None

    def victory(self, p, state):
        # The rendered boss bar persists even when Goo leaves the field of view.
        return state.get("status") != "dead" and state.get("depth") == self.depth \
            and p.boss_seen and state.get("boss_health_text") is None

    @staticmethod
    def safe_steps(p, state, enemies, neighbors):
        pos, width, height = state["hero"]["cell"], state["map"]["width"], state["map"]["height"]
        occupied = {e["cell"] for e in enemies}
        return [c for c in neighbors(pos, width, height) if p.walkable(c, occupied)
                and p.tiles[c]["terrain"] not in {5, 7, 8, 10, 21, 22, 31, 37, 38}
                and not p.tiles[c].get("effects") and not p.tiles[c].get("plant")]

    def evade(self, p, state, enemies, distance, neighbors):
        pos, width, height = state["hero"]["cell"], state["map"]["width"], state["map"]["height"]
        rendered = set(state.get("danger_cells", []))
        goo = next((e for e in enemies if e["name"].lower() == self.name), None)
        danger = rendered | ({c for c in p.tiles if goo_blast_reaches(goo["cell"], c, width, p.tiles)} if goo and rendered else set())
        if pos not in danger or not rendered:
            return None
        steps = self.safe_steps(p, state, enemies, neighbors)
        safe = [c for c in steps if c not in danger]
        if safe:
            buffs = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
            occupied = {e["cell"] for e in enemies}
            mobility = lambda c: sum(p.walkable(n, occupied) and not p.tiles[n].get("plant")
                                      and p.tiles[n]["terrain"] not in {5, 7, 8, 10, 21, 22, 31, 37, 38}
                                      for n in neighbors(c, width, height))
            target = max(safe, key=lambda c: (min(mobility(c), 5),
                         p.tiles[c]["terrain"] == 29 if "ooze" in buffs else True,
                         distance(c, goo["cell"], width) if goo else 0, -p.visits[c]))
            return p.cell(target, "boss: goo evade charged attack")
        # The first warning grows from radius one to radius two. Only the
        # visibly early warning allows planning two moves; a full warning needs
        # an immediate exit, not another move within the charged attack area.
        early = goo and all(distance(c, goo["cell"], width) <= 1 for c in rendered)
        if not early or getattr(p, "badder_bosses", False):
            return self.emergency_escape(p, state)
        occupied = {e["cell"] for e in enemies}
        previous, queue = {pos: None}, deque([pos])
        while queue:
            cell = queue.popleft()
            if cell != pos and cell not in danger:
                step = p.route(previous, cell)[1]
                reason = "boss: goo staged escape from charged attack" if step in rendered else "boss: goo evade charged attack"
                return p.cell(step, reason)
            if len(p.route(previous, cell)) >= 3:
                continue
            for c in neighbors(cell, width, height):
                if c not in previous and p.walkable(c, occupied) and not p.tiles[c].get("effects") \
                        and not p.tiles[c].get("plant") and p.tiles[c]["terrain"] not in {5, 7, 8, 10, 21, 22, 31, 37, 38}:
                    previous[c] = cell
                    queue.append(c)
        return self.emergency_escape(p, state)

    @staticmethod
    def emergency_escape(p, state):
        buffs = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
        for name, action in (("scroll of teleportation", "READ"), ("potion of invisibility", "DRINK")):
            item = next((i for i in state["inventory"] if name in i["name"].lower() and action in i.get("actions", [])), None)
            if item and ("invisibility" not in name or "invisib" not in buffs):
                try:
                    from .room_supplies import use as use_room_supply
                except ImportError:
                    from room_supplies import use as use_room_supply
                return use_room_supply(p,item,action,"boss: goo emergency escape from trapped charge",kind='emergency')
        raise BossEscapeBlocked("Goo charged attack: no immediate safe exit or usable escape; refusing generic movement inside the blast")

    def refuge_size(self, p, state, enemies, goo, start, neighbors, limit=6):
        width, height = state["map"]["width"], state["map"]["height"]
        occupied = {e["cell"] for e in enemies}
        seen, queue = {start}, deque([start])
        while queue and len(seen) < limit:
            for c in neighbors(queue.popleft(), width, height):
                if c not in seen and p.walkable(c, occupied) and not p.tiles[c].get("plant") \
                        and p.tiles[c]["terrain"] not in {5, 7, 8, 10, 21, 22, 31, 37, 38} \
                        and not goo_blast_reaches(goo["cell"], c, width, p.tiles):
                    seen.add(c)
                    queue.append(c)
        return min(len(seen), limit)

    def escape_distance(self, p, state, enemies, goo, start, neighbors, min_refuge=1):
        width, height = state["map"]["width"], state["map"]["height"]
        occupied = {e["cell"] for e in enemies}
        seen, queue = {start}, deque([(start, 0)])
        while queue:
            cell, moves = queue.popleft()
            if not goo_blast_reaches(goo["cell"], cell, width, p.tiles) \
                    and self.refuge_size(p, state, enemies, goo, cell, neighbors, min_refuge) >= min_refuge:
                return moves
            if moves == 6:
                continue
            for c in neighbors(cell, width, height):
                if c not in seen and p.walkable(c, occupied) and not p.tiles[c].get("plant") \
                        and p.tiles[c]["terrain"] not in {5, 7, 8, 10, 21, 22, 31, 37, 38}:
                    seen.add(c)
                    queue.append((c, moves+1))
        return 99

    def avoid_corner(self, p, state, enemies, goo, distance, neighbors):
        pos, width = state["hero"]["cell"], state["map"]["width"]
        if distance(pos, goo["cell"], width) > 2:
            return None
        escape_distance = lambda c: self.escape_distance(p, state, enemies, goo, c, neighbors, min_refuge=8)
        current_escape = escape_distance(pos)
        if current_escape <= (1 if getattr(p, "badder_bosses", False) else 2):
            return None
        candidates = [c for c in self.safe_steps(p, state, enemies, neighbors) if escape_distance(c) < current_escape
                      and (not getattr(p, "badder_bosses", False) or escape_distance(c) <= 1)]
        if candidates:
            target = min(candidates, key=lambda c: (escape_distance(c), -distance(c, goo["cell"], width), p.visits[c]))
            return p.cell(target, "boss: goo leave corner before another charge")
        if getattr(p, "badder_bosses", False):
            transport = p.emergency_transport(state, enemies)
            if transport:
                return transport
            p.stop_no_safe_action("Badder Goo: no verified one-turn charge escape from this corner")
        return None

    def landing_escape_distance(self, p, state, enemies, goo, landing, distance, neighbors):
        result = self.escape_distance(p, state, enemies, goo, landing, neighbors, min_refuge=8)
        pos, width = state["hero"]["cell"], state["map"]["width"]
        # A retreat may let Goo occupy our vacated tile. Do not count an exit
        # through that tile as a lasting escape route after a lure/rinse move.
        if distance(pos, goo["cell"], width) == 1:
            future = dict(goo, cell=pos)
            future_enemies = [future if e is goo else e for e in enemies]
            result = max(result, self.escape_distance(p, state, future_enemies, future,
                                                     landing, neighbors, min_refuge=8))
        return result

    def healing_threshold(self, state):
        fraction = self.health_fraction(state)
        return 0.65 if fraction is not None and fraction <= 0.5 else 0.55

    def prepare(self, p, state, enemies):
        if p.boss_seen or any(not e.get("sleeping") for e in enemies):
            return None
        hero = state["hero"]
        buffs = " ".join(b["name"].lower() for b in hero.get("buffs", []))
        limit = min(120, p.recovery_limit(state, "hungry" in buffs)) if getattr(p, "badder_bosses", False) else 120
        if "starving" in buffs or ("hungry" in buffs and not p.food_items(state)) or self.preparation_waits >= limit:
            return None
        reason = None
        if hero["hp"] < 0.95 * hero["max_hp"]:
            reason = "boss: goo prepare health before engagement"
        else:
            staff = p.staff(state)
            charge = (staff.get("status") or "").split("/") if staff else []
            if len(charge) == 2 and all(c.isdigit() for c in charge) and int(charge[0]) < int(charge[1]):
                reason = "boss: goo prepare wand charges before engagement"
        if reason:
            self.preparation_waits += 1
            return p.decision({"type": "wait"}, reason, intent=Intent.BOSS)
        return None

    def choose(self, p, state, enemies, distance, neighbors):
        goo = next((e for e in enemies if e["name"].lower() == self.name), None)
        if not goo:
            return None  # Do not chase a hidden boss using its last/private position.
        pos, width = state["hero"]["cell"], state["map"]["width"]
        other = [e for e in enemies if e is not goo and not e.get("sleeping")]
        if any(distance(pos, e["cell"], width) < distance(pos, goo["cell"], width) for e in other):
            return None  # Normal combat resolves closer blockers first.
        danger = set(state.get("danger_cells", []))
        steps = [c for c in self.safe_steps(p, state, enemies, neighbors) if c not in danger
                 and all(distance(c, e["cell"], width) > 1 for e in other)]
        on_water = p.tiles.get(goo["cell"], {}).get("terrain") == 29
        if not on_water:
            self.lure_steps = 0
        if on_water and not danger and distance(pos, goo["cell"], width) == 1 and self.lure_steps < 6:
            dry = [c for c in steps if p.tiles[c]["terrain"] != 29 and distance(c, goo["cell"], width) >= 2
                   and self.landing_escape_distance(p, state, enemies, goo, c, distance, neighbors) <= (1 if getattr(p, "badder_bosses", False) else 2)]
            if dry:
                self.lure_steps += 1
                return p.cell(min(dry, key=lambda c: p.visits[c]), "boss: goo lure off healing water")
        if not danger:
            reposition = self.avoid_corner(p, state, enemies, goo, distance, neighbors)
            if reposition:
                return reposition
        attack = p.best_attack(state, goo)  # No last-charge conservation against a boss.
        if attack:
            attack.reason = "boss: goo best estimated damage"
            return attack
        if danger:
            return p.decision({"type": "wait"}, "boss: goo hold outside charged attack", intent=Intent.BOSS)
        key = (state["depth"], pos, goo["cell"])
        p.combat_waits[key] += 1
        if p.combat_waits[key] > 2:
            approach = p.toward(state, goo["cell"], "boss: goo improve line of fire")
            if approach and approach.action["cell"] in steps:
                return approach
        return p.decision({"type": "wait"}, "boss: goo let approach while recharging", intent=Intent.BOSS)


class ObservedBossStrategy:
    """Shared safe movement, never a phase/position oracle."""
    def __init__(self, name, depth):
        self.name, self.depth = name, depth
        self.engaged = False
        self.waits = 0
        self.avoid_cells = set()

    def victory(self, p, state):
        if state.get("boss_health_text"):
            self.engaged = True
        return self.engaged and state.get("status") != "dead" and state.get("boss_health_text") is None

    def healing_threshold(self, state):
        return 0.7

    def prepare(self, p, state, enemies):
        if enemies or self.engaged or self.waits >= p.recovery_limit(state, False):
            return None
        staff = p.staff(state)
        charge = (staff.get("status") or "?").split("/")[0] if staff else "?"
        if state["hero"]["hp"] < 0.8*state["hero"]["max_hp"] or charge.isdigit() and int(charge) < 3:
            buffs = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
            if "starving" not in buffs and "hungry" not in buffs:
                self.waits += 1
                return p.decision({"type": "wait"}, f"boss: {self.name} bounded health/charge preparation", intent=Intent.BOSS)
        return None

    def evade(self, p, state, enemies, distance, neighbors):
        if state["hero"]["cell"] in state.get("danger_cells", []):
            if any("root" in b["name"].lower() for b in state["hero"].get("buffs", [])):
                raise BossEscapeBlocked(f"{self.name}: rooted inside rendered warning; cannot assume a movement escape")
            action = p.retreat(state, enemies, set(state["danger_cells"]))
            if action and action.action.get("cell") not in state["danger_cells"]:
                return action
            raise BossEscapeBlocked(f"{self.name}: no safe exit from rendered warning")
        return None

    def target(self, state, enemies):
        return next((e for e in enemies if e["name"].lower() == self.name), None)

    def minimum_range(self, target):
        return 1

    def choose(self, p, state, enemies, distance, neighbors):
        target = self.target(state, enemies)
        if not target:
            return None
        if hasattr(p, "challenge_withdrawal"):
            withdrawal = p.challenge_withdrawal(state, enemies)
            if withdrawal:
                return withdrawal
        attack = p.best_attack(state, target)
        if attack:
            attack.reason = f"boss: {self.name} attack public priority target"
            return attack
        previous = p.paths(state, {e["cell"] for e in enemies})
        width = state["map"]["width"]
        positions = [c for c in previous if c != state["hero"]["cell"]
                     and p.tiles[c]["terrain"] not in {5, 7, 8, 22, 37}
                     and len(p.route(previous, c)) <= 5
                     and not any(n in self.avoid_cells or n in state.get("danger_cells", []) for n in p.route(previous, c)[1:])
                     and self.minimum_range(target) <= distance(c, target["cell"], width) <= 2]
        if positions:
            return p.toward(state, min(positions, key=lambda c: len(p.route(previous, c))),
                            f"boss: {self.name} approach visible priority target", previous)
        return None


class TenguStrategy(ObservedBossStrategy):
    def __init__(self):
        super().__init__("tengu", 10)
        self.hazard_waits = 0
        self.transitioning = False
        self.transition_steps = 0

    def victory(self, p, state):
        between_phases = super().victory(p, state)
        if state.get("boss_health_text"):
            self.transitioning = False
            self.transition_steps = 0
        if not between_phases:
            return False
        # Arena transitions are not victories. Require a public final reward
        # or the defeat line as well as disappearance of the rendered boss bar.
        names = [i["name"].lower() for i in state.get("inventory", [])]
        names += [o.get("top_item", {}).get("name", o["name"]).lower() for o in state.get("objects", [])]
        won = any("tengu's mask" in name for name in names) or any(
            "free at last" in t.lower() for t in state.get("ui", {}).get("texts", []))
        if won:
            self.transitioning = False
            # The final map can reuse a previously crossed closed door without
            # changing its terrain ID. Rearm that observed work once, not on
            # every later reclosure. Normal paths/loot/safety still arbitrate;
            # neither the unseen exit nor reward collection is certified here.
            if self.name not in p.defeated_bosses:
                p.changed_door_cells.update(t["cell"] for t in state.get("map", {}).get("cells", [])
                    if t.get("visible") and t.get("observed") is not False and t.get("terrain") == 5)
        elif any("tengu:" in t.lower() and "let's make this interesting" in t.lower()
                 for t in state.get("ui", {}).get("texts", [])):
            self.transitioning = True
        return won

    def transition(self, p, state, enemies):
        if not self.transitioning or enemies or state.get("danger_cells"):
            return None
        try:
            from .survival_policy import is_hostile
        except ImportError:
            from survival_policy import is_hostile
        if any(is_hostile(obj) for obj in state.get("objects", [])):
            return None  # Engagement filtering is not proof the route has no enemies.
        # Use observed geometry changes, not a phase oracle, seeded layout or
        # hard-coded trigger coordinate. Safety leaves still precede this leaf.
        previous = p.paths(state)
        doors = [cell for cell in p.changed_door_cells if cell in previous
                 and cell != state["hero"]["cell"] and p.tiles[cell]["terrain"] == 5]
        p.planner.report["boss_transition"] = {
            "boss": "tengu", "status": "traverse-changed-door" if doors else "explore-observed-routes",
            "steps": self.transition_steps, "observed_doors": sorted(doors)}
        if not doors:
            return None  # Normal exploration reveals more of the public route.
        if self.transition_steps >= 64:
            p.stop_no_safe_action("Tengu transition: observed-door traversal budget exhausted")
        for cell in sorted(doors, key=lambda c: len(p.route(previous, c))):
            action = p.toward(state, cell, "boss: tengu traverse observed transition door",
                              previous, intent=Intent.BOSS)
            if action:
                self.transition_steps += 1
                return action
        return None

    def evade(self, p, state, enemies, distance, neighbors):
        # Bomb position is a visible, unpickable heap; radius is a public rule.
        # Do not read Tengu's bomb buff, timer, or future teleport destinations.
        danger = set(state.get("danger_cells", []))
        for obj in state.get("objects", []):
            if obj["name"].lower() == "smoke bomb" and "tengu" in obj.get("description", "").lower():
                danger.update(c for c in p.tiles if distance(c, obj["cell"], state["map"]["width"]) <= 2)
        self.avoid_cells = danger
        try:
            return super().evade(p, dict(state, danger_cells=sorted(danger)), enemies, distance, neighbors)
        except BossEscapeBlocked:
            # A smoke bomb is not an instantaneous laser: its countdown is
            # literally rendered as floating text. Never inspect the bomb buff
            # or assume a fresh timer for a bomb first encountered late.
            counts = [int(t.strip()[0]) for t in state.get("ui", {}).get("texts", [])
                      if re.fullmatch(r"[123]\.\.\.", t.strip())]
            pos, width, height = state["hero"]["cell"], state["map"]["width"], state["map"]["height"]
            buffs = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
            if not counts or pos in state.get("danger_cells", []) or any(s in buffs for s in ("root", "vertigo", "paralys")):
                raise
            try:
                from .combat_items import unencumbered
            except ImportError:
                from combat_items import unencumbered
            if not unencumbered(state):
                raise
            move_time = (2 if any(s in buffs for s in ("slow", "crippl", "chill")) else 1) / (3 if "haste" in buffs else 1)
            occupied = {o["cell"] for o in state.get("objects", []) if not o.get("top_item")}
            previous, queue = {pos: None}, deque([pos])
            while queue:
                cell = queue.popleft()
                route = p.route(previous, cell)
                if (len(route)-1)*move_time > min(counts):
                    continue
                if cell not in danger:
                    return p.cell(route[1], "boss: tengu staged escape within rendered bomb countdown")
                for c in neighbors(cell, width, height):
                    if c not in previous and c not in state.get("danger_cells", []) and c not in p.loot \
                            and p.walkable(c, occupied) and p.tiles[c]["terrain"] not in {5,7,8,22,37}:
                        previous[c] = cell
                        queue.append(c)
            raise

    def choose(self, p, state, enemies, distance, neighbors):
        transition = self.transition(p, state, enemies)
        if transition:
            return transition
        action = super().choose(p, state, enemies, distance, neighbors)
        if action:
            self.hazard_waits = 0
            return action
        if self.target(state, enemies):
            if self.hazard_waits < 3:
                self.hazard_waits += 1
                return p.decision({"type": "wait"}, "boss: tengu bounded hold outside advertised hazards", intent=Intent.BOSS)
            p.stop_no_safe_action("Tengu: no safe advertised-hazard-free approach or usable attack")
        return None


class DM300Strategy(ObservedBossStrategy):
    def __init__(self):
        super().__init__("dm-300", 15)
        self.pylon_search_steps = 0

    def target(self, state, enemies):
        boss = super().target(state, enemies)
        if boss and "cannot be damaged" in boss.get("description", "").lower():
            return next((o for o in state.get("objects", []) if o["name"].lower() == "power pylon"
                         and "currently surging" in o.get("description", "").lower()), None)
        return boss

    def choose(self, p, state, enemies, distance, neighbors):
        target = self.target(state, enemies)
        if target and target["name"].lower() == "power pylon" and distance(state["hero"]["cell"], target["cell"], state["map"]["width"]) <= 1:
            danger = {c for c in p.tiles if distance(c, target["cell"], state["map"]["width"]) <= 1}
            escape = p.retreat(state, enemies+[target], danger)
            if escape and escape.action.get("cell") not in danger:
                escape.reason = "boss: dm-300 keep outside active pylon's rotating lightning radius"
                return escape
            transport = p.emergency_transport(dict(state, danger_cells=sorted(danger)), enemies+[target])
            if transport:
                return transport
            p.stop_no_safe_action("Active pylon: no safe ranged bank outside its lightning radius")
        boss = next((e for e in enemies if e["name"].lower() == self.name), None)
        if boss and "cannot be damaged" in boss.get("description", "").lower() and self.target(state, enemies) is None:
            # No guessed pylon coordinates or attacks on the invulnerable boss.
            escape = p.retreat(state, enemies)
            if escape and self.pylon_search_steps < 12:
                self.pylon_search_steps += 1
                return escape
            p.stop_no_safe_action("Supercharged DM-300: no publicly visible active pylon or safe retreat")
        self.pylon_search_steps = 0
        return super().choose(p, state, enemies, distance, neighbors)

    def minimum_range(self, target):
        return 2 if target["name"].lower() == "power pylon" else 1


class DwarfKingStrategy(ObservedBossStrategy):
    def __init__(self):
        super().__init__("king of dwarves", 20)

    def target(self, state, enemies):
        # Killing visible summons is useful in all phases and avoids wasting
        # limited charges on an unobserved/assumed vulnerable king.
        return next((e for e in enemies if e["name"].lower() in {"dwarf warlock", "dwarf monk", "dwarven ghoul"}), None) or super().target(state, enemies)


class YogStrategy(ObservedBossStrategy):
    def __init__(self):
        super().__init__("yog-dzewa", 25)
        self.eye_cell = None
        self.lure_steps = 0

    def target(self, state, enemies):
        eye = super().target(state, enemies)
        if eye and "cell" in eye:
            self.eye_cell = eye["cell"]
        fists = [e for e in enemies if "fist" in e["name"].lower()]
        if fists:
            width = state.get("map", {}).get("width")
            if self.eye_cell is not None and width:
                fists = [e for e in fists if max(abs(e["cell"]%width-self.eye_cell%width), abs(e["cell"]//width-self.eye_cell//width)) > 4]
            return next(iter(fists), None)
        return eye

    def choose(self, p, state, enemies, distance, neighbors):
        target = self.target(state, enemies)
        fists = [e for e in enemies if "fist" in e["name"].lower()]
        if fists and target is None and self.eye_cell is not None:
            pos, width = state["hero"]["cell"], state["map"]["width"]
            steps = [c for c in GooStrategy.safe_steps(p, state, enemies, neighbors)
                     if c not in state.get("danger_cells", []) and distance(c, self.eye_cell, width) > distance(pos, self.eye_cell, width)]
            if steps and self.lure_steps < 12:
                self.lure_steps += 1
                return p.cell(max(steps, key=lambda c: min(distance(c, e["cell"], width) for e in fists)),
                              "boss: yog lure shielded fists away from observed immobile eye")
            p.stop_no_safe_action("Yog fists remain inside observed eye's protective radius; no bounded safe lure")
        self.lure_steps = 0
        if target and target["name"].lower() == "rotting fist" and hasattr(p, "inspect_enemy"):
            observed = p.inspection_cache
            if not observed or observed["cell"] != target["cell"]:
                inspected = p.inspect_enemy(target)
                if inspected:
                    return inspected
            elif "bleeding" in observed["buffs"]:
                # Let the existing bleed work; refreshing it wastes damage.
                others = [e for e in enemies if e is not target and "fist" in e["name"].lower()]
                for other in others:
                    if self.eye_cell is None or distance(other["cell"], self.eye_cell, state["map"]["width"]) > 4:
                        attack = p.best_attack(state, other)
                        if attack:
                            attack.reason = "boss: yog attack second fist while inspected rotting fist bleeds"
                            return attack
                retreat = p.retreat(state, enemies)
                if retreat:
                    retreat.reason = "boss: yog withdraw while inspected bleeding deals damage"
                    return retreat
            p.stop_no_safe_action("Rotting fist is visibly bleeding; no safe alternative to refreshing its damage")
        return super().choose(p, state, enemies, distance, neighbors)


def create_strategies():
    return {"goo": GooStrategy()}


def create_mage_strategies():
    """Observed boss mechanics shared by normal and configured challenge games.

    Badder Bosses geometry is admitted separately through p.badder_bosses.
    """
    strategies = [GooStrategy(), TenguStrategy(), DM300Strategy(), DwarfKingStrategy(), YogStrategy()]
    return {s.name: s for s in strategies}


def create_challenge_strategies():
    """Compatibility name; creating strategies does not enable a challenge."""
    return create_mage_strategies()


def strategy_for(state, strategies):
    for obj in state.get("objects", []):
        strategy = strategies.get(obj["name"].lower())
        if strategy and state.get("depth") == strategy.depth:
            return strategy
    return next((s for s in strategies.values() if s.depth == state.get("depth")), None)
