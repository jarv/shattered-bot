"""Bounded next-door/recharge movement when an ordinary snake cannot be hit safely."""
try:
    from .challenge_combat import champion, exposure, reach
    from .policy_decision import Intent
except ImportError:
    from challenge_combat import champion, exposure, reach
    from policy_decision import Intent


def seek_next_door(p,state,enemies,distance,neighbors,line_clear):
    active=[e for e in enemies if not e.get("sleeping")]
    hero=state["hero"]
    buffs=" ".join(b["name"].lower() for b in hero.get("buffs",[]))
    pos,width,height=hero["cell"],state["map"]["width"],state["map"]["height"]
    if hero["hp"]<0.45*hero["max_hp"] or state.get("danger_cells") or p.snake_route_inputs>=12 \
            or any(champion(e) for e in active) or any(b in buffs for b in ("root","paral","vertigo","burning")):
        return None
    risk=exposure(p,state,active,pos,distance,line_clear)
    if risk["ranged"] or sum(distance(pos,e["cell"],width)<=reach(e) for e in active)>1:
        return None
    plan=p.snake_route
    if plan and plan["hp"]-hero["hp"]>max(3,0.15*hero["max_hp"]):return None
    occupied={e["cell"] for e in enemies}
    paths=p.paths(state,occupied)
    doors=[c for c in paths if c!=pos and p.tiles[c]["terrain"] in {5,6}
           and 2<=len(p.route(paths,c))<=21]
    options=[]
    for door in doors:
        route=p.route(paths,door)
        if any(c in p.loot or p.tiles[c].get("plant") or p.tiles[c]["terrain"] in {7,8,21,22,31,37,38} for c in route[1:]):continue
        options.append((plan is None or door!=plan.get("door"),len(route),door,route[1]))
    # No usable next door: keep moving over observed ground for recharge, not
    # into an unseen cell or a known dead end, and never endlessly reverse.
    if not options:
        for cell in neighbors(pos,width,height):
            if p.walkable(cell,occupied) and cell not in p.loot and not p.tiles[cell].get("plant") \
                    and p.tiles[cell]["terrain"] not in {5,7,8,21,22,31,37,38} \
                    and sum(p.walkable(n,occupied) for n in neighbors(cell,width,height))>=2:
                options.append((True,50+p.visits[cell],None,cell))
    for _,_,door,step in sorted(options,key=lambda x:(p.snake_route_edges[(x[3],pos)],x[0],x[1])):
        proposed=exposure(p,state,active,step,distance,line_clear)
        if proposed["ranged"] or proposed["exposure"]>risk["exposure"] \
                or proposed["exposure"] and hero["hp"]<0.55*hero["max_hp"] \
                or p.snake_route_edges[(pos,step)]>=2:continue
        p.snake_route=plan or {"door":door,"hp":hero["hp"]}
        p.snake_route["door"]=door
        p.snake_route_inputs+=1
        p.snake_route_edges[(pos,step)]+=1
        return p.cell(step,"snake: seek next observed doorway or reposition while charges recover",intent=Intent.RETREAT)
    return None
