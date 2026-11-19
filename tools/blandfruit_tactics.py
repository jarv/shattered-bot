"""Observed fruit harvesting, known seed recipes and conservative fruit use."""
try:
    from .consumable_tactics import base_name
    from .policy_geometry import distance, neighbors
    from .policy_decision import Intent
except ImportError:
    from consumable_tactics import base_name
    from policy_geometry import distance, neighbors
    from policy_decision import Intent


RECIPES = {
    'sungrass':'sunfruit', 'mageroyal':'dreamfruit', 'fadeleaf':'fadefruit',
    'starflower':'starfruit', 'swiftthistle':'swiftfruit', 'blindweed':'blindfruit',
    'icecap':'icefruit', 'firebloom':'firefruit', 'earthroot':'earthfruit',
    'sorrowmoss':'sorrowfruit', 'stormvine':'stormfruit',
}
SAFE_FOOD = {'dreamfruit', 'fadefruit', 'starfruit', 'swiftfruit', 'blindfruit',
             'blandfruit chunks'}
HARMFUL_FOOD = {'earthfruit', 'sorrowfruit', 'firefruit', 'icefruit', 'stormfruit'}


def recipe(counts, demands, pharmacophobia=False):
    if not counts.get('blandfruit'):return None
    # Quest Rotberry is deliberately not a cooking ingredient. Retain rare
    # experience, last healing and last room-protection seeds.
    for kind in ('mageroyal','fadeleaf','sungrass','icecap','firebloom','blindweed',
                 'swiftthistle','earthroot','sorrowmoss','stormvine','starflower'):
        reserve = 1 if kind in {'sungrass','starflower','swiftthistle','blindweed','stormvine'} else 0
        if (kind=='icecap' and 'frost' in demands or kind=='firebloom' and 'flame' in demands
                or kind=='mageroyal' and 'gas' in demands):reserve=max(reserve,1)
        if kind=='sungrass' and pharmacophobia:continue
        if counts.get('seed of '+kind,0)>reserve:
            return ('blandfruit','seed of '+kind), RECIPES[kind]
    return None


def choose(p,state,enemies):
    hero=state['hero'];pos=hero['cell'];width=state['map']['width']
    buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    if state.get('danger_cells') or any(b in buffs for b in ('burn','poison','bleed','vertigo','paral','root')):
        return None
    # Frost has a small, checked splash, no persistent spreading hazard.
    # Other offensive fruit stays reserved until a collateral-safe use exists.
    ice=next((i for i in state['inventory'] if base_name(i)=='icefruit' and 'THROW' in i.get('actions',[])),None)
    if ice:
        for enemy in enemies:
            target=enemy['cell']
            if distance(pos,target,width)<=2 or not p.shot_clear(state,target):continue
            if any(distance(o['cell'],target,width)<=1 and o not in enemies
                   and 'top_item' not in o for o in state.get('objects',[])):continue
            if any(distance(c,target,width)<=1 and ('potion' in o.get('name','').lower()
                    or 'meat' in o.get('name','').lower()) for c,o in p.loot.items()):continue
            if p.target_allowed(ice,enemy):
                return p.use(ice,'THROW','fruit: frost at a clear distant hostile; avoid hero/allies and fragile loot',target=target)
    if enemies or p.recent_threats:return None
    fruit=next((i for i in state['inventory'] if base_name(i)=='rotfruit' and 'EAT' in i.get('actions',[])),None)
    if fruit and p.item_action_allowed(fruit,'EAT'):
        return p.use(fruit,'EAT','fruit: eat known strength-bearing rotfruit')
    if getattr(p,'barren_land',False):return None
    paths=p.paths(state)
    bushes=[c for c,t in p.tiles.items() if c!=pos and t.get('visible')
            and 'blandfruit' in t.get('plant','').lower() and c in paths
            and len(p.route(paths,c))<=9
            and all(not p.tiles[n].get('trap') and not p.effects_block_movement(p.tiles[n])
                    and (not p.tiles[n].get('plant') or n==c) for n in p.route(paths,c)[1:])]
    if bushes:
        return p.toward(state,min(bushes,key=lambda c:len(p.route(paths,c))),
                        'fruit: harvest observed Blandfruit Bush; verify actual fruit pickup',paths,intent=Intent.LOOT)
    seed=next((i for i in state['inventory'] if base_name(i)=='seed of blandfruit'
               and 'PLANT' in i.get('actions',[])),None)
    tile=p.tiles.get(pos,{})
    key=(state['depth'],seed['id'] if seed else None)
    attempts=getattr(p,'fruit_plant_attempts',set())
    if (seed and key not in attempts and tile.get('terrain') in {1,2,3,14,15}
            and not tile.get('plant') and not tile.get('trap') and not tile.get('effects')):
        attempts.add(key);p.fruit_plant_attempts=attempts
        return p.use(seed,'PLANT','fruit: plant carried Blandfruit Bush seed on safe ground')
    # PLANT is underfoot. Step away once a bush actually appears; the next
    # observation can then route back and activate it.
    if 'blandfruit' in tile.get('plant','').lower():
        banks=[c for c in neighbors(pos,width,state['map']['height']) if c in paths
               and not p.tiles[c].get('plant') and not p.tiles[c].get('trap')
               and not p.effects_block_movement(p.tiles[c]) and p.tiles[c]['terrain'] in {1,2,3,14}]
        if banks:return p.cell(min(banks),'fruit: step off observed planted bush before harvesting',intent=Intent.REPOSITION)
    return None
