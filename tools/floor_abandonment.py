"""Bounded floor abandonment after a recorded planner failure, never blind escape."""
import copy

try:
    from .policy_decision import Intent, PlannerStuck
    from .survival_policy import is_hostile
    from .consumable_tactics import base_name, unknown_potion
    from .priority_resources import targets
    from .pickup_priority import food
    from .escape_commitment import reverses
    from .hunger_budget import admits, travel_cost
except ImportError:
    from policy_decision import Intent, PlannerStuck
    from survival_policy import is_hostile
    from consumable_tactics import base_name, unknown_potion
    from priority_resources import targets
    from pickup_priority import food
    from escape_commitment import reverses
    from hunger_budget import admits, travel_cost


class FloorAbandonment:
    """Run-owned diagnostics survive policy transaction rollback.

    Proposals spend no action budget; only observe() advances progress. At most
    one episode per depth/branch, 64 accepted inputs and eight stalled inputs.
    """
    def __init__(self, policy):
        self.policy = policy
        self.incidents = []
        self.active = None
        self.attempted = set()
        self.route_rejections = []

    def hard_gate(self, state):
        p = self.policy
        if getattr(p, "stop_on_incomplete_loot", False):
            return "strict loot completion requested"
        if any(getattr(p, key, None) for key in (
                "potion_stash", "trap_payload_return", "room_journey", "drop_plan",
                "puzzle_probe", "wood_burn_plan", "menu_plan")):
            return "owned preparation/retrieval must finish first"
        if any(not food(o.get("top_item", o)) for o in targets(p).values()):
            return "observed mandatory progression pickup remains"
        if any(base_name(i) == "potion of strength" for i in state["inventory"]):
            return "held strength must be consumed first"
        if not getattr(p, "strength_identified", False) and any(unknown_potion(i) for i in state["inventory"]):
            return "mandatory potion discovery remains"
        if getattr(p, "ghost_quest", {}).get("stage") in {"reward", "claiming", "collect_dropped"}:
            return "owned quest reward retrieval remains"
        return None

    @staticmethod
    def interrupted(state):
        if not state.get("hero"):
            return True
        buffs = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
        return (state.get("status") != "ready" or state.get("modal")
                or state.get("danger_cells") or state["hero"]["hp"] <= 0
                or any(is_hostile(o) and not o.get("sleeping") for o in state.get("objects", []))
                or any(t in buffs for t in ("burn", "poison", "bleed", "ooze", "vertigo", "paral",
                                           "root", "frozen", "chill", "drowsy", "sleep", "levitat")))

    def route(self, state, target=None):
        p = self.policy
        self.route_rejections = []
        forbidden = p.navigation_barriers(state, Intent.DESCEND)
        allowed = {1, 2, 3, 5, 6, 8, 9, 11, 14, 19, 20, 29}
        excluded = {c for c, t in p.tiles.items()
                    if c in forbidden or not t.get("observed") or t.get("terrain") not in allowed
                    or any(t.get(k) for k in ("trap", "plant", "effects"))
                    or c in p.loot or c in p.neutral_actor_cells}
        # Sleepers and remembered actors also obstruct, even if not attacking.
        excluded.update(o["cell"] for o in state.get("objects", []) if is_hostile(o))
        if state["hero"]["cell"] in excluded:
            return None
        paths = p.paths(state, excluded)
        for cell, tile in p.tiles.items():
            if tile.get("terrain") == 8 and (target is None or cell == target) and (cell not in paths or cell in excluded):
                self.route_rejections.append({"cell": cell, "reason": "unobserved, unsafe or unreachable in admitted graph"})
        candidates = [c for c in paths if c not in excluded and p.tiles.get(c, {}).get("terrain") == 8
                      and (target is None or c == target)]
        choices = []
        for cell in candidates:
            route = p.route(paths, cell)
            if len(route) > 64:
                self.route_rejections.append({"cell": cell, "reason": "route exceeds accepted-input allowance"})
                continue
            step = route[1] if len(route) > 1 else cell
            if not p.tiles.get(step, {}).get("visible") or reverses(p, state, step):
                self.route_rejections.append({"cell": cell, "reason": "next step unseen or protected escape reversal"})
                continue
            if not p.escape_step_allowed(state, step) or not admits(p, state, travel_cost(state, p, route)+10):
                self.route_rejections.append({"cell": cell, "reason": "current escape or hunger admission declined"})
                continue
            choices.append(route)
        return min(choices, key=lambda r: (len(r), r[-1])) if choices else None

    def start(self, state, failure, report, index):
        reason = failure.blocker
        incident = {"id": len(self.incidents)+1, "index": index, "kind": "planner-failure", "severity": "error",
                    "reason": reason, "depth": state["depth"], "branch": state.get("branch", 0),
                    "cell": state["hero"]["cell"], "hp": state["hero"]["hp"],
                    "review_priority": "high", "policy_report": copy.deepcopy(report),
                    "status": "declined", "accepted_actions": 0, "stalled_actions": 0,
                    "collection_credited": False}
        self.incidents.append(incident)
        floor = (state["depth"], state.get("branch", 0))
        if floor in self.attempted:
            incident["recovery_reason"] = "one recovery episode per floor already used"
            return None
        # Only navigation/no-progress and optional-room exhaustion are eligible.
        if not any(text in reason.lower() for text in (
                "hungry no-progress recovery exhausted", "navigation-loop",
                "navigation loop", "piranha-room chest remains uncollected",
                "observed loot incomplete")):
            incident["recovery_reason"] = "failure is not an optional-room or navigation exhaustion"
            return None
        if self.interrupted(state):
            incident["recovery_reason"] = "combat, hazard or impairment requires survival arbitration"
            return None
        self.policy.update(state)
        incident["known_downstairs"] = sorted(c for c,t in self.policy.tiles.items() if t.get("terrain") == 8)
        incident["mandatory_pickups"] = [{"cell": c, "name": o["name"]} for c,o in targets(self.policy).items()
                                         if not food(o.get("top_item",o))]
        gate = self.hard_gate(state)
        if gate or self.policy.recent_threats or self.policy.unseen_damage_turns:
            incident["recovery_reason"] = gate or "recent threats/unexplained damage"
            return None
        route = self.route(state)
        incident["route_rejections"] = copy.deepcopy(self.route_rejections)
        if not route:
            incident["recovery_reason"] = "no observed hazard-admitted route to known downstairs"
            return None
        self.attempted.add(floor)
        incident.update(status="active", target=route[-1], initial_route=route,
                        best_distance=len(route)-1,
                        recovery_reason="abandon optional work; mandatory and safety gates retained")
        self.active = incident
        self.policy.defer_obligations(state, [{"kind": "floor-abandonment intent after planner incident",
                                              "incident": incident["id"], "reason": reason}],
                                      "Optional work deferred; no collection or floor-clear credit")
        # Preserve specific optional rewards too, not only the broad incident.
        try:
            from .loot_completion import required_loot
        except ImportError:
            from loot_completion import required_loot
        self.policy.defer_obligations(state, [
            {"kind": "uncollected observed item/chest", "cell": c, "name": o["name"]}
            for c, o in required_loot(self.policy).items()],
            "Bounded planner recovery descent; no collection credit")
        return self.propose(state, route)

    def stop(self, reason):
        self.active.update(status="exhausted", recovery_reason=reason)
        self.active = None
        raise PlannerStuck("Floor-abandonment recovery exhausted: " + reason)

    def propose(self, state, route):
        incident = self.active
        incident["last_distance"] = len(route)-1
        pos = state["hero"]["cell"]
        target = route[1] if len(route)>1 else pos
        decision = self.policy.cell(target, "recovery: bounded descent after recorded planner incident",
                                    intent=Intent.DESCEND)
        decision.controller = "floor-abandonment"
        decision.navigation_route = tuple(route)
        decision.floor_abandonment = incident["id"]
        return decision

    def next(self, state):
        if self.active is None:
            return None
        incident = self.active
        if incident["accepted_actions"] >= 64 or incident["stalled_actions"] >= 8:
            self.stop("accepted-action or no-progress budget reached")
        if self.interrupted(state):
            # Run the normal policy rather than moving through combat/hazards.
            return None
        self.policy.update(state)
        if (state["depth"], state.get("branch", 0)) != (incident["depth"], incident["branch"]):
            self.stop("displaced from original floor without verified descent receipt")
        gate = self.hard_gate(state)
        if gate:
            self.stop(gate)
        if self.policy.recent_threats or self.policy.unseen_damage_turns:
            return None
        route = self.route(state, incident["target"])
        incident["route_rejections"] = copy.deepcopy(self.route_rejections)
        if not route:
            self.stop("fresh route/visibility/hunger/safety check failed")
        return self.propose(state, route)

    def observe(self, before, decision, after):
        if self.active is None:
            return
        incident = self.active
        incident["accepted_actions"] += 1
        if after.get("hero", {}).get("hp", 1) <= 0:
            incident["status"] = "died"
            self.active = None
        elif (after.get("depth") == incident["depth"]+1
              and after.get("branch", 0) == incident["branch"]
              and getattr(decision, "floor_abandonment", None) == incident["id"]
              and decision.action.get("cell") == incident["target"]):
            incident["status"] = "descended"
            self.active = None
        elif getattr(decision, "floor_abandonment", None) == incident["id"] \
                and after.get("hero", {}).get("cell") != before["hero"]["cell"] \
                and after.get("hero", {}).get("cell") == decision.action.get("cell") \
                and incident.get("last_distance", 64) < incident["best_distance"]:
            incident["best_distance"] = incident["last_distance"]
            incident["stalled_actions"] = 0
        else:
            incident["stalled_actions"] += 1

    def rejected(self):
        if self.active:
            self.active.update(status="rejected", recovery_reason="API explicitly rejected proposed recovery input")
            self.active = None
