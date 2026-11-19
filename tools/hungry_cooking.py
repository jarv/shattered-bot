"""Hungry-time Icecap-first meat preparation, observed recovery, then eating."""
try:
    from .consumable_tactics import base_name
    from .policy_geometry import distance,neighbors
    from .resource_tactics import prepare_meat
except ImportError:
    from consumable_tactics import base_name
    from policy_geometry import distance,neighbors
    from resource_tactics import prepare_meat


def choose(p,state,enemies):
    if enemies or p.recent_threats or state.get('danger_cells') or state.get('status')!='ready' or state.get('modal'):return None
    hero=state['hero'];buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    if hero['hp']<.5*hero['max_hp'] or any(t in buffs for t in ('burn','poison','bleed','paral','root','vertigo','blind')):return None
    plan=p.hungry_cooking_plan
    hungry=any(t in buffs for t in ('hungry','starving'))
    if not hungry and not plan:return None
    cooked=next((i for i in state['inventory'] if base_name(i) in {'frozen carpaccio','chargrilled meat'} and 'EAT' in i.get('actions',[])),None)
    if cooked and hungry:
        p.hungry_cooking_plan=None
        return p.use(cooked,'EAT','food: eat observed cooked meat while hungry')
    if plan:
        plan['steps']+=1
        if plan['steps']>16:
            p.hungry_cooking_plan=None;p.meat_plan=None
            p.log_continuation_error(state,'cooking-incomplete','Prepared meat not recovered within budget; no food credited',dict(plan))
            return None
        if plan['stage']=='plant':
            if plan['kind'] not in p.tiles.get(plan['cell'],{}).get('plant','').lower():
                p.hungry_cooking_plan=None;p.meat_plan=None
                return None  # Do not repeat a seed whose planting was not observed.
            a=prepare_meat(p,state,enemies,distance,neighbors)
            if a:plan['stage']='recover'
            return a
        obj=next((o for o in state.get('objects',[]) if o.get('cell')==plan['cell']
                  and base_name(o.get('top_item',o)) in {'frozen carpaccio','chargrilled meat'}),None)
        tile=p.tiles.get(plan['cell'],{})
        if tile.get('effects') or tile.get('plant'):
            return p.decision({'type':'wait'},'food: wait safely outside cooking effects before retrieval')
        if obj and tile.get('visible') and p.walkable(plan['cell']) and not tile.get('trap'):
            return p.toward(state,plan['cell'],'food: collect observed cooked meat before eating',p.paths(state))
        p.hungry_cooking_plan=None
        return None
    if p.hungry_cooking_attempts>=4 or any(getattr(p,k,None) for k in
            ('potion_stash','trap_payload_return','food_freeze_plan','drop_plan','room_journey','puzzle_probe')):return None
    # The legacy one-piece preparer orders Icecap before Firebloom. Its
    # configured wrapper additionally protects every observed collateral cell.
    a=prepare_meat(p,state,enemies,distance,neighbors)
    if not a:return None
    cell=p.target;kind=p.meat_plan['kind'] if p.meat_plan else None
    p.hungry_cooking_attempts+=1
    p.hungry_cooking_plan={'cell':cell,'kind':kind,'stage':'plant' if kind else 'recover','steps':0}
    return a
