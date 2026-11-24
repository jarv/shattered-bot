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
    from .preparation_itinerary import PreparationItinerary
    from .objective_episodes import Scope
    from .escape_commitment import preflight, reverses
except ImportError:
    from policy_geometry import neighbors
    from policy_decision import Intent
    from combat_items import unencumbered
    from mimic_tactics import suspicious_container
    from room_tactics import GROUND,safe_tile,remaining,PROTECTION
    from preparation_itinerary import PreparationItinerary
    from objective_episodes import Scope
    from escape_commitment import preflight, reverses


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


def paths(p,state,start,kind,allowed,*,probe=False,no_transit_loot=False):
    occupied={o['cell'] for o in [*p.room_actors.values(),*state.get('objects',[])] if not o.get('top_item')
              and o.get('name','').lower() not in CONTAINERS|{'mirror image'}}
    previous={start:None};queue=deque([start])
    while queue:
        c=queue.popleft()
        if c!=start and (p.loot.get(c,{}).get('name','').lower() in CONTAINERS
                        or no_transit_loot and c in p.loot):continue
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


def travel_cost(p,route,speed=1,*,reserve_doors=False):
    return max(0,len(route)-1)*speed + (
        sum(p.tiles.get(c,{}).get('terrain') in {5,6} for c in route[1:])
        if reserve_doors else 0)


def deterministic_doors(state):
    return not any(i.get('equipped') and (
        ' of bulk' in i['name'].lower() or 'curse of bulk' in
        i.get('description','').replace('_','').lower()) for i in state.get('inventory',[]))


def ordinary_endpoint(p,state,cell,*,allow_closed=False):
    tile=p.tiles.get(cell,{})
    return bool(tile.get('observed') and tile.get('visible')
                and tile.get('terrain') in GROUND|({5} if allow_closed else set())
                and cell not in p.room_blocked and cell not in p.blocked
                and cell not in p.neutral_actor_cells and cell not in state.get('danger_cells',[])
                and not any(tile.get(k) for k in ('plant','trap','effects'))
                and not any(o.get('cell')==cell and not o.get('top_item')
                            for o in state.get('objects',[])))


def tour(p,state,kind,allowed,bank,loot,duration,*,probe=False,reserve_doors=False):
    """Subset DP: maximize collected heaps, then minimize timed actions."""
    start=state['hero']['cell']
    # Rooms have three generated heaps; cap unexpected large input explicitly.
    cells=sorted(loot)[:6]
    graphs={c:paths(p,state,c,kind,allowed,probe=probe,no_transit_loot=reserve_doors)
            for c in {start,*cells}}
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
                total=spent+travel_cost(p,p.route(back,bank),speed,reserve_doors=reserve_doors)+MARGIN
                if total<=duration:
                    candidate=(-len(order),total,tuple(order))
                    if best is None or candidate<best:best=candidate
            for i,c in enumerate(cells):
                if mask&(1<<i) or c not in graphs[end]:continue
                new=spent+travel_cost(p,p.route(graphs[end],c),speed,reserve_doors=reserve_doors)+costs[c]
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
    itinerary: PreparationItinerary | None = None
    lifecycle: object = None

    def finish(self,p,state):
        try:
            from .reward_lifecycle import lifecycle
        except ImportError:
            from reward_lifecycle import lifecycle
        work=lifecycle(p,self)
        work.returned(state)
        for c in work.receipts:
            if c not in p.loot and c not in p.unconfirmed_loot:
                p.completed_room_rewards.add((state['depth'],self.kind,c))
        if self.kind=='pool' and self.surveyed:
            for h in p.piranha_habitats.values():
                if h['water']&self.room:h['surveyed']=True
        p.room_journey=None

    def advance(self,p,state,enemies,neighbors):
        try:
            from .reward_lifecycle import lifecycle
        except ImportError:
            from reward_lifecycle import lifecycle
        work=lifecycle(p,self)
        pos=state['hero']['cell']
        bank=self.itinerary.success_return if self.itinerary else self.route[0]
        test_bank=self.itinerary.test_bank if self.itinerary else bank
        if (state['depth'],state.get('branch',0))!=(self.depth,self.branch):
            work.interrupt('protected trip crossed floor or branch')
            p.stop_obligation('room-journey','Protected multi-reward trip crossed floor or branch without returning')
        duration=remaining(state,PROTECTION[self.kind][1])
        work.observe(state,duration)
        if self.itinerary and pos==bank and ordinary_endpoint(p,state,bank):
            if self.stage=='return':
                self.finish(p,state);return None
            if self.stage=='protect' and not duration:
                work.cancel()
                p.room_journey=None;return None  # Failed test, no trip or reward credit.
        # A failed protection hypothesis never started a protected tour.
        # Observed-effect recovery may already have left its staging bank.
        # Only cancel away from the protected route/interior; an unprotected
        # hero inside either must still raise the existing return obligation.
        if self.stage=='protect' and not duration and (
                pos==test_bank or pos not in self.room and pos not in self.route
                and (not self.itinerary or pos not in self.itinerary.return_route)):
            work.cancel()
            p.room_journey=None;return None
        self.steps+=1
        buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
        if not unencumbered(state) or any(k in buffs for k in ('vertigo','paral','root')):
            p.stop_obligation('room-journey','Protected tour movement budget is no longer deterministic')
        if self.itinerary and not deterministic_doors(state):
            p.stop_obligation('room-journey','Split-endpoint door timing changed under equipped bulk')
        if self.stage=='protect':self.stage='outbound'
        expanded=enclosure(p,state,min(self.room)) if self.room else set()
        self.room.update(expanded)
        allowed=self.room|set(self.route)
        if self.itinerary:
            allowed.update(self.itinerary.return_route)
        graph=paths(p,state,pos,self.kind,allowed,no_transit_loot=self.itinerary is not None)
        back=p.route(graph,bank) if bank in graph else []
        speed=2 if any(k in buffs for k in ('slow','crippl','chill')) else 1
        back_cost=travel_cost(p,back,speed,reserve_doors=self.itinerary is not None)+MARGIN
        if not back or duration<back_cost:
            p.stop_obligation('room-journey','Protected tour has no duration-funded verified return')
        if self.steps>=64 or enemies or p.recent_threats or state.get('danger_cells') \
                or state['hero']['hp']<.65*state['hero']['max_hp']:
            self.stage='return'
        loot=targets(p,state,self.kind,self.room)
        self.targets=sorted(set(self.targets)|set(loot))
        # Receipts are copied by observe() before the ordinary ledger clears them.
        available={c:o for c,o in loot.items() if self.interactions.get(c,0)<6}
        plan=tour(p,state,self.kind,allowed,bank,available,duration,
                  reserve_doors=self.itinerary is not None) if self.stage!='return' else None
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
            'stage':self.stage,'duration':duration,'return_cost':back_cost,
            'survey_only':self.survey,'room_clear_claimed':False,
            'interaction_exhausted':sorted(c for c,n in self.interactions.items() if n>=6)}
        if self.itinerary:
            p.planner.report['preparation_itinerary']=self.itinerary.record()
        if self.stage=='return' and pos==bank:
            self.finish(p,state);return None
        tile=p.tiles.get(step,{})
        if self.itinerary and (not p.escape_step_allowed(state,step) or reverses(p,state,step)):
            p.stop_obligation('room-journey','Split-endpoint next step violates a fresh escape constraint')
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


def asymmetric_pool_plan(p,state,ordinary):
    """A bounded alternate return, not permission to test an unknown at a door."""
    if not ordinary or not deterministic_doors(state):
        return None
    start=state['hero']['cell']
    duration=remaining(state,PROTECTION['pool'][1]) or 20
    choices=[]
    for target,habitat in p.piranha_rooms.items():
        if habitat.get('collected') or target not in p.loot:
            continue
        room=enclosure(p,state,target)
        loot=targets(p,state,'pool',room)
        if target not in loot or loot[target].get('name','').lower()!='chest':
            continue
        boundary={n for c in room for n in
                  neighbors(c,state['map']['width'],state['map']['height'])}
        exits=[c for c in ordinary if c!=start and c in boundary and c not in room
               and c not in p.loot and ordinary_endpoint(p,state,c,allow_closed=True)]
        for end in sorted(exits,key=lambda c:(len(p.route(ordinary,c)),c))[:16]:
            allowed=room|set(p.route(ordinary,end))
            plan=tour(p,state,'pool',allowed,end,{target:loot[target]},duration,
                      probe=True,reserve_doors=True)
            if not plan:
                continue
            _,cost,outbound=plan
            if len(outbound)>16:
                continue
            graph=paths(p,state,target,'pool',allowed,probe=True,no_transit_loot=True)
            if end not in graph:
                continue
            returning=p.route(graph,end)
            if any(reverses(p,dict(state,hero=dict(state['hero'],cell=a)),b)
                   or not p.escape_step_allowed(state,b)
                   for a,b in zip(outbound,outbound[1:])):
                continue
            projected=dict(state,hero=dict(state['hero'],cell=target))
            if not preflight(p,projected,returning[:-1],returning[-1]).allowed:
                continue
            if any(not p.tiles.get(c,{}).get('observed') for c in [*outbound,*returning]):
                continue
            origin=next((c for c in outbound if p.tiles[c]['terrain'] in {5,6}),start)
            contract=PreparationItinerary(Scope.of(state),'pool',start,origin,target,
                end,start,tuple(outbound),tuple(returning),cost)
            choices.append((cost,len(outbound),end,contract,room))
    if not choices:
        return None
    _,_,_,contract,room=min(choices,key=lambda c:c[:3])
    return RewardTrip('pool',list(contract.outbound),state['depth'],room,
        [contract.work_target],contract.quoted_cost,branch=state.get('branch',0),
        planned_count=1,itinerary=contract)


def bind_test_storage(p,state,trip,candidate,distance,neighbors,safe_bank):
    """Joint unknown-test + ordinary stash-handoff admission; never mutate intent."""
    contract=getattr(trip,'itinerary',None)
    if contract is None:
        return True
    try:
        from .potion_stash import (potions,stash_cells,stash_paths,bandolier_protected,
                                   can_protect_potions,STASH_TRANSIT)
        from .stash_workflow import StashPhase
        from .escape_commitment import preflight
    except ImportError:
        from potion_stash import (potions,stash_cells,stash_paths,bandolier_protected,
                                  can_protect_potions,STASH_TRANSIT)
        from stash_workflow import StashPhase
        from escape_commitment import preflight
    bank=state['hero']['cell']
    if bank!=contract.test_bank or not safe_bank(p,state,bank,distance,neighbors,
                                                 allow_dry=True,pool_bank=True) \
            or not can_protect_potions(p,state,candidate,distance,neighbors,safe_bank):
        return False
    if p.potion_stash:
        stash=p.potion_stash
        if stash.get('phase')!=StashPhase.READY or stash['bank']!=bank:
            return False
        storage=stash['cell']
        if storage in contract.outbound or storage in contract.return_route:
            return False
    elif bandolier_protected(p,state) or not any(
            i['id']!=candidate['id'] for i in potions(state)):
        storage=None
    else:
        cells=[c for c in stash_cells(p,state,distance,neighbors,safe_bank,all_sites=True)
               if c not in contract.outbound and c not in contract.return_route]
        graph=stash_paths(p,state)
        if not cells:
            return False
        storage=min(cells,key=lambda c:len(p.route(graph,c)))
    handoff=(contract.success_return,)
    if storage is not None:
        projected=dict(state,hero=dict(state['hero'],cell=contract.success_return))
        graph=p.paths(projected)
        if storage not in graph:
            return False
        handoff=p.route(graph,storage)
        if len(handoff)>12 or any(
                not p.tiles.get(c,{}).get('observed')
                or p.tiles[c]['terrain'] not in STASH_TRANSIT|{5,6}
                or any(p.tiles[c].get(k) for k in ('trap','plant','effects'))
                or c in p.room_blocked or c in state.get('danger_cells',[])
                or c in p.loot and c!=storage for c in handoff):
            return False
    # Return movement is RETREAT. Do not promise a stash handoff that reverses
    # the constraints that very return can create. No hypothetical expiry.
    full=(*contract.return_route,*handoff[1:])
    witness=preflight(p,dict(state,hero=dict(state['hero'],cell=full[0])),full[:-1],full[-1])
    if not witness.allowed:
        return False
    trip.itinerary=contract.with_storage(storage,handoff if storage is not None else ())
    return True


def observe(p,state=None):
    trip=p.room_journey
    if isinstance(trip,(RewardTrip,)) or hasattr(trip,'lifecycle'):
        try:
            from .reward_lifecycle import lifecycle
        except ImportError:
            from reward_lifecycle import lifecycle
        work=lifecycle(p,trip)
        if state is not None:
            work.observe(state,remaining(state,PROTECTION[trip.kind][1]))
        if state is None or (work.depth,work.branch)==(
                state['depth'],state.get('branch',0)):
            work.receipts.update(work.goals&p.loot_collection_receipts)
