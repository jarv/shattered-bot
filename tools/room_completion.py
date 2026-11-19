"""Descent obligations from observed puzzles/rewards, never generated room IDs."""
try:
    from .special_rooms import component, fire_barrier
    from .room_tactics import sentry_geometry
except ImportError:
    from special_rooms import component, fire_barrier
    from room_tactics import sentry_geometry


def obligations(p, state):
    pending = []
    pending.extend({'kind':'unrecoverable escaped mimic reward','cell':loss['cell'],
                    'name':loss['name'],'status':loss['status'],'collected':False}
                   for loss in p.missed_loot if loss['depth']==state['depth'])
    pending.extend({"kind":"unresolved suspicious mimic/reward","cell":cell}
                   for cell in p.mimic_obligations)
    quest = p.ghost_quest
    wandmaker=getattr(p,'wandmaker_quest',{})
    if wandmaker.get('depth')==state['depth'] and wandmaker.get('stage')!='done':
        pending.append({'kind':'Wandmaker quest/reward','stage':wandmaker.get('stage','unstarted'),
                        'variant':wandmaker.get('variant'),'cell':wandmaker.get('cell')})
    if quest.get("stage") in {"active","reward","claiming","collect_dropped"}:
        pending.append({"kind":"Sad Ghost quest/reward","stage":quest["stage"]})
    elif getattr(p,'unit_strategies_enabled',False) and quest.get('stage')!='done' and quest.get('last_depth')==state['depth']:
        pending.append({'kind':'unstarted observed Sad Ghost quest','cell':quest.get('last_cell'),
                        'reason':'Requires safe dialogue approach, 80% health and three known magic charges; no completion credit'})
    if p.room_journey or p.puzzle_probe or p.drop_plan:
        pending.append({"kind":"active room/protection plan"})
    for cell,tile in p.tiles.items():
        terrain = tile["terrain"]
        if terrain == 13:
            pending.append({"kind":"unopened barricade","cell":cell})
        elif fire_barrier(tile):
            pending.append({"kind":"magical fire barrier","cell":cell})
        elif terrain == 0 and "distant well" in tile.get("name","").lower():
            pending.append({"kind":"uncompleted distant-well drop","cell":cell})
        elif terrain in {10,21}:
            pending.append({"kind":"unopened locked room","cell":cell})
        elif terrain == 31 and cell not in p.resolved_crystal_alternatives:
            pending.append({"kind":"unresolved crystal choice","cell":cell})
    for cell,obj in p.loot.items():
        if obj.get("for_sale"):
            continue
        name = obj["name"].lower()
        if cell in p.resolved_crystal_alternatives:
            continue
        if cell in p.room_skipped or any(word in name for word in ("tomb","skeleton","crystal chest","locked chest")):
            pending.append({"kind":"uncollected special-room reward","cell":cell,"name":obj["name"]})
        else:
            pending.append({'kind':'uncollected observed item/chest','cell':cell,'name':obj['name']})
    for cell,obj in p.unconfirmed_loot.items():
        if cell not in p.loot and cell not in p.resolved_crystal_alternatives:
            pending.append({'kind':'item disappeared without collection evidence','cell':cell,'name':obj['name']})
    for cell,actor in p.room_actors.items():
        name = actor["name"].lower()
        if name in {"rot lasher","rot heart"}:
            if wandmaker.get('variant')=='berry' and wandmaker.get('stage')=='active':
                pending.append({'kind':'Wandmaker garden objective','cell':cell,'actor':actor['name']})
            continue
        kind = "pool" if "piranha" in name else "sentry" if name == "red sentry" else None
        width,height=state["map"]["width"],state["map"]["height"]
        region=set()
        if kind=="pool":
            water=component(cell,p.tiles,{29},width,height)
            region={y*width+x for c in water for x in range(max(0,c%width-1),min(width,c%width+2))
                    for y in range(max(0,c//width-1),min(height,c//width+2))}
        elif kind=="sentry":
            region,_=sentry_geometry(p,state)
        finished = kind and any(d==state["depth"] and k==kind and c in region
                               for d,k,c in p.completed_room_rewards)
        if not finished:
            pending.append({"kind":"guarded special room not verified complete","cell":cell,"actor":actor["name"]})
    return pending
