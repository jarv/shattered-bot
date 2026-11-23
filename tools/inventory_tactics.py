"""Validated shop sales and ranked, receipt-backed full-pack relief."""
import re
from collections import Counter
try:
    from .combat_items import stats,physical_score,known_cursed
    from .consumable_tactics import base_name
    from .policy_decision import Intent
    from .policy_geometry import distance,neighbors
except ImportError:
    from combat_items import stats,physical_score,known_cursed
    from consumable_tactics import base_name
    from policy_decision import Intent
    from policy_geometry import distance,neighbors


def title(item):return re.sub(r' x\d+$','',item['name'].replace('_','').strip().lower())
def signature(state):return tuple(sorted((title(i),i.get('quantity',1),bool(i.get('equipped'))) for i in state['inventory']))
def count(state,name):return sum(i.get('quantity',1) for i in state['inventory'] if title(i)==name)


def inferior(state,item):
    """Only comparable, identified plain gear; never infer unknown power."""
    if item.get('equipped') or not item.get('identified') or known_cursed(item) or item.get('quantity',1)!=1:return False
    name=title(item);description=item.get('description','').replace('_','').lower()
    try:
        from .artifact_tactics import artifact_name,ARTIFACT_PRIORITY
    except ImportError:
        from artifact_tactics import artifact_name,ARTIFACT_PRIORITY
    if artifact_name(item) in ARTIFACT_PRIORITY:return False
    if any(k in name for k in ('staff','wand','ring','seal','amulet','ankh','mask','crown','pickaxe','bow')):return False
    if any(k in description for k in ('glyph','enchant','curse','seal','augment','quest','unique','artifact',
                                     'extra reach','blocking','surprise','combo','disarm')):return False
    parsed=stats(item)
    if not parsed or parsed[0] not in {'melee','armor'}:return False
    current=next((i for i in state['inventory'] if i.get('equipped') and i.get('identified')
                  and not known_cursed(i) and stats(i) and stats(i)[0]==parsed[0]),None)
    if not current:return False
    # Compare at a strength where both items are usable: over-strength future
    # gear must not look "weaker" just because its current score is zero.
    strength=max(state['hero'].get('strength',0),parsed[2],stats(current)[2])
    return stats(current)[1]>=parsed[1] and stats(current)[2]<=parsed[2] \
        and physical_score(current,strength)>physical_score(item,strength)


def redundant(state,item):
    """Interchangeable identified plain equipment: retain at least one copy."""
    copies=[i for i in state['inventory'] if title(i)==title(item)]
    if len(copies)<2 or not stats(item) or stats(item)[0] not in {'melee','armor'}:return False
    if any(i.get('equipped') or not i.get('identified') or not i.get('curse_known')
           or known_cursed(i) or i.get('quantity',1)!=1 for i in copies):return False
    description=item.get('description','').replace('_','').lower()
    text=title(item)+' '+description
    if any(t in text for t in ('staff','wand','ring','seal','quest','unique','artifact','glyph','enchant',
                              'curse','augment','extra reach','blocking','surprise','combo','disarm','pickaxe','bow')):return False
    return all(stats(i)==stats(item) and i.get('description','').replace('_','').lower()==description
               and set(i.get('actions',[]))==set(item.get('actions',[])) for i in copies)


def candidates(p,state,action):
    try:
        from .rose_outfitting import rose_available,spares
    except ImportError:
        from rose_outfitting import rose_available,spares
    ghost_reserve={title(i) for i in spares(state)} if rose_available(state) else set()
    protected={str(getattr(p,'upgrade_target','')).lower(),str(getattr(p,'ghost_quest',{}).get('selected','')).lower()}
    return [i for i in state['inventory'] if action in i.get('actions',[])
            and title(i) not in protected|ghost_reserve
            and (redundant(state,i) or inferior(state,i)
                  and sum(title(j)==title(i) for j in state['inventory'])==1)]


def sale_candidates(p,state):
    # Goo is optional alchemical energy (3) or shop gold (30), not quest gear.
    # Sell only through a live quote/receipt; never add it to ground-discard candidates.
    return candidates(p,state,'DROP')+[i for i in state['inventory']
            if title(i) in {'blob of goo','blobs of goo'} and i.get('identified')
            and not i.get('equipped') and 'DROP' in i.get('actions',[])]


def discarded(p,cell,obj):
    item=obj.get('top_item',{})
    return bool(item and getattr(p,'intentional_discards',{}).get(cell)==(title(item),item.get('description',''),item.get('quantity',1)))


def quiet(p,state,enemies):
    if enemies or p.recent_threats or state.get('danger_cells') or state.get('status')!='ready' or state.get('modal'):return False
    pos=state['hero']['cell'];tile=p.tiles[pos]
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    return pos not in p.room_blocked and not p.effects_block_movement(tile) and not tile.get('plant') \
        and not tile.get('trap') and not any(b in buffs for b in ('burn','poison','bleed','paral','root','vertigo')) \
        and not any(getattr(p,k,None) for k in ('potion_stash','trap_payload_return','food_freeze_plan','drop_plan','room_journey','puzzle_probe'))


def choose(p,state,enemies,*,incoming_item=None):
    if not getattr(p,'unit_strategies_enabled',False) or not quiet(p,state,enemies):return None
    if p.sell_plan:return None
    if p.inventory_pressure and p.inventory_pressure['signature']!=signature(state):p.inventory_pressure=None
    incoming=(incoming_item or p.inventory_pressure.get('item')) if p.inventory_pressure else None
    if incoming:
        try:
            from .pickup_priority import replacements
        except ImportError:
            from pickup_priority import replacements
        excess=replacements(p,state,incoming)
    else:
        excess=candidates(p,state,'DROP')
    keepers=[o for o in state.get('objects',[]) if o['name'].lower()=='shopkeeper']
    if keepers and not incoming:
        excess=sale_candidates(p,state)
    excess=[i for i in excess if (signature(state),i.get('id')) not in p.inventory_disposal_failures]
    if not excess:return None
    item=excess[0] if incoming else min(excess,key=lambda i:physical_score(
        i,max(state['hero'].get('strength',0),stats(i)[2])) if stats(i) else 0)
    pos=state['hero']['cell'];width=state['map']['width']
    paths=p.paths(state,{o['cell'] for o in keepers})
    if keepers and not incoming:
        keeper=min(keepers,key=lambda o:distance(pos,o['cell'],width))
        if distance(pos,keeper['cell'],width)<=1:
            p.sell_plan={'stage':'keeper','depth':state['depth'],'branch':state.get('branch',0),
                         'name':title(item),'quantity':1,'steps':0,'bags':[],'interchangeable':redundant(state,item)}
            return p.cell(keeper['cell'],'shop: offer gear weaker than equipped gear',intent=Intent.SHOP)
        banks=[c for c in paths if distance(c,keeper['cell'],width)==1 and len(p.route(paths,c))<=9
               and all(n not in p.loot and p.tiles[n]['terrain'] not in {5,7,8,18,21,22,31,37,38}
                       and not p.tiles[n].get('plant') and not p.effects_block_movement(p.tiles[n]) for n in p.route(paths,c)[1:])]
        if banks:return p.toward(state,min(banks,key=lambda c:len(p.route(paths,c))),
                                'shop: approach to sell inferior spare equipment',paths,intent=Intent.SHOP)
    if not p.inventory_pressure:return None
    if pos in p.loot or p.tiles[pos]['terrain'] not in {1,3,9,11,14,20}:
        banks=[c for c in neighbors(pos,width,state['map']['height']) if c in paths and c not in p.loot
               and p.tiles[c]['terrain'] in {1,3,9,11,14,20} and not p.tiles[c].get('trap')
               and not p.tiles[c].get('plant') and not p.effects_block_movement(p.tiles[c])]
        if banks:return p.cell(min(banks),'inventory: leave valuable pickup on a clean safe disposal bank',intent=Intent.REPOSITION)
        return None
    p.inventory_disposal_pending={'name':title(item),'quantity':item.get('quantity',1),'cell':pos,'depth':state['depth'],
                                  'branch':state.get('branch',0),'item_id':item['id'],'description':item.get('description',''),
                                  'signature':signature(state),
                                  'kind':'discarded-inferior-gear' if stats(item) and stats(item)[0] in {'melee','armor'}
                                         else 'discarded-lower-priority-item'}
    return p.use(item,'DROP','inventory: full pack; discard lower-priority item for observed pickup')


def sale_menu(p,state):
    plan=p.sell_plan
    if not plan:return None
    plan['steps']+=1
    if plan['depth']!=state.get('depth') or plan['branch']!=state.get('branch',0):p.stop_unsafe('Shop sale crossed floor/branch unexpectedly')
    if state.get('status')=='ready' and not state.get('modal'):
        p.sell_plan=None;return None
    buttons=state['ui'].get('buttons',[])
    texts=' '.join(state['ui'].get('texts',[])).replace('_','').lower()
    item=next((i for i in sale_candidates(p,state) if title(i)==plan['name']),None)
    if plan['steps']>8:p.stop_unsafe('Unsupported or stalled selling UI; refusing guessed item selection')
    if plan['stage']=='close' or not item:
        plan['stage']='close'
        return p.decision({'type':'back'},'shop: close sale selector; no unverified additional sale')
    if plan['stage']=='keeper':
        sell=[b for b in buttons if b['label'].strip().lower()=='sell an item']
        if len(sell)==1 and 'shopkeeper' in texts:
            plan['stage']='select'
            return p.decision({'type':'button','id':sell[0]['id']},'shop: open ordinary sell selector')
    elif plan['stage']=='select':
        selected=[b for b in buttons if title({'name':b['label']})==plan['name']]
        interchangeable=plan.get('interchangeable') and redundant(state,item) \
            and len(selected)==sum(title(i)==plan['name'] for i in state['inventory'])
        if len(selected)==1 or interchangeable:
            plan['stage']='quote'
            return p.decision({'type':'button','id':selected[0]['id']},'shop: select explicitly inferior spare gear')
        # Goo is a sale candidate but can live in the velvet pouch. Search
        # only observed supported tabs, once each; never guess an item slot.
        bag=next((b for b in buttons if b['label'].lower() in {'backpack','velvet pouch'}
                  and b['label'].lower() not in plan['bags']),None)
        if bag:
            label=bag['label'].lower()
            plan['bags'].append(label)
            return p.decision({'type':'button','id':bag['id']},f'shop: find spare gear in observed {label}')
    elif plan['stage']=='quote' and plan['name'] in texts:
        quotes=[(b,re.fullmatch(r'sell (?:1 for |for )(\d+)g',b['label'].strip().lower())) for b in buttons]
        quotes=[(b,int(m[1])) for b,m in quotes if m and int(m[1])>0]
        if len(quotes)==1:
            button,price=quotes[0];plan.update(stage='verify',price=price,gold_before=state['hero'].get('gold',0),button=button['id'])
            return p.decision({'type':'button','id':button['id']},f"shop: sell {plan['name']} for observed {price}g")
    plan['stage']='close'
    return p.decision({'type':'back'},'shop: cancel changed, ambiguous or unsupported sale')


def observe_accepted(p,before,decision,after):
    if not getattr(p,'unit_strategies_enabled',False):return None
    events=[];plan=p.sell_plan
    same=before.get('depth')==after.get('depth') and before.get('branch',0)==after.get('branch',0)
    if plan and plan['stage']=='verify' and decision.action=={'type':'button','id':plan['button']}:
        if same and count(before,plan['name'])-count(after,plan['name'])==1 \
                and after['hero'].get('gold',0)-plan['gold_before']==plan['price']:
            events.append({'kind':'sold','name':plan['name'],'quantity':1,'gold':plan['price'],'depth':before['depth']})
            plan['stage']='close'
        else:
            plan['stage']='unverified'
            events.append({'kind':'sale-unverified','name':plan['name'],'depth':before.get('depth'),
                           'reason':'Item removal and observed gold gain did not both verify; no retry allowed'})
    drop=p.inventory_disposal_pending;p.inventory_disposal_pending=None
    if drop and decision.action=={'type':'item','id':drop['item_id'],'action':'DROP'}:
        ground=next((o.get('top_item',{}) for o in after.get('objects',[]) if o.get('cell')==drop['cell']),{})
        if same and after['hero']['cell']==drop['cell'] and count(before,drop['name'])-count(after,drop['name'])==drop['quantity'] \
                and ground and title(ground)==drop['name'] and ground.get('quantity',1)==drop['quantity']:
            p.intentional_discards[drop['cell']]=(drop['name'],ground.get('description',''),drop['quantity'])
            p.inventory_pressure=None;p.inventory_drop_count+=1
            events.append({'kind':drop['kind'],'name':drop['name'],'quantity':drop['quantity'],'cell':drop['cell'],'depth':drop['depth'],
                           'evidence':'Inventory removal and matching observed ground item; not new loot or a collection'})
        else:
            # A failed or ambiguous drop must not be clicked repeatedly.
            p.inventory_pressure=None
            p.inventory_disposal_failures.add((drop['signature'],drop['item_id']))
            events.append({'kind':'discard-unverified','name':drop['name'],'depth':drop['depth']})
    # A fresh public failed-pickup message, not flat inventory length, admits
    # one cleanup attempt. Old log text and failed movement are insufficient.
    if same and decision.action.get('type')=='cell' and after['hero']['cell']==decision.action.get('cell'):
        obj=next((o for o in before.get('objects',[]) if o.get('cell')==decision.action['cell'] and o.get('top_item') and not o.get('for_sale')),None)
        if obj:
            name=re.sub(r' [+-]\d+$','',base_name(obj['top_item']))
            message=f"you can't carry: {name}."
            texts=lambda s:Counter(t.replace('_','').strip().lower() for t in s.get('ui',{}).get('texts',[]))
            if texts(after)[message]>texts(before)[message] and signature(before)==signature(after):
                p.inventory_pressure={'depth':before['depth'],'cell':obj['cell'],'name':name,
                                      'item':dict(obj['top_item']),'signature':signature(after)}
                events.append({'kind':'full-pack-observed','name':name,'cell':obj['cell'],'depth':before['depth']})
    p.inventory_events.extend(events)
    return events or None
