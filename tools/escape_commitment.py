"""Short accepted-input escape memory, not a prediction of unseen enemies."""
try:
    from .policy_decision import Intent
except ImportError:
    from policy_decision import Intent


def charges(state):
    return sum(int(i['status'].split('/')[0]) for i in state.get('inventory',[])
               if '/' in (i.get('status') or '') and i['status'].split('/')[0].isdigit()
               and any(k in i['name'].lower() for k in ('staff','wand')))


def observe(p,before,decision,after,active):
    plan=p.escape_commitment
    # Accepted attacks can spend time without changing hero HP or charges.
    # Count public clock progress, but not free targeting/menu observations.
    elapsed=[(s.get('evaluation_stats') or {}).get('elapsed_turns') for s in (before,after)]
    timed=all(isinstance(t,(int,float)) for t in elapsed) and elapsed[1]>elapsed[0]
    progressed=timed or before['hero']['cell']!=after['hero']['cell'] or decision.action.get('type')=='wait' \
        or before['hero']['hp']!=after['hero']['hp'] or charges(before)!=charges(after)
    if plan and progressed:
        plan['age']+=1
        if plan['age']>=12 or after['hero']['hp']>=plan['hp']+max(2,after['hero']['max_hp']*.15) \
                or charges(after)>plan['charges']:
            p.escape_commitment=plan=None
    origin,cell=before['hero']['cell'],after['hero']['cell']
    if active and decision.intent==Intent.RETREAT and origin!=cell:
        if not plan:
            plan=p.escape_commitment={'edges':[],'hp':after['hero']['hp'],
                                      'charges':charges(after),'age':0}
        plan['edges']=(plan['edges']+[(origin,cell)])[-8:]


def reverses(p,state,cell):
    plan=p.escape_commitment
    return bool(plan and (cell,state['hero']['cell']) in plan['edges'])
