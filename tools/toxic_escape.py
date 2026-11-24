"""Leave observed toxic gas before recovery; no hidden gas map or blind steps."""
from collections import deque

try:
    from .policy_decision import Finished, Intent
    from .policy_geometry import neighbors
except ImportError:
    from policy_decision import Finished, Intent
    from policy_geometry import neighbors


def in_toxic_gas(state):
    if state.get("scene") != "GameScene" or state.get("status") != "ready" or state.get("modal"):
        return False
    pos = state.get("hero", {}).get("cell")
    tile = next((t for t in state.get("map", {}).get("cells", []) if t["cell"] == pos), {})
    return any("toxic gas" in effect.lower() for effect in tile.get("effects", []))


def escape(p, state):
    if not in_toxic_gas(state):
        return None
    # An owned gas retrieval already checks the observed immunity duration,
    # outbound/return budget, impairments and every next tile. Do not erase
    # that commitment merely because it has reached the protected cloud.
    try:
        from .room_tactics import remaining
    except ImportError:
        from room_tactics import remaining
    journey = getattr(p, "room_journey", None)
    if journey and journey.kind == "gas" and journey.depth == state.get("depth") \
            and state["hero"]["cell"] in journey.route \
            and remaining(state, "purification barrier") > 0:
        return None
    try:
        from .survival_policy import FLOOR, TRANSITIONS, HARMFUL_PLANTS, is_hostile
    except ImportError:
        from survival_policy import FLOOR, TRANSITIONS, HARMFUL_PLANTS, is_hostile
    if journey:
        try:
            from .reward_lifecycle import interrupt
        except ImportError:
            from reward_lifecycle import interrupt
        interrupt(p, "emergency toxic-gas escape preempted protected work")
    for plan in ("ranged_plan", "ambush_plan", "room_journey", "room_loot_plan"):
        if hasattr(p, plan):
            setattr(p, plan, None)  # Do not resume a stationary lure/loot commitment inside gas.
    pos = state["hero"]["cell"]
    buffs = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
    occupied = {o["cell"] for o in state.get("objects", []) if not o.get("top_item")}
    warnings = set(state.get("danger_cells", []))
    previous, queue = {pos: None}, deque([pos])
    candidates = []
    if not any(word in buffs for word in ("root", "paralys", "vertigo")):
        while queue:
            cell = queue.popleft()
            tile = p.tiles.get(cell, {})
            effects = tile.get("effects", [])
            if cell != pos and not any("toxic gas" in e.lower() for e in effects):
                candidates.append(cell)
                continue
            for step in neighbors(cell, state["map"]["width"], state["map"]["height"]):
                tile = p.tiles.get(step, {})
                if step in previous or step in occupied or step in warnings or step in p.blocked or step in p.loot \
                        or tile.get("observed") is False or tile.get("terrain") not in FLOOR - TRANSITIONS \
                        or (tile.get("trap") and tile.get("terrain") != 19) \
                        or tile.get("plant", "").lower() in HARMFUL_PLANTS \
                        or not p.escape_step_allowed(state, step):
                    continue
                # Clear of gas is not clear of other recognized room hazards:
                # a piranha bank otherwise wins over a longer ordinary exit,
                # then room escape sends us straight back into the cloud.
                # Keep gas traversal, but never route through or stop on a
                # gas-free tile already excluded by special-room assessment.
                if step in p.room_blocked and not any(
                        "toxic gas" in e.lower() for e in tile.get("effects", [])):
                    continue
                if any("toxic gas" not in e.lower() and not p.harmless_effect(e) for e in tile.get("effects", [])):
                    continue
                previous[step] = cell
                queue.append(step)
    if candidates:
        # A last-observed clear tile may now contain spreading gas. Reobserve
        # after ONE ordinary step; never claim an unseen destination is safe.
        destination = min(candidates, key=lambda c: (len(p.route(previous, c)),
                          not p.tiles[c].get("visible"), c))
        route = p.route(previous, destination)
        p.planner.report["toxic_gas_escape"] = {
            "status": "leave-cloud", "target": destination, "route_steps": len(route)-1,
            "target_currently_visible": bool(p.tiles[destination].get("visible")),
        }
        return p.cell(route[1], "hazard: leave toxic gas toward observed clear ground", intent=Intent.RETREAT)
    transport = p.emergency_transport(state, [o for o in state.get("objects", []) if is_hostile(o)])
    if transport and transport.action.get("type") != "wait":
        return transport
    # A boxed cloud is not exhausted while known purity can clear it. Shatter
    # on the hero's ordinary floor; drinking grants immunity but does not clear
    # the blocked route. This selects a rescue, never protection or loot credit.
    try:
        from .consumable_tactics import base_name
        from .room_supplies import use as use_room_supply, eligible
    except ImportError:
        from consumable_tactics import base_name
        from room_supplies import use as use_room_supply, eligible
    tile = p.tiles.get(pos, {})
    if tile.get("visible") and tile.get("observed") is not False \
            and tile.get("terrain") in {1, 2, 3, 5, 6, 9, 14, 15, 19, 20, 29, 30} \
            and not tile.get("plant") and (not tile.get("trap") or tile.get("terrain") == 19) \
            and pos not in warnings and not any(b in buffs for b in ("paralys", "vertigo")):
        purity = next((i for i in state.get("inventory", [])
                       if base_name(i) == "potion of purity" and i.get("identified")
                       and i.get("quantity", 1) > 0 and "THROW" in i.get("actions", [])
                       and eligible(p, i, "THROW", "emergency")), None)
        if purity:
            return use_room_supply(p, purity, "THROW",
                "survival: emergency known purity self-splash to clear boxed toxic gas",
                kind="emergency", target=pos)
    # This is a technical stop, not an admission failure that until-death
    # continuation can turn back into a stationary wait.
    raise Finished("blocked", "Toxic gas: no observed traversable exit or usable escape; refusing recovery waits",
                   kind="immediate-safety-emergency")
