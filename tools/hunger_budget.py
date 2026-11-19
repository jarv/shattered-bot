"""Conservative turn forecasts from public hunger, clocks, food and known routes."""
try:
    from .consumable_tactics import base_name
    from .policy_geometry import distance
except ImportError:
    from consumable_tactics import base_name
    from policy_geometry import distance


# Food energy in ordinary game turns. Unknown/unsafe foods receive no credit.
# Pasty variants can supply less than the ordinary pasty: use the lower value.
ENERGY = {'ration of food':300, 'pasty':300, 'small food ration':150,
          'frozen carpaccio':150, 'chargrilled meat':150, 'stewed meat':150,
          'berry':100, 'supply ration':200}


def energy(p, item):
    value=ENERGY.get(base_name(item),0)
    return value/3 if getattr(p,'on_diet',False) else value


def observe(p,state):
    turn=state.get('evaluation_stats',{}).get('elapsed_turns')
    if not isinstance(turn,(int,float)) or isinstance(turn,bool):return
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    phase='starving' if 'starving' in buffs else 'hungry' if 'hungry' in buffs else 'fed'
    old=p.hunger_projection
    if old and turn==old['turn']:return  # Repeated planning does not spend time.
    foods={}
    for i in p.food_items(state):
        name=base_name(i)
        foods[name]=foods.get(name,0)+i.get('quantity',1)
    if not old or turn<old['turn']:
        remaining=150 if phase=='fed' else 0
    else:
        delta=turn-old['turn']
        action=getattr(getattr(p,'last_decision',None),'action',{})
        # Searching takes two clock turns but consumes six hunger units (twelve
        # with a cursed foresight talisman). Budget twelve conservatively.
        extra=10 if action.get('type')=='search' and delta>0 else 0
        remaining=old['remaining']-delta-extra
        if action.get('action')=='EAT':
            # Credit only an observed inventory decrease after the eating action,
            # never the intended meal or an item ID that shifted after pickup.
            for name,count in old['foods'].items():
                if count>foods.get(name,0):
                    remaining+=energy(p,{'name':name})
                    break
        if phase=='fed':
            remaining=max(150,min(450,remaining))
        elif phase=='hungry':
            if old['phase']=='fed':remaining=max(remaining,150-delta-extra)
            remaining=min(150,remaining)
    if phase=='starving':remaining=0
    p.hunger_projection={'turn':turn,'phase':phase,'remaining':max(0,remaining),'foods':foods}


def travel_cost(state,p,route):
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    step=2 if any(b in buffs for b in ('crippl','slow')) else 1
    return max(0,len(route)-1)*step+sum(p.tiles[c].get('terrain')==5 for c in route[1:])


def forecast(p,state):
    sample=getattr(p,'hunger_projection',None)
    turn=state.get('evaluation_stats',{}).get('elapsed_turns')
    if not sample or turn!=sample['turn']:return None
    carried=sum(max(0,energy(p,i)-3)*i.get('quantity',1) for i in p.food_items(state))
    horizon=sample['remaining']+carried
    try:
        from .region_navigation import safe_paths
        from .exploration_budget import food_loot
    except ImportError:
        from region_navigation import safe_paths
        from exploration_budget import food_loot
    paths=safe_paths(p,state,p.paths(state))
    supplies=[]
    exits=[]
    candidates={c for c,t in p.tiles.items() if t['terrain'] in {8,22}}
    candidates.update(c for c,o in p.loot.items() if food_loot(o) and energy(p,o.get('top_item') or o)>0)
    for cell in candidates:
        if cell not in paths:continue
        if cell in p.blocked:continue
        route=p.route(paths,cell)
        if any(distance(c,e['cell'],state['map']['width'])<=4
               for c in route for e in p.recent_threats.values()):continue
        cost=travel_cost(state,p,route)
        obj=p.loot.get(cell,{})
        item=obj.get('top_item') or obj
        if food_loot(obj) and energy(p,item)>0:
            # Pickup + eating cost; floor food is a destination, not prepaid fuel.
            supplies.append({'cell':cell,'turns':cost+4,'food_turns':energy(p,item)})
        if p.tiles[cell]['terrain'] in {8,22}:exits.append({'cell':cell,'turns':cost+1})
    supplies.sort(key=lambda s:s['turns'])
    reachable=[s for s in supplies if s['turns']<=horizon]
    destination=min(reachable,key=lambda s:s['turns']) if reachable else min(exits,key=lambda s:s['turns'],default=None)
    reserve=(destination['turns'] if destination else 0)+30
    result={'remaining_to_starvation_lower_bound':sample['remaining'],
            'carried_food_turns':carried, 'supported_turns':horizon,
            'next_supply':reachable[0] if reachable else None,
            'known_food_routes':supplies, 'destination':destination,
            'reserved_turns':reserve,'optional_turns':max(0,horizon-reserve),
            'qualification':'Conservative forecast, not exact satiety. No unseen food, raw meat, or uncollected food credited; reserve includes 30 turns of uncertainty.'}
    p.planner.report['hunger_budget']=result
    return result


def admits(p,state,cost):
    estimate=forecast(p,state)
    allowed=estimate is None or cost<=estimate['optional_turns']
    if estimate:
        p.planner.report.setdefault('hunger_admissions',[]).append({
            'work_hunger_cost':cost,'admitted':allowed,
            'projected_supported_turns_after_work':estimate['supported_turns']-cost,
            'reserved_turns':estimate['reserved_turns']})
    return allowed


def exhausted(p,state):
    estimate=forecast(p,state)
    return bool(estimate and estimate['optional_turns']==0 and not estimate['next_supply'])


def prioritize_supply(p,state,enemies):
    """Spend the reserved route budget on an actual pickup, never an early meal."""
    if enemies or p.recent_threats or state.get('danger_cells'):return None
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    if any(b in buffs for b in ('burn','poison','bleed','ooze','paral','root','vertigo','blind')):return None
    estimate=forecast(p,state)
    if not estimate or estimate['optional_turns']>20 or not estimate['next_supply']:return None
    try:
        from .policy_decision import Intent
    except ImportError:
        from policy_decision import Intent
    return p.toward(state,estimate['next_supply']['cell'],
                    'food budget: collect known supply before optional turns exhaust food reserve',
                    p.paths(state),intent=Intent.LOOT)
