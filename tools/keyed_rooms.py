"""Recognize locks and local choice groups using observed geometry and key receipts."""
from collections import deque

try:
    from .policy_geometry import neighbors
except ImportError:
    from policy_geometry import neighbors


GROUND = {1,2,3,9,11,14,15,19,20,29,30}


def region(p, state, start):
    """Room-local floor; ordinary door thresholds delimit separate choices."""
    width,height=state['map']['width'],state['map']['height']
    found=set();queue=deque([start])
    while queue and len(found)<=256:
        cell=queue.popleft()
        tile=p.tiles.get(cell,{})
        if cell in found or tile.get('terrain') not in GROUND \
                or tile.get('trap') or tile.get('plant') or p.effects_block_movement(tile):
            continue
        found.add(cell)
        queue.extend(n for n in neighbors(cell,width,height) if n not in found)
    return found if len(found)<=256 else set()


def local_alternatives(p,state,target,doors,branch_cells,baseline):
    width,height=state['map']['width'],state['map']['height']
    banks=[n for n in neighbors(target,width,height) if n in baseline and p.tiles.get(n,{}).get('terrain') in GROUND]
    vestibule=set().union(*(region(p,state,n) for n in banks)) if banks else set()
    local=[door for door in doors if any(n in vestibule for n in neighbors(door,width,height))]
    # Only a witnessed pair sharing the same vestibule is a choice hypothesis.
    # Three-plus locks can be a vault/path; never write them off as alternatives.
    if len(local)!=2 or target not in local:return set()
    if not any(p.loot.get(c,{}).get('name','').lower()=='chest'
               for door in local for c in branch_cells.get(door,set())):
        return set()  # A key-budgeted multi-door path is not a two-room chest choice.
    other=next(door for door in local if door!=target)
    return branch_cells.get(other,set())-branch_cells.get(target,set())


def record_spend(p,state,target,kind,alternatives):
    p.crystal_spend_plans[target]={'depth':state['depth'],'branch':state.get('branch',0),
                                  'kind':kind,'keys':p.keys.get('crystal',0),
                                  'alternatives':set(alternatives)}


def observe(p,state):
    held=p.keys.get('crystal',0)
    if held>p.crystal_key_count:
        # Extra publicly found keys can make an earlier alternative obtainable.
        p.resolved_crystal_alternatives.clear()
    p.crystal_key_count=held
    visible={t['cell'] for t in state['map']['cells'] if t.get('visible')}
    for target,plan in list(p.crystal_spend_plans.items()):
        if plan['depth']!=state['depth'] or plan['branch']!=state.get('branch',0):
            p.crystal_spend_plans.pop(target,None);continue
        opened=p.tiles.get(target,{}).get('terrain')!=31 if plan['kind']=='door' \
            else p.loot.get(target,{}).get('name','').lower()!='crystal chest'
        if target in visible and opened and p.keys.get('crystal',0)==plan['keys']-1:
            if plan['keys']==1:
                p.resolved_crystal_alternatives.update(plan['alternatives'])
            p.crystal_spend_plans.pop(target,None)
    locks=[{'cell':c,'kind':'door','required_key':{10:'iron',31:'crystal',21:'worn',38:'skeleton'}[t['terrain']]}
           for c,t in p.tiles.items() if t['terrain'] in {10,31,21,38}
           and c not in p.resolved_crystal_alternatives]
    locks.extend({'cell':c,'kind':o['name'].lower(),'required_key':'crystal' if o['name'].lower()=='crystal chest' else 'golden'}
                 for c,o in p.loot.items() if o['name'].lower() in {'crystal chest','locked chest'}
                 and c not in p.resolved_crystal_alternatives and not o.get('for_sale'))
    for lock in locks:
        lock['status']='key held; plan observed access' if p.keys.get(lock['required_key'],0) else 'find matching key; do not retry lock'
    p.planner.report['keyed_rooms']={'locks':locks,'held_keys':dict(p.keys),
        'qualification':'Public lock types, held floor keys and room-local geometry only; no generated room IDs or hidden prizes'}


def chest_choice(p,state,target,candidates):
    """Only the two chests in one observed room share a one-key choice."""
    room=region(p,state,target)
    local={c for c in candidates if c in room}
    if len(local)==2:
        record_spend(p,state,target,'chest',local-{target})
