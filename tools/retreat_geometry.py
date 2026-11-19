"""Observed onward room for ordinary retreats; never an enemy-motion model."""
try:
    from .policy_geometry import neighbors
except ImportError:
    from policy_geometry import neighbors


def onward_exit(p,state,cell,origin,occupied,threats=()):
    exits=[c for c in neighbors(cell,state['map']['width'],state['map']['height'])
        if c!=origin and p.walkable(c,occupied) and c not in p.loot
        and p.tiles[c]['terrain'] not in {5,7,8,10,21,22,31,37,38} and not p.tiles[c].get('plant')]
    if threats:
        try:
            from .challenge_combat import reach
            from .policy_geometry import distance
        except ImportError:
            from challenge_combat import reach
            from policy_geometry import distance
        width=state['map']['width']
        close_fly=any(not e.get('sleeping') and e['name'].lower()=='swarm of flies'
                      and distance(cell,e['cell'],width)<=reach(e)+1 for e in threats)
        if close_fly and not any(all(e.get('sleeping') or distance(n,e['cell'],width)>
                reach(e)+(e['name'].lower()=='swarm of flies') for e in threats) for n in exits):
            return False  # Multiple nominal exits can all be sealed by the pursuing fly.
    if threats and len(exits)==1:
        # One threatened onward square is a self-sealing pocket. Do not impose
        # a global zero-exposure requirement on larger multi-exit retreats.
        try:
            from .challenge_combat import reach
            from .policy_geometry import distance
        except ImportError:
            from challenge_combat import reach
            from policy_geometry import distance
        return all(e.get('sleeping') or distance(exits[0],e['cell'],state['map']['width'])>reach(e) for e in threats)
    return bool(exits)


def onward_runway(p,state,cell,origin,occupied,threats,steps=2):
    """Two connected onward steps, not a single safe cul-de-sac square.

    Preserve funneling's existing >2-square observed margin. This is bounded
    geometry, never a prediction of enemy movement or guaranteed escape.
    """
    try:
        from .policy_geometry import distance
        from .challenge_combat import reach
    except ImportError:
        from policy_geometry import distance
        from challenge_combat import reach
    width,height=state['map']['width'],state['map']['height']
    queue=[(cell,{origin,cell},0)]
    for current,seen,depth in queue:
        if depth>=steps:return True
        for n in neighbors(current,width,height):
            if n in seen or not p.walkable(n,occupied) or n in p.loot \
                    or n in state.get('danger_cells',[]) or p.tiles[n].get('plant') \
                    or p.tiles[n].get('effects') or p.tiles[n]['terrain'] in {5,7,8,10,21,22,31,37,38}:continue
            if any(not e.get('sleeping') and distance(n,e['cell'],width)<=max(2,reach(e)) for e in threats):continue
            queue.append((n,seen|{n},depth+1))
    return False
