"""Revealed trap and bomb tactics using visible terrain, actors and item text."""
try:
    from .combat_items import stats
    from .consumable_tactics import base_name
    from .policy_decision import Intent
    from .payload_workflow import throw as throw_payload, workflow as payload_workflow, PayloadPhase, finish_if_settled
    from .objective_episodes import Scope
except ImportError:
    from combat_items import stats
    from consumable_tactics import base_name
    from policy_decision import Intent
    from payload_workflow import throw as throw_payload, workflow as payload_workflow, PayloadPhase, finish_if_settled
    from objective_episodes import Scope


def payload(state):
    reusable=next((i for i in state["inventory"] if base_name(i) in {"waterskin","dew vial","dew pouch"}
                   and "THROW" in i.get("actions",[]) and not i.get("equipped")),None)
    if reusable:
        return reusable  # Throwing the container does not consume its stored dew.
    # Do not spend food, wands, seeds, scrolls or equipped gear to press a plate.
    choices = [i for i in state["inventory"] if not i.get("equipped")
                 and "THROW" in i.get("actions", []) and stats(i)
                 and not any(k in i["name"].lower() for k in ("explosive", "incendiary", "force cube"))
                  and (i.get("identified") or i.get("curse_known"))]
    return min(choices,key=lambda i:(stats(i)[0]!="thrown",i.get("quantity",1)==1)) if choices else None


def trigger_trap(p, state, enemies, distance, neighbors, line_clear):
    active = [e for e in enemies if not e.get("sleeping")]
    item = payload(state)
    if not active or not item or state.get("danger_cells"):
        return None
    pos, width, height = state["hero"]["cell"], state["map"]["width"], state["map"]["height"]
    actors = {o["cell"] for o in state.get("objects", []) if not o.get("top_item")}
    friends = actors - {e["cell"] for e in active}
    choices = []
    for cell, tile in p.tiles.items():
        key = (state["depth"], cell)
        name = tile.get("trap", "").lower()
        if tile["terrain"] != 18 or not tile.get("visible") or cell in actors or cell in p.loot \
                or key in p.trap_attempts or not p.shot_clear(state, cell):
            continue
        hits = 0
        if name in {"worn dart trap", "poison dart trap"}:
            targets = [e for e in active if distance(cell, e["cell"], width) <= 2
                       and line_clear(cell, e["cell"], width, p.tiles)]
            if not targets:
                continue
            sq = lambda c: (c%width-cell%width)**2 + (c//width-cell//width)**2
            nearest = min(sq(e["cell"]) for e in targets)
            if nearest >= sq(pos) or any(sq(c) <= nearest for c in friends):
                continue
            # Do not infer a nearest target through unexplored surroundings.
            region = [y*width+x for y in range(max(0,cell//width-2),min(height,cell//width+3))
                      for x in range(max(0,cell%width-2),min(width,cell%width+3)) if sq(y*width+x) <= nearest]
            if not all(p.tiles.get(c, {}).get("visible") for c in region):
                continue
            hits = 1
        elif name == "chilling trap":
            if distance(pos, cell, width) <= 1 or any(distance(c, cell, width) <= 1 for c in friends):
                continue
            hits = sum(distance(e["cell"], cell, width) <= 1 for e in active)
        if hits:
            choices.append((hits, -distance(pos,cell,width), -cell, cell))
    if choices:
        target = max(choices)[3]
        action=throw_payload(p,state,item,target,"trap: press revealed mechanism against visible enemies; recover item only after safe disarm")
        if action:p.trap_attempts.add((state["depth"],target))
        return action
    return None


def recover_trap_payload(p,state,enemies):
    if not p.trap_payload_return or state.get("status")!="ready" or state.get("modal"):
        return None
    plan=payload_workflow(p)
    if finish_if_settled(p):
        return None
    if enemies or state.get("danger_cells") or p.recent_threats:
        return None
    if plan.scope!=Scope.of(state):
        p.stop_obligation("trap-payload","Reusable trap payload left on another floor or branch")
    if plan.phase==PayloadPhase.UNVERIFIED:
        p.stop_obligation("trap-payload","Reusable trap payload landing lacks a matching accepted transfer receipt")
    if plan.phase in {PayloadPhase.PROPOSED,PayloadPhase.AIMING}:
        return None
    paths=p.paths(state)
    if plan.cell not in paths or (plan.disarm_required and p.tiles[plan.cell].get("terrain")!=19) \
            or p.effects_block_movement(p.tiles.get(plan.cell,{})):
        return None  # Do not enter a still-active or otherwise hazardous trap.
    if plan.steps>=16:
        p.stop_obligation("trap-payload","Reusable trap payload retrieval exceeded bounded path budget")
    plan.steps+=1
    return p.toward(state,plan.cell,"trap: retrieve reusable payload after fresh disarm/hazard checks",paths,intent=Intent.LOOT)


def cold_trigger_safe(p,state,cell,distance,neighbors):
    """Only a revealed radius-one chilling plate; distance alone cannot avoid darts."""
    tile=p.tiles.get(cell,{})
    if tile.get('terrain')!=18 or tile.get('trap','').lower()!='chilling trap' \
            or not tile.get('visible') or distance(state['hero']['cell'],cell,state['map']['width'])<=1 \
            or not p.shot_clear(state,cell):return False
    obj=p.loot.get(cell,{})
    if obj and obj.get('name','').lower()!='chest':return False
    if obj and any(w in obj.get('description','').lower() for w in ('feels off','bad idea')):return False
    area={cell,*neighbors(cell,state['map']['width'],state['map']['height'])}
    for c in area:
        if c not in p.tiles or not p.tiles[c].get('visible'):return False
        if p.tiles[c].get('effects') or p.tiles[c].get('plant'):return False
        if c!=cell and p.tiles[c].get('trap') and p.tiles[c]['terrain']!=19 \
                and p.tiles[c]['trap'].lower()!='chilling trap':return False
        heap=p.loot.get(c,{})
        if heap.get('top_item') and any(k in base_name(heap['top_item']) for k in ('potion','elixir','brew')):return False
    for actor in state.get('objects',[]):
        if actor.get('top_item'):continue
        if actor['cell'] in area and not (actor['cell']==cell and actor['name'].lower()=='chest'):return False
    return True


def clear_blocking_trap(p,state,enemies,distance,neighbors):
    if enemies or p.recent_threats or state.get('danger_cells') or p.trap_payload_return:return None
    item=payload(state)
    if not item:return None
    before=p.paths(state);choices=[]
    for cell,tile in list(p.tiles.items()):
        if (state['depth'],cell) in p.trap_attempts or cell in before:continue
        if not cold_trigger_safe(p,state,cell,distance,neighbors):continue
        # Admission-only comparison, never a claim that the trap has disarmed.
        old_blocked=p.room_blocked
        try:
            p.tiles[cell]=dict(tile,terrain=19,trap=None)
            p.room_blocked=old_blocked-{cell}
            after=p.paths(state)
        finally:
            p.tiles[cell]=tile;p.room_blocked=old_blocked
        gain=len(set(after)-set(before))
        beyond=any(n not in before and p.tiles.get(n,{}).get('terrain') in {1,2,3,5,6,9,11,14,15,18,19,20,29,30}
                   for n in neighbors(cell,state['map']['width'],state['map']['height']))
        if gain and (gain>1 or p.loot.get(cell) or beyond):
            choices.append((-gain,distance(state['hero']['cell'],cell,state['map']['width']),cell))
    if not choices:return None
    cell=min(choices)[-1]
    action=throw_payload(p,state,item,cell,'trap: remotely press revealed blocking chilling trap from outside its radius')
    if not action:return None
    p.trap_attempts.add((state['depth'],cell))
    p.planner.report['trap_clearance']={'cell':cell,'trap':'chilling trap','ordinary_chest':bool(p.loot.get(cell)),
        'caveat':'Known cold radius only; observe disarm and cloud expiry before walking/retrieving. No hidden trap assumed.'}
    return action


def observe_bombs(p, state, distance):
    width = state["map"]["width"]
    seen = set()
    for obj in state.get("objects", []):
        item = obj.get("top_item", obj)
        if base_name(item) == "bomb" and "fuse is burning" in item.get("description", "").lower():
            seen.add(obj["cell"])
    p.bomb_cells.update(seen)
    if state.get("status") == "ready":
        p.bomb_cells = {c for c in p.bomb_cells if c in seen or not p.tiles.get(c, {}).get("visible")}
    danger = {c for c in p.tiles if any(distance(c, b, width) <= 1 for b in p.bomb_cells)}
    p.room_blocked.update(danger)
    return danger


def use_bomb(p, state, enemies, distance, neighbors):
    bomb = next((i for i in state["inventory"] if base_name(i) == "bomb"
                 and "LIGHTTHROW" in i.get("actions", [])), None)
    active = [e for e in enemies if not e.get("sleeping")]
    if not bomb or not active or p.bomb_cells or state.get("danger_cells"):
        return None
    pos, width, height = state["hero"]["cell"], state["map"]["width"], state["map"]["height"]
    enemy_cells = {e["cell"] for e in active}
    actors = {o["cell"] for o in state.get("objects", []) if not o.get("top_item")}
    choices = []
    for cell, tile in p.tiles.items():
        if not tile.get("visible") or tile["terrain"] not in {1,2,6,9,11,14,15,19,20,29,30} \
                or cell in actors or not 2 <= distance(pos,cell,width) <= 5 or not p.shot_clear(state,cell):
            continue
        area = {cell, *neighbors(cell,width,height)}
        if any(not p.tiles.get(c, {}).get("visible") or p.tiles[c].get("plant") or p.tiles[c].get("effects")
               or p.tiles[c].get("trap") and p.tiles[c]["terrain"] != 19
               or p.tiles[c]["terrain"] not in {1,2,4,6,9,11,14,15,19,20,29,30}
               or c in p.loot or c in actors-enemy_cells for c in area):
            continue
        hits = sum(e["cell"] in area for e in active)
        # No fuse-time prediction: throw only while already outside its blast,
        # retaining at least two safe exits. Enemies may move before it explodes.
        exits = sum(n not in area and p.walkable(n, actors) for n in neighbors(pos,width,height))
        if hits and exits >= 2 and (hits >= 2 or any(e["name"].lower() in {"great crab", "demon spawner"} and e["cell"] in area for e in active)):
            choices.append((hits,-distance(pos,cell,width),-cell,cell))
    if choices:
        target = max(choices)[3]
        p.bomb_cells.add(target)
        return p.use(bomb,"LIGHTTHROW","bomb: light and throw from outside blast with observed collateral checks",target=target)
    return None
