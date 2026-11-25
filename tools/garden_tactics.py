"""Use publicly described gardens/visible Sungrass, never generated room IDs."""
try:
    from .policy_decision import Intent
    from .policy_geometry import distance
except ImportError:
    from policy_decision import Intent
    from policy_geometry import distance

GARDEN_DESCRIPTION='shafts of light pierce the gloom of the underground garden.'


def garden_effect(text):
    return text.strip().lower()==GARDEN_DESCRIPTION


def in_garden(tile):
    return any(garden_effect(e) for e in tile.get('effects',[]))


def harvest_supplies(p, state, enemies, floor):
    """Known dew/seed producers are ordinary supplies, not secret-room hunts."""
    if enemies or p.recent_threats or p.dm100_threat or state.get("danger_cells") or p.unseen_damage_turns:
        return None
    if floor.get("harvest_inputs", 0) >= 64:
        return None
    buffs = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
    if any(k in buffs for k in ("burn", "poison", "bleed", "ooze", "vertigo", "paral", "root", "starv")):
        return None
    attempts = floor.get("harvest_attempts", {})
    targets = {c for c, t in p.tiles.items()
               if t.get("observed") and t.get("plant", "").lower().replace(" ", "") in {"dewcatcher", "seedpod"}
               and not attempts.get(c)}
    for target in sorted(targets, key=lambda c: distance(state["hero"]["cell"], c, state["map"]["width"])):
        occupied = {c for c, t in p.tiles.items() if t.get("plant") and c != target}
        previous = p.paths(state, occupied)
        if target not in previous or len(p.route(previous, target)) > 17:
            continue
        action = p.toward(state, target, "simple: harvest observed dewcatcher/seed pod; collect only witnessed drops",
                          previous, intent=Intent.LOOT)
        if action:
            action.simple_harvest_target = target
            action.simple_navigation = True
            return action
    return None


def choose(p,state,enemies):
    if enemies or p.recent_threats or state.get('danger_cells'):return None
    hero=state['hero'];pos=hero['cell'];width=state['map']['width']
    buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    if any(b in buffs for b in ('burning','poison','bleed','ooze','vertigo','paral','root')):return None
    paths=p.paths(state)
    gardens={c for c,t in p.tiles.items() if in_garden(t)}
    plants={c for c,t in p.tiles.items() if 'sungrass' in t.get('plant','').lower()}
    targets=gardens|plants
    if not targets:return None
    # Finish actual observed pickups instead of trampling past them.
    if any(c in targets and not o.get('for_sale') for c,o in p.loot.items()):return None
    hp=hero['hp']/max(1,hero['max_hp'])
    if 'herbal healing' in buffs and hp<.95 and 'starving' not in buffs and p.garden_waits<60:
        p.garden_waits+=1
        return p.decision({'type':'wait'},'garden: preserve observed Sungrass healing without moving',intent=Intent.RECOVER)
    def admitted(c):
        return c in paths and len(p.route(paths,c))<=9 and all(
            p.tiles[n]['terrain'] not in {5,7,8,10,18,21,22,31,37,38}
            and not p.tiles[n].get('trap') and not p.effects_block_movement(p.tiles[n])
            and (not p.tiles[n].get('plant') or n==c and c in plants)
            and not p.loot.get(n,{}).get('for_sale') for n in p.route(paths,c)[1:])
    if not getattr(p,'barren_land',False) and hp<.8 and 'starving' not in buffs and 'herbal healing' not in buffs:
        sungrass=[c for c in plants if admitted(c) and p.tiles[c].get('visible')]
        if sungrass:
            c=min(sungrass,key=lambda c:len(p.route(paths,c)))
            return p.toward(state,c,'garden: activate publicly observed Sungrass for efficient recovery',paths,intent=Intent.RECOVER)
    if p.garden_steps>=16:return None
    # Trample each visible high-grass patch once for observed dew/seed drops;
    # do not assume a hidden plant, heal, loot drop or hunger immunity.
    grass=[c for c in gardens if c!=pos and p.tiles[c]['terrain']==15 and p.tiles[c].get('visible') and admitted(c)]
    if grass:
        c=min(grass,key=lambda c:(len(p.route(paths,c)),p.visits[c],c))
        p.garden_steps+=1
        return p.toward(state,c,'garden: inspect and trample observed high grass for supplies',paths,intent=Intent.EXPLORE)
    return None
