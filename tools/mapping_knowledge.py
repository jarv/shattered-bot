"""Full-floor mapping receipts from accepted input/public effect text, not proposals."""
from collections import Counter
try:
    from .consumable_tactics import base_name
except ImportError:
    from consumable_tactics import base_name


def complete(p,state):
    return (state.get('depth'),state.get('branch',0)) in p.mapped_floors


def observe(p,before,decision,after):
    floor=(before.get('depth'),before.get('branch',0))
    if floor!=(after.get('depth'),after.get('branch',0)):return None
    item=next((i for i in before.get('inventory',[]) if i['id']==decision.action.get('id')),None)
    named=item and base_name(item)=='scroll of magic mapping' and decision.action.get('action')=='READ'
    def count(s):return sum(i.get('quantity',1) for i in s.get('inventory',[]) if base_name(i)=='scroll of magic mapping')
    texts=lambda s:Counter(t.replace('_','').strip().lower() for t in s.get('ui',{}).get('texts',[]))
    message='you are now aware of the level layout.'
    public_effect=texts(after)[message]>texts(before)[message]
    if public_effect or named and count(after)<count(before):
        p.mapped_floors.add(floor);p.secret_search_goal=None
        return {'depth':floor[0],'branch':floor[1],'full_mapping_confirmed':True,
                'named_scroll_consumption':bool(named and count(after)<count(before)),
                'public_layout_message':public_effect,'searches_suppressed':True}
    return None
