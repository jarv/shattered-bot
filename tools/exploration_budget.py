"""Resource-aware descent using only observed routes, loot and hero condition."""
try:
    from .policy_decision import Intent
    from .consumable_tactics import base_name
    from .mimic_tactics import suspicious_container
    from .policy_geometry import distance
except ImportError:
    from policy_decision import Intent
    from consumable_tactics import base_name
    from mimic_tactics import suspicious_container
    from policy_geometry import distance


def food_loot(obj):
    item=obj.get('top_item') or {}
    name=base_name(item) if item else obj.get('name','').lower()
    return not obj.get('for_sale') and not suspicious_container(obj) and (
        'EAT' in item.get('actions',[]) and not any(raw in name for raw in ('seed','mystery meat','blandfruit'))
        or any(food in name for food in ('ration of food','pasty','grilled meat','frozen carpaccio')))


def starving_food(p,state,enemies):
    """Starvation changes food value even when no exit has been discovered."""
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    if 'starving' not in buffs or enemies or state.get('danger_cells'):return None
    if any(b in buffs for b in ('burning','poison','bleed','ooze','paral','vertigo','root')):return None
    carried=p.food_items(state)
    if carried:return p.use(carried[0],'EAT','survival: eat carried food before optional work while starving')
    paths=p.paths(state)
    width=state['map']['width']
    candidates=[c for c,o in p.loot.items() if c in paths and food_loot(o) and c not in p.blocked
                and all(not any(distance(n,e['cell'],width)<=4 for e in p.recent_threats.values())
                        for n in p.route(paths,c)[1:])]
    for cell in sorted(candidates,key=lambda c:len(p.route(paths,c))):
        pressure=getattr(p,'inventory_pressure',None)
        if pressure:
            try:
                from .inventory_tactics import choose as cleanup, signature
                from .pickup_priority import bag
            except ImportError:
                from inventory_tactics import choose as cleanup, signature
                from pickup_priority import bag
            incoming=p.loot[cell].get('top_item',p.loot[cell])
            refused=pressure.get('item')
            if pressure.get('depth')==state['depth'] and pressure['signature']==signature(state) \
                    and refused and bag(state,refused)==bag(state,incoming):
                # Preparation precedes normal inventory relief. A receipt-backed
                # full bag needs the same guarded cleanup, not another food click.
                # Decline if cleanup cannot act; the pickup remains outstanding.
                return cleanup(p,state,enemies,incoming_item=incoming)
        action=p.toward(state,cell,'survival: prioritize observed food while starving',paths,intent=Intent.LOOT)
        if action:return action
    return None


def pressure(p,state):
    try:
        from .hunger_budget import exhausted
    except ImportError:
        from hunger_budget import exhausted
    if exhausted(p,state):return "projected hunger budget exhausted without a reachable known food pickup"
    hero=state["hero"]
    buffs=" ".join(b["name"].lower() for b in hero.get("buffs",[]))
    food=p.food_items(state)
    hp=hero["hp"]/max(1,hero["max_hp"])
    if not food and "starving" in buffs:return "starving without food"
    if not food and "hungry" in buffs and hp<0.7:return "hungry, wounded and without food"
    if not food and hp<0.45 and not p.charged_magic(state):return "low health without food or ready magic"
    return None


def useful_loot(obj):
    if obj.get("for_sale") or suspicious_container(obj) or not obj.get("top_item"):return False
    item=obj["top_item"]
    name=base_name(item)
    if item.get("known_cursed"):
        return False
    # Equipment can be valuable on later floors even when not yet wearable.
    # This only retains short admitted pickups; it never auto-equips unknown gear.
    try:
        from .combat_items import stats, accessory_kind
    except ImportError:
        from combat_items import stats, accessory_kind
    if stats(item) or accessory_kind(item):
        return True
    return any(word in name for word in ("ration of food","pasty","grilled meat","frozen carpaccio",
                                         "wand","scroll of upgrade","potion of strength","torch","key"))


def current_floor_food_work(p,state,enemies=(),paths=None):
    """Known safe viewing/door work, not an assertion that unseen food exists."""
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    if 'starving' not in buffs or enemies or state.get('danger_cells'):return []
    if any(b in buffs for b in ('burning','poison','bleed','ooze','paral','vertigo','root','blind')):return []
    try:
        from .region_navigation import safe_paths
    except ImportError:
        from region_navigation import safe_paths
    paths=safe_paths(p,state,p.paths(state) if paths is None else paths)
    report=p.exploration_report(state,paths);pos=state['hero']['cell'];width=state['map']['width']
    targets=set(report['unexplored_frontiers'])|set(report['unopened_doors'])
    return sorted(c for c in targets if c!=pos and c in paths
        and all(p.tiles[n]['terrain'] not in {7,8,10,21,22,31,37,38}
                and not p.tiles[n].get('plant') and not p.tiles[n].get('effects')
                and not p.loot.get(n,{}).get('for_sale')
                and not any(distance(n,e['cell'],width)<=4 for e in p.recent_threats.values())
                for n in p.route(paths,c)[1:]))


def selective_descent(p,state,enemies):
    depth=state.get("depth",0)
    level=state["hero"].get("level",1)
    p.planner.report["progression"]={
        "depth":depth,"level":level,"early_level_target":depth+1 if 1<=depth<=5 else None,
        "below_early_target":1<=depth<=5 and level<depth+1,
        "policy":"Prefer useful equipment and quest rewards; experience target is advisory, never farm or block descent"}
    food=starving_food(p,state,enemies)
    if food:return food
    try:
        from .hunger_budget import exhausted
    except ImportError:
        from hunger_budget import exhausted
    urgent=exhausted(p,state)
    if getattr(p,'strict_observed_loot',False) and (
            not urgent or getattr(p,'stop_on_incomplete_loot',True)):
        try:
            from .loot_completion import pending_collections
        except ImportError:
            from loot_completion import pending_collections
        if pending_collections(p):return None
    reason=pressure(p,state)
    if not reason or enemies or state.get("danger_cells"):return None
    buffs=" ".join(b["name"].lower() for b in state["hero"].get("buffs",[]))
    if any(b in buffs for b in ("burning","poison","bleed","ooze","paral","vertigo","root")):return None
    paths=p.paths(state)
    food_work=current_floor_food_work(p,state,enemies,paths)
    if food_work and not urgent:
        p.planner.report['food_search_priority']={'known_current_floor_targets':food_work,
            'selection':'search current-floor frontiers/doors before starvation descent',
            'caveat':'No unseen food assumed; normal bounded navigation and safety admission still apply'}
        return None
    exits=[c for c in paths if p.tiles[c]["terrain"] in {8,22}]
    if not exits:return None
    # Never deliberately walk into a recently observed pursuer's reach to skip a floor.
    width=state["map"]["width"]
    def route_safe(target):
        return all(not any(distance(c,e["cell"],width)<=4 for e in p.recent_threats.values())
                   for c in p.route(paths,target)[1:])
    exits=[c for c in exits if route_safe(c)]
    if not exits:return None
    # Short concrete supply detours remain valuable; speculative rooms do not.
    candidates=[c for c,o in p.loot.items() if c in paths and len(p.route(paths,c))<=7
                and c not in p.blocked and useful_loot(o) and route_safe(c)]
    for c in sorted(candidates,key=lambda c:len(p.route(paths,c))):
        action=p.toward(state,c,"explore-budget: nearby useful supply before early descent",paths,intent=Intent.LOOT)
        if action:return action
    for target in sorted(exits,key=lambda c:len(p.route(paths,c))):
        action=p.toward(state,target,"stairs: resource-aware descent: "+reason,paths,intent=Intent.DESCEND)
        if action:
            report=p.exploration_report(state,paths)
            p.planner.report["exploration_budget"]={"reason":reason,"hp":state["hero"]["hp"],
                "food_stacks":len(p.food_items(state)),"level":state["hero"].get("level"),
                 "frontiers_deferred":len(report["unexplored_frontiers"]),
                 "doors_deferred":len(report['unopened_doors']),
                 "unreachable_deferred":len(report['unreachable_known_floor']),
                 "loot_deferred":len(p.loot),"stairs":target}
            return action
    return None
