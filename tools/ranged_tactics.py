"""DM-100 doorway lures, Trickster ranged damage/cover, and other ranged threats."""
try:
    from .policy_geometry import distance,neighbors,line_clear,projectile_line_clear
    from .policy_decision import Intent
    from .challenge_combat import exposure
    from .combat_items import unencumbered
    from .consumable_tactics import base_name
except ImportError:
    from policy_geometry import distance,neighbors,line_clear,projectile_line_clear
    from policy_decision import Intent
    from challenge_combat import exposure
    from combat_items import unencumbered
    from consumable_tactics import base_name


def ranged_enemy(p,enemy):
    return bool({'ranged-attacks','ranged-pull'} & set(p.unit_strategies.profile(enemy).capabilities)) and not enemy.get('sleeping')


def exposed_wait(p,state,enemies):
    if not getattr(p,'unit_strategies_enabled',False):return False
    threats=list(enemies)+[e for c,e in p.recent_threats.items() if c not in {o['cell'] for o in enemies}]
    try:
        from .dm100_escape import exposed_memory
    except ImportError:
        from dm100_escape import exposed_memory
    return exposed_memory(p,state) or any(ranged_enemy(p,e) and distance(state['hero']['cell'],e['cell'],state['map']['width'])>1
               and p.enemy_can_see(state,e,state['hero']['cell']) for e in threats)


def choose(p,state,enemies,*,escape_only=False):
    if not getattr(p,'unit_strategies_enabled',False) or state.get('status')!='ready' or state.get('modal') \
             or state.get('danger_cells') or state.get('boss_health_text'):return None
    if p.ranged_plan and p.ranged_plan.get('mode')=='door-flight':
        try:
            from .dm100_escape import choose as door_flight
        except ImportError:
            from dm100_escape import choose as door_flight
        return door_flight(p,state,enemies)
    active=[e for e in enemies if not e.get('sleeping')]
    targets=[e for e in active if ranged_enemy(p,e)]
    plan=p.ranged_plan
    if not targets:
        targets=[e for e in p.recent_threats.values() if ranged_enemy(p,e) and
                 (e['name'].lower()=='gnoll trickster' or 'ranged-pull' in p.unit_strategies.profile(e).capabilities)]
    if not targets and p.dm100_threat and plan and plan.get('name')=='dm-100':
        targets=[{'name':'DM-100','cell':p.dm100_threat['cell']}]
    if not targets and not plan:return None
    if not targets:
        targets=[e for e in p.recent_threats.values() if ranged_enemy(p,e) and plan['name']==e['name'].lower()]
    if not targets:p.ranged_plan=None;return None
    pos=state['hero']['cell'];width=state['map']['width']
    target=min(targets,key=lambda e:distance(pos,e['cell'],width))
    dm100=target['name'].lower()=='dm-100'
    if any(p.unit_strategies.profile(e).strategy.startswith('boss:') for e in active):return None
    threats=active+[e for e in targets if e not in active]
    # A closed door ceases to block bolts when crossed. Unknown cells cannot
    # prove cover either: treat them as transparent for this defensive check.
    open_tiles=None
    if dm100:
        open_tiles={c:{'terrain':1} for c in range(width*state['map']['height'])}
        open_tiles.update({c:dict(t,terrain=6) if t['terrain']==5 else t for c,t in p.tiles.items()})
    def sees(enemy,cell):
        if dm100 and enemy['name'].lower()=='dm-100':
            return line_clear(enemy['cell'],cell,width,open_tiles) or \
                projectile_line_clear(enemy['cell'],cell,width,open_tiles)
        return p.enemy_can_see(state,enemy,cell)
    exposed=lambda c:any(sees(e,c) and distance(c,e['cell'],width)>1 for e in targets)
    risk=lambda c:exposure(p,state,threats,c,distance,line_clear)['exposure']
    paths=p.paths(state,{e['cell'] for e in enemies})
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    hp=state['hero']['hp'];maximum=state['hero']['max_hp']
    estimate=max(12,.18*maximum)
    dot=any(b in buffs for b in ('poison','bleed','burning','starving'))
    harmful={name for name in ('poison','bleed','burning') if name in buffs}
    trickster=target['name'].lower()=='gnoll trickster'
    if (trickster or dm100) and plan and plan["mode"] == "close":
        p.ranged_plan=None;plan=None  # Reconsider cover instead of continuing a caster chase.
    if dm100 and plan and plan['name']!='dm-100':
        p.ranged_plan=None;plan=None
    pull='ranged-pull' in p.unit_strategies.profile(target).capabilities
    bulk=any(i.get('equipped') and (' of bulk' in i['name'].lower()
             or 'curse of bulk' in i.get('description','').replace('_','').lower())
             for i in state['inventory'])
    cover_first=trickster or pull or dm100
    def door_bank(cell):
        return next((door for door in neighbors(cell,width,state['map']['height'])
                     if p.tiles.get(door,{}).get('terrain') in {5,6}
                     and sees(target,door)),None)
    def can_wait():
        if not dm100:return True
        if harmful:return False
        try:
            from .hunger_budget import admits
        except ImportError:
            from hunger_budget import admits
        affordable=admits(p,state,1)
        # This is bounded combat luring, not optional wand recharging. Do not
        # fund stationary starvation damage when the food reserve is exhausted.
        return affordable or 'starving' not in buffs
    if pull and hp<.5*maximum:
        try:
            from .consumable_tactics import choose_consumable
        except ImportError:
            from consumable_tactics import choose_consumable
        rescue=p.emergency_transport(state,enemies) or choose_consumable(p,state,enemies,distance,neighbors)
        if rescue:return rescue
    p.planner.report['unit_strategy_selection']={'name':target['name'],'cell':target['cell'],'strategy':p.unit_strategies.profile(target).strategy,
        'status':'Door-bank sight break, bounded lure wait, then adjacent attack' if dm100 else
                 'Ranged damage and line-breaking cover; no melee chase' if trickster else
                  'Committed short closure or verified line-breaking cover; no exposed recharge wait'}
    impaired=any(b in buffs for b in ('root','paral','vertigo','slow','crippl','chill'))

    def report_dm(status,route=()):
        if not dm100:return
        current=p.ranged_plan or {}
        p.planner.report['dm100_door_ambush']={
            'status':status,'target_cell':target['cell'],'target_currently_visible':target in active,
            'door':current.get('door'),'goal':current.get('goal'),'remaining_route':list(route),
            'waits':current.get('waits',0),'floor_waits':p.ranged_cover_waits['dm-100'],
            'qualification':'Observed walls must block both projected bolt lines with doors open; unknown cells do not prove cover'}

    def safe_route(route):
        return not impaired and all(p.tiles[c]['terrain'] not in {0,7,8,10,18,21,22,31,37,38}
            and not p.tiles[c].get('plant') and not p.effects_block_movement(p.tiles[c])
            and not p.tiles[c].get('trap') and c not in p.loot and c not in state.get('danger_cells',[])
            and exposure(p,state,[e for e in threats if e is not target],c,distance,line_clear)['exposure']
                <=exposure(p,state,[e for e in threats if e is not target],pos,distance,line_clear)['exposure']
            for c in route[1:])

    def safe_cover(route):
        # Pull control is not ranged damage, but the guard still hits adjacent
        # cells. The target is excluded from safe_route's other-threat check;
        # do not score a walk through its melee reach as an unexposed escape.
        # Known bulk also slows doorway entry. A separated final bank cannot
        # certify that exposed doorway transit against a guard's pull. Check
        # both new and committed routes without guessing its chain-use state.
        if pull and bulk and any(p.tiles[c]['terrain'] in {5,6} and sees(target,c)
                                 for c in route[1:]):
            return False
        return not pull or all(exposure(p,state,[target],c,distance,line_clear)['melee']==0
                               for c in route[1:])

    def move(destination,mode):
        route=p.route(paths,destination)
        if len(route)<2 or not safe_route(route) or mode=='cover' and not safe_cover(route):return None
        if dm100 and mode=='cover' and hp<=10*sum(exposed(c) for c in route[1:]):return None
        p.ranged_plan={'name':target['name'].lower(),'goal':destination,'mode':mode,'steps':1,'waits':0,'hp':hp,'dot':dot,
                       'harmful':sorted(harmful)}
        if dm100:p.ranged_plan['door']=door_bank(destination)
        report_dm('move to verified doorway bank',route)
        if trickster:p.trickster_reposition=False
        return p.cell(route[1],'ranged: commit to '+('close melee range' if mode=='close' else 'doorway or wall cover'),
                      intent=Intent.APPROACH if mode=='close' else Intent.RETREAT)

    # Never keep waiting or walk away when the visible caster has arrived.
    if dm100 and target in active and distance(pos,target['cell'],width)==1:
        p.ranged_plan=None
        attack=p.best_attack(state,target)
        if attack:attack.reason='DM-100: attack adjacent caster after doorway lure; no lightning-range chase'
        report_dm('attack currently observed adjacent caster')
        return attack
    if trickster and target in active and not p.trickster_reposition and (not plan or pos==plan['goal']) \
            and (hp>.35*maximum or not exposed(pos)) \
            and not (plan and pos==plan['goal'] and 'poison' in buffs):
        ranged_attack=p.best_attack(state,target,allowed_kinds={'magic','thrown'})
        if ranged_attack:
            p.ranged_plan=None;p.trickster_reposition=True
            ranged_attack.reason='quest: gnoll trickster prioritize ranged damage, then break dart line'
            return ranged_attack
    if plan:
        lost_hp=hp<plan['hp']
        damaged=lost_hp and not (dot or plan.get('dot',False))
        newly_harmful=bool(harmful-set(plan.get('harmful',harmful)))
        plan['harmful']=sorted(harmful)
        plan['hp']=hp;plan['dot']=dot;plan['steps']+=1
        if plan['mode']=='cover' and pos==plan['goal']:
            # Damage during the last exposed transit is not proof that the
            # newly reached bank failed. Damage after a covered wait is.
            failed_damage=lost_hp and plan['waits']>0 if dm100 else damaged
            if failed_damage or newly_harmful or exposed(pos) or p.tiles[pos]['terrain'] in {5,6} \
                    or dm100 and door_bank(pos) is None:
                p.ranged_failed_cover.add((plan['name'],pos));p.ranged_plan=None;plan=None
            elif plan['waits']<6 and p.ranged_cover_waits[plan['name']]<12 and risk(pos)==0 and not state.get('danger_cells'):
                if not can_wait():return None
                if 'poison' in buffs or p.seed_plan and p.seed_plan.get('kind')=='mageroyal':
                    try:
                        from .seed_tactics import choose_seed
                    except ImportError:
                        from seed_tactics import choose_seed
                    cleanse=choose_seed(p,state,enemies,distance,neighbors)
                    if cleanse:return cleanse
                plan['waits']+=1
                p.ranged_cover_waits[plan['name']]+=1
                report_dm('bounded covered wait for approach')
                return p.decision({'type':'wait'},'ranged: wait behind verified cover for enemy approach',intent=Intent.RECOVER)
            else:
                p.ranged_failed_cover.add((plan['name'],pos));p.ranged_plan=None;plan=None
        elif plan['goal'] in paths and plan['steps']<=12:
            route=p.route(paths,plan['goal'])
            affordable=plan['mode']!='close' or hp>.35*maximum+(len(route)-1)*estimate \
                and distance(plan['goal'],target['cell'],width)==1
            if plan['mode']=='cover' and pull:
                # A following guard can see a formerly separated destination
                # before we reach it. Revalidate the endpoint as well as the
                # transit, using the same admission as a newly selected bank.
                affordable=affordable and not exposed(plan['goal']) and risk(plan['goal'])==0 \
                    and p.tiles[plan['goal']]['terrain'] not in {5,6}
            if dm100:
                affordable=affordable and not exposed(plan['goal']) and door_bank(plan['goal']) is not None \
                    and hp>10*sum(exposed(c) for c in route[1:])
            if len(route)>1 and safe_route(route) and affordable and (plan['mode']!='cover' or safe_cover(route)):
                report_dm('continue revalidated doorway-bank route',route)
                return p.cell(route[1],'ranged: finish committed '+plan['mode']+' route',
                              intent=Intent.APPROACH if plan['mode']=='close' else Intent.RETREAT)
            p.ranged_plan=None;plan=None
        else:p.ranged_plan=None;plan=None
    if not trickster and target in active and distance(pos,target['cell'],width)==1 and not (pull and hp<.5*maximum):
        p.ranged_plan=None
        return p.best_attack(state,target)
    # Covered and not pursuing a plan: do not walk back into a caster's lane.
    if not exposed(pos):
        if cover_first and risk(pos)==0 and p.tiles[pos]['terrain'] not in {5,6} \
                and (target['name'].lower(),pos) not in p.ranged_failed_cover \
                and p.ranged_cover_waits[target['name'].lower()]<12 \
                and (not dm100 or door_bank(pos) is not None) and can_wait():
            p.ranged_plan={'name':target['name'].lower(),'goal':pos,'mode':'cover','steps':1,'waits':1,
                           'hp':hp,'dot':dot,'harmful':sorted(harmful)}
            p.ranged_cover_waits[target['name'].lower()]+=1
            report_dm('retain verified bank for bounded lure')
            return p.decision({'type':'wait'},'ranged: retain wall/door cover against ranged/control threat; do not step into doorway',intent=Intent.RECOVER)
        attack=p.best_attack(state,target,allowed_kinds={'magic','thrown'}) if target in active else None
        if attack:return attack
        # A sensed enemy through a wall is not a reason to wait indefinitely.
        if not active:return None
    close=[];cover=[]
    for cell in paths:
        route=p.route(paths,cell)
        if not 2<=len(route)<=10 or not safe_route(route):continue
        if not trickster and distance(cell,target['cell'],width)==1 and len(route)<=4 and target in active and unencumbered(state) \
                and hp>.35*maximum+(len(route)-1)*estimate \
                and all(distance(b,target['cell'],width)<distance(a,target['cell'],width) for a,b in zip(route,route[1:])):
            close.append((len(route),cell))
        if safe_cover(route) and p.tiles[cell]['terrain'] not in {5,6} and not exposed(cell) and risk(cell)==0 and (target['name'].lower(),cell) not in p.ranged_failed_cover \
                and (not dm100 or door_bank(cell) is not None
                     and hp>10*sum(exposed(c) for c in route[1:])):
            door=any(p.tiles[c]['terrain'] in {5,6} for c in route)
            cover.append((sum(exposed(c) for c in route[1:]),not door,len(route),cell))
    if close and (not cover or not cover_first and min(close)[0]<=3):return move(min(close)[1],'close')
    if cover:return move(min(cover)[-1],'cover')
    if escape_only:return None
    attack=p.best_attack(state,target,allowed_kinds={'magic','thrown'}) if target in active else None
    if attack:
        if trickster:
            p.trickster_reposition=True
            attack.reason='quest: gnoll trickster ranged damage without admitted line-breaking cover'
        return attack
    # The early ranged leaf can abort before the shared runestone controller.
    # Once damage and verified movement are exhausted, retain the observed
    # single-caster disable instead of immediately entering ordinary retreat.
    # Selecting this throw is not evidence of sleep, a hit, or a safe escape.
    if dm100 and target in active and len(active)==1 and exposed(pos) and not p.stone_cooldown:
        sleep=next((i for i in state['inventory'] if base_name(i)=='stone of deep sleep'
                    and i.get('identified') and 'THROW' in i.get('actions',[])),None)
        if sleep and p.shot_clear(state,target['cell']) and p.target_allowed(sleep,target) \
                and p.item_action_allowed(sleep,'THROW'):
            p.stone_cooldown=8
            return p.use(sleep,'THROW','DM-100: known deep sleep after attacks and verified cover are exhausted',
                         target=target['cell'])
    if trickster and target in active:
        p.stop_no_safe_action('Gnoll Trickster: no usable ranged attack or verified cover; refusing melee chase')
    if exposed(pos):p.stop_no_safe_action('Ranged exposure: no admitted attack, short melee closure or verified cover; do not wait for recharge in the firing lane')
    return None
