"""Mage survival ranking of all trinkets in the pinned game, not a universal tier list.

Catalyst costs six energy; never auto-energize supplies or auto-upgrade trinkets.
Only observed offered item buttons and the matching confirmation are accepted.
"""
try:
    from .consumable_tactics import base_name
except ImportError:
    from consumable_tactics import base_name


# Higher is preferred. Favor predictable loot/terrain and wand-friendly evasion
# over changes to vision, emergency healing, targeting, and enemy generation.
TRINKETS = {
    'petrified seed': 180, 'mossy clump': 170, 'cracked spyglass': 160,
    'ferret tuft': 150, 'exotic crystals': 140, 'parchment scrap': 130,
    'thirteen leaf clover': 120, 'wondrous resin': 110, 'salt cube': 100,
    'dimensional sundial': 90, 'vial of blood': 80, 'rat skull': 70,
    'eye of newt': 60, 'trap mechanism': 50, 'chaotic censer': 40,
    'shard of oblivion': 30, 'mimic tooth': 20,
}


def trinket_menu(p, state):
    plan = p.alchemy_plan
    if not plan or plan['brew'].output != 'trinket':
        return None
    if plan['steps']>18:
        p.stop_unsafe('Trinket selection exceeded its bounded menu budget')
    buttons = state.get('ui', {}).get('buttons', [])
    texts = ' '.join(state.get('ui', {}).get('texts', [])).replace('_', '').lower()
    if plan['stage'] == 'trinket-confirm':
        chosen = plan['trinket']
        confirm = [b for b in buttons if b['label'].strip().lower() == 'confirm']
        titles=[text.replace('_','').strip().lower() for text in state.get('ui',{}).get('texts',[])]
        if len(confirm) != 1 or chosen not in titles:
            p.stop_unsafe('Trinket confirmation does not match the selected observed reward')
        plan['stage'] = 'done'
        plan['trinket_confirmed'] = True
        plan['crafted_output'] = chosen
        if chosen in plan['inventory_before']:
            plan['before_counts'] = dict(plan['inventory_before'])
        else:
            plan.pop('before_counts',None)  # Never assume an unobserved baseline is zero.
        return p.decision({'type': 'button', 'id': confirm[0]['id']},
                          'alchemy: confirm highest-ranked observed trinket')
    if 'create a trinket' not in texts:
        return None
    if plan.get('trinket_confirmed'):
        p.stop_unsafe('Trinket confirmation did not close the choice; do not retry')
    if plan['stage'] != 'done':
        p.stop_unsafe('Trinket choice appeared before the planned craft')
    offers = [(TRINKETS[base_name({'name': b['label']})], b)
              for b in buttons if base_name({'name': b['label']}) in TRINKETS]
    if not offers:
        p.stop_unsafe('No recognized observed trinket offered; never choose a random or guessed reward')
    _, chosen = max(offers, key=lambda pair: pair[0])
    plan['trinket'] = base_name({'name': chosen['label']})
    plan['stage'] = 'trinket-confirm'
    return p.decision({'type': 'button', 'id': chosen['id']},
                      'alchemy: inspect highest-ranked observed trinket')
