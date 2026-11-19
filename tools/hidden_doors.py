"""Rank hidden-door hypotheses from observed geometry, not generated room data."""

try:
    from .policy_decision import Intent
except ImportError:
    from policy_decision import Intent

WALLS = {4, 12}
INTERIOR = {1, 2, 3, 6, 11, 14, 15, 19, 20, 29}


def secret_search_allowed(state,p=None):
    """Public floor progression rule; Goo's Rat King entrance is the exception."""
    depth=state.get('depth')
    if p is not None:
        try:
            from .mapping_knowledge import complete
        except ImportError:
            from mapping_knowledge import complete
        if complete(p,state):return False
    return isinstance(depth,int) and state.get('branch',0)==0 and (depth%5!=0 or depth==5)


def observe_secret_discovery(p,before,after):
    if not before or before.get('depth')!=after.get('depth'):return
    old={t['cell']:t for t in before.get('map',{}).get('cells',[])}
    for tile in after.get('map',{}).get('cells',[]):
        previous=old.get(tile['cell'],{})
        if previous.get('visible') and previous.get('terrain') in WALLS \
                and tile.get('visible') and tile['terrain'] in {5,6}:
            p.secret_area_found=True
            p.planner.report['secret_discovery']={'cell':tile['cell'],
                'evidence':'previously visible wall became a publicly visible door; no generated room identity'}
            return


def corridor_ends(tiles, width, height, searched=()):
    """Observed two-tile narrow corridor facing a single wall, not proof of a door."""
    found=set()
    def terrain(x,y):
        if not (0<=x<width and 0<=y<height):
            return None
        return tiles.get(y*width+x,{}).get("terrain")
    for wall,tile in tiles.items():
        if tile["terrain"] not in WALLS or wall in searched:
            continue
        x,y=wall%width,wall//width
        if x in {0,width-1} or y in {0,height-1}:
            continue
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            tx,ty=-dy,dx
            if terrain(x+dx,y+dy) is not None and terrain(x+dx,y+dy) not in INTERIOR:
                continue
            if not all(terrain(x-i*dx,y-i*dy) in INTERIOR for i in (1,2,3)):
                continue
            if all(terrain(x-i*dx+sign*tx,y-i*dy+sign*ty) in WALLS
                   for i in (0,1,2) for sign in (-1,1)):
                found.add(wall)
    return found


def seek_corridor_end(p,state,enemies,distance):
    """Small proactive budget, shared with ordinary search accounting."""
    if getattr(p,'unit_strategies_enabled',False):
        return seek_required_corridor_tip(p,state,enemies,distance)
    if not secret_search_allowed(state,p):return None
    hero=state["hero"]
    buffs=" ".join(b["name"].lower() for b in hero.get("buffs",[]))
    if enemies or p.recent_threats or state.get("danger_cells") or hero["hp"]<0.7*hero["max_hp"] \
            or any(t in buffs for t in ("hungry","starving","burning","poison","blind","vertigo","paral","root")) \
            or p.corridor_tip_searches>=4 or p.secret_search_steps>=12:
        return None
    width,height=state["map"]["width"],state["map"]["height"]
    ends=corridor_ends(p.tiles,width,height,p.searched_walls)
    paths=p.paths(state)
    pos=hero["cell"]
    choices=[c for c in paths if p.tiles[c]["terrain"] in INTERIOR and not p.wall_searches[c]
              and c not in p.loot and len(p.route(paths,c))<=9
              and all(p.tiles[n]['terrain'] in INTERIOR and not p.tiles[n].get('plant')
                      and not p.tiles[n].get('effects') for n in p.route(paths,c)[1:])
              and any(abs(c%width-w%width)+abs(c//width-w//width)==1
                      and (c!=pos or p.tiles[w].get("visible")) for w in ends)]
    if not choices:
        return None
    target=min(choices,key=lambda c:len(p.route(paths,c)))
    p.secret_search_steps+=1
    if target!=pos:
        return p.toward(state,target,"explore: inspect likely corridor-end hidden doorway",paths,intent=Intent.EXPLORE)
    p.searches+=1
    p.corridor_tip_searches+=1
    p.wall_searches[pos]+=1
    p.searched_walls.update(search_coverage(p.tiles,pos,width,height))
    return p.decision({"type":"search"},"explore: search high-priority observed corridor dead end")


def narrow_dead_ends(tiles,width,height,searched=()):
    """Observed one-wide tip: three cardinal walls and one observed way back.

    Includes short stubs; a search is warranted without claiming a door exists.
    Unknown side cells are not walls, and map borders are not door candidates.
    """
    found={}
    for tip,tile in tiles.items():
        if tile.get('terrain') not in INTERIOR:continue
        x,y=tip%width,tip//width
        if not 1<=x<width-1 or not 1<=y<height-1:continue
        sides=[tip-width,tip+width,tip-1,tip+1]
        walls=[c for c in sides if tiles.get(c,{}).get('terrain') in WALLS]
        back=[c for c in sides if tiles.get(c,{}).get('terrain') in INTERIOR|{5}]
        if len(walls)!=3 or len(back)!=1:continue
        wall=2*tip-back[0]
        side=width if abs(wall-tip)==1 else 1
        if any(tiles.get(c,{}).get('terrain') not in WALLS for c in (wall-side,wall+side)):continue
        if wall in walls and wall not in searched and wall%width not in {0,width-1} and wall//width not in {0,height-1}:
            found[wall]=tip
    return found


def continue_search_vantage(p,state,enemies,paths):
    """Finish one pending search before a door toggle revives competing frontier work."""
    goal=p.secret_search_goal
    if not goal:return None
    hero=state['hero'];pos=hero['cell'];target=goal['cell']
    buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    if not secret_search_allowed(state,p) or target in p.completed_maze_cells or enemies or p.recent_threats or state.get('danger_cells') \
            or hero['hp']<.7*hero['max_hp'] or any(b in buffs for b in ('starving','burn','poison','bleed','blind','vertigo','paral','root')) \
            or target not in paths or goal['steps']>=64 or not (goal['walls']-p.searched_walls):
        p.secret_search_goal=None;return None
    route=p.route(paths,target)
    try:
        from .hunger_budget import admits,travel_cost
    except ImportError:
        from hunger_budget import admits,travel_cost
    if not admits(p,state,2*travel_cost(state,p,route)+12):
        p.secret_search_goal=None
        return None
    if any(p.tiles[c].get('trap') or p.tiles[c].get('plant') or p.effects_block_movement(p.tiles[c])
           or p.tiles[c]['terrain'] in {7,8,10,18,21,22,31,37,38} for c in route[1:]):
        p.secret_search_goal=None;return None
    if pos!=target:
        goal['steps']+=1;p.secret_search_steps+=1
        return p.toward(state,target,'explore: finish committed secret-search vantage',paths,intent=Intent.EXPLORE)
    coverage=search_coverage(p.tiles,pos,state['map']['width'],state['map']['height'])
    p.secret_search_goal=None
    if not coverage.intersection(goal['walls']-p.searched_walls):return None
    p.searches+=1;p.wall_searches[pos]+=1;p.searched_walls.update(coverage)
    return p.decision({'type':'search'},'explore: complete committed visible-wall search before frontier work')


def seek_required_corridor_tip(p,state,enemies,distance):
    if not secret_search_allowed(state,p):return None
    hero=state['hero'];pos=hero['cell'];buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    if enemies or p.recent_threats or state.get('danger_cells') or hero['hp']<.5*hero['max_hp'] \
            or any(b in buffs for b in ('burn','poison','bleed','blind','vertigo','paral','root')):return None
    paths=p.paths(state);choices=[]
    for wall,tip in narrow_dead_ends(p.tiles,state['map']['width'],state['map']['height'],p.searched_walls).items():
        if tip in p.completed_maze_cells:continue
        if tip not in paths or p.corridor_tip_routes[wall]>=64:continue
        route=p.route(paths,tip)
        try:
            from .hunger_budget import admits,travel_cost
        except ImportError:
            from hunger_budget import admits,travel_cost
        if not admits(p,state,2*travel_cost(state,p,route)+12):continue
        if 'starving' in buffs and tip!=pos:continue
        if any(p.tiles[c].get('plant') or p.tiles[c].get('trap') or p.effects_block_movement(p.tiles[c])
               or p.tiles[c]['terrain'] in {7,8,22,37} for c in route[1:]):continue
        if tip==pos and not p.tiles[wall].get('visible'):continue
        choices.append((len(route),wall,tip))
    if not choices:return None
    _,wall,tip=min(choices)
    p.planner.report['corridor_dead_end']={'wall':wall,'tip':tip,'status':'Required observed narrow-tip search',
        'qualification':'One search per observed end; no hidden door or room assumed; safety and boss-floor rules remain'}
    if tip!=pos:
        p.corridor_tip_routes[wall]+=1
        return p.toward(state,tip,'explore: reach observed one-wide corridor dead end for required search',paths,intent=Intent.EXPLORE)
    p.searches+=1;p.corridor_tip_searches+=1;p.wall_searches[pos]+=1
    p.searched_walls.update(search_coverage(p.tiles,pos,state['map']['width'],state['map']['height']))
    return p.decision({'type':'search'},'explore: search observed one-wide corridor dead end once')


def wall_scores(tiles, width, height, searched=()):
    scores = {}
    ends=corridor_ends(tiles,width,height,searched)

    def cell(x, y):
        return y * width + x if 0 <= x < width and 0 <= y < height else None

    def terrain(x, y):
        return tiles.get(cell(x, y), {}).get("terrain")

    for wall, tile in tiles.items():
        if tile["terrain"] not in WALLS or wall in searched:
            continue
        x, y = wall % width, wall // width
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            # A door passes across a straight wall, never through a room corner.
            tx, ty = -dy, dx
            if terrain(x-dx, y-dy) not in INTERIOR:
                continue
            if not all(terrain(x+sign*tx, y+sign*ty) in WALLS for sign in (-1, 1)):
                continue
            beyond = terrain(x+dx, y+dy)
            if beyond is not None and beyond not in INTERIOR:
                continue
            wide_room = all(terrain(x-dx+sign*tx, y-dy+sign*ty) in INTERIOR for sign in (-1, 1))
            dead_end = all(terrain(x-dx+sign*tx, y-dy+sign*ty) in WALLS for sign in (-1, 1))
            score = 12 if wall in ends else 8 if beyond in INTERIOR else 5 if wide_room else 4 if dead_end else 2
            scores[wall] = max(scores.get(wall, 0), score)
    return scores


def search_coverage(tiles, pos, width, height):
    """Mage's ordinary radius-one search only checks currently visible cells."""
    x, y = pos % width, pos // width
    return {cy * width + cx for cy in range(max(0, y-1), min(height, y+2))
            for cx in range(max(0, x-1), min(width, x+2))
            if tiles.get(cy * width + cx, {}).get("visible")
            and tiles[cy * width + cx]["terrain"] in WALLS}
