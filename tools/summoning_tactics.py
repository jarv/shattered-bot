"""Remote summoning activation from an observed, exterior one-cell choke."""
from collections import deque
try:
    from .policy_geometry import neighbors, distance
    from .combat_items import stats, physical_score
    from .environment_tactics import payload
    from .policy_decision import Intent
except ImportError:
    from policy_geometry import neighbors, distance
    from combat_items import stats, physical_score
    from environment_tactics import payload
    from policy_decision import Intent


INTERIOR = {1,2,3,9,11,14,15,18,19,20,29,30}


def suspected_rooms(tiles, loot, width, height):
    """Central bones in a small plain rectangular chamber are a hypothesis."""
    result = []
    for cell, obj in loot.items():
        if obj.get("name","").lower() not in {"skeleton","skeletal remains"}:
            continue
        area, queue = {cell}, deque([cell])
        while queue and len(area) <= 36:
            for n in neighbors(queue.popleft(),width,height):
                if n not in area and tiles.get(n,{}).get("terrain") == 1:
                    area.add(n)
                    queue.append(n)
        xs, ys = {c%width for c in area}, {c//width for c in area}
        if not 3 <= len(xs) <= 6 or not 3 <= len(ys) <= 6 or len(area) != len(xs)*len(ys):
            continue
        if abs(cell%width-(min(xs)+max(xs))/2) > .5 or abs(cell//width-(min(ys)+max(ys))/2) > .5:
            continue
        if any(tiles.get(c,{}).get("terrain") != 1 or not tiles[c].get("observed")
               or tiles[c].get("effects") or tiles[c].get("plant") for c in area):
            continue
        if set(loot) & area != {cell}:
            continue
        edge = {n for c in area for n in neighbors(c,width,height)
                if n%width == c%width or n//width == c//width} - area
        doors = {c for c in edge if tiles.get(c,{}).get("terrain") in {5,6}}
        unknown = {c for c in edge if c not in tiles}
        if len(doors) == 1 and len(unknown) <= 1 and all(
                tiles.get(c,{}).get("terrain") in {4,12} for c in edge-doors-unknown):
            result.append((area,next(iter(doors))))
    return result


def inspect(p, state, enemies):
    if enemies or p.recent_threats or state.get("danger_cells"):
        return None
    w,h = state["map"]["width"],state["map"]["height"]
    pos = state["hero"]["cell"]
    for area,door in suspected_rooms(p.tiles,p.loot,w,h):
        p.planner.report["summoning_room"] = {"status":"suspected", "door":door,
            "reason":"central bones in small plain chamber; search before entering"}
        # Ordinary manual search reaches the first interior row from the door.
        # Two accepted searches are a bound, never clearance certification.
        if pos == door and p.trap_scan_cells[pos] < 2 and sum(p.trap_scan_cells.values()) < 6:
            if state["hero"].get("buffs") or state["hero"]["hp"] < .95*state["hero"]["max_hp"]:
                return None
            p.trap_scan_pending = {"depth":state["depth"],"branch":state.get("branch",0),
                                  "cell":pos,"traps":[]}
            action = p.decision({"type":"search"},"summoning: search central-bones chamber from doorway")
            action.controller = "trap-field-scan"
            action.summoning_scan = True
            return action
    return None

def rooms(tiles, width, height):
    """Flood observed space bounded by walls/doors, never generated room IDs."""
    found = []
    covered = set()
    for cell, tile in tiles.items():
        if cell in covered or tile.get("terrain") != 18 or tile.get("trap", "").lower() != "summoning trap":
            continue
        area, queue = {cell}, deque([cell])
        while queue and len(area) <= 36:
            for n in neighbors(queue.popleft(), width, height):
                if n not in area and tiles.get(n, {}).get("terrain") in INTERIOR:
                    area.add(n)
                    queue.append(n)
        covered.update(area)
        if len(area) <= 36:
            found.append(area)
    return found


def ready(p, state):
    """Conservative readiness heuristic, not a promise to survive a crowd.

    Start with sewer melee-only populations. Later ranged populations and
    champion rolls need additional control admission before deliberate summons.
    """
    hero = state["hero"]
    if state["depth"] > 4 or getattr(p, "hostile_champions", False):
        return False
    if hero["hp"] < .95 * hero["max_hp"] or hero.get("buffs"):
        return False
    gear = [i for i in state["inventory"] if i.get("equipped") and i.get("identified")
            and not i.get("known_cursed") and stats(i)
            and stats(i)[2] <= hero["strength"]]
    armor = max((physical_score(i, hero["strength"]) for i in gear if stats(i)[0] == "armor"), default=0)
    weapon = max((physical_score(i, hero["strength"]) for i in gear if stats(i)[0] == "melee"), default=0)
    # Weak challenge armor and unknown upgrades cannot certify a crowd fight.
    return not getattr(p, "faith_is_my_armor", False) and armor >= 3 and weapon >= 8


def choose(p, state, enemies):
    if enemies or p.recent_threats or state.get("danger_cells") or p.trap_payload_return:
        return None
    scan = inspect(p,state,enemies)
    if scan:
        return scan
    areas = rooms(p.tiles, state["map"]["width"], state["map"]["height"])
    if not areas:
        return None
    report = {"status": "blocked", "reason": "requires known crowd-ready gear, exterior choke and remote payload"}
    p.planner.report["summoning_room"] = report
    if not ready(p, state):
        return None
    item = payload(state)
    if not item or not p.item_action_allowed(item, "THROW"):
        return None
    w, h = state["map"]["width"], state["map"]["height"]
    pos = state["hero"]["cell"]
    paths = p.paths(state)
    for area in areas:
        if len(area) > 36 or pos in area:
            continue
        boundary = {n for c in area for n in neighbors(c,w,h)} - area
        doors = {c for c in boundary if p.tiles.get(c, {}).get("terrain") in {5,6}}
        if len(doors) != 1:
            continue
        door = next(iter(doors))
        if any(not p.tiles.get(c, {}).get("observed") or p.tiles[c]["terrain"] not in {4,12}
               for c in boundary - doors):
            continue
        # Stand on the exterior side. Standing in the door itself can expose
        # three adjacent attackers or allow a spawn to block the retreat.
        stands = [c for c in neighbors(door,w,h) if c not in area and c in paths and c != door
                  and p.tiles[c].get("visible") and p.tiles[c]["terrain"] in INTERIOR - {18}
                  and not any(n in area for n in neighbors(c,w,h))
                  and p.walkable(c) and p.escape_step_allowed(state,c)]
        for stand in sorted(stands, key=lambda c:len(p.route(paths,c))):
            retreat = [c for c in neighbors(stand,w,h) if c != door and c not in area
                       and p.tiles.get(c,{}).get("visible") and p.walkable(c)
                       and p.escape_step_allowed(state,c)]
            if not retreat:
                continue
            visible = [c for c in area if p.tiles[c].get("visible")
                       and p.tiles[c].get("terrain") == 18
                       and p.tiles[c].get("trap","").lower() == "summoning trap"
                       and (state["depth"],c) not in p.trap_attempts
                       and c not in p.loot]
            if not visible:
                continue
            if pos != stand:
                return p.toward(state,stand,"summoning: stage outside single-door choke",paths,intent=Intent.REPOSITION)
            target = next((c for c in sorted(visible) if p.shot_clear(state,c)),None)
            if target is None or p.tiles[door]["terrain"] != 6:
                continue
            # The whole potential spawn area is separated from hero and retreat.
            # No gas prethrow: gas can diffuse through this same open doorway.
            p.trap_attempts.add((state["depth"],target))
            p.trap_payload_return = {"cell":target,"name":item["name"].lower().split(" x")[0],
                                     "depth":state["depth"],"steps":0}
            p.summoning_pending = {"area":set(area),"door":door,"stand":stand}
            report.update(status="ready",reason="remote activation from exterior choke",
                          target=target,door=door,stand=stand,retreat=retreat)
            return p.use(item,"THROW","summoning: trigger visible plate remotely from exterior choke",target=target)
    return None


def quarantine(p, state):
    """Retain the triggered room until actual inactive plates establish clearance."""
    plan = p.summoning_pending
    if not plan:
        return
    area = plan["area"]
    occupied = any(o.get("cell") in area | {plan["door"]} and not o.get("top_item")
                   and o.get("name","").lower() not in {"skeletal remains","chest"}
                   for o in state.get("objects",[]))
    cleared = all(p.tiles.get(c,{}).get("visible") and p.tiles[c].get("terrain") == 19 for c in area)
    if cleared and not occupied and not p.recent_threats:
        p.summoning_pending = None
    else:
        p.room_blocked.update(area)
