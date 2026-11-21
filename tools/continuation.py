"""Best-effort ordinary inputs after survival admission fails; never API retries."""
try:
    from .policy_decision import Intent
    from .policy_geometry import distance
    from .consumable_tactics import base_name
    from .incoming_damage import priority
except ImportError:
    from policy_decision import Intent
    from policy_geometry import distance
    from consumable_tactics import base_name
    from incoming_damage import priority


def best_effort(p,state,enemies):
    if state.get('status')!='ready' or state.get('modal') or state['hero']['hp']<=0:return None
    try:
        from .toxic_escape import escape
    except ImportError:
        from toxic_escape import escape
    gas_escape=escape(p,state)
    if gas_escape:return gas_escape
    try:
        from .dm100_escape import choose as door_escape
    except ImportError:
        from dm100_escape import choose as door_escape
    flight=door_escape(p,state,enemies)
    if flight:return flight
    try:
        from .exploration_budget import starving_food
    except ImportError:
        from exploration_budget import starving_food
    food=starving_food(p,state,enemies)
    if food:return food
    # Known usable healing remains preferable to accepting damage. Do not
    # guess potion identities or override Pharmacophobia/item eligibility.
    needs_healing=state['hero']['hp']<state['hero']['max_hp'] or any(
        'burning' in b['name'].lower() for b in state['hero'].get('buffs',[]))
    for item in state.get('inventory',[]) if needs_healing else ():
        if base_name(item) in {'potion of healing','waterskin'} and 'DRINK' in item.get('actions',[]) \
                and p.item_action_allowed(item,'DRINK'):
            return p.use(item,'DRINK','last resort: use known healing after no verified safe action')
    escape=p.emergency_transport(state,enemies)
    if escape:return escape
    if getattr(p,'unit_strategies_enabled',False):
        try:
            from .fly_tactics import desperate_attack
        except ImportError:
            from fly_tactics import desperate_attack
        fly=desperate_attack(p,state,enemies)
        if fly:return fly
    # Without enemies or a rendered warning there is nothing to retreat from.
    danger=state.get('danger_cells',[])
    escape=p.retreat(state,enemies,danger) if enemies or danger else None
    if escape:
        escape.reason='last resort: ordinary retreat without a verified survival guarantee'
        return escape
    active=[e for e in enemies if not e.get('sleeping')]
    pos=state['hero']['cell'];width=state['map']['width']
    for enemy in sorted(active,key=lambda e:(-priority(p,state,active,e),distance(pos,e['cell'],width))):
        if distance(pos,enemy['cell'],width)!=1 and not p.shot_clear(state,enemy['cell']):continue
        attack=p.best_attack(state,enemy)
        if attack:
            attack.reason='last resort: admitted attack while accepting unresolved danger'
            return attack
    return None  # No admitted rescue remains; do not manufacture a wait to die.
