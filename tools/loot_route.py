"""Exact shortest observed-room pickup tour, using walkable cells, not room IDs."""
from collections import deque

try:
    from .policy_geometry import neighbors
except ImportError:
    from policy_geometry import neighbors


class TourTooLarge(ValueError):
    pass


def nearest_tour(start,targets,cells,width,height,end=None):
    """Bounded nearest-pickup heuristic for large observed rooms; NOT optimal."""
    cells=set(cells)|{start};remaining=set(targets);order=[];cost=0;current=start
    if end is not None:cells.add(end)
    while remaining:
        found={current:0};queue=deque([current])
        while queue:
            cell=queue.popleft()
            if cell==end and cell!=current:continue
            for n in neighbors(cell,width,height):
                if n in cells and n not in found:found[n]=found[cell]+1;queue.append(n)
        reachable=[c for c in remaining if c in found]
        if not reachable:return None
        target=min(reachable,key=lambda c:(found[c],c))
        cost+=found[target];order.append(target);remaining.remove(target);current=target
    if end is not None:
        found={current:0};queue=deque([current])
        while queue and end not in found:
            cell=queue.popleft()
            for n in neighbors(cell,width,height):
                if n in cells and n not in found:found[n]=found[cell]+1;queue.append(n)
        if end not in found:return None
        cost+=found[end]
    return order,cost


def shortest_tour(start,targets,cells,width,height,end=None):
    """Held–Karp on BFS distances. End is an optional room-exit destination.

    This is exact on the supplied safe, static observed graph. Opening chests,
    picking a key up, new sightings or changed terrain require replanning.
    Never label a nearest-neighbor fallback optimal when exact work is too big.
    """
    targets=tuple(sorted(set(targets)))
    if len(targets)>14:raise TourTooLarge('More than 14 room pickup cells; exact route budget exceeded')
    cells=set(cells)|{start}
    if end is not None:cells.add(end)
    def distances(source):
        found={source:0};queue=deque([source])
        while queue:
            cell=queue.popleft()
            if cell==end and cell!=source:continue  # Exit is an endpoint, never transit.
            for n in neighbors(cell,width,height):
                if n in cells and n not in found:
                    found[n]=found[cell]+1;queue.append(n)
        return found
    distances_from={c:distances(c) for c in set(targets)|{start}}
    if any(c not in distances_from[start] for c in targets):return None
    # Stable tie break prefers a nearer first pickup, then stable cell ordering.
    targets=tuple(sorted(targets,key=lambda c:(distances_from[start][c],c)))
    if not targets:return ([],distances_from[start].get(end,0))
    dp={(1<<i,i):(distances_from[start][c],(i,)) for i,c in enumerate(targets)}
    full=(1<<len(targets))-1
    for mask in range(1,full+1):
        for last in range(len(targets)):
            value=dp.get((mask,last))
            if value is None:continue
            cost,order=value
            for nxt,cell in enumerate(targets):
                if mask&(1<<nxt):continue
                distance=distances_from[targets[last]].get(cell)
                if distance is None:continue
                key=(mask|(1<<nxt),nxt);candidate=(cost+distance,order+(nxt,))
                if key not in dp or candidate<dp[key]:dp[key]=candidate
    choices=[]
    for last,cell in enumerate(targets):
        value=dp.get((full,last))
        extra=distances_from[cell].get(end) if end is not None else 0
        if value is not None and extra is not None:choices.append((value[0]+extra,value[1]))
    if not choices:return None
    cost,order=min(choices)
    return [targets[i] for i in order],cost
