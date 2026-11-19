"""Prioritize Chains pulls onto an observed adjacent chasm, never inferred kills."""
try:
    from .policy_geometry import distance,BEAM_BLOCKERS,neighbors
    from .policy_decision import Intent
    from .combat_items import unencumbered
    from .challenge_combat import exposure
    from .policy_geometry import line_clear
except ImportError:
    from policy_geometry import distance,BEAM_BLOCKERS,neighbors
    from policy_decision import Intent
    from combat_items import unencumbered
    from challenge_combat import exposure
    from policy_geometry import line_clear


def ray(source,target,width):
    dx,dy=abs(target%width-source%width),abs(target//width-source//width)
    sx=1 if target%width>source%width else -1;sy=1 if target//width>source//width else -1
    major,minor,a,b=(dx,dy,sx,sy*width) if dx>dy else (dy,dx,sy*width,sx)
    if not major:return []
    error=major//2;cell=source;result=[]
    for _ in range(major):
        cell+=a;error+=minor
        if error>=major:cell+=b;error-=major
        result.append(cell)
    return result


def choose_chasm_pull(p,state,enemies,chains):
    if not chains or not chains.get('equipped') or chains.get('known_cursed') or 'CAST' not in chains.get('actions',[]) or p.artifact_cooldown \
            or state.get('status')!='ready' or state.get('modal') or state.get('danger_cells'):return None
    raw=(chains.get('status') or '?').split('/')[0]
    if not raw.isdigit():return None
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    if any(b in buffs for b in ('magic immun','root','paral','vertigo','invisib','cloaked')):return None
    pos=state['hero']['cell'];width=state['map']['width']
    occupied={o['cell'] for o in state.get('objects',[]) if not o.get('top_item')}

    def opportunity(origin,enemy):
        profile=p.unit_strategies.profile(enemy)
        if enemy.get('sleeping') or profile.movement!='ground' or profile.strategy.startswith(('boss:','quest:')) \
                or profile.strategy in {'stationary','crystal-mimic'} \
                or any(word in enemy.get('description','').lower() for word in ('giant champion','immovable','levitat','flying')):return None
        path=ray(origin,enemy['cell'],width)
        if len(path)<2 or not all(p.tiles.get(c,{}).get('visible') for c in path):return None
        # Conservatively accept only a clear public ray. Chains can pass some
        # walls, but we do not guess the first free landing behind an obstacle.
        if any(p.tiles[c]['terrain'] in BEAM_BLOCKERS-{0} or c in occupied for c in path[:-1]):return None
        landing=path[0]
        if p.tiles[landing]['terrain']!=0 or landing in occupied or landing in p.loot:return None
        if distance(enemy['cell'],landing,width)>int(raw):return None
        if profile.name in {'dm-200','modified dm-200','golem','great crab'}:return None  # Large-space/pull exceptions unmodeled.
        return (profile.urgency,distance(origin,enemy['cell'],width),enemy,landing)

    choices=[choice for enemy in enemies if (choice:=opportunity(pos,enemy))]
    if not choices:
        if p.chain_setup_steps>=2 or state['hero']['hp']<.6*state['hero']['max_hp'] or not unencumbered(state):return None
        if any(b in buffs for b in ('slow','crippl','chill')):return None
        current=exposure(p,state,enemies,pos,distance,line_clear)['exposure']
        for bank in neighbors(pos,width,state['map']['height']):
            tile=p.tiles.get(bank,{})
            if not tile.get('visible') or not p.walkable(bank,occupied) or tile.get('terrain') not in {1,3,9,11,14,19,20,29} \
                    or tile.get('trap') or tile.get('plant') or tile.get('effects') or bank in p.loot:continue
            if exposure(p,state,enemies,bank,distance,line_clear)['exposure']>current:continue
            if any(opportunity(bank,e) for e in enemies):
                p.chain_setup_steps+=1
                return p.cell(bank,'artifact: bounded safe ledge setup for grounded-enemy chasm pull',intent=Intent.REPOSITION)
        return None
    _,_,enemy,landing=max(choices,key=lambda c:(c[0],c[1]))
    p.planner.report['chains_pull']={'target':enemy['cell'],'name':enemy['name'],'predicted_landing':landing,
        'evidence':'Visible public ray; first free landing is an observed chasm; grounded species',
        'qualification':'Attempt only: disappearance is not proof of a kill or recovered loot'}
    p.artifact_cooldown=12
    return p.use(chains,'CAST','artifact: prioritize grounded enemy pull onto observed chasm',target=enemy['cell'])
