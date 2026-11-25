"""Priority food, permanent progression, and matching-key pickups; no identity guesses."""
import re
try:
    from .consumable_tactics import base_name
    from .policy_decision import Intent
    from .policy_geometry import distance,neighbors
except ImportError:
    from consumable_tactics import base_name
    from policy_decision import Intent
    from policy_geometry import distance,neighbors


NAMES={'scroll of upgrade','potion of strength'}


def guarded_food(p,cell,obj,width):
    """Visibility loss must not restart optional food work beside a sleeper."""
    try:
        from .pickup_priority import food
    except ImportError:
        from pickup_priority import food
    return food(obj.get('top_item',obj)) and any(
        e.get('sleeping') and distance(cell,e['cell'],width)<=1
        for e in getattr(p,'enemy_sightings',{}).values())


def targets(p):
    try:
        from .room_supplies import deferred_loot
    except ImportError:
        from room_supplies import deferred_loot
    deferred=deferred_loot(p)
    try:
        from .pickup_priority import food
        from .inventory_tactics import discarded
    except ImportError:
        from pickup_priority import food
        from inventory_tactics import discarded
    locks={10:'iron',21:'worn',31:'crystal',38:'skeleton'}
    kinds={locks[t['terrain']] for t in getattr(p,'tiles',{}).values() if t.get('terrain') in locks}
    kinds.update('golden' if o.get('name','').lower()=='locked chest' else 'crystal'
                 for o in p.loot.values() if o.get('name','').lower() in {'locked chest','crystal chest'})
    needed={f'{kind} key' for kind in kinds if not getattr(p,'keys',{}).get(kind,0)}
    result = {c:o for c,o in p.loot.items() if not o.get('for_sale')
            and c not in deferred
            and not discarded(p,c,o)
             and (base_name(o.get('top_item',o)) in NAMES | needed or food(o.get('top_item',o)))}
    if not getattr(getattr(p, "profile", None), "full_exploration", True):
        try:
            from .simple_navigation import loot
        except ImportError:
            from simple_navigation import loot
        eligible, _ = loot(p, p.last_state)
        result = {c:o for c,o in result.items() if c in eligible}
    return result


def diagnostics(p,state,enemies=(),paths=None):
    """Report existing public-policy vetoes; never relax pickup admission."""
    pending=targets(p)
    report={'depth':state.get('depth'),'branch':state.get('branch',0),
            'hero_cell':state.get('hero',{}).get('cell'),'targets':[],
            'qualification':'Observed/cached public resources and current policy bookkeeping; no pickup or safe route inferred'}
    if state.get('status')!='ready' or state.get('modal') or not state.get('hero'):
        report['general_veto']='not a ready gameplay observation'
        return report
    paths=p.paths(state) if paths is None else paths
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    report['general_veto']=[label for flag,label in (
        (bool(enemies),'current enemies'),(bool(p.recent_threats),'remembered threats'),
        (bool(state.get('danger_cells')),'rendered warnings'),
        (any(b in buffs for b in ('burn','poison','bleed','paral','root','vertigo','blind')),'damaging or impaired condition'),
        (bool(p.inventory_pressure),'inventory pressure')) if flag]
    report['preparation_state']={
        'puzzle_probe_active':bool(getattr(p,'puzzle_probe',None)),
        'puzzle_hungry_frost':bool(getattr(p,'puzzle_hungry_frost',False)),
        'reserve_floor_puzzle_supplies':bool(getattr(p,'reserve_floor_puzzle_supplies',False)),
        'room_journey_active':bool(getattr(p,'room_journey',None)),
        'potion_stash_active':bool(getattr(p,'potion_stash',None)),
        'trap_payload_return_active':bool(getattr(p,'trap_payload_return',None)),
        'deferred_room_controllers':sorted(getattr(p,'deferred_room_controllers',set())),
        'puzzle_meal_attempted':(state['depth'],'puzzle-meal') in p.room_attempts}
    width=state['map']['width']
    def rejection(cell):
        tile=p.tiles.get(cell,{})
        reasons=[]
        if cell in p.blocked:reasons.append('blocked by prior movement bookkeeping')
        if p.failed_moves[cell]:reasons.append('failed movement recorded')
        if cell in p.room_blocked:reasons.append('room hazard/obligation barrier')
        if cell in p.neutral_actor_cells and cell not in p.friendly_passage_cells:reasons.append('neutral/friendly occupancy')
        if cell in getattr(p,'fire_buffer',set()):reasons.append('observed eternal-fire safety buffer')
        if cell in getattr(p,'fire_spread_buffer',set()):reasons.append('observed fire-spread safety buffer')
        if tile.get('trap'):reasons.append('observed trap')
        if tile.get('plant'):reasons.append('observed plant')
        if p.effects_block_movement(tile):reasons.append('observed/cached harmful effects')
        if tile.get('terrain') in {7,8,10,18,21,22,31,37,38}:reasons.append('transition, lock or hazard terrain')
        if not p.walkable(cell) and not reasons:reasons.append('other walkability or interaction veto')
        return {'cell':cell,'terrain':tile.get('terrain'),'reasons':reasons}
    for cell,obj in sorted(pending.items())[:8]:
        route=p.route(paths,cell) if cell in paths else []
        entry={'cell':cell,'public_name':base_name(obj.get('top_item',obj)),
               'priority_veto':(['remembered sleeping enemy guards optional food']
                                if guarded_food(p,cell,obj,width) else []),
               'currently_visible':bool(p.tiles.get(cell,{}).get('visible')),
               'reachable_in_current_paths':cell in paths,'target_rejections':rejection(cell),
               'route':route[:32],'route_steps':len(route)-1 if route else None,
               'route_omitted_steps':max(0,len(route)-32)}
        entry['route_rejections']=[rejection(c) for c in route[1:] if
            c in p.room_blocked or p.tiles[c].get('trap') or p.tiles[c].get('plant')
            or p.effects_block_movement(p.tiles[c])
            or p.tiles[c]['terrain'] in {7,8,10,18,21,22,31,37,38}][:8]
        if not route:
            try:
                from .survival_policy import TRANSITIONS,DOOR_KEYS
            except ImportError:
                from survival_policy import TRANSITIONS,DOOR_KEYS
            expandable=[c for c in paths if c==state['hero']['cell'] or (
                p.tiles[c]['terrain'] not in TRANSITIONS|DOOR_KEYS.keys()
                and not p.loot.get(c,{}).get('for_sale')
                and 'chest' not in p.loot.get(c,{}).get('name','').lower())]
            boundary={n for c in expandable for n in neighbors(c,width,state['map']['height'])
                      if n not in paths and n in p.tiles and p.tiles[n]['terrain'] in {1,2,3,5,6,7,8,9,10,11,14,15,18,19,20,21,22,29,30,31,32,37,38}}
            entry['nearest_reachable_component_boundaries']=[rejection(c) for c in
                sorted(boundary,key=lambda c:(distance(c,cell,width),c))[:8]]
        report['targets'].append(entry)
    report['omitted_targets']=max(0,len(pending)-8)
    return report


def clear_shocking_resource(p,state,resources,paths):
    """Press only a required, revealed plate with a fully bounded electrical footprint."""
    try:
        from .environment_tactics import payload
    except ImportError:
        from environment_tactics import payload
    if any(getattr(p,key,None) for key in ('trap_payload_return','puzzle_probe','potion_stash','room_journey')):return None
    item=payload(state)
    # Keep the existing reusable-container retrieval obligation; no expendable
    # projectile effects or replacement supply are assumed here.
    if not item or base_name(item) not in {'waterskin','dew vial','dew pouch'}:return None
    width,height=state['map']['width'],state['map']['height']
    pos=state['hero']['cell']
    for cell in sorted(resources):
        name=base_name(resources[cell].get('top_item',resources[cell]))
        if name not in NAMES and not name.endswith(' key'):continue
        tile=p.tiles.get(cell,{})
        if cell in paths or (state['depth'],cell) in p.trap_attempts \
                or tile.get('terrain')!=18 or tile.get('trap','').lower()!='shocking trap' \
                or not tile.get('visible') or not p.shot_clear(state,cell):continue
        # ShockingTrap seeds the non-solid 3x3; Electricity then spreads
        # recursively through cardinally connected water, not just radius one.
        area={c for c in {cell,*neighbors(cell,width,height)}
              if p.tiles.get(c,{}).get('terrain')!=4}
        queue=list(area);valid=True
        for c in queue:
            t=p.tiles.get(c,{})
            if not t.get('visible') or t.get('effects') or t.get('plant') \
                    or (c!=cell and t.get('trap') and t.get('terrain')!=19):
                valid=False;break
            for n in neighbors(c,width,height):
                if distance(c,n,width)!=1 or (c%width!=n%width and c//width!=n//width):continue
                boundary=p.tiles.get(n,{})
                if not boundary.get('visible'):
                    valid=False;break
                if boundary.get('terrain')==29 and n not in area:
                    area.add(n);queue.append(n)
            if not valid:break
        if not valid or pos in area or any(o['cell'] in area and not o.get('top_item')
                                         for o in state.get('objects',[])):continue
        try:
            from .payload_workflow import throw as throw_payload
        except ImportError:
            from payload_workflow import throw as throw_payload
        action=throw_payload(p,state,item,cell,
            'trap: remotely clear revealed shocking plate under required resource; reobserve electricity before retrieval',
            track=True)
        if action:
            p.trap_attempts.add((state['depth'],cell))
            return action
    return None


def clear_aquarium_resource(p,state):
    """A stationary, known missile only; no bank entry or defeat inferred."""
    if not any(h['profile']=='aquarium' for h in getattr(p,'piranha_habitats',{}).values()):
        return None
    if getattr(p,'hostile_champions',False) or p.inventory_pressure \
            or any(o.get('name','').lower()=='phantom piranha' for o in state.get('objects',[])):
        return None
    if any(getattr(p,key,None) for key in (
            'potion_stash','room_journey','puzzle_probe','trap_payload_return','drop_plan')):
        return None
    hero=state['hero'];pos=hero['cell']
    buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    tile=p.tiles.get(pos,{})
    if hero['hp']<.85*hero['max_hp'] or any(b in buffs for b in (
            'invisib','starving','ooze','frozen','chill','drowsy','sleep','levitat','magic immun')) \
            or p.unseen_damage_turns or pos in p.room_blocked or pos in p.blocked \
            or not tile.get('visible') or tile.get('terrain') not in {1,2,3,6,9,11,14,19,20,29} \
            or any(tile.get(k) for k in ('effects','plant','trap')):
        return None
    # Staff names include their visible melee enchantment before the imbued
    # wand's staff name. That prefix does not change the known ZAP effect.
    def missile_name(item):
        name=re.sub(r' [+-]\d+$','',base_name(item))
        return name in {'staff of magic missile','wand of magic missile'} \
            or name.endswith(' staff of magic missile')
    missile=next((i for i in state['inventory'] if missile_name(i)
        and i.get('identified') and i.get('curse_known') and not i.get('known_cursed')
        and (i.get('status') or '?').split('/')[0].isdigit()
        and int(i['status'].split('/')[0])>0 and 'ZAP' in i.get('actions',[])
        and p.item_action_allowed(i,'ZAP')),None)
    if not missile:return None
    try:
        from .hunger_budget import admits
    except ImportError:
        from hunger_budget import admits
    width,height=state['map']['width'],state['map']['height']
    for habitat in getattr(p,'piranha_habitats',{}).values():
        if habitat['profile']!='aquarium':continue
        water=habitat['water']
        border={n for c in water for n in neighbors(c,width,height)}-water
        # Close even diagonal water connections, and require fresh visibility
        # throughout. The ordinary fish cannot leave this observed water island.
        if any(not p.tiles.get(c,{}).get('visible') or not p.tiles[c].get('observed')
               for c in water|border) or any(p.tiles[c]['terrain']==29 for c in border) \
                or min(distance(pos,c,width) for c in water)<=1:
            continue
        # Keys are worth preparing before the matching lock is discovered.
        # Optional food/gold alone must not start an aquarium fight.
        if not any(c in water|border and c in p.room_blocked and not o.get('for_sale')
                   and (base_name(o.get('top_item',o)) in NAMES
                        or base_name(o.get('top_item',o)).endswith(' key'))
                   for c,o in p.loot.items()):
            continue
        for fish in sorted(state.get('objects',[]),key=lambda o:o['cell']):
            if fish.get('name','').lower()!='giant piranha' or fish['cell'] not in water \
                    or not p.shot_clear(state,fish['cell']) \
                    or not p.attack_kind_allowed(state,fish,'magic') \
                    or not p.target_allowed(missile,fish):
                continue
            if not admits(p,state,1):return None
            return p.use(missile,'ZAP',
                'loot: clear observed aquarium resource guard with stationary magic missile; reobserve before pickup',
                target=fish['cell'])
    return None


def choose(p,state,enemies):
    resources=targets(p)
    try:
        from .resource_reobservation import refresh
    except ImportError:
        from resource_reobservation import refresh
    refresh(p,state,resources)
    if resources and hasattr(p,'planner'):
        p.planner.report['priority_resource']=diagnostics(p,state,enemies)
    if enemies or p.recent_threats or state.get('danger_cells') or state.get('status')!='ready' or state.get('modal'):return None
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    if any(b in buffs for b in ('burn','poison','bleed','paral','root','vertigo','blind')):return None
    clearance=clear_aquarium_resource(p,state)
    if clearance:return clearance
    if not resources:return None
    if getattr(p,'trap_payload_return',None):
        try:
            from .environment_tactics import recover_trap_payload
        except ImportError:
            from environment_tactics import recover_trap_payload
        return recover_trap_payload(p,state,enemies)
    paths=p.paths(state);choices=[]
    for cell,obj in resources.items():
        # Current enemies veto this leaf even while sleeping. Keep optional
        # food beside a remembered sleeper from reversing admitted shopping
        # whenever that same enemy drops out of view. Retain the obligation;
        # fresh public absence clears sightings in update(), not a fake pickup.
        if guarded_food(p,cell,obj,state['map']['width']):continue
        if cell not in paths or p.failed_moves[cell] or cell in p.blocked:continue
        route=p.route(paths,cell)
        if any(c in p.room_blocked or p.tiles[c].get('trap') or p.tiles[c].get('plant')
               or p.effects_block_movement(p.tiles[c]) or p.tiles[c]['terrain'] in {7,8,10,18,21,22,31,37,38}
               for c in route[1:]):continue
        choices.append((len(route),cell))
    if not choices:
        # Mandatory loot preempts general preparation, including its post-fire
        # return controller. Delegate that unfinished transaction here too:
        # mapping or distant keyed-room work cannot resolve its cold entrance.
        try:
            from .barrier_followup import advance as finish_barrier
        except ImportError:
            from barrier_followup import advance as finish_barrier
        followup=finish_barrier(p,state,enemies,distance,neighbors) if getattr(p,'barrier_followup',None) else None
        if followup:return followup
        clearance=clear_shocking_resource(p,state,resources,paths)
        if clearance:return clearance
        # Preparation yields to this priority leaf. If pickup is not admitted,
        # allow the existing guarded puzzle-supply controller to make progress.
        try:
            from .puzzle_supplies import prepare_supplies
        except ImportError:
            from puzzle_supplies import prepare_supplies
        preparation=prepare_supplies(p,state,enemies,distance,neighbors)
        if preparation:return preparation
        try:
            from .resource_reobservation import choose as reobserve
        except ImportError:
            from resource_reobservation import choose as reobserve
        observation=reobserve(p,state,resources,enemies)
        if observation:return observation
        if any(cell not in paths and (base_name(obj.get('top_item',obj)) in NAMES
                                     or base_name(obj.get('top_item',obj)).endswith(' key'))
               for cell,obj in resources.items()):
            # General preparation yields to this leaf while required loot is
            # pending. Unknown-supply preparation deliberately skips a known
            # frost potion, so also admit the existing guarded extinguisher.
            # Matching keys are mandatory targets too; do not strand their
            # known frost supply behind the upgrade/strength-only branch.
            # This neither crosses the fire nor receipts the blocked pickup.
            if not (p.puzzle_probe or p.potion_stash or p.room_journey):
                try:
                    from .room_tactics import extinguish
                except ImportError:
                    from room_tactics import extinguish
                preparation=extinguish(p,state,enemies,distance)
                if preparation:return preparation
        if any(cell not in paths and base_name(obj.get('top_item',obj)) in NAMES
               for cell,obj in resources.items()):
            # Awareness may reveal a reward without its connecting passage.
            # Mapping discovers routes; it is not a pickup or hazard permit.
            try:
                from .runestone_tactics import prepare_mapping
            except ImportError:
                from runestone_tactics import prepare_mapping
            return prepare_mapping(p,state,required=True)
        return None
    _,cell=min(choices)
    if p.inventory_pressure:
        try:
            from .inventory_tactics import choose as cleanup
            from .pickup_priority import bag
        except ImportError:
            from inventory_tactics import choose as cleanup
            from pickup_priority import bag
        incoming=resources[cell].get('top_item',resources[cell])
        refused=p.inventory_pressure.get('item')
        if refused and bag(state,refused)!=bag(state,incoming):
            # A full specialist pouch does not prove the food backpack is full.
            return p.toward(state,cell,'loot: prioritize observed pickup in a different bag',paths,intent=Intent.LOOT)
        room=cleanup(p,state,enemies,incoming_item=incoming)
        if room:return room
        return None  # Do not repeatedly click a known full-pack pickup.
    name=base_name(resources[cell].get('top_item',resources[cell]))
    reason='loot: prioritize observed permanent upgrade/strength resource' if name in NAMES \
        else 'loot: prioritize observed matching key' if 'key' in name else 'loot: prioritize observed food pickup'
    return p.toward(state,cell,reason,paths,intent=Intent.LOOT)
