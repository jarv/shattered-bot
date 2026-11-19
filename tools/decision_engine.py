"""Experimental goal arbitration and relative risk scoring, from observations only.

Scores are heuristics, not inferred monster HP, damage, speed, or hit statistics.
Special enemies and boss warnings retain their dedicated safety controllers.
"""
from collections import deque
from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path

try:
    from .policy_decision import Intent
    from .combat_items import magic_score, physical_score, stats, known_cursed
except ImportError:
    from policy_decision import Intent
    from combat_items import magic_score, physical_score, stats, known_cursed


SPECIAL = {"goo", "tengu", "sewer snake", "wraith", "tormented spirit", "skeleton",
           "necromancer's skeleton", "dwarven skeleton", "necromancer", "spectral necromancer"}
ZAPPERS = {"dm-100", "gnoll shaman", "dwarf warlock"}
NO_STEP = {5, 7, 8, 10, 21, 22, 31, 37, 38}


def source_revision():
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


@dataclass
class Goal:
    kind: str
    target: int
    depth: int
    reason: str
    remaining: int = 12


@dataclass
class Candidate:
    action: dict
    reason: str
    score: float
    risk: dict
    target: int | None = None


class RiskModel:
    def __init__(self, policy, state, enemies, distance, line_clear):
        self.p, self.state, self.enemies = policy, state, enemies
        self.distance, self.line_clear = distance, line_clear
        self.width = state["map"]["width"]
        self.hp = state["hero"]["hp"] / max(1, state["hero"]["max_hp"])
        self.weight = 2.5 + 8 * (1 - self.hp) ** 2

    def at(self, cell):
        if hasattr(self.p, "challenge_combat"):
            try:
                from .challenge_combat import exposure
            except ImportError:
                from challenge_combat import exposure
            return exposure(self.p, self.state, self.enemies, cell, self.distance, self.line_clear)
        melee = ranged = fast = 0.0
        for enemy in self.enemies:
            if enemy.get("sleeping"):
                continue
            dist = self.distance(cell, enemy["cell"], self.width)
            if dist <= 1:
                melee += 0.8 if enemy["name"].lower() in ZAPPERS else 1
            elif enemy["name"].lower() in ZAPPERS and self.line_clear(cell, enemy["cell"], self.width, self.p.tiles):
                ranged += 2
            elif dist == 2 and "extremely fast" in enemy.get("description", "").lower():
                fast += 0.6
        return {"melee": melee, "ranged": ranged, "fast_pursuit": fast,
                "exposure": melee + ranged + fast}

    def cost(self, cell, duration=1):
        return self.at(cell)["exposure"] * self.weight * duration


class DecisionEngine:
    def __init__(self):
        self.goal = None
        self.edges = deque(maxlen=8)
        self.recovery_waits = 0
        self.positioning_steps = 0
        self.report = {}

    def reset(self):
        self.__init__()

    def begin(self):
        self.report = {"goal": asdict(self.goal) if self.goal else None}

    def track_navigation(self, state, target, reason, intent):
        kinds = {Intent.LOOT: "loot", Intent.EXPLORE: "explore",
                 Intent.SHOP: "shop", Intent.APPROACH: "combat"}
        if intent in kinds:
            kind = kinds[intent]
            if not self.goal or (self.goal.kind, self.goal.target) != (kind, target):
                self.goal = Goal(kind, target, state["depth"], reason)

    def continue_navigation(self, p, state, enemies):
        goal = self.goal
        if not goal or enemies:
            return None
        pos = state["hero"]["cell"]
        valid = goal.depth == state["depth"] and goal.remaining > 0 and goal.target != pos
        if goal.kind == "loot":
            valid &= goal.target in p.loot and not p.loot.get(goal.target, {}).get("for_sale")
        elif goal.kind == "combat":
            valid &= goal.target in p.enemy_sightings and not p.enemy_sightings.get(goal.target, {}).get("sleeping")
        elif goal.kind == "shop":
            valid &= state["depth"] not in p.shop_visited_floors and not p.loot.get(goal.target, {}).get("for_sale")
        elif goal.kind not in {"explore", "shop"}:
            valid = False
        previous = p.paths(state)
        if not valid or goal.target not in previous:
            self.goal = None
            return None
        step = p.route(previous, goal.target)[1]
        goal.remaining -= 1
        self.report = {"goal": asdict(goal), "selection": "continue validated navigation goal"}
        # Commit only an ordinary navigation step, never an attack at a memory.
        # Following a last-seen enemy is ordinary exploration, not an attack
        # against live knowledge. Keep movement/loop accounting active here.
        intent = {"shop": Intent.SHOP, "combat": Intent.EXPLORE,
                  "loot": Intent.LOOT, "explore": Intent.EXPLORE}[goal.kind]
        return p.cell(step, goal.reason, intent=intent)

    @staticmethod
    def resources(p, state):
        magic = p.charged_magic(state)
        known_charges = sum(int(i["status"].split("/")[0]) for i in magic
                            if (i.get("status") or "?").split("/")[0].isdigit())
        return {"food": sum(i.get("quantity", 1) for i in p.food_items(state)),
                "known_usable_charges": known_charges,
                "unknown_charge_wands": sum(not (i.get("status") or "?").split("/")[0].isdigit() for i in magic),
                "healing_potions": sum(i.get("quantity", 1) for i in state["inventory"]
                                       if "potion of healing" in i["name"].lower() and p.item_action_allowed(i, "DRINK")),
                "poisonous_healing_potions": sum(i.get("quantity", 1) for i in state["inventory"]
                                               if "potion of healing" in i["name"].lower() and not p.item_action_allowed(i, "DRINK")),
                "equipped_armor": next((i["name"] for i in state["inventory"]
                                        if i.get("equipped") and stats(i) and stats(i)[0] == "armor"), None)}

    @staticmethod
    def eligible(state, enemies):
        active = [e for e in enemies if not e.get("sleeping")]
        return bool(active) and not state.get("danger_cells") and not any(e["name"].lower() in SPECIAL for e in active)

    def recover(self, p, state, enemies):
        if enemies or state.get("danger_cells") or p.tiles[state["hero"]["cell"]].get("effects"):
            return None
        hero = state["hero"]
        hp = hero["hp"] / max(1, hero["max_hp"])
        buffs = " ".join(b["name"].lower() for b in hero.get("buffs", []))
        ledger = self.resources(p, state)
        if "locked" in buffs or "starving" in buffs:
            return None
        food = p.food_items(state)
        if "hungry" in buffs and hp < 0.6 and food:
            self.goal = None
            self.report = {"selection": "feed before entering another fight wounded", "resources": ledger}
            return p.use(food[0], "EAT", "recover: planned meal before further exploration", intent=Intent.RECOVER)
        # Let the existing sheltered seed controller use sungrass first.
        if not getattr(p, "barren_land", False) and hp < 0.65 and any("seed of sungrass" in i["name"].lower() for i in state["inventory"]):
            return None
        budget = p.recovery_limit(state, "hungry" in buffs)
        if "hungry" in buffs and not food:
            budget = 8 if hp < 0.35 else 0
        needs_health = hp < (0.95 if state["depth"] == 5 else 0.8)
        needs_charge = state["depth"] >= 4 and ledger["known_usable_charges"] < 2 and bool(food)
        if (needs_health or needs_charge) and self.recovery_waits < budget:
            self.recovery_waits += 1
            self.report = {"selection": "bounded recovery reserve", "resources": ledger,
                           "floor_recovery_inputs": self.recovery_waits, "budget": budget}
            return p.decision({"type": "wait"}, "recover: planned health and magic reserve", intent=Intent.RECOVER)
        return None

    def tactical(self, p, state, enemies, distance, neighbors, line_clear):
        active = [e for e in enemies if not e.get("sleeping")]
        if not self.eligible(state, enemies):
            return None
        pos, width = state["hero"]["cell"], state["map"]["width"]
        model = RiskModel(p, state, active, distance, line_clear)
        current = model.at(pos)
        ledger = self.resources(p, state)
        candidates = []
        weapon = next((i for i in state["inventory"] if i.get("equipped") and stats(i) and stats(i)[0] == "melee"), None)
        for enemy in active:
            dist = distance(pos, enemy["cell"], width)
            bar = enemy.get("health_bar")
            wounded = 1 - bar[0] / bar[1] if bar and bar[1] > 0 else 0
            commitment = 1 if self.goal and self.goal.kind == "combat" and self.goal.target == enemy["cell"] else 0
            bonus = 2 * wounded + commitment
            if dist == 1 and not (weapon and known_cursed(weapon)) and p.attack_kind_allowed(state,enemy,'melee'):
                damage = physical_score(weapon, state["hero"].get("strength", 0)) if weapon else 2
                duration = 1.5 if weapon and "rather slow" in weapon.get("description", "").lower() else 1
                score = 0.75 * p.attack_score(state, enemy, "melee", damage) + bonus - model.cost(pos, duration)
                candidates.append(Candidate({"type": "cell", "cell": enemy["cell"]}, "combat: planner melee", score, current, enemy["cell"]))
            if not p.shot_clear(state, enemy["cell"]):
                continue
            for item in p.charged_magic(state):
                if not p.target_allowed(item, enemy):
                    continue
                charge_cost = 0.7 + 1 / max(1, ledger["known_usable_charges"])
                damage = p.attack_score(state, enemy, "magic", magic_score(item))
                if damage <= 0:
                    continue
                score = damage + bonus - model.cost(pos) - charge_cost
                if "living earth" in item["name"].lower() and not getattr(p, "faith_is_my_armor", False):
                    score += (1 - model.hp) * 2  # Publicly described protective armor.
                candidates.append(Candidate({"type": "item", "id": item["id"], "action": "ZAP"},
                                            "combat: planner reliable magic", score, current, enemy["cell"]))
            for item in state["inventory"]:
                value = stats(item)
                if value and value[0] == "thrown" and "THROW" in item.get("actions", []) and "force cube" not in item["name"].lower() \
                        and p.attack_kind_allowed(state,enemy,'thrown'):
                    damage = physical_score(item, state["hero"].get("strength", 0))
                    if damage > 0:
                        score = p.attack_score(state, enemy, "thrown", damage * (0.5 if dist == 1 else 0.8)) + bonus - model.cost(pos)
                        candidates.append(Candidate({"type": "item", "id": item["id"], "action": "THROW"},
                                                    "combat: planner thrown weapon", score, current, enemy["cell"]))
        nearest = min(active, key=lambda e: distance(pos, e["cell"], width))
        occupied = {e["cell"] for e in enemies}
        buffs = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
        duration = (2 if "crippled" in buffs or "slowed" in buffs else 1) / (3 if "haste" in buffs else 1)
        for cell in neighbors(pos, width, state["map"]["height"]):
            if self.positioning_steps >= 12:
                break
            if not p.walkable(cell, occupied) or p.tiles[cell]["terrain"] in NO_STEP or p.tiles[cell].get("plant") or cell in p.loot:
                continue
            risk = model.at(cell)
            if model.hp < 0.5 and risk["ranged"] > current["ranged"]:
                continue
            progress = distance(pos, nearest["cell"], width) - distance(cell, nearest["cell"], width)
            score = 1.5 * progress - 1 - model.cost(cell, duration)
            score += 2 * max(0, current["exposure"] - risk["exposure"])
            score -= 3 * self.edges.count((cell, pos))
            candidates.append(Candidate({"type": "cell", "cell": cell}, "combat: planner reposition", score, risk))
        if not candidates:
            return None
        chosen = max(candidates, key=lambda c: c.score)
        self.report = {"selection": chosen.reason, "score": round(chosen.score, 3), "risk": chosen.risk,
                       "resources": ledger, "alternatives": [
                           {"reason": c.reason, "score": round(c.score, 3), "risk": c.risk}
                           for c in sorted(candidates, key=lambda c: c.score, reverse=True)[:4]]}
        if chosen.target is not None:
            self.positioning_steps = 0
            self.goal = Goal("combat", chosen.target, state["depth"], "explore: continue last-seen combat approach")
        else:
            self.positioning_steps += 1
            self.edges.append((pos, chosen.action["cell"]))
        self.report["goal"] = asdict(self.goal) if self.goal else None
        if chosen.action["type"] == "item":
            item = next(i for i in state["inventory"] if i["id"] == chosen.action["id"])
            return p.use(item, chosen.action["action"], chosen.reason, target=chosen.target)
        return p.cell(chosen.action["cell"], chosen.reason,
                      intent=Intent.OTHER if chosen.target is not None else Intent.REPOSITION)
