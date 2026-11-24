"""Bounded reassessment of accepted retreat moves, not hidden enemy timers."""
try:
    from .policy_decision import Intent
    from .policy_geometry import distance, neighbors, line_clear
    from .challenge_combat import champion, reach, magic_factor, exposure, enemy_line
    from .combat_items import magic_score
except ImportError:
    from policy_decision import Intent
    from policy_geometry import distance, neighbors, line_clear
    from challenge_combat import champion, reach, magic_factor, exposure, enemy_line
    from combat_items import magic_score


def observe_accepted(p,before,decision,after):
    try:
        from .survival_policy import is_hostile
    except ImportError:
        from survival_policy import is_hostile
    if before.get('depth')!=after.get('depth'):
        p.pursuit_retreat_moves=p.pursuit_interventions=p.pursuit_last_intervention_move=p.pursuit_quiet_moves=0
        p.pursuit_outcome=p.escape_commitment=None
        p.pursuit_reassessed_move=0
        p.pursuit_lure_exhausted=False
        return None
    if 'hero' not in before or 'hero' not in after:return None
    moved=before['hero']['cell']!=after['hero']['cell']
    elapsed=[s.get('evaluation_stats',{}).get('elapsed_turns') for s in (before,after)]
    timed=all(isinstance(t,(int,float)) for t in elapsed) and elapsed[1]>elapsed[0]
    active=any(is_hostile(o) and not o.get('sleeping') for o in before.get('objects',[]))
    following=any(is_hostile(o) and not o.get('sleeping') for o in after.get('objects',[]))
    try:
        from .escape_commitment import observe,charges
    except ImportError:
        from escape_commitment import observe,charges
    observe(p,before,decision,after,active)
    if active or following:
        outcome=p.pursuit_outcome
        if outcome is None:
            outcome=p.pursuit_outcome={'hp_loss':0,'charge_gain':0,'new_sightings':0,'seen':set()}
        outcome['hp_loss']+=max(0,before['hero']['hp']-after['hero']['hp'])
        outcome['charge_gain']+=max(0,charges(after)-charges(before))
        sightings={(o['name'],o['cell']) for o in after.get('objects',[]) if is_hostile(o)}
        # Positions are sightings, never enemy identities or inferred spawn counts.
        outcome['new_sightings']+=len(sightings-outcome['seen'])
        outcome['seen'].update(sightings)
    if active or following:
        p.pursuit_quiet_moves=0
        if decision.intent==Intent.RETREAT and moved:
            p.pursuit_retreat_moves+=1
            return {'accepted_retreat_moves':p.pursuit_retreat_moves,
                    'moves_since_intervention':p.pursuit_retreat_moves-p.pursuit_last_intervention_move,
                    'interventions':p.pursuit_interventions}
    elif moved or decision.action.get('type')=='wait' or timed:
        # A brief visibility flicker or free inspection must not erase pursuit.
        # Accepted pickups and searches also provide quiet observation time when
        # the public clock advances; do not require extra idle recovery inputs.
        p.pursuit_quiet_moves+=1
        if getattr(p,'unit_strategies_enabled',False) and p.pursuit_quiet_moves>=3 \
                and not p.recent_threats and not p.unseen_damage_turns \
                and after['hero']['hp']>=before['hero']['hp'] \
                and not any(t in b['name'].lower() for b in after['hero'].get('buffs',[])
                            for t in ('poison','burn','bleed')):
            p.escape_commitment=None  # Quiet observed recovery releases route protection, not proof of a kill.
        if p.pursuit_quiet_moves>=3 and p.pursuit_retreat_moves:
            p.pursuit_retreat_moves=p.pursuit_interventions=p.pursuit_last_intervention_move=0
            p.pursuit_outcome=None
            p.pursuit_lure_exhausted=False
            p.pursuit_reassessed_move=0
            return {'reset':'three accepted quiet movement/wait or timed inputs; no kill inferred'}
    return None


def due(p):
    return p.pursuit_retreat_moves-p.pursuit_last_intervention_move>=4 and p.pursuit_interventions<2


def reassess(p,state,enemies):
    if not due(p) or state.get('status')!='ready' or state.get('modal') or state.get('danger_cells'):
        return None
    hero=state['hero']
    buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    if any(b in buffs for b in ('invisib','cloaked','burning','poison','bleed','ooze','paral','vertigo','root','magic immun')):
        return None
    if p.room_journey or p.drop_plan or p.puzzle_probe:return None
    active=[e for e in enemies if not e.get('sleeping')]
    excluded={'fetid rat','gnoll trickster','great crab','demon spawner'}
    if not active or state.get('boss_health_text') or any(e['name'].lower() in p.boss_strategies
            or e['name'].lower() in excluded or 'fist' in e['name'].lower()
            or 'mimic' in e['name'].lower() for e in active):return None
    hp=hero['hp']/max(1,hero['max_hp'])
    # Healthy HP is not progress once accepted pursuit has exhausted its lure
    # budget. Let that outcome reach the same bounded known-charge review;
    # contact, sight-break, hazard and projectile checks below still apply.
    if hp>=0.65 and not p.pursuit_lure_exhausted and 'starving' not in buffs \
            and not any(champion(e)=='growing' for e in active):
        return None
    pos,width,height=hero['cell'],state['map']['width'],state['map']['height']
    current=exposure(p,state,active,pos,distance,line_clear)
    if current['melee']>=2 or current['ranged']:return None
    occupied={e['cell'] for e in enemies}
    # Prefer an actual next-step sight break over another attack trade. Closing
    # the currently occupied ordinary door is an observed movement mechanic.
    closed=dict(p.tiles)
    if p.tiles[pos]['terrain']==6:closed[pos]=dict(p.tiles[pos],terrain=5)
    for cell in neighbors(pos,width,height):
        if not p.walkable(cell,occupied) or p.tiles[cell]['terrain'] in {5,7,8,10,21,22,31,37,38} \
                or cell in p.loot or p.tiles[cell].get('plant'):continue
        if exposure(p,state,active,cell,distance,line_clear)['exposure']:continue
        if all(not enemy_line(p,e,cell,width,line_clear) or not line_clear(e['cell'],cell,width,closed)
               for e in active):return None
    options=[]
    for target in active:
        if distance(pos,target['cell'],width)>reach(target)+1 or not p.shot_clear(state,target['cell']):continue
        if magic_factor(target)<1 or champion(target)=='blazing' and p.tiles[pos]['terrain']!=29:continue
        bar=target.get('health_bar')
        fraction=bar[0]/bar[1] if bar and bar[1]>0 else 1
        for wand in p.charged_magic(state):
            charge=(wand.get('status') or '?').split('/')[0]
            if not wand.get('curse_known') or wand.get('known_cursed') or not charge.isdigit() or int(charge)<=0 \
                    or not p.target_allowed(wand,target) or p.unknown_magic_cooldowns[wand['name']]:continue
            score=p.attack_score(state,target,'magic',magic_score(wand))
            if score<=0:continue
            protected_blazing=champion(target)=='blazing' and p.tiles[pos]['terrain']==29 \
                and distance(pos,target['cell'],width)<=reach(target)
            priority=(champion(target)!='growing',not protected_blazing,
                      target['name'].lower()!='sewer snake',fraction,-score)
            options.append((priority,wand,target))
    if not options:return None
    _,wand,target=min(options,key=lambda option:option[0])
    p.pursuit_interventions+=1
    p.pursuit_last_intervention_move=p.pursuit_retreat_moves
    p.ambush_plan=p.doorway_hold=p.snake_door_reset=None
    p.planner.report['pursuit_reassessment']={'accepted_retreat_moves':p.pursuit_retreat_moves,
        'intervention':p.pursuit_interventions,'target':target['cell'],'target_name':target['name'],
        'known_charges_before':int((wand['status']).split('/')[0]),
        'protected_blazing_priority':champion(target)=='blazing' and p.tiles[pos]['terrain']==29
            and distance(pos,target['cell'],width)<=reach(target),
        'outcome':'bounded ranged intervention; no kill or survival guarantee'}
    return p.use(wand,'ZAP','combat: bounded ranged reassessment after sustained pursuit',target=target['cell'])


def review_outcome(p,state):
    """Outcome review continues even after the two attack interventions are spent."""
    if p.pursuit_retreat_moves-p.pursuit_reassessed_move<4:return
    p.pursuit_reassessed_move=p.pursuit_retreat_moves
    outcome=p.pursuit_outcome or {}
    exhausted=p.pursuit_retreat_moves>=12 or outcome.get('hp_loss',0)>=max(3,.2*state['hero']['max_hp'])
    if exhausted:
        p.pursuit_lure_exhausted=True
        p.ambush_plan=p.snake_door_reset=None
    p.planner.report['pursuit_outcome']={'retreat_moves':p.pursuit_retreat_moves,
        'hp_lost':outcome.get('hp_loss',0),'observed_charge_gains':outcome.get('charge_gain',0),
        'new_position_sightings':outcome.get('new_sightings',0),
        'new_doorway_setups_exhausted':p.pursuit_lure_exhausted,
        'caveat':'No kill or new-enemy count inferred; safe sight breaks remain eligible'}
