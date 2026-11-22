"""Per-engagement dispatch with shared groups and protected unit-specific tactics."""
try:
    from .policy_geometry import distance,neighbors,line_clear
    from .policy_decision import Intent
    from .incoming_damage import priority
    from .challenge_combat import exposure,reach
    from .necromancer_tactics import choose_necromancer,NecromancerStalemate
    from .ghost_quest import quest_combat
    from .mimic_hunt import crystal_mimic
    from .mimic_tactics import fight_mimic
    from .fly_tactics import escape as fly_escape
    from .doorway_tactics import doorway_first
    from .environment_tactics import trigger_trap,use_bomb
    from .runestone_tactics import choose_runestone
except ImportError:
    from policy_geometry import distance,neighbors,line_clear
    from policy_decision import Intent
    from incoming_damage import priority
    from challenge_combat import exposure,reach
    from necromancer_tactics import choose_necromancer,NecromancerStalemate
    from ghost_quest import quest_combat
    from mimic_hunt import crystal_mimic
    from mimic_tactics import fight_mimic
    from fly_tactics import escape as fly_escape
    from doorway_tactics import doorway_first
    from environment_tactics import trigger_trap,use_bomb
    from runestone_tactics import choose_runestone


def ranged_first(p,state,enemies,target):
    return p.best_attack(state,target,allowed_kinds={'magic','thrown'})


def ranged(p,state,enemies,target):
    try:
        from .ranged_tactics import choose
    except ImportError:
        from ranged_tactics import choose
    return choose(p,state,enemies)


def thief(p,state,enemies,target):
    attack=ranged_first(p,state,enemies,target)
    if attack:return attack
    pos=state['hero']['cell'];width=state['map']['width']
    if distance(pos,target['cell'],width)==1:return p.best_attack(state,target)
    # Only a visible, lone thief and a bounded lower-exposure approach. The
    # species budget counts accepted movements, not proposals or guessed IDs.
    if len(enemies)!=1 or state['hero']['hp']<.6*state['hero']['max_hp'] \
            or p.unit_pursuit_moves[target['name'].lower()]>=4:return None
    paths=p.paths(state,{target['cell']});current=exposure(p,state,enemies,pos,distance,line_clear)
    banks=[c for c in paths if distance(c,target['cell'],width)==1 and 2<=len(p.route(paths,c))<=4
           and all(p.tiles[n]['terrain'] not in {5,7,8,10,18,21,22,31,37,38} and not p.tiles[n].get('plant')
                   and not p.effects_block_movement(p.tiles[n]) and n not in p.loot for n in p.route(paths,c)[1:])
           and exposure(p,state,enemies,p.route(paths,c)[1],distance,line_clear)['exposure']<=current['exposure']]
    if not banks:return None
    bank=min(banks,key=lambda c:len(p.route(paths,c)));step=p.route(paths,bank)[1]
    p.unit_pending_movement={'depth':state['depth'],'branch':state.get('branch',0),
        'name':target['name'].lower(),'from':pos,'to':step,'strategy':'thief'}
    return p.cell(step,'unit: bounded visible thief interception before theft or escape',intent=Intent.APPROACH)


def dedicated(p,state,enemies,target,strategy):
    if strategy.startswith('quest:'):return quest_combat(p,state,enemies,distance,neighbors)
    if strategy=='crystal-mimic':return crystal_mimic(p,state,enemies,distance)
    if strategy=='evasive':return p.snake_combat(state,enemies,' '.join(b['name'].lower() for b in state['hero'].get('buffs',[])))
    if strategy=='wraith':return p.wraith_combat(state,enemies,' '.join(b['name'].lower() for b in state['hero'].get('buffs',[])))
    if strategy=='summoner':
        try:return choose_necromancer(p,state,enemies,distance,neighbors,line_clear)
        except NecromancerStalemate as error:p.stop_no_safe_action(str(error))
    if strategy=='undead':
        return ranged_first(p,state,enemies,target)  # All-target death-blast safety already ran before dispatch.
    if strategy=='fly-swarm':
        try:
            from .fly_tactics import desperate_attack
        except ImportError:
            from fly_tactics import desperate_attack
        return fly_escape(p,state,enemies,list(p.recent_threats.values())) or ranged_first(p,state,enemies,target) \
            or desperate_attack(p,state,enemies)
    if strategy=='mimic':return fight_mimic(p,state,enemies,distance,neighbors,line_clear)
    if strategy in {'ranged-first','stationary','aquatic'}:return ranged_first(p,state,enemies,target)
    if strategy=='ranged':return ranged(p,state,enemies,target)
    if strategy=='thief':return thief(p,state,enemies,target)
    return None  # Ordinary melee/flying units share existing attack scoring.


def choose(p,state,enemies):
    active=[e for e in enemies if not e.get('sleeping')]
    p.unit_pending_movement=None
    if not active:return None
    book=p.unit_strategies
    bosses=[e for e in active if book.profile(e).strategy.startswith('boss:')]
    if bosses:
        p.planner.report['unit_strategy_selection']={'status':'dedicated boss controller','strategy':book.profile(bosses[0]).strategy}
        return None
    pos=state['hero']['cell'];width=state['map']['width']
    target=min(active,key=lambda e:(-priority(p,state,active,e),-book.profile(e).urgency,distance(pos,e['cell'],width),e['cell']))
    contact_attack=None
    # Species urgency must not spend the remaining bolts on a remote swarm
    # while a revealed mimic is already biting. Only replace that remote-fly
    # shot with an admitted magic attack, never physical splitting or a move.
    # Contact/next-step flies retain their existing protected strategy.
    if book.profile(target).strategy=='fly-swarm' and distance(pos,target['cell'],width)>reach(target)+1:
        contacts=sorted((e for e in active if book.profile(e).strategy=='mimic'
                         and distance(pos,e['cell'],width)==1),key=lambda e:e['cell'])
        for mimic in contacts:
            attack=p.best_attack(state,mimic,allowed_kinds={'magic'})
            if attack:
                target=mimic;contact_attack=attack
                break
    profile=book.profile(target)
    p.planner.report['unit_target']=target['cell']
    selection={'name':target['name'],'cell':target['cell'],'strategy':profile.strategy,
               'movement':profile.movement,'status':'selected; admitted action or shared fallback'}
    p.planner.report['unit_strategy_selection']=selection
    action=contact_attack or dedicated(p,state,enemies,target,profile.strategy)
    if action:
        selection['status']='unit strategy selected an action'
        return action
    if profile.strategy=='thief':
        # A floor-local chase budget can be spent long before this sighting.
        # Do not reset it or invent another move. The shared stone controller
        # is below this veto and normally requires low HP; an exhausted lone
        # thief can instead be disabled with an observed, known sleep stone.
        # This selects a throw only, never sleep/defeat or collection credit.
        if target['name'].lower() in {'crazy thief','crazy bandit'} and len(enemies)==1 \
                and p.unit_pursuit_moves[target['name'].lower()]>=4 \
                and distance(pos,target['cell'],width)>1 and not p.stone_cooldown \
                and state.get('status')=='ready' and not state.get('modal') \
                and not state.get('danger_cells') and p.tiles.get(target['cell'],{}).get('visible'):
            sleep=next((i for i in state['inventory'] if i['name'].lower()=='stone of deep sleep'
                        and i.get('identified') and 'THROW' in i.get('actions',[])),None)
            if sleep and p.shot_clear(state,target['cell']) and p.target_allowed(sleep,target) \
                    and p.item_action_allowed(sleep,'THROW'):
                p.stone_cooldown=8
                selection['status']='unit strategy selected an action'
                return p.use(sleep,'THROW','thief: known deep sleep after attacks and bounded pursuit are exhausted',
                             target=target['cell'])
        p.stop_no_safe_action('Visible thief: no usable ranged interception or bounded accepted-pursuit route')
    if state['hero'].get('subclass',state['hero']['name']).lower()=='warlock' and len(enemies)==1 \
            and state['hero']['hp']<.7*state['hero']['max_hp'] and not p.inspection_cache \
            and distance(pos,target['cell'],width)==1:
        inspected=p.inspect_enemy(target)
        if inspected:return inspected
    if book.allows_funnel(enemies):
        action=doorway_first(p,state,enemies,distance,neighbors,line_clear)
        if action:return action
    environment=trigger_trap(p,state,enemies,distance,neighbors,line_clear) or use_bomb(p,state,enemies,distance,neighbors)
    if environment:return environment
    stone=choose_runestone(p,state,enemies,distance,neighbors)
    if stone:return stone
    withdrawal=p.challenge_withdrawal(state,enemies)
    if withdrawal:return withdrawal
    selection['status']='shared combat fallback for selected unit profile'
    return None


def observe_accepted(p,before,decision,after):
    plan=p.unit_pending_movement
    if not plan:return
    p.unit_pending_movement=None
    expected=Intent.RETREAT if plan['strategy']=='ranged' else Intent.APPROACH
    if decision.intent!=expected or decision.action.get('type')!='cell':return
    if (before.get('depth'),before.get('branch',0),before['hero']['cell'],decision.action.get('cell')) != \
            (plan['depth'],plan['branch'],plan['from'],plan['to']):return
    if after.get('depth')!=plan['depth'] or after.get('branch',0)!=plan['branch'] \
            or after['hero']['cell']!=plan['to'] or plan['to']==plan['from']:return
    budget=p.unit_cover_moves if plan['strategy']=='ranged' else p.unit_pursuit_moves
    budget[plan['name']]+=1
    return dict(plan,accepted_movements=budget[plan['name']],
                caveat='Floor-local public-species budget; not a stable or hidden individual enemy ID')
