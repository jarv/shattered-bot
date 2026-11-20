"""Reserve observed room supplies; defer spent supplies only from accepted receipts."""
from collections import Counter, deque

try:
    from .consumable_tactics import base_name, unknown_potion
    from .policy_geometry import distance, neighbors
except ImportError:
    from consumable_tactics import base_name, unknown_potion
    from policy_geometry import distance, neighbors

POTIONS = {"pool": "potion of invisibility", "flight": "potion of levitation",
           "fall": "potion of levitation", "sentry": "potion of haste",
           "gas": "potion of purity", "frost": "potion of frost",
           "flame": "potion of liquid flame"}
ALTERNATIVES = {"fall": {"elixir of feather fall", "potion of cleansing"}}
NAMES = set(POTIONS.values()) | set().union(*ALTERNATIVES.values())


def supplies(kind):
    return {POTIONS[kind]} | ALTERNATIVES.get(kind,set())


def counts(state):
    result = Counter()
    for item in state.get("inventory", []):
        if unknown_potion(item) or base_name(item) in NAMES:
            result[base_name(item)] += item.get("quantity", 1)
    return result


def requirements(p, state):
    if not getattr(p,"reserve_floor_puzzle_supplies",False) or not state \
            or not state.get("hero") or not state.get("map"):return []
    try:
        from .puzzle_supplies import demands
    except ImportError:
        from puzzle_supplies import demands
    result=demands(p,state,distance,include_deferred=True)
    if any(d.kind=="fall" for d in result):
        try:
            from .puzzle_supplies import Demand
        except ImportError:
            from puzzle_supplies import Demand
        choice=next((n for n in ("elixir of feather fall","potion of cleansing")
                     if counts(state)[n]),POTIONS["fall"])
        result=[Demand(d.kind,choice,d.cell) if d.kind=="fall" else d for d in result]
    return result


def exhausted(p, state, kind):
    if kind not in POTIONS:return False
    options=supplies(kind)
    if not options & getattr(p, "room_supply_spent_elsewhere", set()) or any(counts(state)[n] for n in options):
        return False
    # A known replacement, including a deliberately dropped dose, remains usable.
    return not any(base_name(o.get("top_item", o)) in options and not o.get("for_sale")
                   for o in {**p.unconfirmed_loot, **p.loot}.values())


def depleted(p, state):
    if not getattr(p, "room_supply_spent_elsewhere", set()):return set()
    return {d.kind for d in requirements(p,state) if d.kind in POTIONS and exhausted(p,state,d.kind)}


def allowed(p, item, action):
    name = base_name(item)
    if action not in {"DRINK", "THROW"} or name not in NAMES:return True
    permit = getattr(p, "room_supply_permit", None)
    if permit and permit[:2] == (item.get("id"), name):return True
    state = getattr(p, "last_state", None)
    needed = {d.kind for d in requirements(p,state) if d.potion == name}
    if not needed:return True
    # Preserve at least one dose per recognized puzzle kind; extras remain usable.
    return counts(state)[name] > len(needed)


def use(p, item, action, reason, *, kind, target=None):
    """Explicit room/emergency purpose, not an inference from human-readable reason."""
    previous = getattr(p, "room_supply_permit", None)
    p.room_supply_permit = (item.get("id"), base_name(item), kind)
    try:
        decision = p.use(item, action, reason, **({"target":target} if target is not None else {}))
        if hasattr(decision, "action"):decision.potion_purpose = kind
        return decision
    finally:
        p.room_supply_permit = previous


def eligible(p,item,action,kind):
    previous=getattr(p,"room_supply_permit",None)
    p.room_supply_permit=(item.get("id"),base_name(item),kind)
    try:
        return p.item_action_allowed(item,action)
    finally:
        p.room_supply_permit=previous


def eligible_target(p,item,target,kind):
    previous=getattr(p,"room_supply_permit",None)
    p.room_supply_permit=(item.get("id"),base_name(item),kind)
    try:
        return p.target_allowed(item,target)
    finally:
        p.room_supply_permit=previous


def observe(p, before, decision, after):
    """Accepted input only. Color changes are matched only when unambiguous."""
    if not hasattr(p, "room_supply_pickups"):return None
    if (before.get("depth"), before.get("branch",0)) != (after.get("depth"), after.get("branch",0)):
        return None
    old, new = counts(before), counts(after)
    owned = p.room_supply_pickups
    action = decision.action
    used = next((i for i in before.get("inventory",[]) if i.get("id")==action.get("id")),None)
    purpose = getattr(decision, "potion_purpose", None)
    # Intuition/identification renames a carried type without acquiring it anew.
    lost = [n for n in old if n.endswith(" potion") and new[n] == 0]
    gained = [n for n in NAMES if new[n] > old[n]]
    alias = {}
    if len(lost)==len(gained)==1:
        a,b = lost[0],gained[0]
        drinking = bool(used and base_name(used)==a and action.get("action")=="DRINK")
        if old[a] == new[b]-old[b] + int(drinking):
            alias[a] = b
            owned[b] += owned.pop(a,0)
            old[b] += old.pop(a)
    # A new observed protective effect identifies a singleton drink's purpose;
    # damaging statuses such as burning/chill are not used to guess identities.
    if used and unknown_potion(used) and action.get("action")=="DRINK" and not alias:
        before_buffs={b["name"].lower() for b in before.get("hero",{}).get("buffs",[])}
        after_buffs={b["name"].lower() for b in after.get("hero",{}).get("buffs",[])}
        effects={"invisible":"potion of invisibility","levitating":"potion of levitation",
                 "haste":"potion of haste","purification barrier":"potion of purity"}
        fresh=[effects[b] for b in after_buffs-before_buffs if b in effects]
        a=base_name(used)
        if len(fresh)==1 and old[a]==1 and new[a]==0:
            b=fresh[0];alias[a]=b
            owned[b]+=owned.pop(a,0);old[b]+=old.pop(a)
    if used and action.get("type")=="item" and action.get("action") in {"DRINK","THROW"}:
        name = alias.get(base_name(used),base_name(used))
        p.room_supply_pending_use = (name,purpose)
    elif action.get("type")=="back":
        p.room_supply_pending_use = None
    elif action.get("type")=="item":
        p.room_supply_pending_use = None  # DROP/other item use is not a throw confirmation.
    receipt = None
    pending = p.room_supply_pending_use
    if pending:
        name, purpose = pending
        removed = old[name]-new[name]
        floor_removed = max(0,owned[name]-new[name])
        if removed > 0:
            intended=purpose in POTIONS and name in supplies(purpose)
            if floor_removed and name in NAMES and not intended:
                p.room_supply_spent_elsewhere.add(name)
                receipt = {"potion":name,"purpose":purpose or "other use",
                           "floor_doses_used":floor_removed,"collection_credited":False}
            p.room_supply_pending_use = None
    # A drop/removal is not consumption and cannot leave phantom carried origins.
    for name in list(owned):
        owned[name] = min(owned[name],new[name])
    # Only a matching observed ground pickup plus inventory gain proves floor origin.
    if action.get("type")=="cell" and after.get("hero",{}).get("cell")==action.get("cell"):
        obj = next((o for o in before.get("objects",[]) if o.get("cell")==action["cell"]
                    and o.get("top_item") and not o.get("for_sale")),None)
        if obj:
            item = obj["top_item"]
            name = base_name(item)
            if unknown_potion(item) or name in NAMES:
                gained = new[name]-old[name]
                if gained > 0:owned[name] += gained
    return receipt


def deferred_loot(p, state=None):
    """Associate known loot with exhausted room barriers, never authorize crossing."""
    state = state or getattr(p,"last_state",None)
    kinds = depleted(p,state)
    if not kinds:return set()
    try:
        from .room_tactics import GROUND, sentry_geometry
        from .special_rooms import fire_barrier
    except ImportError:
        from room_tactics import GROUND, sentry_geometry
        from special_rooms import fire_barrier
    width,height = state["map"]["width"],state["map"]["height"]
    ordinary = set(p.paths(state))
    loot = {**p.unconfirmed_loot,**p.loot}
    result = set()
    occupied = set(p.room_actors) | p.neutral_actor_cells
    for kind in kinds:
        matching = set()
        if kind=="pool":
            for cell,room in p.piranha_rooms.items():
                if not room["collected"]:result.add(cell)
                matching.update(room["water"])
                matching.update(n for c in room["water"] for n in neighbors(c,width,height))
        elif kind=="frost":
            matching = {c for c,t in p.tiles.items() if fire_barrier(t)} | p.fire_buffer
        elif kind=="flame":
            matching = {c for c,t in p.tiles.items() if t["terrain"] in {13,27}}
        elif kind=="flight":
            matching = {c for c,t in p.tiles.items() if t["terrain"] in {0,18}}
        elif kind=="gas":
            matching = {c for c,t in p.tiles.items() if t.get("effects") and
                        all("cloud of toxic gas" in e.lower() for e in t["effects"])}
        elif kind=="sentry":
            region,_ = sentry_geometry(p,state)
            matching = {c for c in region if p.tiles[c]["terrain"]==14}
        seen,queue = set(ordinary),deque(ordinary)
        while queue:
            for c in neighbors(queue.popleft(),width,height):
                if c in seen or c in occupied or c in p.blocked:continue
                tile = p.tiles.get(c,{})
                if not tile or tile.get("plant") or tile.get("observed") is False:continue
                if c in p.room_blocked and c not in matching:continue
                if tile.get("trap") and kind!="flight":continue
                matching_effect = kind=="gas" and c in matching or kind=="frost" and tile.get("effects") \
                    and all(fire_barrier({"effects":[e]}) or p.harmless_effect(e) for e in tile["effects"])
                if p.effects_block_movement(tile) and not matching_effect:continue
                if tile["terrain"] not in GROUND | {5} and not (
                        c in matching and tile["terrain"] in {0,13,18,27}):continue
                seen.add(c);queue.append(c)
        result.update(c for c in loot if c in seen-ordinary)
    return result


def descend(p,state,enemies):
    kinds = depleted(p,state)
    if not kinds:return None
    if enemies or p.recent_threats or state.get("danger_cells") or p.room_journey or p.puzzle_probe \
            or p.potion_stash or p.trap_payload_return or p.drop_plan:return None
    paths = p.paths(state)
    exits = [c for c in paths if p.tiles[c]["terrain"] in {8,22}]
    if not exits:return None
    try:
        from .policy_decision import Intent
    except ImportError:
        from policy_decision import Intent
    for kind in sorted(kinds):
        p.defer_obligations(state,[{"kind":"potion-room supply exhausted","room":kind,"potion":POTIONS[kind]}],
                            "This floor's collected potion was used elsewhere; room remains uncollected")
    return p.toward(state,min(exits,key=lambda c:len(p.route(paths,c))),
                    "stairs: leave deferred potion room after its floor supply was used elsewhere",
                    paths,intent=Intent.DESCEND)
