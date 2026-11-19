"""Bound stationary natural healing by food/hunger and total floor spending."""
try:
    from .garden_tactics import in_garden
except ImportError:
    from garden_tactics import in_garden


def budget(p,state,hungry):
    hero=state['hero'];hp=hero['hp']/max(1,hero['max_hp'])
    buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    food=bool(p.food_items(state))
    if 'starving' in buffs or hungry and (not food or hp>=.5):limit=0
    else:limit=6 if hungry else 48 if food else 24
    # Gardens slow hunger only while their public Shadows buff is present;
    # they are not free food or immunity to starvation.
    if limit and in_garden(p.tiles.get(hero['cell'],{})) and 'shadows' in buffs:limit+=12
    p.planner.report['healing_economy']={'floor_waits_spent':p.natural_healing_waits,'floor_wait_limit':limit,
        'carried_food':food,'hungry':hungry,'note':'Stationary natural healing only; movement/seed healing remain distinct'}
    return limit if p.natural_healing_waits<limit else 0
