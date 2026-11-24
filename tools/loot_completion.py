"""Hard observed-loot coverage, with inventory/key-backed collection evidence."""
try:
    from .floor_metrics import inventory,name
except ImportError:
    from floor_metrics import inventory,name


def required_loot(p):
    try:
        from .inventory_tactics import discarded
    except ImportError:
        from inventory_tactics import discarded
    # Resolved crystal alternatives are an observed mutually exclusive choice,
    # not a skipped collectible. Shop purchases have separate money/price rules.
    return {c:o for c,o in {**p.unconfirmed_loot,**p.loot}.items()
            if not o.get('for_sale') and c not in p.resolved_crystal_alternatives and not discarded(p,c,o)}


def pending_collections(p):
    try:
        from .room_supplies import deferred_loot
    except ImportError:
        from room_supplies import deferred_loot
    return bool(set(required_loot(p))-deferred_loot(p) or missing_keys(p) or p.mimic_obligations
                or p.potion_stash or p.trap_payload_return or p.physical_ledger.has_unresolved())


def missing_keys(p):
    try:
        from .room_supplies import deferred_loot
    except ImportError:
        from room_supplies import deferred_loot
    deferred=deferred_loot(p)
    kinds=set()
    for cell,obj in required_loot(p).items():
        if cell in deferred:continue
        title=obj['name'].lower()
        if 'locked chest' in title and not p.keys.get('golden',0):kinds.add('golden')
        if 'crystal chest' in title and not p.keys.get('crystal',0):kinds.add('crystal')
    for c,tile in p.tiles.items():
        if c in p.resolved_crystal_alternatives:continue
        kind={10:'iron',21:'worn',31:'crystal',38:'skeleton'}.get(tile['terrain'])
        if kind and not p.keys.get(kind,0):kinds.add(kind)
    return kinds


def observe_collected(p,before,decision,after):
    """Called only after an accepted action. Absence alone is not collection."""
    if (before.get('depth'),before.get('branch',0)) != (
            after.get('depth'),after.get('branch',0)) or decision.action.get('type')!='cell':return
    try:
        from .maze_objective import observe_open,collected
    except ImportError:
        from maze_objective import observe_open,collected
    observe_open(p,before,decision)
    cell=decision.action.get('cell')
    obj=next((o for o in before.get('objects',[]) if o.get('cell')==cell and o.get('top_item')
              and not o.get('for_sale')),None)
    if not obj:return
    item=obj['top_item'];item_name=name(item)
    old,new=inventory(before),inventory(after)
    gained=new[item_name]>old[item_name] and sum(new.values())>sum(old.values())
    if 'key' in item_name:
        kind=next((kind for kind in ('iron','golden','crystal','worn','skeleton')
                   if f'{kind} key' in item_name),None)
        def key_count(state):
            return sum(k.get('quantity',1) for k in state.get('keys',[])
                       if kind and k.get('depth')==before['depth'] and f'{kind} key' in k['name'].lower())
        gained=gained or key_count(after)>key_count(before)
    if 'gold' in item_name:
        gained=gained or after.get('hero',{}).get('gold',0)>before.get('hero',{}).get('gold',0)
    try:
        from .collection_evidence import journal_pickup
    except ImportError:
        from collection_evidence import journal_pickup
    journal=journal_pickup(before,decision.action,after)
    gained=gained or bool(journal)
    if gained:
        try:
            from .reward_lifecycle import observe_collection
        except ImportError:
            from reward_lifecycle import observe_collection
        observe_collection(p,before,cell)
        collected(p,cell)
        p.loot_collection_receipts.add(cell)
        p.unconfirmed_loot.pop(cell,None)
        if journal:return {'cell':cell,'name':journal,'evidence':'fresh public journal-item pickup confirmation; not backpack acquisition'}


def remember_missing(p,old_loot):
    for cell,obj in old_loot.items():
        if (obj.get('top_item') or 'chest' in obj['name'].lower()) \
                and cell not in p.mimic_obligations and not obj.get('for_sale') and cell not in p.loot \
                and cell not in p.loot_collection_receipts:
            p.unconfirmed_loot[cell]=obj
    for cell in p.loot:p.unconfirmed_loot.pop(cell,None)
    p.loot_collection_receipts.clear()
