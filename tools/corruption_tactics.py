"""Utility control from public health pixels, status icons and nearby enemies."""
try:
    from .consumable_tactics import base_name
    from .policy_geometry import distance
    from .challenge_combat import reach
except ImportError:
    from consumable_tactics import base_name
    from policy_geometry import distance
    from challenge_combat import reach


def icons(enemy):
    return ' '.join(str(b).lower() for b in enemy.get('status_icons',[]))


def clock(state):
    return state.get('evaluation_stats',{}).get('elapsed_turns',0)


def choose(p,state,enemies):
    if not getattr(p,'unit_strategies_enabled',False) or state.get('status')!='ready' or state.get('modal') \
            or state.get('danger_cells') or p.corruption_pending:return None
    active=[e for e in enemies if not e.get('sleeping')]
    hero=state['hero'];pos=hero['cell'];w=state['map']['width']
    buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    if not active or hero['hp']<.35*hero['max_hp'] or any(t in buffs for t in ('magic immun','blind','burn','paral','vertigo')):return None
    if p.corruption_attempts['total']>=8:return None
    wand=next((i for i in state['inventory'] if base_name(i) in {'wand of corruption','staff of corruption'}
               and (i.get('identified') or i.get('curse_known')) and not i.get('known_cursed')
               and 'ZAP' in i.get('actions',[]) and (i.get('status') or '').split('/')[0].isdigit()
               and int(i['status'].split('/')[0])>0),None)
    if not wand:return None
    # A random debuff is not a guaranteed emergency disable. Do not spend a
    # setup turn under adjacent/fast pressure or override emergency priorities.
    for e in active:
        speed=2 if 'fast-movement' in p.unit_strategies.profile(e).capabilities else 1
        if distance(pos,e['cell'],w)<=reach(e)+speed-1:return None
    direct=bool(p.charged_magic(state));choices=[]
    for e in active:
        name=e['name'].lower();profile=p.unit_strategies.profile(e)
        wraith=name=='wraith'
        if (profile.protected and not wraith) or profile.strategy.startswith(('boss:','quest:')) or not p.target_allowed(wand,e) \
                or not p.shot_clear(state,e['cell']) or any(t in icons(e) for t in ('corrupt','doom')):continue
        if p.corruption_attempts[('name',name)]>=4 or p.corruption_attempts[(name,e['cell'])]>=2 \
                or clock(state)<p.corruption_ready_at.get(name,0):continue
        bar=e.get('health_bar');fraction=bar[0]/bar[1] if bar and bar[1]>0 else None
        debuffs=sum(t in icons(e) for t in ('weak','vulnerab','crippl','blind','terror','slow','hex','paraly','poison','burn','chill','bleed'))
        if not wraith and not debuffs and (fraction is None or fraction>.65):continue
        others=sum(other is not e and distance(e['cell'],other['cell'],w)<=4 for other in active)
        if direct and fraction is not None and fraction<=.1 and not others:continue
        # Conversion can restore an enemy and turn it on nearby hostiles. Never
        # estimate exact private resistance, promise a conversion, or call it DPS.
        utility=min(others,3)*3 + min(debuffs,3) + (2 if fraction is not None and fraction<=.5 else 0) \
            + (2 if not direct else 0) + (3 if wraith else 0)
        if utility<5:continue
        choices.append((utility,-distance(pos,e['cell'],w),e))
    if not choices:return None
    utility,_,target=max(choices,key=lambda c:c[:2]);name=target['name'].lower()
    p.corruption_pending={'name':name,'cell':target['cell'],'wand':wand['name'],'depth':state['depth']}
    p.planner.report['corruption_utility']={'target':target['cell'],'utility':utility,
        'basis':'Public weakened/status-bearing target and nearby hostile opportunities',
        'qualification':'Random control or corruption, not direct damage or a guaranteed ally/kill'}
    return p.use(wand,'ZAP','wand: corruption utility control on weakened target near other threats; verify actual status',target=target['cell'])


def observe(p,before,decision,after):
    plan=p.corruption_pending
    if not plan:return None
    if decision.action.get('type')=='back' and before.get('status')=='targeting':
        p.corruption_pending=None;return {'cancelled':True,'confirmed':False}
    if decision.action!={'type':'cell','cell':plan['cell']} or before.get('status')!='targeting':return None
    p.corruption_pending=None
    if before.get('depth')!=after.get('depth'):return None
    name=plan['name']
    p.corruption_attempts['total']+=1;p.corruption_attempts[('name',name)]+=1
    p.corruption_attempts[(name,plan['cell'])]+=1;p.corruption_ready_at[name]=clock(after)+3
    actor=next((o for o in after.get('objects',[]) if o['cell']==plan['cell'] and o['name'].lower()==name),None)
    return {'target_cell':plan['cell'],'accepted_target_input':True,
            'observed_status_icons':actor.get('status_icons',[]) if actor else [],
            'corruption_visible_at_cast_cell':bool(actor and 'corrupt' in icons(actor)),
            'qualification':'Only actual public icons at cast cell; disappearance/movement is not a conversion or kill receipt'}
