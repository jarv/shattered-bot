"""Conservative sewer-room recognition from visible/remembered observations only.

These are explicit skips, not claims that a room has been cleared. No room IDs,
generation data, or hidden actor state are used.
"""

from collections import deque


ROOM_ACTORS = {"red sentry", "giant piranha", "phantom piranha", "animated statue", "armored statue", "rot lasher", "rot heart"}
CONTAINERS = {"chest", "locked chest", "crystal chest", "tomb", "skeleton", "skeletal remains", "remains"}


def container_name(obj):
    """Name for container hazards, not for identifying an observed item heap."""
    name = obj.get("name", "").lower()
    if name == "skeleton key" and obj.get("top_item", {}).get("name", "").lower() == name:
        # The public heap item is not unopened bones. Do not infer this from
        # the title alone, and do not waive terrain, actor or mimic checks.
        return ""
    return name


def fire_barrier(tile):
    """Recognize the rendered eternal-fire description, not an internal blob ID."""
    text=" ".join(tile.get("effects",[])).replace("_","").lower()
    return "magical fire" in text or ("wall" in text and "fire" in text
        and "caused by magic" in text and "extinguish" in text)


def adjacent(cell, width, height):
    x, y = cell % width, cell // width
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        if 0 <= x + dx < width and 0 <= y + dy < height:
            yield (y + dy) * width + x + dx


def component(start, tiles, allowed, width, height):
    found, queue = {start}, deque([start])
    while queue:
        for cell in adjacent(queue.popleft(), width, height):
            if cell not in found and tiles.get(cell, {}).get("terrain") in allowed:
                found.add(cell)
                queue.append(cell)
    return found


def assess(tiles, actors, loot, width, height, harmless_effect=None, rot_quest=False):
    blocked, skipped, notes = set(), set(), []
    for actor in actors.values():
        name, pos = actor["name"].lower(), actor["cell"]
        blocked.add(pos)
        if name == "red sentry":
            room = component(pos, tiles, {1, 11, 14, 25, 26}, width, height)
            blocked.update(c for c in room if tiles.get(c, {}).get("terrain") == 14)
            skipped.update(room)
            notes.append({"kind": "sentry", "cell": pos, "reason": "Requires a planned haste round trip; never attack or rest on exposed flooring"})
        elif name in {"rot lasher", "rot heart"}:
            # The visible quest plants identify this room. Flood only observed
            # interior: walls and door thresholds delimit it, not generated IDs.
            garden = component(pos, tiles, {1, 2, 3, 9, 11, 14, 15, 19, 20, 29, 30, 32}, width, height)
            if not rot_quest:
                blocked.update(garden)
                skipped.update(garden)
            if name == "rot lasher":
                x, y = pos % width, pos // width
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if 0 <= x+dx < width and 0 <= y+dy < height:
                            blocked.add((y+dy)*width+x+dx)
            notes.append({"kind": "rot garden quest", "cell": pos,
                          "reason": "Active Wandmaker: avoid lasher melee and gas; preserve seed from fire" if rot_quest else
                          "Wandmaker quest detour: skip the room and lasher melee reach; never rest, plant, or loot inside"})
        elif "piranha" in name:
            pool = component(pos, tiles, {29}, width, height)
            # Piranhas cannot leave water, but can melee a hero on the bank,
            # including diagonally. Buffer the whole connected pool because
            # a visible piranha can swim along it between observations.
            shore = set()
            for cell in pool:
                x, y = cell % width, cell // width
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if 0 <= x + dx < width and 0 <= y + dy < height:
                            neighbor = (y + dy) * width + x + dx
                            if tiles.get(neighbor, {}).get("terrain") in {1, 2, 3, 5, 6, 11, 14, 15, 19, 20, 29}:
                                shore.add(neighbor)
            blocked.update(pool | shore)
            skipped.update(pool | shore)
            notes.append({"kind": "piranha pool", "cell": pos, "reason": "Avoid the water and adjacent banks within melee reach; defer until a ranged/invisibility plan is implemented"})
        elif "statue" in name:
            notes.append({"kind": "animated statue", "cell": pos, "reason": "Do not awaken or attack an optional high-risk guardian"})
    for cell, tile in tiles.items():
        if tile.get("effects") and not all("power of health radiates" in e.lower() or harmless_effect and harmless_effect(e) for e in tile["effects"]):
            blocked.add(cell)
            notes.append({"kind": "gas/fire", "cell": cell, "reason": "Requires identified protection/extinguishing resource and a return-time budget"})
        elif tile["terrain"] == 13:
            blocked.add(cell)
            notes.append({"kind": "barricaded storage", "cell": cell, "reason": "Requires a controlled burn and waiting for the fire to expire"})
        elif tile["terrain"] == 0 or (tile["terrain"] == 18 and
                len(component(cell, tiles, {18}, width, height)) >= 3):
            blocked.add(cell)
            notes.append({"kind": "chasm/trap", "cell": cell, "reason": "Requires a levitation round-trip plan"})
    for cell, obj in loot.items():
        if any(word in container_name(obj) for word in ("tomb", "skeleton", "crystal chest")):
            blocked.add(cell)
            notes.append({"kind": "crypt/choice container", "cell": cell, "reason": "Do not open on a transit route; preparation or a resource choice is needed"})
    skipped.update(blocked)
    try:
        from .summoning_tactics import rooms, suspected_rooms
    except ImportError:
        from summoning_tactics import rooms, suspected_rooms
    for room in rooms(tiles, width, height):
        blocked.update(room)
        skipped.update(room)
        notes.append({"kind":"summoning room", "cell":min(room),
                      "reason":"Remote activation from prepared exterior choke; never enter the active field"})
    for room,door in suspected_rooms(tiles,loot,width,height):
        blocked.update(room)
        skipped.update(room)
        notes.append({"kind":"suspected summoning room","cell":min(room),"door":door,
                      "reason":"Central bones in plain enclosed chamber; search from doorway before entry"})
    return blocked, skipped, notes
