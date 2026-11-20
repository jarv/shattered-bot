"""Public-item retention tiers; lower is more valuable, None is protected.

Unknown identities stay unknown. Equipment estimates use rendered upgrades,
damage/blocking, and strength requirements, never private item levels.
"""
import re
from collections import Counter

try:
    from .consumable_tactics import base_name
    from .combat_items import stats, accessory_kind, known_cursed, physical_score
except ImportError:
    from consumable_tactics import base_name
    from combat_items import stats, accessory_kind, known_cursed, physical_score


FOOD = {'ration of food', 'small ration', 'pasty', 'meat pie', 'mystery meat',
        'stewed meat', 'grilled meat', 'chargrilled meat', 'frozen carpaccio', 'blandfruit', 'sunfruit',
        'rotberry', 'dreamfruit', 'fadefruit', 'starfruit', 'swiftfruit', 'blindfruit',
        'sorrowfruit', 'stormfruit', 'firefruit', 'icefruit', 'earthfruit',
        'dungeon berry', 'blandfruit chunks', 'phantom meat', 'fish leftovers',
        'small food ration', 'supply ration', 'steamed fish', 'amulet of yendor?',
        'easter egg', 'rainbow potion', 'green cake', 'pumpkin pie', 'blue cake',
        'candy cane', 'sparkling potion'}
BAGS = {'backpack', 'velvet pouch', 'scroll holder', 'potion bandolier', 'magical holster'}
ESSENTIAL = {'waterskin', 'torch', 'pickaxe', 'dark gold', 'dried rose petal',
             'corpse dust', 'embers', 'rotberry seed', 'seed of rotberry', 'ceremonial candle',
             'amulet of yendor', "tengu's mask", "dwarf king's crown", 'broken seal',
             'spirit bow', 'rat skull crown', 'document page', 'journal page'}
ESSENTIAL |= {'dark gold ore', 'dwarf token', 'elemental embers', 'escape crystal',
              'obsidian statuette', 'vault beacon', 'blob of goo', 'cursed metal shard',
              'lost backpack'}


def name(item):
    return re.sub(r' [+-]\d+$', '', base_name(item).replace('_', '').strip())


def food(item):
    return name(item) in FOOD or ('EAT' in item.get('actions', []) and
                                  not name(item).startswith('seed of '))


def protected(item):
    n = name(item)
    return bool(item.get('equipped') or n in BAGS | ESSENTIAL or 'key' in n.split()
                or 'IMBUE' in item.get('actions', []) or n.startswith('staff of ')
                or any(w in item.get('description', '').lower()
                       for w in ('quest item', 'quest-item')))


def duplicate(state, item):
    """Keep another equally described copy; do not equate different upgrades."""
    parsed = stats(item)
    if not parsed or parsed[0] not in {'melee', 'armor'}:
        return False
    return any(other is not item and base_name(other) == base_name(item)
               and other.get('description', '') == item.get('description', '')
               and other.get('identified') == item.get('identified') for other in state['inventory'])


def below_equipped(state, item):
    parsed=stats(item)
    strength=state['hero'].get('strength',0)
    if not item.get('identified') or not parsed or parsed[2]>strength:
        return False  # Typical/unidentified stats cannot establish true power.
    current=next((i for i in state['inventory'] if i.get('equipped') and i.get('identified')
                  and not known_cursed(i) and stats(i) and stats(i)[0]==parsed[0]
                  and stats(i)[2]<=strength),None)
    if not current:return False
    return physical_score(current,strength)>physical_score(dict(item,known_cursed=False),strength)


def rank(state, item):
    if protected(item):
        return None
    n = name(item)
    if n in {'potion of strength', 'scroll of upgrade', 'ankh', 'blessed ankh'} or food(item):
        return 0
    if accessory_kind(item) or 'ZAP' in item.get('actions', []) or n.startswith(('wand of ', 'ring of ')) \
            or n.startswith(('scroll of ', 'stone of ')) or 'potion' in n or n in {'arcane stylus'}:
        return 1
    try:
        from .trinket_tactics import TRINKETS
    except ImportError:
        from trinket_tactics import TRINKETS
    if n in TRINKETS or 'CAST' in item.get('actions', []):
        return 1
    parsed = stats(item)
    if parsed and parsed[0] == 'thrown':
        return 2
    if n.startswith('seed of ') or 'catalyst' in n or n in {'arcane resin', 'liquid metal'}:
        return 3
    if 'bomb' in n or 'honeypot' in n:
        return 4
    if parsed and parsed[0] in {'melee', 'armor'}:
        # Curses are a within-tier tie-break, not an automatic low-value label.
        if below_equipped(state, item):
            return 6
        if duplicate(state, item):
            return 5
    return 1  # Unknown gear/items retain option value; never guess identity.


def bag(state, item):
    """Pinned public bag rules; do not free the wrong container's capacity."""
    bags = {name(i) for i in state['inventory']} & BAGS
    n = name(item)
    if food(item):
        return 'backpack'
    if 'velvet pouch' in bags and (n.startswith(('seed of ', 'stone of ')) or n in {'blob of goo', 'metal shard', 'cursed metal shard'}):
        return 'velvet pouch'
    if 'potion bandolier' in bags and ('potion' in n or n in {'waterskin', 'liquid metal'}):
        return 'potion bandolier'
    if 'scroll holder' in bags and (n.startswith('scroll of ') or n in {'arcane resin', 'arcane stylus'} or
            'CAST' in item.get('actions', []) and not accessory_kind(item)):
        return 'scroll holder'
    if 'magical holster' in bags and ('ZAP' in item.get('actions', [])
            or n.startswith('wand of ') or stats(item) and stats(item)[0] == 'thrown'):
        return 'magical holster'
    return 'backpack'


def replacements(p, state, incoming):
    incoming_rank = rank(state, incoming)
    if incoming_rank is None:
        incoming_rank = 0  # Collect observed keys/utilities, never drop them.
    protected_names = {str(getattr(p, 'upgrade_target', '')).lower(),
                       str(getattr(p, 'ghost_quest', {}).get('selected', '')).lower()}
    try:
        from .room_supplies import requirements
    except ImportError:
        from room_supplies import requirements
    for potion,needed in Counter(d.potion for d in requirements(p,state)).items():
        if sum(i.get('quantity',1) for i in state['inventory'] if name(i)==potion)<=needed:
            protected_names.add(potion)
    try:
        from .rose_outfitting import rose_available, spares
    except ImportError:
        from rose_outfitting import rose_available, spares
    if rose_available(state):
        protected_names.update(base_name(i) for i in spares(state))
    domain = bag(state, incoming)
    candidates = [i for i in state['inventory'] if 'DROP' in i.get('actions', [])
                  and not protected(i) and base_name(i) not in protected_names
                  and rank(state, i) is not None and rank(state, i) > incoming_rank
                  and bag(state, i) == domain]
    def order(item):
        parsed = stats(item)
        power = physical_score(dict(item, known_cursed=False),
                               max(state['hero'].get('strength', 0), parsed[2])) if parsed else 0
        return (-rank(state, item), not known_cursed(item), power, item.get('quantity', 1), name(item))
    return sorted(candidates, key=order)
