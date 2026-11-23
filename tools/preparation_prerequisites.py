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
    # Shelves stop ordinary sight and movement. Their unseen backs do not
    # border paths, but can still explain a reserved flame obligation.
    # Scout only an observed shelf edge adjoining reachable ground; this
    # authorizes information gathering, not burning, crossing or collection.
    shelf_gaps = {n for c, t in p.tiles.items()
                  if t.get("observed") and t.get("terrain") == 27
                  and any(a in paths for a in neighbors(c, width, height))
                  for n in neighbors(c, width, height)
                  if not p.tiles.get(n, {}).get("observed")
                  and not p.tiles.get(n, {}).get("mapped")}
    gaps.update(shelf_gaps)
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


def sentry_reobservation(p, state):
    """Observe incomplete sentry geometry from ordinary known ground only.

    SentryRoom.Sentry targets EMPTY_SP (14), not ordinary floor/door cells.
    We never cross that terrain, infer a missing wall, or authorize a drink.
    """
    try:
        from .room_tactics import sentry_geometry
        from .special_rooms import component
        from .policy_geometry import distance, line_clear
        from .survival_policy import is_hostile
        from .escape_commitment import reverses
        from .hunger_budget import travel_cost
    except ImportError:
        from room_tactics import sentry_geometry
        from special_rooms import component
        from policy_geometry import distance, line_clear
        from survival_policy import is_hostile
        from escape_commitment import reverses
        from hunger_budget import travel_cost
    if state.get("status") != "ready" or state.get("modal") or not state.get("hero"):
        return None
    if sentry_geometry(p,state)[0] or p.recent_threats or p.unseen_damage_turns or state.get("danger_cells") \
            or any(is_hostile(o) for o in state.get("objects",[])) \
            or any(getattr(p,key,None) for key in ("potion_stash","room_journey","drop_plan","trap_payload_return","puzzle_probe")):
        return None
    hero=state["hero"];pos=hero["cell"];width,height=state["map"]["width"],state["map"]["height"]
    buffs=" ".join(b["name"].lower() for b in hero.get("buffs",[]))
    if hero["hp"]<.85*hero["max_hp"] or any(t in buffs for t in (
            "burn","poison","bleed","blind","vertigo","paral","root","frozen","chill","drowsy","sleep")):
        return None
    actors=[a for a in p.room_actors.values() if a["name"].lower()=="red sentry"]
    if len(actors)!=1:
        return None
    region=component(actors[0]["cell"],p.tiles,{1,11,14,25,26},width,height)
    if len(region)>200:
        return None
    gaps={n for c in region for n in neighbors(c,width,height) if not p.tiles.get(n,{}).get("observed")}
    if not gaps:
        return None
    plan=getattr(p,"preparation_scout",None)
    if not plan or (plan["depth"],plan["branch"])!=(state["depth"],state.get("branch",0)):
        plan=dict(depth=state["depth"],branch=state.get("branch",0),target=None,visited=[],
                  accepted=0,stalled=0,status="planning")
    if plan["accepted"]>=48 or plan["stalled"]>=8 or len(plan["visited"])>=4:
        p.planner.report["preparation_reconnaissance"]={**plan,"reason":"bounded reobservation allowance exhausted"}
        return None
    ordinary={1,2,3,5,6,9,11,19,20,29}
    barriers=p.navigation_barriers(state,Intent.REPOSITION)
    excluded={c for c,t in p.tiles.items() if c in barriers or not t.get("observed")
              or t.get("terrain") not in ordinary or any(t.get(k) for k in ("effects","plant","trap"))
              or c in p.loot or c in p.neutral_actor_cells}
    if pos in excluded:
        return None
    paths=p.paths(state,excluded)
    choices=[]
    for cell in paths:
        if cell==pos or cell in excluded or cell in plan["visited"]:
            continue
        if plan["target"] is not None and cell!=plan["target"]:
            continue
        route=p.route(paths,cell)
        if len(route)>33:
            continue
        potential=sum(distance(cell,g,width)<=6 and line_clear(cell,g,width,p.tiles) for g in gaps)
        if not potential:
            continue
        step=route[1]
        if not p.tiles[step].get("visible") or reverses(p,state,step) \
                or not admits(p,state,2*travel_cost(state,p,route)+14):
            continue
        choices.append((-potential,len(route),cell,route))
    if not choices:
        return None
    _,_,target,route=min(choices)
    plan.update(target=target,status="approaching",known_gaps=sorted(gaps))
    p.preparation_scout=plan
    p.planner.report["preparation_reconnaissance"]={**plan,"route":route,
        "qualification":"ordinary-floor observation only; no protection, wall or reward inferred"}
    action=p.toward(state,target,"planning: reobserve incomplete sentry perimeter from ordinary ground",
                    paths,intent=Intent.REPOSITION)
    if action:
        action.preparation_scout=target
    return action


def observe_reconnaissance(p,before,decision,after):
    plan=getattr(p,"preparation_scout",None)
    if not plan or not hasattr(decision,"preparation_scout"):
        return None
    if (after.get("depth"),after.get("branch",0))!=(plan["depth"],plan["branch"]):
        plan["status"]="displaced"
        return dict(plan)
    plan["accepted"]+=1
    if after.get("hero",{}).get("cell")==before.get("hero",{}).get("cell"):
        plan["stalled"]+=1
    else:
        plan["stalled"]=0
    if after.get("hero",{}).get("cell")==plan["target"]:
        plan["visited"].append(plan["target"])
        plan.update(target=None,status="arrived-reobserve")
    return dict(plan)
