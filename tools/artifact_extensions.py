"""Observed Skeleton Key, Rose, Tome and Spellbook strategies and artifact recovery."""
try:
    from .policy_decision import Intent,Finished
    from .policy_geometry import distance,neighbors
    from .artifact_tactics import artifact_name
    from .combat_items import known_cursed
    from .mimic_tactics import suspicious_container
except ImportError:
    from policy_decision import Intent,Finished
    from policy_geometry import distance,neighbors
    from artifact_tactics import artifact_name
    from combat_items import known_cursed
    from mimic_tactics import suspicious_container


def charges(item):
    raw=(item.get('status') or '').split('/')[0].rstrip('%')
    return int(raw) if raw.isdigit() else None


def issue(p,state,item,action,reason,*,target=None,expected=None):
    name=artifact_name(item);key=(name,action,target,expected)
    if p.artifact_extension_attempts[key]>= (3 if action=='READ' else 6 if action=='CAST' else 2):return None
    p.artifact_extension_attempts[key]+=1
    p.artifact_extension_pending={'name':name,'action':action,'target':target,'expected':expected,
                                  'charges':charges(item),'depth':state['depth'],'branch':state.get('branch',0)}
    return p.use(item,action,reason,target=target)


def observe(p,state):
    try:
        from .spellbook_feeding import observe as observe_add
    except ImportError:
        from spellbook_feeding import observe as observe_add
    observe_add(p,state)
    if isinstance(p.artifact_menu,dict) and p.artifact_menu.get('kind')=='rose' \
            and p.artifact_menu.get('stage')=='close' and state.get('status')=='ready' and not state.get('modal'):
        p.artifact_menu=None
    plan=p.artifact_extension_pending
    if not plan or state.get('status')!='ready' or state.get('modal'):return
    if isinstance(p.artifact_menu,dict) and p.artifact_menu.get('kind')=='spellbook':p.artifact_menu=None
    if p.artifact_menu:return
    if plan['depth']!=state['depth'] or plan['branch']!=state.get('branch',0):
        p.artifact_extension_pending=None;return
    item=next((i for i in state.get('inventory',[]) if artifact_name(i)==plan['name']),{})
    confirmed=False
    if plan['expected']=='ward':confirmed=any('holy ward' in b['name'].lower() or 'holy armor' in b['name'].lower() for b in state['hero'].get('buffs',[]))
    elif plan['expected']=='summon':confirmed='DIRECT' in item.get('actions',[])
    elif isinstance(plan['expected'],int):confirmed=p.tiles.get(plan['target'],{}).get('terrain')==plan['expected']
    else:confirmed=charges(item) is not None and plan['charges'] is not None and charges(item)<plan['charges']
    p.planner.report['artifact_outcome']={**plan,'confirmed_public_effect':confirmed,
        'qualification':'Observed buff/action/terrain or charge change only; no kill, reward collection or ally position inferred'}
    if not confirmed:
        p.log_continuation_error(state,'artifact-unconfirmed','Artifact activation has no modeled public confirmation; do not infer success or blindly retry',dict(plan))
    p.artifact_extension_pending=None


def seek_pickup(p,state):
    try:
        from .artifact_tactics import ARTIFACT_PRIORITY
        from .inventory_tactics import quiet
    except ImportError:
        from artifact_tactics import ARTIFACT_PRIORITY
        from inventory_tactics import quiet
    if not quiet(p,state,[]) or state['hero']['hp']<.65*state['hero']['max_hp']:return None
    paths=p.paths(state);pos=state['hero']['cell'];width,height=state['map']['width'],state['map']['height']
    for cell,obj in sorted(p.loot.items(),key=lambda pair:distance(pos,pair[0],width)):
        item=obj.get('top_item',{})
        if not item or artifact_name(item) not in ARTIFACT_PRIORITY or obj.get('for_sale') or p.artifact_pickup_routes[cell]>=24:continue
        if not p.tiles.get(cell,{}).get('visible'):continue  # Reobserve, never claim a remembered pickup.
        if p.failed_moves[cell] or cell in p.blocked or cell in p.room_loot_deferred:
            bank=p.artifact_pickup_banks.get(cell)
            if bank is None:
                choices=[c for c in neighbors(cell,width,height) if c in paths and c!=pos and c not in p.loot
                         and p.tiles[c]['terrain'] in {1,2,3,9,11,14,15,19,20,29} and not p.tiles[c].get('plant')
                         and not p.tiles[c].get('trap') and not p.effects_block_movement(p.tiles[c])]
                if not choices:continue
                bank=min(choices,key=lambda c:len(p.route(paths,c)));p.artifact_pickup_banks[cell]=bank
            if bank not in paths:continue
            if pos!=bank:
                p.artifact_pickup_routes[cell]+=1
                return p.toward(state,bank,'artifact: reobserve unconfirmed valuable pickup from a different safe bank',paths,intent=Intent.REPOSITION)
            # A new bank and public observation is a new deliberate interaction, not an API retry.
            key=('pickup',cell,bank)
            if p.artifact_extension_attempts[key]>=1:continue
            if p.tiles[cell]['terrain'] not in {1,2,3,9,11,14,15,19,20,29} or p.tiles[cell].get('trap') \
                    or p.tiles[cell].get('plant') or p.effects_block_movement(p.tiles[cell]):continue
            p.artifact_extension_attempts[key]+=1
            p.blocked.discard(cell);p.failed_moves.pop(cell,None)
            p.defer_obligations(state,[{'kind':'unconfirmed artifact pickup','cell':cell,'name':item['name']}],
                                'Prior interaction did not collect artifact; reobserved from a different bank; no collection credit')
            return p.cell(cell,'artifact: deliberate reobserved pickup from changed approach; verify inventory',intent=Intent.LOOT)
    return None


def choose(p,state,enemies):
    if state.get('status')!='ready' or state.get('modal') or state.get('danger_cells') or p.artifact_extension_pending:return None
    hero=state['hero'];pos=hero['cell'];width,height=state['map']['width'],state['map']['height']
    buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    if any(b in buffs for b in ('magic immun','paral','vertigo')):return None
    items={artifact_name(i):i for i in state['inventory'] if i.get('equipped') and not known_cursed(i)}
    active=[e for e in enemies if not e.get('sleeping')]
    key=items.get('skeleton key');charge=charges(key) if key else None
    if key and 'INSERT' in key.get('actions',[]) and key.get('curse_known') and not state.get('boss_health_text') \
            and state.get('branch',0)==0 and state['depth']%5:
        adjacent=list(neighbors(pos,width,height))
        if not enemies and not p.recent_threats:
            for cell in adjacent:
                tile=p.tiles.get(cell,{})
                if tile.get('visible') and tile.get('terrain')==38:
                    a=issue(p,state,key,'INSERT','artifact: reopen observed self-locked ordinary door',target=cell,expected=5)
                    if a:return a
                if tile.get('visible') and tile.get('terrain')==10 and charge is not None and charge>=1:
                    a=issue(p,state,key,'INSERT','artifact: unlock observed ordinary iron door with Skeleton Key',target=cell,expected=5)
                    if a:return a
                loot=p.loot.get(cell,{})
                if tile.get('visible') and loot.get('name','').lower()=='locked chest' and not loot.get('for_sale') \
                        and not suspicious_container(loot) and charge is not None and charge>=2:
                    a=issue(p,state,key,'INSERT','artifact: unlock observed golden chest; verify opening, not collection',target=cell)
                    if a:return a
            if hero['hp']>=.65*hero['max_hp'] and charge is not None and charge>=1:
                paths=p.paths(state);staging=[]
                for target,tile in p.tiles.items():
                    loot=p.loot.get(target,{})
                    cost=0 if tile['terrain']==38 else 1 if tile['terrain']==10 else 2 if loot.get('name','').lower()=='locked chest' \
                        and not loot.get('for_sale') and not suspicious_container(loot) else None
                    if cost is None or charge<cost or p.artifact_extension_attempts[('key-approach',target)]>=24:continue
                    for bank in neighbors(target,width,height):
                        if bank==pos or bank not in paths:continue
                        route=p.route(paths,bank)
                        if len(route)>25 or any(p.tiles[c].get('trap') or p.tiles[c].get('plant') or p.effects_block_movement(p.tiles[c])
                                or p.tiles[c]['terrain'] in {7,8,10,18,21,22,31,37,38} for c in route[1:]):continue
                        staging.append((len(route),target,bank))
                if staging:
                    _,target,bank=min(staging);p.artifact_extension_attempts[('key-approach',target)]+=1
                    return p.toward(state,bank,'artifact: approach observed ordinary lock for Skeleton Key use',paths,intent=Intent.REPOSITION)
        if active and charge is not None and charge>=2 and .35*hero['max_hp']<=hero['hp']<.65*hero['max_hp']:
            try:
                from .multi_enemy_tactics import single_file
            except ImportError:
                from multi_enemy_tactics import single_file
            escape=[c for c in adjacent if p.walkable(c,{e['cell'] for e in enemies}) and c not in p.loot
                    and all(distance(c,e['cell'],width)>1 for e in active)]
            if escape and single_file(p,state,active,pos):
                for door in adjacent:
                    if p.tiles.get(door,{}).get('visible') and p.tiles[door]['terrain'] in {5,6} and door not in p.loot \
                            and not any(o['cell']==door for o in state.get('objects',[])) \
                            and all(distance(door,e['cell'],width)<distance(pos,e['cell'],width) for e in active):
                        return issue(p,state,key,'INSERT','artifact: lock observed choke against pursuit; retain observed exit',target=door,expected=38)
    tome=items.get('holy tome')
    if tome and 'CAST' in tome.get('actions',[]) and tome.get('curse_known') and (charges(tome) or 0)>=2 \
            and active and .35*hero['max_hp']<=hero['hp']<.65*hero['max_hp'] and not any(b in buffs for b in ('holy ward','holy armor')):
        a=issue(p,state,tome,'CAST','artifact: open offered Holy Ward defense spell; verify actual buff',expected='ward')
        if a:
            p.artifact_menu={'kind':'tome','steps':0}
            return a
    rose=items.get('dried rose')
    if rose and rose.get('curse_known') and 'DIRECT' in rose.get('actions',[]) and active and hero['hp']>=.7*hero['max_hp']:
        target=min(active,key=lambda e:distance(pos,e['cell'],width))
        return issue(p,state,rose,'DIRECT','artifact: direct available ghost toward observed enemy; no position or kill assumed',target=target['cell'])
    if enemies or p.recent_threats or any(b in buffs for b in ('invisib','burn','poison','bleed','blind')) \
            or any(getattr(p,k,None) for k in ('room_journey','puzzle_probe','potion_stash','drop_plan')):return None
    pickup=seek_pickup(p,state)
    if pickup:return pickup
    if any(b in buffs for b in ('hungry','starving')):return None
    try:
        from .rose_outfitting import choose as outfit
    except ImportError:
        from rose_outfitting import choose as outfit
    outfitting=outfit(p,state,enemies)
    if outfitting:return outfitting
    if rose and rose.get('curse_known') and 'SUMMON' in rose.get('actions',[]) and hero['hp']>=.7*hero['max_hp']:
        if any(c not in p.tiles or p.tiles[c].get('trap') or p.tiles[c].get('plant') or p.effects_block_movement(p.tiles[c])
               for c in neighbors(pos,width,height)):return None
        space=[c for c in neighbors(pos,width,height) if p.walkable(c) and p.tiles[c].get('visible')
               and not p.tiles[c].get('trap') and not p.tiles[c].get('plant') and not p.effects_block_movement(p.tiles[c])]
        if space:return issue(p,state,rose,'SUMMON','artifact: summon quest-enabled ghost in observed quiet space; verify DIRECT availability',expected='summon')
    book=items.get('unstable spellbook')
    if book:
        try:
            from .spellbook_feeding import choose as feed_book
        except ImportError:
            from spellbook_feeding import choose as feed_book
        feeding=feed_book(p,state,enemies,book)
        if feeding:return feeding
    if book and book.get('curse_known') and hero['hp']>=.95*hero['max_hp'] and not p.artifact_cooldown and state['depth']%5:
        if 'READ' in book.get('actions',[]) and (charges(book) or 0)>0:
            a=issue(p,state,book,'READ','artifact: bounded safe-window random spellbook reading; outcome not guessed')
            if a:
                p.artifact_cooldown=30;p.artifact_menu={'kind':'spellbook','steps':0}
            return a
    return None


def menu(p,state,plan):
    if plan['kind']=='spellbook-add':
        try:
            from .spellbook_feeding import menu as add_menu
        except ImportError:
            from spellbook_feeding import menu as add_menu
        return add_menu(p,state,plan)
    if plan['kind']=='rose':
        try:
            from .rose_outfitting import menu as outfit_menu
        except ImportError:
            from rose_outfitting import menu as outfit_menu
        return outfit_menu(p,state,plan)
    plan['steps']+=1
    if plan['steps']>8:raise Finished('blocked','Artifact menu exceeded bounded public UI workflow')
    buttons=[b for b in state['ui'].get('buttons',[]) if b.get('enabled',True)]
    def label(b):return b.get('label','').replace('_','').strip().lower().split('\n')[0]
    if plan['kind']=='tome':
        ward=next((b for b in buttons if label(b)=='holy ward'),None)
        if not ward:raise Finished('blocked','Holy Tome does not expose an understood offered Holy Ward button')
        p.artifact_menu=None
        return p.decision({'type':'button','id':ward['id']},'artifact: cast publicly offered Holy Ward; verify buff before assuming defense')
    if plan['kind']=='spellbook':
        # An empowered choice names the regular and exotic scrolls publicly.
        regular={'scroll of identify','scroll of remove curse','scroll of magic mapping','scroll of recharging',
                 'scroll of mirror image','scroll of lullaby','scroll of terror','scroll of rage','scroll of retribution',
                 'scroll of teleportation','scroll of transmutation','scroll of upgrade'}
        text=' '.join(state['ui'].get('texts',[])).lower()
        empowered='regular' in text and 'exotic' in text and 'scroll' in text
        choice=next((b for b in buttons if label(b) in regular),None) if empowered else None
        p.artifact_menu=None;p.menu_plan='discover-scroll';p.consumable_menu_bags=set()
        if choice:return p.decision({'type':'button','id':choice['id']},'artifact: choose publicly named regular spellbook effect; no random outcome inferred')
        # Direct inventory-selection results use the existing observed-scroll workflow.
        if any(label(b) in {'backpack','potion bandolier','velvet pouch'} or any(label(b)==i['name'].lower() for i in state['inventory']) for b in buttons):
            return p.menu(state)
        raise Finished('blocked','Unsupported Spellbook result UI; refusing a guessed random-effect selection')
    raise Finished('blocked','Unknown artifact extension menu')
