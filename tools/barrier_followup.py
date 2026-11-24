"""Finish observed local work after opening a fire barrier, without room IDs."""
try:
    from .special_rooms import fire_barrier
    from .policy_decision import Intent
    from .mimic_tactics import suspicious_container
except ImportError:
    from special_rooms import fire_barrier
    from policy_decision import Intent
    from mimic_tactics import suspicious_container


def begin(p,state,target,neighbors):
    w,h=state['map']['width'],state['map']['height']
    group={target};queue=[target]
    for c in queue:
        for n in neighbors(c,w,h):
            if n not in group and fire_barrier(p.tiles.get(n,{})):
                group.add(n);queue.append(n)
    p.barrier_followup={'depth':state['depth'],'barriers':group,'origin':state['hero']['cell'],
        'anchor':target,'entered':False,'steps':0,'target':None}


def advance(p,state,enemies,distance,neighbors):
    plan=p.barrier_followup
    if not plan:return None
    if plan['depth']!=state['depth']:
        p.barrier_followup=None
        return None
    observe(p)
    if state.get('status')!='ready' or state.get('modal') or enemies or state.get('danger_cells') \
            or p.puzzle_probe or p.potion_stash or p.room_journey or p.drop_plan:
        return None
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    if any(b in buffs for b in ('burning','poison','root','paral','chill','frozen','vertigo','blind')):return None
    if 'starving' in buffs and p.food_items(state):return None
    paths=p.paths(state)
    pos=state['hero']['cell'];w=state['map']['width']
    cleared=[c for c in plan['barriers'] if p.tiles.get(c,{}).get('visible')
             and not fire_barrier(p.tiles[c]) and c in paths]
    # Keep previously verified anchors through visibility loss, but require
    # positive observation of extinguishing before creating a return goal.
    plan.setdefault('cleared',set()).update(cleared)
    anchors=[c for c in plan['cleared'] if c in paths]
    def defer(reason):
        p.defer_obligations(state,[{'kind':'post-barrier local sweep','cell':plan['anchor']}],reason)
        p.barrier_followup=None
    if plan['steps']>=64 or state['hero']['hp']<0.5*state['hero']['max_hp']:
        defer('Post-barrier sweep health/movement budget exhausted; rewards not certified collected')
        return None
    if not anchors:
        # A successful frost throw can leave the *approach* cold while the
        # fire cells themselves are clear. Do not discard the return goal just
        # because ordinary paths correctly exclude that temporary cloud.
        # This is a fresh-observation hold on safe ground, never cold entry or
        # an expiry inference. Both accounts are finite; all gates rerun.
        tile=p.tiles.get(pos,{})
        cold=[c for c,t in p.tiles.items()
              if t.get('visible') and t.get('observed') and t.get('effects')
              and all(e.lower()=='the air is unnaturally frigid here.' for e in t['effects'])
              and min((distance(c,a,w) for a in plan['cleared']),default=99)<=2
              and any(n in paths for n in neighbors(c,w,state['map']['height']))]
        if cold and plan.get('cold_waits',0)<12 and not p.recent_threats \
                and not p.unseen_damage_turns and not p.trap_payload_return \
                and state['hero']['hp']>=.95*state['hero']['max_hp'] \
                and not any(b in buffs for b in ('hungr','starv','bleed','levitat','drows','sleep')) \
                and tile.get('visible') and tile.get('observed') \
                and tile.get('terrain') in {1,3,6,9,11,14,19,20,29} \
                and not any(tile.get(k) for k in ('effects','plant','trap')) \
                and p.walkable(pos) and distance(pos,plan['anchor'],w)<=4 \
                and all(p.tiles.get(a,{}).get('visible') and not fire_barrier(p.tiles[a])
                        for a in plan['barriers']) \
                and any(p.walkable(n) and not any(p.tiles[n].get(k) for k in ('effects','plant','trap'))
                        for n in neighbors(pos,w,state['map']['height'])):
            plan['cold_waits']=plan.get('cold_waits',0)+1
            plan['steps']+=1
            return p.decision({'type':'wait'},
                'room: observe temporary frost clearing from safe ground before required return')
        if plan['cleared']:
            # The entry was visibly extinguished but may still remember cold
            # after recovery moved out of sight. Reobserve from safe ground;
            # never assume an unseen cloud expired or step into it blindly.
            views=[c for c in paths if c!=pos and not p.tiles[c].get('effects')
                   and c not in p.loot and p.tiles[c]['terrain'] not in {5,7,8,10,21,22,31,37,38}
                   and len(p.route(paths,c))<=13
                   and min(distance(c,a,w) for a in plan['cleared'])<=2
                   and min(distance(c,a,w) for a in plan['cleared'])<min(distance(pos,a,w) for a in plan['cleared'])]
            if views:
                view=min(views,key=lambda c:(min(distance(c,a,w) for a in plan['cleared']),len(p.route(paths,c))))
                plan['steps']+=1
                return p.toward(state,view,'room: reobserve extinguished entry after cold recovery',paths,intent=Intent.EXPLORE)
        defer('No observed extinguished reachable entry; retain hazard restrictions')
        return None
    anchor=min(anchors,key=lambda c:len(p.route(paths,c)))
    if not plan['entered']:
        if pos in plan['cleared']:plan['entered']=True
        else:
            plan['steps']+=1
            return p.toward(state,anchor,'room: return to observed extinguished barrier before distant exploration',paths,intent=Intent.EXPLORE)
    # A straight observed barrier provides an approach/far-side distinction,
    # not a generated room identity. Bound local work to eight observed tiles.
    cols={c%w for c in plan['barriers']};rows={c//w for c in plan['barriers']}
    origin=plan['origin'];center=plan['anchor']
    def local(c):
        if distance(c,center,w)>8:return False
        if len(cols)==1 and origin%w!=center%w:
            return (c%w-center%w)*(origin%w-center%w)<=0
        if len(rows)==1 and origin//w!=center//w:
            return (c//w-center//w)*(origin//w-center//w)<=0
        return distance(c,center,w)<=4
    def safe(c):
        if c not in paths:return False
        route=p.route(paths,c)
        return len(route)<=17 and all(p.tiles[n]['terrain'] not in {5,7,8,10,21,22,31,37,38}
            and not p.tiles[n].get('plant') for n in route[1:])
    rewards=[c for c,o in p.loot.items() if local(c) and safe(c) and not o.get('for_sale')
             and not suspicious_container(o) and c not in p.combat_deferred_loot
             and (o.get('top_item') or o['name'].lower()=='chest' or c in p.allowed_chests)]
    frontiers=[c for c in p.exploration_report(state,paths)['unexplored_frontiers']
               if c!=pos and local(c) and safe(c)]
    targets=rewards or frontiers
    if not targets:
        unfinished=[{'kind':'post-barrier unresolved reward','cell':c,'name':o['name']}
                    for c,o in p.loot.items() if local(c)]
        if unfinished:p.defer_obligations(state,unfinished,'No admitted local pickup; not proof of collection')
        p.barrier_followup=None
        p.planner.report['barrier_followup']={'status':'observed local sweep exhausted; no unseen-room certification'}
        return None
    old=plan['target']
    target=old if old in targets else min(targets,key=lambda c:len(p.route(paths,c)))
    plan.update(target=target,steps=plan['steps']+1)
    p.planner.report['barrier_followup']={'target':target,'steps':plan['steps'],'known_rewards':len(rewards)}
    return p.toward(state,target,'loot: finish observed post-barrier rewards' if rewards else
        'room: reveal remaining observed post-barrier frontiers',paths,intent=Intent.LOOT if rewards else Intent.EXPLORE)


def observe(p):
    plan=p.barrier_followup
    if plan:
        plan.setdefault('cleared',set()).update(c for c in plan['barriers']
            if p.tiles.get(c,{}).get('visible') and not fire_barrier(p.tiles[c]))
