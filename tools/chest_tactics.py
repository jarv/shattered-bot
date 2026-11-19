"""Use matching journal keys; crystal rewards come only from inspection text."""


def eligible_chests(loot, keys):
    allowed = set()
    crystal = []
    for cell, obj in loot.items():
        name = obj["name"].lower()
        if obj.get("for_sale"):
            continue
        if name == "locked chest" and keys.get("golden", 0):
            allowed.add(cell)
        if name == "crystal chest" and keys.get("crystal", 0):
            description = obj.get("description", "").replace("_", "").lower()
            if "artifact" in description:
                continue
            category = 0 if "a wand" in description else 1 if "a ring" in description else None
            if category is not None:
                crystal.append((category, cell))
    # Pick the useful category before making any path through a crystal display.
    if crystal:
        best = min(c[0] for c in crystal)
        allowed.update(cell for rank, cell in crystal if rank == best)
    return allowed
