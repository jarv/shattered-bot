"""Small observed reward tours with an independent, protection-funded return.

Used by gas sweeps and chest-independent pool surveys; other Journey controllers
retain their existing contracts. Recognition is never movement authorization.
"""
from collections import deque
from dataclasses import dataclass,field

try:
    from .policy_geometry import neighbors
    from .policy_decision import Intent
    from .combat_items import unencumbered
    from .mimic_tactics import suspicious_container
    from .room_tactics import GROUND,safe_tile,remaining,PROTECTION
except ImportError:
    from policy_geometry import neighbors
    from policy_decision import Intent
    from combat_items import unencumbered
    from mimic_tactics import suspicious_container
    from room_tactics import GROUND,safe_tile,remaining,PROTECTION


MARGIN=3
CONTAINERS={'chest','locked chest','crystal chest','tomb','skeleton','skeletal remains'}


def enclosure(p,state,start):
    """Observed interior only, with ordinary doors as boundaries."""
    found=set();queue=deque([start])
    while queue and len(found)<=196:
        c=queue.popleft()
        if c in found or not p.tiles.get(c,{}).get('observed') \
                or p.tiles[c]['terrain'] not in GROUND-{6}:continue
        found.add(c)
        queue.extend(n for n in neighbors(c,state['map']['width'],state['map']['height']) if n not in found)
    return found if len(found)<=196 else set()


def gas_profile(p,state,room):
    around=room|{n for c in room for n in neighbors(c,state['map']['width'],state['map']['height'])}
    return any(p.tiles.get(c,{}).get('terrain')==25 for c in around) and any(
        p.tiles[c].get('terrain')==19 and 'toxic vent' in (
            str(p.tiles[c].get('trap',''))+' '+p.tiles[c].get('name','')).lower() for c in room)


def reward_cost(obj):
    if obj.get('top_item'):return 1  # Pickup time in addition to the movement edge.
    return 4 if obj.get('name','').lower() in {'skeleton','skeletal remains','tomb'} else 2


def targets(p,state,kind,room):
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    prepared=not any(k in buffs for k in ('hungry','starving')) and state['hero']['hp']>=.85*state['hero']['max_hp'] and sum(
        int(i['status'].split('/')[0]) for i in p.charged_magic(state)
        if (i.get('status') or '?').split('/')[0].isdigit())>=3
    known_gas=kind=='gas' and gas_profile(p,state,room)
    found={}
    for c,o in p.loot.items():
        name=o.get('name','').lower()
        if c not in room or o.get('for_sale') or suspicious_container(o) or c in p.combat_deferred_loot:continue
        if kind=='pool' and not o.get('top_item') and name!='chest':continue
        if kind=='gas' and name in {'skeleton','skeletal remains','tomb'} and not prepared:continue
        if not o.get('top_item') and name not in CONTAINERS:continue
        if name in {'locked chest','crystal chest','tomb','skeleton','skeletal remains'} \
                and c not in p.allowed_chests and not (
                    known_gas and prepared and name in {'skeleton','skeletal remains'}):
            continue
        found[c]=o
    return found


def paths(p,state,start,kind,allowed,*,probe=False):
    occupied={o['cell'] for o in [*p.room_actors.values(),*state.get('objects',[])] if not o.get('top_item')
              and o.get('name','').lower() not in CONTAINERS|{'mirror image'}}
    previous={start:None};queue=deque([start])
    while queue:
        c=queue.popleft()
        if c!=start and p.loot.get(c,{}).get('name','').lower() in CONTAINERS:continue
        for n in neighbors(c,state['map']['width'],state['map']['height']):
            tile=p.tiles.get(n,{})
            door=tile.get('terrain') in {5,6} and not any(tile.get(k) for k in ('plant','trap','effects'))
            if n in previous or n not in allowed or not tile.get('observed') \
                    or n in state.get('danger_cells',[]) or n in occupied:continue
            if not (safe_tile(p,n,kind,occupied) or door):continue
            # A different special-room exclusion is not immunity to its hazard.
            if n in p.room_blocked and not (
                kind=='pool' and tile.get('terrain') in {11,14,29} or kind=='gas' and (
                    tile.get('effects') and all('cloud of toxic gas' in e.lower() for e in tile['effects'])
                    or n in p.allowed_chests or p.loot.get(n,{}).get('name','').lower() in {'skeleton','skeletal remains'}
                    and gas_profile(p,state,allowed))):continue
            previous[n]=c;queue.append(n)
    return previous


def tour(p,state,kind,allowed,bank,loot,duration,*,probe=False):
    """Subset DP: maximize collected heaps, then minimize timed actions."""
    start=state['hero']['cell']
    # Rooms have three generated heaps; cap unexpected large input explicitly.
    cells=sorted(loot)[:6]
    graphs={c:paths(p,state,c,kind,allowed,probe=probe) for c in {start,*cells}}
    costs={c:reward_cost(loot[c]) for c in cells}
    speed=2 if any(k in b['name'].lower() for b in state['hero'].get('buffs',[])
                   for k in ('slow','crippl','chill')) else 1
    states={(0,start):(0,[])};best=None
    for mask in range(1<<len(cells)):
        for end in [start,*cells]:
            entry=states.get((mask,end))
            if entry is None:continue
            spent,order=entry;back=graphs[end]
            if mask and bank in back:
                total=spent+(len(p.route(back,bank))-1)*speed+MARGIN
                if total<=duration:
                    candidate=(-len(order),total,tuple(order))
                    if best is None or candidate<best:best=candidate
            for i,c in enumerate(cells):
                if mask&(1<<i) or c not in graphs[end]:continue
                new=spent+(len(p.route(graphs[end],c))-1)*speed+costs[c]
                key=(mask|(1<<i),c)
                if new+MARGIN<=duration and (key not in states or new<states[key][0]):
                    states[key]=(new,order+[c])
    if best is None:return None
    order=list(best[2])
    return order,best[1],p.route(graphs[start],order[0])


@dataclass
class RewardTrip:
    kind: str
    route: list
    depth: int
    room: set
    targets: list
    cost: float
    branch: int = 0
    stage: str = 'protect'
    steps: int = 0
    collected: set = field(default_factory=set)
    survey: bool = False
    surveyed: set = field(default_factory=set)
    interactions: dict = field(default_factory=dict)
    planned_count: int = 0

    def advance(self,p,state,enemies,neighbors):
        pos=state['hero']['cell'];bank=self.route[0]
        if (state['depth'],state.get('branch',0))!=(self.depth,self.branch):
            p.stop_obligation('room-journey','Protected multi-reward trip crossed floor or branch without returning')
        duration=remaining(state,PROTECTION[self.kind][1])
        if self.stage=='protect' and not duration and pos==bank:
            p.room_journey=None;return None
        self.steps+=1
        buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
        if not unencumbered(state) or any(k in buffs for k in ('vertigo','paral','root')):
            p.stop_obligation('room-journey','Protected tour movement budget is no longer deterministic')
        if self.stage=='protect':self.stage='outbound'
        expanded=enclosure(p,state,min(self.room)) if self.room else set()
        self.room.update(expanded)
        allowed=self.room|set(self.route)
        graph=paths(p,state,pos,self.kind,allowed)
        back=p.route(graph,bank) if bank in graph else []
        speed=2 if any(k in buffs for k in ('slow','crippl','chill')) else 1
        if not back or duration<(len(back)-1)*speed+MARGIN:
            p.stop_obligation('room-journey','Protected tour has no duration-funded verified return')
        if self.steps>=64 or enemies or p.recent_threats or state.get('danger_cells') \
                or state['hero']['hp']<.65*state['hero']['max_hp']:
            self.stage='return'
        loot=targets(p,state,self.kind,self.room)
        self.targets=sorted(set(self.targets)|set(loot))
        # Receipts are copied by observe() before the ordinary ledger clears them.
        available={c:o for c,o in loot.items() if self.interactions.get(c,0)<6}
        plan=tour(p,state,self.kind,allowed,bank,available,duration) if self.stage!='return' else None
        if plan:
            order,self.cost,leg=plan;target=order[0]
            if target==pos or len(leg)==2 and loot[target].get('name','').lower() in CONTAINERS:
                self.interactions[target]=self.interactions.get(target,0)+1
                return p.cell(target,'room: open or retrieve next protected reward; require pickup receipt')
            step=leg[1]
        elif self.survey and self.stage!='return' and self.route[-1] not in self.surveyed:
            target=self.route[-1]
            if pos==target:
                self.surveyed.add(target);self.stage='return';step=back[1] if len(back)>1 else bank
            elif target in graph:
                leg=p.route(graph,target);returning=paths(p,state,target,self.kind,allowed)
                if bank in returning and (len(leg)+len(p.route(returning,bank))-2)*speed+MARGIN<=duration:
                    step=leg[1]
                else:self.stage='return';step=back[1] if len(back)>1 else bank
            else:self.stage='return';step=back[1] if len(back)>1 else bank
        else:
            self.stage='return';step=back[1] if len(back)>1 else bank
        p.planner.report['protected_rewards']={'kind':self.kind,'targets':self.targets,
            'collected':sorted(self.collected),'unresolved':sorted(set(self.targets)-self.collected),
            'stage':self.stage,'duration':duration,'return_cost':(len(back)-1)*speed+MARGIN,
            'survey_only':self.survey,'room_clear_claimed':False,
            'interaction_exhausted':sorted(c for c,n in self.interactions.items() if n>=6)}
        if self.stage=='return' and pos==bank:
            for c in self.collected:
                if c not in p.loot and c not in p.unconfirmed_loot:
                    p.completed_room_rewards.add((state['depth'],self.kind,c))
            if self.kind=='pool' and self.surveyed:
                for h in p.piranha_habitats.values():
                    if h['water']&self.room:h['surveyed']=True
            p.room_journey=None;return None
        tile=p.tiles.get(step,{})
        if not tile.get('visible'):
            p.stop_obligation('room-journey','Protected tour next step is not freshly visible')
        return p.cell(step,'room: return before protection expires' if self.stage=='return'
                      else 'room: follow budgeted multi-reward route',intent=Intent.RETREAT if self.stage=='return' else Intent.REPOSITION)


def gas_plan(p,state,journey):
    room=enclosure(p,state,journey.route[-1])
    loot=targets(p,state,'gas',room)
    # A recognized gas room may reveal its other heaps only after activation.
    # Keep that trip adaptive even when just one heap is initially observed.
    if not loot or len(loot)<2 and not gas_profile(p,state,room):return journey
    allowed=room|set(journey.route)
    duration=remaining(state,PROTECTION['gas'][1]) or 20
    plan=tour(p,state,'gas',allowed,journey.route[0],loot,duration,probe=True)
    if not plan:return journey
    order,cost,leg=plan
    return RewardTrip('gas',leg,state['depth'],room,sorted(loot),cost,
                      branch=state.get('branch',0),planned_count=len(order))


def observe(p):
    trip=p.room_journey
    if isinstance(trip,RewardTrip):
        trip.collected.update(set(trip.targets)&p.loot_collection_receipts)
