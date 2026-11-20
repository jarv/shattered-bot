"""Wandmaker workflows from rendered dialogue, landmarks and carried items."""
import re

try:
    from .consumable_tactics import base_name
    from .policy_geometry import distance, neighbors
    from .policy_decision import Intent
except ImportError:
    from consumable_tactics import base_name
    from policy_geometry import distance, neighbors
    from policy_decision import Intent


OBJECTIVES={'dust':'corpse dust','ember':'elemental embers','berry':'seed of rotberry'}


def count(state,name):
    return sum(i.get('quantity',1) for i in state.get('inventory',[]) if base_name(i)==name)


def wand_name(name):
    return re.sub(r'\s+[+-]\d+$','',base_name({'name':name}))


def observe(p,state):
    q=p.wandmaker_quest
    for o in state.get('objects',[]):
        if o['name'].lower()=='old wandmaker':
            q.update(cell=o['cell'],depth=state['depth'])
    objective=OBJECTIVES.get(q.get('variant'))
    if objective and count(state,objective) and q.get('stage') not in {'claiming','done','collect_dropped'}:
        q['stage']='return'
    if q.get('stage') in {'claiming','collect_dropped'}:
        carried=sum(i.get('quantity',1) for i in state['inventory']
                    if wand_name(i['name'])==q.get('selected'))
        if carried>q.get('count_before',0) and not count(state,objective):
            q['stage']='done'
        elif not count(state,objective):
            q['stage']='collect_dropped'  # Quest hand-in isn't inventory collection.
    pending=q.get('candle_pending')
    if pending and state.get('status')=='ready' and not state.get('modal'):
        heap=p.loot.get(pending['cell'],{})
        if 'ceremonial candle' in heap.get('name','').lower() and count(state,'ceremonial candle')<pending['before']:
            q.setdefault('placed',set()).add(pending['cell']);q.pop('candle_pending',None)
        elif any(o['name'].lower()=='newborn fire elemental' for o in state.get('objects',[])):
            q.pop('candle_pending',None);q['summoned']=True
        # Otherwise do not repeat an ambiguously completed throw.
    for c in q.get('placed',set()):
        if 'ceremonial candle' in p.loot.get(c,{}).get('name','').lower():
            p.room_blocked.add(c);p.room_skipped.add(c)


def menu(p,state):
    plan=p.wandmaker_menu;q=p.wandmaker_quest
    plan['steps']+=1
    text=' '.join(state['ui'].get('texts',[])).replace('_','').lower()
    buttons=state['ui'].get('buttons',[])
    def click(b,reason):return p.decision({'type':'button','id':b['id']},reason)
    if plan['steps']>14:
        p.stop_unsafe('Wandmaker dialogue exceeded bounded workflow')
    if plan.get('stage')=='preview':
        selected=plan['options'][plan['index']]
        cancel=next((b for b in buttons if b['label'].lower()=='cancel'),None)
        if cancel and wand_name(selected) in text:
            # Both are publicly named wands. Favor a new utility over duplicate
            # types; no hidden level, charges or damage are read or assumed.
            owned=any(wand_name(i['name'])==wand_name(selected) for i in state['inventory'])
            priority=next((v for n,v in (('frost',5),('corrosion',4),('blast wave',3),
                         ('regrowth',2)) if n in selected.lower()),1)
            plan.setdefault('scores',[]).append(priority-10*owned)
            plan['stage']='next'
            return click(cancel,'quest: compare inspected Wandmaker reward')
    elif plan.get('stage')=='next':
        plan['index']+=1
        if plan['index']<len(plan['options']):
            plan['stage']='preview';label=plan['options'][plan['index']]
        else:
            plan['stage']='confirm'
            label=plan['options'][max(range(len(plan['scores'])),key=lambda i:plan['scores'][i])]
            plan['selected']=wand_name(label)
        b=next((b for b in buttons if b['label']==label),None)
        if b:return click(b,'quest: inspect selected Wandmaker wand')
    elif plan.get('stage')=='confirm':
        b=next((b for b in buttons if b['label'].lower()=='confirm'),None)
        if b and plan['selected'] in text:
            q.update(stage='claiming',selected=plan['selected'],count_before=sum(
                i.get('quantity',1) for i in state['inventory'] if wand_name(i['name'])==plan['selected']))
            p.wandmaker_menu=None
            return click(b,'quest: confirm inspected wand; require inventory-backed collection')
    else:
        options=[b for b in buttons if wand_name(b.get('label','')).startswith('wand of ')]
        if len(options)==2 and q.get('stage')=='return':
            plan.update(stage='preview',options=[b['label'] for b in options],index=0,scores=[])
            return click(options[0],'quest: inspect first Wandmaker reward')
        variant=next((k for k,n in OBJECTIVES.items()
                      if (n in text or k=='ember' and ('those embers' in text or 'fresh embers' in text)
                          or k=='berry' and 'rotberry' in text)),None)
        if variant:
            q.update(variant=variant,stage='return' if count(state,OBJECTIVES[variant]) else 'active')
            p.wandmaker_menu=None
            return p.decision({'type':'back'},'quest: accept publicly described Wandmaker objective')
        if 'i may have a task for you' in text:
            return p.decision({'type':'back'},'quest: advance Wandmaker introduction to objective dialogue')
    p.stop_unsafe('Unrecognized Wandmaker dialogue/reward controls; refusing guessed input')


def safe_route(p,state,paths,cell,limit=80):
    return cell in paths and len(p.route(paths,cell))<=limit and all(
        not p.tiles[n].get('trap') and not p.tiles[n].get('plant')
        and not p.effects_block_movement(p.tiles[n]) and not p.loot.get(n,{}).get('for_sale')
        for n in p.route(paths,cell)[1:])


def choose(p,state,enemies):
    q=p.wandmaker_quest;hero=state['hero'];pos=hero['cell'];width=state['map']['width']
    if q.get('depth')!=state['depth'] or q.get('stage')=='done' or state.get('danger_cells'):return None
    if q.get('variant')=='ember':
        action=ember_combat(p,state,enemies)
        if action:return action
    buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    if any(b in buffs for b in ('burn','poison','bleed','vertigo','paral','root')):return None
    if q.get('stage')=='collect_dropped':
        if enemies or p.recent_threats:return None
        paths=p.paths(state)
        targets=[c for c,o in p.loot.items() if wand_name(o.get('top_item',o)['name'])==q['selected']
                 and not o.get('for_sale') and safe_route(p,state,paths,c)]
        if targets:return p.toward(state,min(targets,key=lambda c:len(p.route(paths,c))),
                                  'quest: collect observed dropped Wandmaker wand',paths,intent=Intent.LOOT)
        return None
    returning=q.get('stage')=='return'
    if returning or not q.get('variant'):
        # Dust summons pursuers: return through safe observed ground rather than
        # optional exploration. Adjacent threats still receive normal combat.
        if enemies and (not returning or any(distance(pos,e['cell'],width)<=1 for e in enemies)):return None
        if not returning and (p.recent_threats or hero['hp']<.8*hero['max_hp']):return None
        paths=p.paths(state,{e['cell'] for e in enemies})
        visible=any(o['name'].lower()=='old wandmaker' and o['cell']==q['cell'] for o in state.get('objects',[]))
        if visible and distance(pos,q['cell'],width)==1:
            p.wandmaker_menu={'steps':0,'stage':'dialogue'}
            return p.cell(q['cell'],'quest: return Wandmaker ingredient' if returning else 'quest: ask observed Wandmaker for objective')
        banks=[c for c in neighbors(q['cell'],width,state['map']['height']) if c!=pos and safe_route(p,state,paths,c)]
        if banks:return p.toward(state,min(banks,key=lambda c:len(p.route(paths,c))),
                                'quest: approach observed Wandmaker',paths,intent=Intent.REPOSITION)
        return None
    if enemies or p.recent_threats or hero['hp']<.7*hero['max_hp']:return None
    if q.get('stage')!='active':return None
    if q['variant']=='berry':
        # Only non-burning ranged attacks, outside lasher reach. The heart's
        # defense releases gas; ordinary movement continues to reject that gas.
        plants=[o for o in state.get('objects',[]) if o['name'].lower()=='rot heart']
        for target in plants:
            if distance(pos,target['cell'],width)<=1:continue
            if p.shot_clear(state,target['cell']):
                attack=p.best_attack(state,target,allowed_kinds={'magic','thrown'})
                if attack:
                    attack.reason='quest: attack Rot Heart without fire; leave lashers untouched'
                    return attack
            paths=p.paths(state)
            banks=[c for c in paths if c!=pos and distance(c,target['cell'],width)>1
                   and safe_route(p,state,paths,c,24)
                   and p.shot_clear(dict(state,hero=dict(hero,cell=c)),target['cell'])]
            if banks and any(p.target_allowed(i,target) for i in p.charged_magic(state)):
                return p.toward(state,min(banks,key=lambda c:len(p.route(paths,c))),
                                'quest: bypass lashers outside melee reach to reach a Rot Heart firing position',
                                paths,intent=Intent.REPOSITION)
    paths=p.paths(state)
    objective=OBJECTIVES[q['variant']]
    names={objective}
    if q['variant']=='ember' and not q.get('summoned'):names.add('ceremonial candle')
    targets=[c for c,o in p.loot.items() if base_name(o.get('top_item',o)) in names
             and c not in q.get('placed',set()) and not o.get('for_sale') and safe_route(p,state,paths,c)]
    if targets:return p.toward(state,min(targets,key=lambda c:len(p.route(paths,c))),
                              'quest: collect observed Wandmaker objective/supply',paths,intent=Intent.LOOT)
    if q['variant']=='ember':return ritual(p,state,paths)
    return None


def ritual(p,state,paths):
    q=p.wandmaker_quest
    if q.get('summoned') or q.get('candle_pending'):return None
    width=state['map']['width'];pos=state['hero']['cell']
    markers={c for c,t in p.tiles.items() if t.get('visible') and t.get('name','').lower()=='ritual marker'}
    centers=[c for c in markers if {c+dy*width+dx for dy in (-1,0,1) for dx in (-1,0,1)}<=markers]
    if len(centers)!=1:return None
    center=centers[0];slots={center-width,center+1,center+width,center-1}
    placed={c for c in slots if 'ceremonial candle' in p.loot.get(c,{}).get('name','').lower()}
    q['placed']=placed
    if count(state,'ceremonial candle')+len(placed)<4:return None
    # Known frost is a public quest-specific kill mechanism. Do not summon on
    # speculative wand charges, unidentified colors or a blocked retreat.
    frost=any(base_name(i) in {'potion of frost','icefruit'} and 'THROW' in i.get('actions',[])
              for i in state['inventory'])
    try:
        from .environment_tactics import payload
    except ImportError:
        from environment_tactics import payload
    frost=frost or (not p.barren_land and count(state,'seed of icecap') and payload(state))
    if not frost:return None
    missing=slots-placed
    if not missing:return None
    banks=[c for c in paths if 2<=distance(c,center,width)<=6 and safe_route(p,state,paths,c,12)
           and p.tiles[c].get('visible') and not p.tiles[c].get('effects')
           and sum(n in paths and n not in slots and n!=center
                   for n in neighbors(c,width,state['map']['height']))>=2]
    bank=min(banks,key=lambda c:(not near_water(p,state,c),len(p.route(paths,c)))) if banks else None
    if pos!=bank:
        if bank is not None:return p.toward(state,bank,
                                'quest: stage ritual near water where available, with escape space and known cold',paths,intent=Intent.REPOSITION)
        return None
    targets=[c for c in missing if p.shot_clear(state,c) and not p.loot.get(c)]
    if targets:
        target=min(targets)
        candle=next(i for i in state['inventory'] if base_name(i)=='ceremonial candle')
        q['candle_pending']={'cell':target,'before':count(state,'ceremonial candle')}
        return p.use(candle,'THROW','quest: place one candle on observed ritual slot; verify placement before continuing',target=target)
    return None


def near_water(p,state,cell):
    return any(p.tiles.get(c,{}).get('terrain')==29 and p.walkable(c)
               for c in [cell,*neighbors(cell,state['map']['width'],state['map']['height'])])


def ember_combat(p,state,enemies):
    """Elementals fly: Icecap needs an actual thrown payload, not a ground lure."""
    q=p.wandmaker_quest;width=state['map']['width'];pos=state['hero']['cell']
    foe=next((e for e in enemies if e['name'].lower()=='newborn fire elemental'),None)
    if not foe:return None
    q['summoned']=True
    def safe(cell):
        area={cell,*neighbors(cell,width,state['map']['height'])}
        return (pos not in area and p.shot_clear(state,cell)
                and all(p.tiles.get(c,{}).get('visible') for c in area)
                and not any(o['cell'] in area and o not in enemies and 'top_item' not in o
                            for o in state.get('objects',[]))
                and not any(c in area and ('potion' in o.get('name','').lower()
                            or 'meat' in o.get('name','').lower()) for c,o in p.loot.items()))
    cold=next((i for i in state['inventory'] if base_name(i) in {'potion of frost','icefruit'}
                and 'THROW' in i.get('actions',[]) and p.item_action_allowed(i,'THROW')),None)
    if cold and safe(foe['cell']):
        return p.use(cold,'THROW','quest: use known cold against observed newborn elemental',target=foe['cell'])
    try:
        from .environment_tactics import payload
    except ImportError:
        from environment_tactics import payload
    weight=payload(state)
    plan=q.get('icecap')
    if plan:
        cell=plan['cell'];q.pop('icecap',None)
        if (weight and 'icecap' in p.tiles.get(cell,{}).get('plant','').lower()
                and distance(cell,foe['cell'],width)<=1 and safe(cell)):
            if base_name(weight) in {'waterskin','dew vial','dew pouch'}:
                p.trap_payload_return={'cell':cell,'name':base_name(weight),'depth':state['depth'],
                                       'steps':0,'disarm_required':False}
            return p.use(weight,'THROW','quest: trigger observed Icecap with payload; flying elemental cannot trample it',target=cell)
    seed=next((i for i in state['inventory'] if base_name(i)=='seed of icecap'
               and 'THROW' in i.get('actions',[])),None)
    if seed and weight and not p.barren_land and not q.get('icecap_attempted'):
        cells=[c for c in neighbors(foe['cell'],width,state['map']['height'])
               if safe(c) and p.tiles[c]['terrain'] in {1,2,3,14,15,29,30}
               and not p.tiles[c].get('trap') and not p.tiles[c].get('plant')
               and not p.tiles[c].get('effects') and c not in p.loot]
        if cells:
            cell=min(cells);q['icecap']={'cell':cell};q['icecap_attempted']=True
            return p.use(seed,'THROW','quest: plant Icecap beside elemental; activation requires observed plant and payload',target=cell)
    if not near_water(p,state,pos) and q.get('water_steps',0)<8:
        paths=p.paths(state,{e['cell'] for e in enemies})
        banks=[c for c in paths if c!=pos and near_water(p,state,c)
               and safe_route(p,state,paths,c,5)
               and all(distance(n,e['cell'],width)>1 for n in p.route(paths,c)[1:] for e in enemies)]
        if banks:
            q['water_steps']=q.get('water_steps',0)+1
            return p.toward(state,min(banks,key=lambda c:len(p.route(paths,c))),
                            'quest: fight newborn elemental from safe ground near water',paths,intent=Intent.REPOSITION)
    return None
