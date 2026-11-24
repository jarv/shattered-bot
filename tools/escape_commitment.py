"""Short accepted-input escape memory, not a prediction of unseen enemies."""
from dataclasses import dataclass
try:
    from .policy_decision import Intent
except ImportError:
    from policy_decision import Intent


def charges(state):
    return sum(int(i['status'].split('/')[0]) for i in state.get('inventory',[])
               if '/' in (i.get('status') or '') and i['status'].split('/')[0].isdigit()
                and any(k in i['name'].lower() for k in ('staff','wand')))


def append_edge(edges, origin, cell):
    """One edge rule shared by accepted execution and conservative preflight."""
    return (list(edges)+[(origin,cell)])[-8:]


@dataclass(frozen=True)
class RetreatPreflight:
    allowed: bool
    reason: str
    edge: tuple = ()
    projected_edges: tuple = ()

    def record(self):
        return dict(allowed=self.allowed,reason=self.reason,edge=list(self.edge),
                    projected_edges=[list(edge) for edge in self.projected_edges])


def preflight(p,state,route,hide):
    """Check approach + hide against existing and newly created retreat edges.

    This is a compositional constraint check, not geometry, timing, line-of-sight,
    enemy-arrival or hazard admission. Future healing, recharging and expiry are
    not assumed. Projections never mutate or create a live escape commitment.
    """
    route=tuple(route)
    if not route or route[0]!=state["hero"]["cell"]:
        return RetreatPreflight(False,"approach origin does not match current position")
    edges=list((p.escape_commitment or {}).get("edges",()))
    for origin,cell in zip(route,(*route[1:],hide)):
        if origin==cell:
            return RetreatPreflight(False,"itinerary contains a non-movement edge",
                                    (origin,cell),tuple(edges))
        if (cell,origin) in edges:
            return RetreatPreflight(False,"itinerary reverses a protected retreat edge",
                                    (origin,cell),tuple(edges))
        edges=append_edge(edges,origin,cell)
    return RetreatPreflight(True,"approach and hide retain retreat commitments",
                            projected_edges=tuple(edges))


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
        plan['edges']=append_edge(plan['edges'],origin,cell)


def reverses(p,state,cell):
    plan=p.escape_commitment
    return bool(plan and (cell,state['hero']['cell']) in plan['edges'])
