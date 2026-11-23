"""Observed-room round trips with explicit protection and interaction budgets.

No generated room names/IDs are consumed. Special-room labels in reports are
recognition hypotheses; route cells and resource prerequisites are verified.
"""
from collections import deque
from dataclasses import dataclass
import re

try:
    from .consumable_tactics import base_name
    from .combat_items import unencumbered
    from .special_rooms import fire_barrier
    from .policy_decision import Intent
    from .mimic_hunt import begin_hunt
    from .mimic_tactics import suspicious_container
    from .room_supplies import use as use_room_supply, eligible as room_supply_eligible
except ImportError:
    from consumable_tactics import base_name
    from combat_items import unencumbered
    from special_rooms import fire_barrier
    from policy_decision import Intent
    from mimic_hunt import begin_hunt
    from mimic_tactics import suspicious_container
    from room_supplies import use as use_room_supply, eligible as room_supply_eligible


GROUND = {1, 2, 3, 6, 9, 11, 14, 15, 19, 20, 29, 30}
PROTECTION = {"gas": ("potion of purity", "purification barrier"),
              "flight": ("potion of levitation", "levitating"),
              "pool": ("potion of invisibility", "invisible"),
              "sentry": ("potion of haste", "haste")}


def remaining(state, name):
    for buff in state["hero"].get("buffs", []):
        if buff["name"].lower() == name:
            match = re.search(r"remaining:\s*(\d+(?:\.\d+)?)", buff.get("description", "").lower())
            return float(match[1]) if match else 0
    return 0


def safe_tile(p, cell, kind, occupied):
    tile = p.tiles.get(cell)
    if not tile or cell in occupied or tile.get("plant") or cell in p.blocked:
        return False
    effects = tile.get("effects", [])
    if effects and not (kind == "gas" and all("cloud of toxic gas" in e.lower() for e in effects)):
        return False
    if tile.get("trap") and tile["terrain"] != 19 and kind != "flight":
        return False
    if tile["terrain"] not in GROUND | ({0, 18} if kind == "flight" else set()):
        return False
    return cell not in p.neutral_actor_cells or cell in p.friendly_passage_cells


@dataclass
class Journey:
    kind: str
    route: list
    depth: int
    stage: str = "protect"
    interactions: int = 0
    steps: int = 0
    interaction_budget: int = 2

    def advance(self, p, state, enemies, neighbors):
        pos = state["hero"]["cell"]
        self.steps += 1
        if self.depth != state["depth"]:
            p.room_journey = None
            return None
        _, buff = PROTECTION[self.kind]
        duration = remaining(state, buff)
        if self.stage == "protect" and duration == 0:
            # This is still a hypothesis, not a protected trip. Recovery from
            # an actual failed potion effect may have moved off the dry-run
            # route; discard the unstarted plan before checking displacement.
            p.room_journey = None
            return None
        if pos not in self.route:
            p.stop_obligation("room-journey","Protected room journey displaced off its verified return route")
        if not unencumbered(state):
            p.stop_obligation("room-journey","Protected movement budget invalidated by unknown or over-strength armor")
        index = self.route.index(pos)
        buffs = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
        if any(name in buffs for name in ("vertigo", "paralys", "root")):
            p.stop_obligation("room-journey","Protected room movement is no longer deterministic; refusing a blind route step")
        impaired = any(name in buffs for name in ("slow", "crippl", "chill"))
        if self.kind == "sentry" and impaired:
            p.stop_obligation("room-journey","Sentry haste crossing invalidated by observed movement impairment")
        if self.stage == "protect":
            self.stage = "outbound"
        if self.route[-1] in p.combat_deferred_loot:
            self.stage = "return"  # Keep protection/return checks; abandon only the reward.
        move_time = 1/3 if self.kind == "sentry" else 2 if impaired else 1
        if self.steps >= 40 or enemies or state.get("danger_cells") or state["hero"]["hp"] < 0.65*state["hero"]["max_hp"] or duration < index*move_time+5:
            self.stage = "return"
        required = (2*(len(self.route)-1)-index)*move_time + max(0,self.interaction_budget-self.interactions) + 3
        if self.stage == "outbound" and duration < required:
            self.stage = "return"
        occupied = {o["cell"] for o in state.get("objects", []) if not o.get("top_item")
                    and o["name"].lower() not in {"chest", "locked chest", "crystal chest", "mirror image"}}
        if self.stage == "outbound" and index == len(self.route)-1:
            if self.interactions < self.interaction_budget and pos in p.loot and not p.loot[pos].get("for_sale"):
                self.interactions += 1
                return p.cell(pos, "room: collect protected reward within interaction budget")
            self.stage = "return"
        if self.stage == "return" and index == 0:
            if self.route[-1] not in p.loot and self.route[-1] not in p.combat_deferred_loot:
                p.completed_room_rewards.add((state["depth"],self.kind,self.route[-1]))
            p.room_journey = None
            return None
        target = self.route[index-1 if self.stage == "return" else index+1]
        # A wandering fish can occupy a planned waypoint after activation.
        # Replace only the remaining suffix, never attack it or lengthen the
        # protected round trip. Keep the same reward and return-bank prefix.
        if self.kind == "pool" and self.stage == "outbound" and index+2 < len(self.route) \
                and any(o["cell"] == target and "piranha" in o["name"].lower()
                        for o in state.get("objects", [])):
            water = p.piranha_rooms.get(self.route[-1], {}).get("water", set())
            width, height = state["map"]["width"], state["map"]["height"]
            reward = self.route[-1]
            queue, seen = deque([[pos]]), set(self.route[:index+1])
            while queue:
                suffix = queue.popleft()
                if suffix[-1] == reward:
                    self.route = self.route[:index] + suffix
                    target = self.route[index+1]
                    break
                if len(suffix) >= len(self.route)-index:
                    continue
                for c in neighbors(suffix[-1], width, height):
                    if c not in seen and (c in water or c == reward) \
                            and p.tiles.get(c, {}).get("visible") \
                            and p.tiles[c].get("observed") is not False \
                            and c not in state.get("danger_cells", []) \
                            and safe_tile(p, c, self.kind, occupied):
                        seen.add(c)
                        queue.append(suffix+[c])
        tile=p.tiles.get(target,{})
        reopen=tile.get('terrain')==5 and target not in occupied and target not in p.blocked \
            and not tile.get('plant') and not tile.get('trap') and not p.effects_block_movement(tile)
        if self.kind == "gas" and self.stage == "return" and target in occupied \
                and duration >= index*move_time+2:
            # A newly visible actor can block the old return prefix. Replace
            # only that prefix with a freshly observed DRY route to the SAME
            # bank. Allow at most one extra move, funded by observed immunity.
            # Never extend immunity or claim a pickup.
            width, height = state["map"]["width"], state["map"]["height"]
            max_moves = min(index+1, int((duration-2)//move_time))
            queue, seen = deque([[pos]]), {pos}
            while queue:
                path = queue.popleft()
                if path[-1] == self.route[0]:
                    self.route = list(reversed(path)) + self.route[index+1:]
                    index = len(path)-1
                    target = self.route[index-1]
                    break
                if len(path)-1 >= max_moves:
                    continue
                for c in neighbors(path[-1], width, height):
                    t = p.tiles.get(c, {})
                    if c not in seen and t.get("visible") and t.get("observed") is not False \
                            and not t.get("effects") and not t.get("trap") \
                            and c not in p.room_blocked and c not in p.loot \
                            and c not in state.get("danger_cells", []) \
                            and p.escape_step_allowed(state, c) \
                            and safe_tile(p, c, self.kind, occupied):
                        seen.add(c)
                        queue.append(path+[c])
        if target in state.get("danger_cells", []) or not (safe_tile(p, target, self.kind, occupied) or reopen) or duration < (index*move_time+2 if self.stage == "return" else 3):
            p.stop_obligation("room-journey","Protected room return route obstructed or protection budget insufficient")
        if self.stage=='outbound' and index==0:
            p.room_attempts.add((state['depth'],self.kind,self.route[-1]))
        return p.cell(target, "room: return before protection expires" if self.stage == "return" else "room: follow verified protected route")


def sentry_geometry(p, state):
    """Reconstruct a completely observed rectangular enclosure, not a room ID.

    Sentry lock-on delay is the public room-width crossing rule. Never infer
    dimensions from missing tiles, an actor's private room, or current charge.
    """
    width, height = state["map"]["width"], state["map"]["height"]
    sentries = [a for a in p.room_actors.values() if a["name"].lower() == "red sentry"]
    if len(sentries) != 1:
        return set(), 0
    start = sentries[0]["cell"]
    found, queue = {start}, deque([start])
    while queue and len(found) <= 200:
        cell = queue.popleft()
        x, y = cell % width, cell//width
        for nx, ny in ((x-1,y), (x+1,y), (x,y-1), (x,y+1)):
            if 0 <= nx < width and 0 <= ny < height:
                n = ny*width+nx
                if n not in found and p.tiles.get(n, {}).get("terrain") in GROUND-{6}:
                    found.add(n)
                    queue.append(n)
    if len(found) > 200:
        return set(), 0
    left, right = min(c%width for c in found)-1, max(c%width for c in found)+1
    top, bottom = min(c//width for c in found)-1, max(c//width for c in found)+1
    if left < 0 or right >= width or top < 0 or bottom >= height:
        return set(), 0
    interior = {y*width+x for x in range(left+1, right) for y in range(top+1, bottom)}
    if any(c not in p.tiles for c in interior):
        return set(), 0
    boundary = {y*width+x for x in range(left, right+1) for y in range(top, bottom+1)
                if x in {left,right} or y in {top,bottom}}
    doors = [c for c in boundary if p.tiles.get(c, {}).get("terrain") in {5,6}]
    if len(doors) != 1 or any(p.tiles.get(c, {}).get("terrain") not in {4,12} for c in boundary-set(doors)):
        return set(), 0
    length = right-left+1 if doors[0]%width in {left,right} else bottom-top+1
    return interior, max(0, 2*(length-5)/3+0.1)


def sentry_route_safe(p, route, delay):
    if not delay or p.tiles[route[0]]["terrain"] == 14 or p.tiles[route[-1]]["terrain"] == 14:
        return False
    longest = run = 0
    for cell in route:
        run = run+1 if p.tiles[cell]["terrain"] == 14 else 0
        longest = max(longest, run)
    return longest > 0 and longest/3+0.05 < delay


def plan_journey(p, state, enemies, neighbors, *, probe_kind=None, plan_only=False):
    # Hypothetical protection only plans a route; it never admits a hazard step
    # or labels an unknown potion. Journey.advance rechecks the actual buff.
    if probe_kind is not None and (not plan_only or probe_kind not in PROTECTION):
        raise ValueError('Protection hypotheses may only request a dry-run journey plan')
    if "room-journey" in p.deferred_room_controllers:return None
    if enemies or p.room_journey or state.get("danger_cells") or state["hero"]["hp"] < 0.8*state["hero"]["max_hp"]:
        return None
    if not unencumbered(state):
        return None
    pos, width, height = state["hero"]["cell"], state["map"]["width"], state["map"]["height"]
    if pos in p.room_blocked or p.tiles[pos].get("effects"):
        return None
    inventory = {base_name(i): i for i in state["inventory"]}
    ordinary_paths=p.paths(state) if getattr(p,'reserve_floor_puzzle_supplies',False) else None
    occupied = {a["cell"] for a in p.room_actors.values()} | (p.neutral_actor_cells-p.friendly_passage_cells)
    try:
        from .special_rooms import component
    except ImportError:
        from special_rooms import component
    pool_region = set()
    for room in p.piranha_rooms.values():
        pool_region.update(room['water'])
        pool_region.update(n for c in room['water'] for n in neighbors(c,width,height))
    for actor in p.room_actors.values():
        if "piranha" in actor["name"].lower():
            pool = component(actor["cell"], p.tiles, {29}, width, height)
            pool_region.update(pool)
            pool_region.update(n for c in pool for n in neighbors(c, width, height))
    sentry_region, sentry_delay = sentry_geometry(p, state)
    # A held key admits a chest, but does not cover every observed lock.
    # Prefer another matching key to spending flight on that chest while a
    # deficit remains. Only fully admitted trips below enter this preference.
    flight_key_deficit = sum(o.get("name", "").lower() == "locked chest"
                             and not o.get("for_sale") for o in p.loot.values()) > p.keys.get("golden", 0)
    for kind, (potion, buff) in PROTECTION.items():
        if probe_kind is not None and kind!=probe_kind:continue
        item = inventory.get(potion)
        duration = remaining(state,buff)
        if not duration and (not item or "DRINK" not in item.get("actions", [])) and probe_kind!=kind:
            continue
        if kind == "pool" and not pool_region:
            continue
        if kind == "sentry":
            if not sentry_region or pos not in sentry_region:
                continue
            if any(any(t in b["name"].lower() for t in ("slow", "crippl", "root", "paral", "chill", "vertigo"))
                   for b in state["hero"].get("buffs", [])):
                continue
        fallback = None
        def select(journey):
            if plan_only:return journey
            p.room_attempts.add((state["depth"], kind, journey.route[-1]))
            p.room_journey = journey
            if duration:
                return journey.advance(p,state,enemies,neighbors)
            return use_room_supply(p,item,"DRINK",f"room: prepare {kind} protection for verified round trip",kind=kind)
        paths, queue = {pos: None}, deque([pos])
        while queue:
            cell = queue.popleft()
            route = p.route(paths, cell)
            if len(route) > (18 if kind == "sentry" else 8):
                continue
            loot = p.loot.get(cell)
            hazard = any(p.tiles[c]["terrain"] in {0, 18} if kind == "flight" else
                         bool(p.tiles[c].get("effects")) if kind == "gas" else c in p.room_blocked
                         for c in route[1:])
            key = (state["depth"], kind, cell)
            permitted = loot and not suspicious_container(loot) and cell not in p.combat_deferred_loot and (loot["name"].lower() not in {"tomb", "skeleton", "skeletal remains", "crystal chest", "locked chest"}
                                   or cell in p.allowed_chests)
            if kind=='pool' and p.piranha_rooms:
                permitted=permitted and cell in p.piranha_rooms and not p.piranha_rooms[cell]['collected']
            if kind=='flight' and ordinary_paths is not None and cell in ordinary_paths:
                permitted=False  # A chasm shortcut to ordinary loot cannot justify the room's levitation supply.
            if permitted and cell != pos and hazard and key not in p.room_attempts and not loot.get("for_sale"):
                if kind == "sentry" and not sentry_route_safe(p, route, sentry_delay):
                    continue
                interactions = 4 if loot["name"].lower() in {"locked chest","crystal chest","tomb","skeleton","skeletal remains"} else 2
                budget = 2*(len(route)-1)*(1/3 if kind=="sentry" else 1)+interactions+3
                if budget > (duration or 20):
                    continue
                journey=Journey(kind,route,state['depth'],interaction_budget=interactions)
                if kind == "flight" and flight_key_deficit and base_name(loot.get("top_item", loot)) != "golden key":
                    if fallback is None:fallback = journey
                else:
                    return select(journey)
            # Container clicks interact before moving. In particular a flight
            # route through two locked chests can spend the only held key, then
            # retry the second lock without advancing the protection clock.
            # Keep admitted containers as endpoints above, never as transit.
            if loot and loot.get("name", "").lower() in {
                    "chest", "locked chest", "crystal chest", "tomb",
                    "skeleton", "skeletal remains"} and cell != pos:
                continue
            for adjacent in neighbors(cell, width, height):
                closed_probe = plan_only and kind in PROTECTION and p.tiles.get(adjacent,{}).get('terrain')==5 \
                    and adjacent not in occupied and adjacent not in p.blocked and not p.tiles[adjacent].get('effects') \
                    and not p.tiles[adjacent].get('plant') and not p.tiles[adjacent].get('trap')
                if adjacent not in paths and (safe_tile(p, adjacent, kind, occupied) or closed_probe):
                    # Never reinterpret a statue/sentry/quest exclusion as a
                    # flight puzzle. Only the matching hazard may be traversed.
                    if adjacent in p.room_blocked and not (
                        kind == "flight" and p.tiles[adjacent]["terrain"] in {0, 18}
                        or kind == "gas" and p.tiles[adjacent].get("effects")
                        or kind == "pool" and adjacent in pool_region
                        or kind == "sentry" and adjacent in sentry_region
                        or adjacent in p.allowed_chests):
                        continue
                    paths[adjacent] = cell
                    queue.append(adjacent)
        if fallback is not None:return select(fallback)
    return None


def extinguish(p, state, enemies, distance):
    if enemies or state.get("danger_cells"):
        return None
    frost = next((i for i in state["inventory"] if base_name(i) == "potion of frost" and "THROW" in i.get("actions", [])), None)
    if not frost:
        return None
    pos, width = state["hero"]["cell"], state["map"]["width"]
    for cell, tile in p.tiles.items():
        key = (state["depth"], "extinguish", cell)
        if key in p.room_attempts or not fire_barrier(tile):
            continue
        if not tile.get("visible") or not p.shot_clear(state,cell):
            move=throw_vantage(p,state,cell,distance)
            if move:
                return move
            continue
        if p.shot_clear(state, cell):
            if distance(pos,cell,width)<3:
                move = throw_vantage(p,state,cell,distance)
                if move:
                    return move
                continue
            p.room_attempts.add(key)
            try:
                from .barrier_followup import begin
                from .policy_geometry import neighbors
            except ImportError:
                from barrier_followup import begin
                from policy_geometry import neighbors
            begin(p,state,cell,neighbors)
            return use_room_supply(p,frost,"THROW","room: extinguish observed magical fire from safe distance",kind='frost',target=cell)
    return None


def throw_vantage(p,state,target,distance):
    paths = p.paths(state)
    width = state["map"]["width"]
    choices = [c for c in paths if 3<=distance(c,target,width)<=5 and len(p.route(paths,c))<=5
               and p.tiles[c]["terrain"] in GROUND and not p.tiles[c].get("effects") and c not in p.loot
               and p.shot_clear(dict(state,hero=dict(state["hero"],cell=c)),target)]
    if choices:
        return p.toward(state,min(choices,key=lambda c:len(p.route(paths,c))),
                         "room: gain safe throwing distance before altering observed barrier",paths,intent=Intent.EXPLORE)
    return None


def controlled_burn(p, state, enemies, distance, neighbors):
    """Only isolated barriers, with known nonflammable neighbors and no loot."""
    if getattr(p,'reserve_floor_puzzle_supplies',False):
        try:
            from .wooden_barrier import known_burn
        except ImportError:
            from wooden_barrier import known_burn
        planned=known_burn(p,state,enemies)
        if planned:return planned
    if enemies or state.get("danger_cells") or state["hero"]["hp"] < 0.8*state["hero"]["max_hp"]:
        return None
    flame = next((i for i in state["inventory"] if base_name(i) == "potion of liquid flame"
                  and "THROW" in i.get("actions", []) and room_supply_eligible(p,i,"THROW","flame")), None)
    if not flame:
        return None
    pos, width, height = state["hero"]["cell"], state["map"]["width"], state["map"]["height"]
    paths = p.paths(state)
    nonflammable = {0, 1, 3, 4, 9, 11, 12, 14, 19, 20, 24, 25, 26, 28, 29}
    for cell, tile in p.tiles.items():
        key = (state["depth"], "burn", cell)
        around = list(neighbors(cell, width, height))
        if tile["terrain"] not in {13, 27} or not tile.get("visible") or key in p.room_attempts \
                or not p.shot_clear(state, cell):
            continue
        if any(n in p.loot or n not in p.tiles or p.tiles[n]["terrain"] not in nonflammable for n in around) or cell in p.loot:
            continue
        if not any(n in paths for n in around) or not any(n not in paths and p.tiles[n]["terrain"] in GROUND for n in around):
            continue
        if distance(pos,cell,width)<3:
            move = throw_vantage(p,state,cell,distance)
            if move:
                return move
            continue
        p.room_attempts.add(key)
        return use_room_supply(p,flame,"THROW","room: burn isolated observed barrier; normal hazard checks forbid entry until clear",kind='flame',target=cell)
    return None


def suspect_container_pending(p,state):
    return any(not obj.get("for_sale") and "feels off" in obj.get("description","").lower()
                and "bad idea" in obj.get("description","").lower()
                and cell not in p.suspect_staging_deferred
               and (state["depth"],"suspect-container",cell) not in p.room_attempts
               for cell,obj in p.loot.items())


def investigate_suspect_container(p,state,enemies,distance):
    """A rendered warning warrants caution, not a hidden mimic identity lookup."""
    if getattr(p,'unit_strategies_enabled',False) and (p.recent_threats or any(
            getattr(p,k,None) for k in ('ambush_plan','doorway_hold','multi_door_plan','ranged_plan'))):
        return None  # Disappearing pursuers do not make an optional chest trip quiet.
    hero=state["hero"]
    buffs=" ".join(b["name"].lower() for b in hero.get("buffs",[]))
    if enemies or state.get("danger_cells") or hero["hp"]<0.9*hero["max_hp"] \
            or any(t in buffs for t in ("starving","burning","poison","blind","vertigo")):
        return None
    wand=next((i for i in p.charged_magic(state) if "magic missile" in i["name"].lower()
               and not i.get("known_cursed") and (i.get("status") or "").split("/")[0].isdigit()
               and int(i["status"].split("/")[0])>=3),None)
    if not wand:
        return None
    paths=p.paths(state)
    width=state["map"]["width"]
    plan=p.suspect_probe_plan
    if plan and (plan['cell'] not in p.loot or plan['cell'] in p.suspect_staging_deferred):
        p.suspect_probe_plan=plan=None
    ordered=[(plan['cell'],p.loot[plan['cell']])] if plan else list(p.loot.items())
    for cell,obj in ordered:
        text=obj.get("description","").replace("_","").lower()
        key=(state["depth"],"suspect-container",cell)
        if p.mimic_obligations and cell not in p.mimic_obligations:
            continue
        if obj.get("for_sale") or "feels off" not in text or "bad idea" not in text or key in p.room_attempts \
                or cell in p.suspect_staging_deferred:
            continue
        def defer(reason):
            p.suspect_staging_deferred.add(cell)
            p.suspect_probe_plan=None
            p.defer_obligations(state,[{'kind':'unresolved suspicious staging','cell':cell,'name':obj['name']}],reason)
        if plan and plan['steps']>=32:
            defer('Committed suspicious-container route exceeded bounded staging budget; not tested or collected')
            return None
        # Into Darkness without a light source can reveal only two squares.
        # A three-square firing bank then oscillates forever without a target.
        crystal=obj["name"].lower()=="crystal chest"
        if crystal:
            ready=next((i for i in p.charged_magic(state) if 'magic missile' in i['name'].lower()
                        and not i.get('known_cursed') and (i.get('status') or '').split('/')[0].isdigit()
                        and int(i['status'].split('/')[0])>=4),None)
            if not ready:
                p.planner.report['suspect_readiness']={'cell':cell,'known_charges_required':4,
                    'reason':'Three-shot crystal attempt previously exhausted before confirmed resolution',
                    'caveat':'Fourth shot is reserve, not guaranteed kill damage or certain survival'}
                continue
            wand=ready
        low,high=(2,2) if crystal or "illuminated" not in buffs else (3,5)
        outside=[]
        if crystal:
            try:
                from .room_loot import room_region
                from .policy_geometry import line_clear
            except ImportError:
                from room_loot import room_region
                from policy_geometry import line_clear
            interior=room_region(p,dict(state,hero=dict(hero,cell=cell)))
            outside=[c for c in p.tiles if c not in interior and p.walkable(c)
                     and not p.tiles[c].get('plant') and not p.tiles[c].get('effects')]
        banks=[c for c in paths if (low<=distance(c,cell,width)<=high or
                not crystal and c==hero["cell"] and 3<=distance(c,cell,width)<=5 and p.tiles.get(cell,{}).get("visible"))
               and len(p.route(paths,c))<=24
               and p.tiles[c]["terrain"] in GROUND|({5} if crystal else set()) and not p.tiles[c].get("effects") and c not in p.loot
                 and p.shot_clear(dict(state,hero=dict(hero,cell=c)),cell)]
        # Rank known outward firing lines, not presumed enemy locations. A closed
        # ordinary door can be opened and occupied through normal observed moves;
        # leaving it behind previously hid the whole outside route after reveal.
        sight={bank:sum(distance(bank,c,width)<=6 and line_clear(bank,c,width,p.tiles)
                        for c in outside) for bank in banks} if crystal else {}
        banks=[c for c in banks if (cell,c) not in p.suspect_failed_banks]
        if plan and plan['bank'] in banks:
            banks=[plan['bank']]  # Do not reselect a chest/bank after each accepted step.
        elif plan:
            p.suspect_failed_banks.add((cell,plan['bank']))
            p.suspect_probe_plan=plan=None
        if sum(c==cell for c,_ in p.suspect_failed_banks)>=3:
            defer('No confirmed firing view after bounded staging attempts; reward remains unfinished')
            return None
        for bank in sorted(banks,key=lambda c:(-sight.get(c,0),len(p.route(paths,c)),c)):
            escape=p.paths(dict(state,hero=dict(hero,cell=bank)))
            doors=[c for c in escape if p.tiles[c]["terrain"] in {5,6} and len(p.route(escape,c))<=7]
            exits=[c for c in escape if len(p.route(escape,c))==2 and c not in p.loot
                   and not p.tiles[c].get("plant") and not p.tiles[c].get("effects")]
            if not (len(exits)>=2 if crystal else doors):
                continue
            if bank!=hero["cell"]:
                if not plan:
                    plan=p.suspect_probe_plan={'cell':cell,'bank':bank,'steps':0}
                plan['steps']+=1
                p.planner.report['suspect_staging']={'cell':cell,'bank':bank,'steps':plan['steps'],'status':'committed observed target'}
                if crystal:p.planner.report['suspect_staging'].update(
                    outward_line_score=sight.get(bank,0),
                    caveat='Known geometry only; no assumed flee destination, physical doorway block or guaranteed visibility')
                return p.toward(state,bank,"room: stage two-square ranged crystal-chest provocation; no doorway blocking" if crystal
                                else "room: stage suspicious-container test near a known doorway escape",paths,intent=Intent.REPOSITION)
            if not p.tiles.get(cell,{}).get("visible"):
                p.suspect_failed_banks.add((cell,bank))
                p.suspect_probe_plan=None
                return None  # Arrival without sight is failure, never a provocation or pickup.
            p.suspect_probe_plan=None
            p.room_attempts.add(key)
            begin_hunt(p,state,cell,obj)
            return p.use(wand,"ZAP","room: provoke publicly suspicious crystal chest from range; prepare fleeing interception" if crystal
                         else "room: cautiously test publicly suspicious container from range with doorway escape",target=cell)
    return None


def charge_suspect_container(p,state,enemies):
    """Bridge a one-charge readiness gap instead of exhausting exploration."""
    hero=state["hero"]
    buffs=" ".join(b["name"].lower() for b in hero.get("buffs",[]))
    tile=p.tiles.get(hero["cell"],{})
    if enemies or state.get("danger_cells") or p.recent_threats or not suspect_container_pending(p,state) \
            or hero["hp"]<0.9*hero["max_hp"] or tile.get("effects") or tile.get("plant") or tile.get("trap") \
            or any(t in buffs for t in ("starving","burning","poison","paral","vertigo","blind")):
        return None
    pending=[o for c,o in p.loot.items() if not o.get('for_sale')
             and 'feels off' in o.get('description','').lower() and 'bad idea' in o.get('description','').lower()
             and (state['depth'],'suspect-container',c) not in p.room_attempts
             and c not in p.suspect_staging_deferred]
    plan=p.suspect_probe_plan
    planned=p.loot.get(plan['cell']) if plan else None
    required=4 if (planned and planned['name'].lower()=='crystal chest') or (
        pending and all(o['name'].lower()=='crystal chest' for o in pending)) else 3
    staff=next((i for i in state["inventory"] if "staff of magic missile" in i["name"].lower()
                and (i.get('status') or '').split('/')[0].isdigit()
                and 2<=int(i['status'].split('/')[0])<required
                and len(i['status'].split('/'))==2 and i['status'].split('/')[1].isdigit()
                and int(i['status'].split('/')[1])>=required
                and not i.get('known_cursed') and "ZAP" in i.get("actions",[])),None)
    if any("magic missile" in i["name"].lower() and not i.get("known_cursed")
           and (i.get("status") or "").split("/")[0].isdigit()
            and int(i["status"].split("/")[0])>=required for i in p.charged_magic(state)):
        return None
    if not staff:
        return None
    key=(state["depth"],"suspect-charge-waits")
    used=sum(1 for attempt in p.room_attempts if attempt[:2]==key)
    if used>=40:
        return None
    p.room_attempts.add((*key,used))
    return p.decision({"type":"wait"},"room: bounded recharge for required ranged suspicious-container test",intent=Intent.RECOVER)


def prepare_containers(p, state):
    """Crypt/pit preparedness and crystal choice, never hidden chest identities."""
    hero = state["hero"]
    charges = sum(int(i["status"].split("/")[0]) for i in p.charged_magic(state)
                  if (i.get("status") or "?").split("/")[0].isdigit())
    hunger = " ".join(b["name"].lower() for b in hero.get("buffs", []))
    if hero["hp"] >= 0.85*hero["max_hp"] and charges >= 3 and "hungry" not in hunger and "starving" not in hunger:
        paths = p.paths(state)
        width = state["map"]["width"]
        for cell, obj in p.loot.items():
            if obj["name"].lower() in {"tomb", "skeleton", "skeletal remains"} and not obj.get("for_sale"):
                banks = [n for n in paths if max(abs(n%width-cell%width), abs(n//width-cell//width)) == 1
                         and p.tiles[n]["terrain"] in GROUND and p.walkable(n) and len(p.route(paths, n)) <= 6]
                if not banks:
                    continue
                p.allowed_chests.add(cell)
                p.room_blocked.discard(cell)
                p.room_skipped.discard(cell)
    if p.keys.get("crystal", 0):
        choices = []
        useful_wands = sum("wand of " in i["name"].lower() for i in state["inventory"])
        rings = sum("ring of " in i["name"].lower() for i in state["inventory"])
        for cell, obj in p.loot.items():
            if obj["name"].lower() != "crystal chest" or obj.get("for_sale"):
                continue
            p.allowed_chests.discard(cell)
            description = obj.get("description", "").replace("_", "").lower()
            if "feels off" in description and "bad idea" in description:
                continue
            score = (8 if not useful_wands else 4) if "a wand" in description else (7 if not rings else 3) if "a ring" in description else 5 if "artifact" in description else 0
            if score:
                choices.append((score, -cell, cell))
        if choices:
            target = max(choices)[2]
            p.allowed_chests.add(target)
            p.room_blocked.discard(target)
            p.room_skipped.discard(target)
            try:
                from .keyed_rooms import chest_choice
            except ImportError:
                from keyed_rooms import chest_choice
            chest_choice(p,state,target,[entry[2] for entry in choices])


def crystal_choice(p, state, enemies, neighbors):
    """Spend a crystal key on observed rewards, never expected generated prizes."""
    if enemies or p.recent_threats or state.get('danger_cells') or not p.keys.get("crystal", 0):
        return None
    doors = [c for c, t in p.tiles.items() if t["terrain"] == 31
             and c not in p.resolved_crystal_alternatives]
    if len(doors) < 2:
        return None  # A single door can be the necessary exit from a pit room.
    baseline = p.paths(state)
    pos, width, height = state["hero"]["cell"], state["map"]["width"], state["map"]["height"]
    choices = []
    branch_cells = {}
    for door in doors:
        paths, queue = {pos: None}, deque([pos])
        while queue:
            cell = queue.popleft()
            for n in neighbors(cell, width, height):
                terrain = p.tiles.get(n, {}).get("terrain")
                # Ordinary closed doors are transit in the real paths too.
                # Excluding them here erases distant observed branch rewards.
                if n not in paths and (n == door or terrain in GROUND | {5} and p.walkable(n)):
                    paths[n] = cell
                    queue.append(n)
        branch_cells[door] = (set(paths)-set(baseline)) | {door}
        value = 0
        for cell in set(paths)-set(baseline):
            obj = p.loot.get(cell)
            if not obj or obj.get("for_sale") or cell in p.combat_deferred_loot:
                continue
            visible = obj.get("top_item", {})
            name = visible.get("name", obj["name"]).lower()
            description = obj.get("description", "").replace("_", "").lower()
            if (name == "potion of healing" and p.pharmacophobia) or visible.get("known_cursed"):
                continue
            reward = 25 if any(k in name for k in ("strength", "scroll of upgrade", "experience")) else \
                     20 if "wand" in name or "a wand" in description else \
                     15 if "artifact" in description or "ring" in name else \
                     12 if any(k in name for k in ("teleportation", "recharging", "invisibility")) else \
                     8 if any(k in name for k in ("potion", "scroll", "food", "ration")) \
                     or obj['name'].lower()=='chest' and not suspicious_container(obj) else 1
            value += reward
        if value >= 8 and door in baseline:
            choices.append((value, -len(p.route(baseline, door)), -door, door))
    if choices:
        target = max(choices)[3]
        try:
            from .keyed_rooms import local_alternatives,record_spend
        except ImportError:
            from keyed_rooms import local_alternatives,record_spend
        alternatives=local_alternatives(p,state,target,doors,branch_cells,baseline)
        p.crystal_choice_groups[target] = alternatives
        record_spend(p,state,target,'door',alternatives)
        p.deferred_crystal_doors.discard(target)
        p.optional_locks.discard(target)
        return p.toward(state, target, "room: spend crystal key on highest-value observed branch", baseline)
    p.optional_locks.update(doors)
    p.deferred_crystal_doors.update(doors)
    p.room_notes.append({"kind": "crystal choice", "cells": doors,
                         "reason": "Defer mutually exclusive branches without observed useful rewards; no hidden prize inference"})
    return None


def awareness_well(p, state, enemies, neighbors):
    if enemies or not any(not i.get("identified") or not i.get("curse_known") for i in state["inventory"]):
        return None
    pos, width, height = state["hero"]["cell"], state["map"]["width"], state["map"]["height"]
    paths = p.paths(state)
    choices = []
    for cell, tile in p.tiles.items():
        key = (state["depth"], "awareness", cell)
        if key in p.room_attempts or not any("power of knowledge radiates" in e.lower() for e in tile.get("effects", [])):
            continue
        for bank in neighbors(cell, width, height):
            if bank in paths and len(p.route(paths, bank)) <= 10:
                choices.append((len(p.route(paths, bank)), bank, cell))
    if choices:
        _, bank, well = min(choices)
        if pos != bank:
            return p.toward(state, bank, "well: approach inspected awareness water", paths)
        p.room_attempts.add((state["depth"], "awareness", well))
        return p.cell(well, "well: identify equipped items and inventory curses without potion testing")
    return None
