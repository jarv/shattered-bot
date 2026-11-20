"""Immediate, committed flight to an observed door; no unseen destination clicks."""
try:
    from .policy_geometry import neighbors,distance,line_clear,projectile_line_clear
    from .policy_decision import Intent
    from .challenge_combat import exposure
except ImportError:
    from policy_geometry import neighbors,distance,line_clear,projectile_line_clear
    from policy_decision import Intent
    from challenge_combat import exposure


GROUND={1,2,3,5,6,9,11,14,15,19,20,29,30}


def observe(p,state):
    if state.get('status')!='ready' or state.get('modal'):return
    visible=[o for o in state.get('objects',[]) if o['name'].lower()=='dm-100' and not o.get('sleeping')]
    turn=state.get('evaluation_stats',{}).get('elapsed_turns')
    if visible:
        enemy=min(visible,key=lambda o:distance(state['hero']['cell'],o['cell'],state['map']['width']))
        p.dm100_threat={'cell':enemy['cell'],'age':0,'turn':turn}
    elif p.dm100_threat:
        p.dm100_threat['age']+=1
        last=p.dm100_threat.get('turn')
        age=turn-last if isinstance(turn,(int,float)) and isinstance(last,(int,float)) else p.dm100_threat['age']
        if age>12:p.dm100_threat=None


def sight_tiles(p,state,*,open_doors=False):
    # Unknown cells cannot prove cover; bolts cross chasms and newly opened doors.
    tiles={c:{'terrain':1} for c in range(state['map']['width']*state['map']['height'])}
    tiles.update({c:dict(t,terrain=1 if t['terrain']==0 else 6 if open_doors and t['terrain']==5 else t['terrain'])
                  for c,t in p.tiles.items()})
    return tiles


def sees(p,state,source,target,*,open_doors=False):
    tiles=sight_tiles(p,state,open_doors=open_doors)
    width=state['map']['width']
    return line_clear(source,target,width,tiles) or projectile_line_clear(source,target,width,tiles)


def exposed_memory(p,state):
    memory=p.dm100_threat
    return bool(memory and distance(state['hero']['cell'],memory['cell'],state['map']['width'])>1
                and sees(p,state,memory['cell'],state['hero']['cell']))


def clean(p,state,cell,occupied):
    tile=p.tiles.get(cell,{})
    return tile.get('terrain') in GROUND and tile.get('observed') is not False \
        and cell not in occupied and cell not in p.loot and cell not in state.get('danger_cells',[]) \
        and not tile.get('trap') and not tile.get('plant') and not p.effects_block_movement(tile) \
        and p.walkable(cell,occupied)


def choose(p,state,enemies):
    if not getattr(p,'unit_strategies_enabled',False) or state.get('status')!='ready' or state.get('modal') \
            or state.get('danger_cells') or state.get('boss_health_text'):return None
    pos=state['hero']['cell'];width,height=state['map']['width'],state['map']['height']
    active=[e for e in enemies if not e.get('sleeping')]
    targets=[e for e in active if e['name'].lower()=='dm-100']
    plan=p.ranged_plan if p.ranged_plan and p.ranged_plan.get('mode')=='door-flight' else None
    memory=p.dm100_threat
    if not targets and not plan and not exposed_memory(p,state):return None
    if any(p.unit_strategies.profile(e).strategy.startswith('boss:') for e in active):return None
    target=min(targets,key=lambda e:distance(pos,e['cell'],width)) if targets else None
    source=target['cell'] if target else plan['last_seen'] if plan else memory['cell']
    if target and distance(pos,target['cell'],width)==1:
        if plan and target['cell']==plan['door'] and (plan.get('armed') or
                plan['stage']=='bank' and pos==plan['goal'] and p.previous_position==plan['door']):
            p.ranged_plan=None
            return p.cell(target['cell'],'DM-100: doorway surprise on observed arrival')
        p.ranged_plan=None
        attack=p.best_attack(state,target)
        if attack:attack.reason='DM-100: attack adjacent caster after doorway lure; no lightning-range chase'
        return attack
    # A robust old bank plan is handled by the established covered-wait controller.
    if p.ranged_plan and p.ranged_plan.get('mode')=='cover' and p.ranged_plan.get('name')=='dm-100':
        return None
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    if any(b in buffs for b in ('root','paral','vertigo','slow','crippl','chill')):return None
    occupied={e['cell'] for e in enemies}
    others=[e for e in active if e['name'].lower()!='dm-100']
    paths=p.paths(state,occupied)
    def route_ok(route):
        return all(clean(p,state,c,occupied) and
                   exposure(p,state,others,c,distance,line_clear)['exposure']
                   <=exposure(p,state,others,pos,distance,line_clear)['exposure']
                   for c in route[1:])
    def report(status,route=()):
        current=p.ranged_plan or {}
        p.planner.report['dm100_door_ambush']={
            'status':status,'door':current.get('door'),'goal':current.get('goal'),
            'remaining_route':list(route),'target_cell':source,'target_currently_visible':bool(target),
            'waits':current.get('waits',0),
            'qualification':'Shortest admitted observed-door route; reobserve beyond the threshold; no survival or unseen enemy position guarantee'}
    def abandon(reason):
        if plan:
            p.dm100_failed_doors.add(plan['door'])
        p.ranged_plan=None
        report(reason)
    if plan:
        if target:plan['last_seen']=source
        plan['steps']+=1
        if plan['depth']!=state['depth'] or plan['branch']!=state.get('branch',0) or plan['steps']>24 \
                or p.tiles.get(plan['door'],{}).get('terrain') not in {5,6}:
            abandon('door-flight invalidated or bounded transit expired');plan=None
        elif plan['stage']=='bank' and pos==plan['goal']:
            door=plan['door']
            if p.previous_position==door:
                plan['armed']=True  # Accepted step off a door closes its sight line.
            lost=state['hero']['hp']<plan['hp'];plan['hp']=state['hero']['hp']
            if not clean(p,state,pos,occupied) or sees(p,state,source,pos) or lost and plan['waits']>0 \
                    or any(b in buffs for b in ('poison','bleed','burning','starving')):
                abandon('do not wait in a reopened, damaging, or exposed doorway bank');plan=None
            elif plan['waits']<6 and p.ranged_cover_waits['dm-100']<12:
                plan['waits']+=1;p.ranged_cover_waits['dm-100']+=1
                report('bounded covered wait for doorway surprise')
                return p.decision({'type':'wait'},'DM-100: wait off the closed doorway for an observed surprise opportunity',
                                  intent=Intent.RECOVER)
            else:
                abandon('bounded doorway arrival wait exhausted');plan=None
        elif plan['stage']=='bank':
            bank=plan['goal']
            if bank in paths:
                route=p.route(paths,bank)
                if len(route)>1 and route_ok(route):
                    report('finish doorway sight break',route)
                    return p.cell(route[1],'DM-100: finish stepping behind committed doorway; no lane reversal',intent=Intent.RETREAT)
            abandon('committed doorway bank obstructed');plan=None
        elif pos==plan['door']:
            # Opening/reaching the visible door is not permission to click an
            # unseen square. Only newly observed safe far-side banks qualify.
            previous=plan['approach']
            banks=[]
            closed=sight_tiles(p,state);closed[plan['door']]={'terrain':5}
            for bank in neighbors(pos,width,height):
                dot=(bank%width-pos%width)*(previous%width-pos%width)+(bank//width-pos//width)*(previous//width-pos//width)
                if dot>=0 or not clean(p,state,bank,occupied) or p.tiles[bank]['terrain'] in {5,6} \
                        or line_clear(source,bank,width,closed) or projectile_line_clear(source,bank,width,closed):
                    continue
                if exposure(p,state,others,bank,distance,line_clear)['exposure'] \
                        >exposure(p,state,others,pos,distance,line_clear)['exposure']:continue
                banks.append(bank)
            if banks:
                bank=min(banks,key=lambda c:(sees(p,state,source,c,open_doors=True),p.visits[c],c))
                plan.update(stage='bank',goal=bank)
                report('step off observed threshold and close door',[pos,bank])
                return p.cell(bank,'DM-100: step behind nearest observed door and break lightning sight',intent=Intent.RETREAT)
            abandon('no observed safe hiding square beyond opened door');plan=None
        elif plan['door'] in paths:
            route=p.route(paths,plan['door'])
            if len(route)>1 and route_ok(route):
                plan['approach']=route[-2]
                report('continue fastest committed door flight',route)
                return p.cell(route[1],'DM-100: flee directly to committed visible door; no ranged exchange',intent=Intent.RETREAT)
            abandon('observed door route changed or became hazardous');plan=None
        else:
            abandon('committed door no longer reachable');plan=None
    if not target and not exposed_memory(p,state):return None
    options=[]
    for door,tile in p.tiles.items():
        if tile['terrain'] not in {5,6} or tile.get('observed') is False \
                or door in p.dm100_failed_doors or door not in paths or door==pos:continue
        route=p.route(paths,door)
        if not 2<=len(route)<=17 or not route_ok(route):continue
        if any(distance(c,e['cell'],width)<=1 for c in route[1:] for e in targets):continue
        options.append((not tile.get('visible'),len(route),door,route))
    if not options:return None
    remembered,_,door,route=min(options)
    # Known wall-backed banks can retain the existing thoroughly tested cover
    # workflow. Otherwise approach the door first and discover its far side.
    approach=route[-2];banks=[]
    for bank in neighbors(door,width,height):
        dot=(bank%width-door%width)*(approach%width-door%width)+(bank//width-door//width)*(approach//width-door//width)
        if dot<0 and clean(p,state,bank,occupied) and p.tiles[bank]['terrain'] not in {5,6} \
                and not sees(p,state,source,bank,open_doors=True):
            banks.append(bank)
    hp=state['hero']['hp']
    if banks and hp>10*sum(sees(p,state,source,c,open_doors=True) for c in route[1:]):
        bank=min(banks)
        p.ranged_plan={'name':'dm-100','mode':'cover','door':door,'goal':bank,'steps':1,'waits':0,'hp':hp,
                       'dot':any(b in buffs for b in ('poison','bleed','burning','starving')),
                       'harmful':[b for b in ('poison','bleed','burning') if b in buffs]}
    else:
        p.ranged_plan={'name':'dm-100','mode':'door-flight','stage':'door','door':door,'goal':door,
                       'approach':approach,'steps':0,'waits':0,'depth':state['depth'],'branch':state.get('branch',0),
                       'last_seen':source,'hp':hp,'armed':False}
    report('immediate flight to nearest visible admitted door' if not remembered
           else 'no current visible door; use nearest previously observed door',route)
    return p.cell(route[1],'DM-100: flee immediately to nearest '+('remembered' if remembered else 'visible')+' door before trading lightning',
                  intent=Intent.RETREAT)
