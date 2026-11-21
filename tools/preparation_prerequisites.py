"""Information gathering for a blocked objective, not presumed protection."""
try:
    from .consumable_tactics import base_name
    from .policy_decision import Intent
    from .hunger_budget import admits
    from .mapping_knowledge import complete
    from .policy_geometry import neighbors
except ImportError:
    from consumable_tactics import base_name
    from policy_decision import Intent
    from hunger_budget import admits
    from mapping_knowledge import complete
    from policy_geometry import neighbors


def reconnaissance(p, state):
    """Use known information resources once when observed routes border unknown space."""
    if complete(p, state) or state["depth"] in p.mapping_attempts \
            or state.get("danger_cells") or p.recent_threats or p.unseen_damage_turns:
        return None
    pos = state["hero"]["cell"]
    tile = p.tiles.get(pos, {})
    buffs = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
    if not tile.get("visible") or tile.get("terrain") not in {1, 3, 6, 9, 11, 14, 19, 20, 29} \
            or any(tile.get(k) for k in ("effects", "plant", "trap")) \
            or pos in p.room_blocked or pos in p.blocked or pos in p.neutral_actor_cells \
            or any(b in buffs for b in ("blind", "invisib", "magic immun", "vertigo", "paral")):
        return None
    width, height = state["map"]["width"], state["map"]["height"]
    paths = p.paths(state)
    gaps = {n for c in paths for n in neighbors(c, width, height)
            if not p.tiles.get(n, {}).get("observed") and not p.tiles.get(n, {}).get("mapped")}
    if not gaps or not admits(p, state, 1):
        return None
    nearby = any((c % width-pos % width)**2+(c // width-pos // width)**2 <= 18**2 for c in gaps)
    choices = [("stone of clairvoyance", "THROW"), ("scroll of magic mapping", "READ")]
    for name, action in choices:
        if action == "THROW" and not nearby:
            continue
        item = next((i for i in state["inventory"] if base_name(i) == name
                     and action in i.get("actions", []) and p.item_action_allowed(i, action)), None)
        if item:
            # Existing mapping bookkeeping rolls back on explicit rejection.
            p.mapping_attempts.add(state["depth"])
            return p.use(item, action, "planning: reveal missing preparation geometry; reobserve before execution",
                         **({"target": pos} if action == "THROW" else {}), intent=Intent.REPOSITION)
    return None
