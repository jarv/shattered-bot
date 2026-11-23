"""Sad Ghost only: public dialogue/rewards and three separate enemy tactics."""
try:
    from .combat_items import stats,physical_score
    from .consumable_tactics import base_name
    from .policy_decision import Intent
except ImportError:
    from combat_items import stats,physical_score
    from consumable_tactics import base_name
    from policy_decision import Intent


TARGETS = {"fetid rat", "gnoll trickster", "great crab"}


def map_explored(p,state):
    """Finish public exploration before spawning a quest foe, not a secret-map claim."""
    paths=p.paths(state)
    report=p.exploration_report(state,paths)
    try:
        from .policy_geometry import neighbors
    except ImportError:
        from policy_geometry import neighbors
    skipped=set(report['skipped_special_cells'])
    # Exhausted route attempts are not proof that fog/mapped-only tiles were seen.
    frontier=[c for c in paths if c not in skipped and p.tiles[c]['terrain'] in
              {1,2,3,5,6,9,11,14,15,19,20,29,30} and (
                  p.tiles[c].get('observed') is False or
                  any(n not in p.tiles for n in neighbors(c,state['map']['width'],state['map']['height'])))]
    locks=[c for c in report['unresolved_doors'] if c not in p.resolved_crystal_alternatives]
    pending={'frontiers':frontier,'unopened_doors':report['unopened_doors'],
             'unreachable_known_floor':report['unreachable_known_floor'],'unresolved_locks':locks}
    ready=not any(pending.values())
    p.planner.report['ghost_exploration']={'ready':ready,**pending,
        'qualification':'Observed reachable map and known locks; deferred hazardous areas/secrets are not certified clear'}
    if not ready:
        p.planner.report['ghost_readiness']={'status':'deferred','reason':'Explore the floor before starting Sad Ghost quest'}
    return ready


def observe_quest(p, state):
    text = " ".join(state.get("ui", {}).get("texts", [])).replace("_", "").lower()
    ghosts = [o for o in state.get("objects",[]) if o["name"].lower()=="sad ghost"]
    if ghosts:
        p.ghost_quest.update(last_cell=ghosts[0]["cell"],last_depth=state["depth"])
        if 'origin_cell' not in p.ghost_quest:
            try:
                from .room_loot import room_region
            except ImportError:
                from room_loot import room_region
            cell=ghosts[0]['cell']
            region=room_region(p,dict(state,hero=dict(state['hero'],cell=cell)))
            p.ghost_quest.update(origin_cell=cell,origin_depth=state['depth'],
                                 origin_area=sorted(region or {cell}))
    if p.ghost_quest.get("stage")=="active" and any(o["name"].lower()==p.ghost_quest.get("target") for o in state.get("objects",[])):
        p.ghost_quest.update(target_seen=True,reminder_queried=False)
    if p.ghost_quest.get("stage") == "active" and "thank you... come find me" in text:
        p.ghost_quest["stage"] = "reward"
        p.great_crab_plan=None
        p.ghost_quest["travel"] = 0
        p.ghost_quest.pop('return_goal',None)
        p.ghost_quest['return_views']=[]
    if p.ghost_quest.get("stage") in {"claiming","collect_dropped"}:
        # A click is not proof of collection. Confirm the public pickup/farewell
        # or the actual selected item appearing in own inventory.
        reward = p.ghost_quest.get("selected", "")
        count = sum(i.get("quantity",1) for i in state.get("inventory",[]) if reward and reward in base_name(i))
        carried = count > p.ghost_quest.get("count_before",0)
        if carried and ("farewell, adventurer" in text or "you now have" in text or p.ghost_quest["stage"]=="collect_dropped"):
            p.ghost_quest["stage"] = "done"
        elif "farewell, adventurer" in text:
            p.ghost_quest["stage"] = "collect_dropped"


def visit_ghost(p, state, enemies, distance, neighbors):
    configured=getattr(p,'unit_strategies_enabled',False)
    if configured:
        buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
        if p.recent_threats or p.ranged_plan \
                or p.escape_commitment and p.ghost_quest.get('stage')!='reward' \
                or state['hero']['hp']<.5*state['hero']['max_hp'] \
                or any(b in buffs for b in ('poison','burning','bleed')):
            return None  # A momentarily unseen quest foe is not a completed/peaceful encounter.
    if not enemies and p.ghost_quest.get("stage")=="collect_dropped":
        paths=p.paths(state)
        reward=p.ghost_quest.get("selected","")
        cells=[c for c,o in p.loot.items() if c in paths and reward and reward in base_name(o.get("top_item",o))]
        if cells:
            return p.toward(state,min(cells,key=lambda c:len(p.route(paths,c))),"quest: pick up observed dropped Sad Ghost reward",paths,
                            intent=Intent.LOOT if configured else Intent.OTHER)
    query = p.ghost_quest.get("stage")=="active" and p.ghost_quest.get("target_seen") and not p.ghost_quest.get("reminder_queried")
    if enemies or state["depth"] not in {2,3,4} or p.ghost_quest.get("stage") in {"done","claiming","collect_dropped"} \
            or p.ghost_quest.get("stage")=="active" and not query:
        return None
    hero = state["hero"]
    reward = p.ghost_quest.get("stage") == "reward"
    returning = reward or query
    if (not returning and hero["hp"] < 0.8*hero["max_hp"]) or state.get("danger_cells"):
        return None
    # Starting dialogue spawns a foe. Prepare before speaking, not afterwards.
    if not returning:
        if not map_explored(p,state):
            return None
        charges = sum(int(i["status"].split("/")[0]) for i in p.charged_magic(state)
                      if (i.get("status") or "?").split("/")[0].isdigit())
        if charges < 3:
            p.planner.report['ghost_readiness']={'status':'deferred','reason':'Need three observed magic charges before spawning quest foe','known_charges':charges}
            return None
    ghosts = [o for o in state.get("objects", []) if o["name"].lower() == "sad ghost"]
    if configured and reward:
        return return_for_reward(p,state,ghosts,distance,neighbors)
    if not ghosts and (returning or configured) and p.ghost_quest.get("last_depth")==state["depth"]:
        # A last-seen position is an approach prior, not a live NPC. Do not
        # circle its neighbors after reaching interaction range and observing
        # it empty. A more distant remembered area can still be approached.
        if distance(hero["cell"],p.ghost_quest["last_cell"],state["map"]["width"])<=1 \
                and any(t.get('cell')==p.ghost_quest["last_cell"] and t.get('visible')
               for t in state.get('map',{}).get('cells',[])):
            return None
        ghosts = [{"name":"sad ghost","cell":p.ghost_quest["last_cell"],"remembered":True}]
    if not ghosts or p.ghost_quest.get("travel",0) >= 60:
        return None
    target = min(ghosts,key=lambda o: distance(hero["cell"],o["cell"],state["map"]["width"]))
    if not target.get("remembered") and distance(hero["cell"],target["cell"],state["map"]["width"]) == 1:
        if query:
            p.ghost_quest["reminder_queried"]=True
        p.ghost_menu = {"stage":"dialogue","steps":0}
        return p.cell(target["cell"],"quest: collect pending Sad Ghost reward" if reward else
                      "quest: ask Sad Ghost for public completion evidence" if query else "quest: speak to observed Sad Ghost with prepared health and magic")
    paths = p.paths(state)
    banks = [n for n in neighbors(target["cell"],state["map"]["width"],state["map"]["height"])
              if n in paths and n!=hero["cell"] and len(p.route(paths,n)) <= 24]
    if banks:
        p.ghost_quest["travel"] = p.ghost_quest.get("travel",0)+1
        return p.toward(state,min(banks,key=lambda c:len(p.route(paths,c))),
                        'quest: approach last observed Sad Ghost' if target.get('remembered') else 'quest: approach visible Sad Ghost',
                        paths,intent=Intent.REPOSITION if configured else Intent.OTHER)
    return None


def return_for_reward(p,state,ghosts,distance,neighbors):
    """Reobserve first encounter area instead of orbiting an absent old cell."""
    q=p.ghost_quest;hero=state['hero'];pos=hero['cell'];width,height=state['map']['width'],state['map']['height']
    if q.get('origin_depth',q.get('last_depth'))!=state['depth']:return None
    if q.get('travel',0)>=100:
        p.stop_gameplay('Sad Ghost reward still uncollected after bounded return/search; cannot descend with reward pending')
    if ghosts:
        target=min(ghosts,key=lambda o:distance(pos,o['cell'],width))
        if distance(pos,target['cell'],width)==1:
            p.ghost_menu={'stage':'dialogue','steps':0}
            return p.cell(target['cell'],'quest: collect pending Sad Ghost reward')
        targets=list(neighbors(target['cell'],width,height))
        q.pop('return_goal',None)
    else:
        origin=q.get('origin_cell',q.get('last_cell'))
        if origin is None:return None
        area=set(q.get('origin_area',[origin]))
        # Only observed terrain is a search destination. The first encounter
        # region is a return prior, never a claim that an unseen NPC occupies it.
        area.update(n for c in list(area) for n in neighbors(c,width,height)
                    if p.tiles.get(n,{}).get('terrain') in {1,2,3,6,9,11,14,15,19,20,29,30})
        views=set(q.get('return_views',[]))
        if q.get('return_goal')==pos:
            views.add(pos);q['return_views']=sorted(views);q.pop('return_goal',None)
        paths=p.paths(state)
        goal=q.get('return_goal')
        if goal in paths and goal!=pos:targets=[goal]
        else:
            targets=[c for c in area if c!=pos and c not in views and c in paths
                     and p.tiles[c].get('terrain') not in {5,8,22} and not p.tiles[c].get('plant')
                     and (not p.tiles[c].get('trap') or p.tiles[c].get('terrain')==19)
                     and not p.effects_block_movement(p.tiles[c])]
            if not targets:
                p.stop_gameplay('Sad Ghost reward pending: first encounter area searched without a visible ghost; no collection or descent inferred')
            # Reach the remembered region, then inspect different nearby views;
            # do not select alternating neighbors of a stale NPC coordinate.
            target=min(targets,key=lambda c:(distance(c,origin,width),len(p.route(paths,c)),c))
            q['return_goal']=target;targets=[target]
    paths=p.paths(state)
    # An escape commitment protects directed retreat edges, not every onward
    # route. Keep that memory intact and reject reversal anywhere in the return.
    protected=set((p.escape_commitment or {}).get('edges',[]))
    banks=[c for c in targets if c in paths and c!=pos and len(p.route(paths,c))<=80
           and all((b,a) not in protected for a,b in
                   zip(p.route(paths,c),p.route(paths,c)[1:]))
           # Triggered traps retain their public type label. As in walkable(),
           # only terrain 19 proves that label is inactive; effects still veto.
           and all((not p.tiles[n].get('trap') or p.tiles[n].get('terrain')==19)
                   and not p.tiles[n].get('plant')
                   and not p.effects_block_movement(p.tiles[n]) for n in p.route(paths,c)[1:])]
    if not banks:return None
    bank=min(banks,key=lambda c:len(p.route(paths,c)));q['travel']=q.get('travel',0)+1
    p.planner.report['ghost_return']={'origin':q.get('origin_cell'),'goal':bank,
        'ghost_visible':bool(ghosts),'reward_collected':False}
    return p.toward(state,bank,'quest: return to first Sad Ghost encounter area and reobserve reward giver'
                    if not ghosts else 'quest: approach visible Sad Ghost for pending reward',paths,intent=Intent.REPOSITION)


def prepare_ghost(p,state,enemies):
    """Small dedicated safe readiness budget; never spawn a quest foe while unprepared."""
    if not getattr(p,'unit_strategies_enabled',False) or state['depth'] not in {2,3,4} \
            or p.ghost_quest.get('last_depth')!=state['depth'] or p.ghost_quest.get('stage') not in {None,'new'} \
             or enemies or p.recent_threats or p.ranged_plan or p.escape_commitment or state.get('danger_cells'):return None
    if not map_explored(p,state):return None
    hero=state['hero'];buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    charges=sum(int(i['status'].split('/')[0]) for i in p.charged_magic(state)
                if (i.get('status') or '?').split('/')[0].isdigit())
    need=hero['hp']<.8*hero['max_hp'] or charges<3
    if not need:return None
    reason='Need 80% health and three observed magic charges before quest dialogue'
    p.planner.report['ghost_readiness']={'status':'deferred','reason':reason,'known_charges':charges}
    if hero['hp']<.5*hero['max_hp'] or any(b in buffs for b in ('hungry','starving','burn','poison','bleed','ooze','locked')):return None
    pos=hero['cell'];tile=p.tiles.get(pos,{})
    if not p.walkable(pos) or tile.get('effects') or tile.get('plant') or tile.get('trap'):return None
    # Sleeping is not a certificate that a nearby enemy cannot awaken.
    if any(o.get('sleeping') for o in state.get('objects',[])):return None
    if p.ghost_quest.get('prepare_depth')!=state['depth']:
        p.ghost_quest.update(prepare_depth=state['depth'],prepare_inputs=0)
    if p.ghost_quest['prepare_inputs']>=24:return None
    p.ghost_quest['prepare_inputs']+=1
    p.planner.report['ghost_readiness']['status']='bounded safe readiness wait'
    return p.decision({'type':'wait'},'quest: bounded safe health/magic preparation before Sad Ghost',intent=Intent.RECOVER)


def seek_quest_foe(p,state,enemies):
    """Bounded ordinary-floor reconnaissance after accepting the Ghost's request."""
    quest=p.ghost_quest
    if quest.get('stage')!='active' or quest.get('depth')!=state['depth'] \
            or quest.get('target_seen') or enemies or p.recent_threats \
            or state.get('danger_cells') or p.room_journey or p.potion_stash:
        return None
    hero=state['hero']
    buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    if hero['hp']<.8*hero['max_hp'] or any(
            b in buffs for b in ('starv','burn','poison','bleed','blind','vertigo','paral','root')):
        return None
    paths=p.paths(state);pos=hero['cell']
    visited=quest.setdefault('hunt_visited',[])
    goal=quest.get('hunt_goal')
    if goal==pos:
        if goal not in visited:visited.append(goal)
        quest['hunt_goal']=goal=None
    if quest.get('hunt_steps',0)>=64:
        p.planner.report['ghost_hunt']={'status':'exhausted','reason':'64 reconnaissance inputs; quest unfinished'}
        return None
    try:
        from .hunger_budget import admits,travel_cost
    except ImportError:
        from hunger_budget import admits,travel_cost
    def safe(c):
        route=p.route(paths,c)
        return 2<=len(route)<=21 and admits(p,state,2*travel_cost(state,p,route)+12) \
            and all(p.tiles[n].get('observed') and p.tiles[n]['terrain'] in {1,3,5,6,9,11,14,20,29}
                    and n not in p.loot and not any(p.tiles[n].get(k) for k in ('trap','plant','effects'))
                    for n in route[1:])
    candidates=[c for c in paths if c not in visited and safe(c)]
    if not candidates:
        p.planner.report['ghost_hunt']={'status':'deferred','reason':'No safely funded ordinary-floor vantage; quest unfinished'}
        return None
    if goal not in candidates:
        goal=max(candidates,key=lambda c:(len(p.route(paths,c)), -c))
        quest['hunt_goal']=goal
    quest['hunt_steps']=quest.get('hunt_steps',0)+1
    return p.toward(state,goal,'quest: seek accepted Sad Ghost foe on observed ordinary floor',paths,intent=Intent.EXPLORE)


def quest_menu(p,state):
    plan=p.ghost_menu
    plan["steps"]+=1
    texts=state["ui"].get("texts",[])
    text=" ".join(texts).replace("_","").lower()
    buttons=state["ui"]["buttons"]
    def click(button,reason):
        return p.decision({"type":"button","id":button["id"]},reason)
    if plan["steps"] > 12:
        p.ghost_menu=None
        return p.decision({"type":"back"},"quest: cancel bounded reward workflow")
    if plan["stage"] == "dialogue":
        if "defeated" in text and any(name in text for name in TARGETS):
            p.ghost_quest["stage"]="reward"
            options=[b for b in buttons if b.get("label") and b["label"].lower() not in {"close","back"}]
            if len(options) == 2:
                plan.update(stage="preview",options=[b["label"] for b in options],index=0,scores=[])
                return click(options[0],"quest: inspect first public reward before choosing")
        else:
            name=next((n for n in TARGETS if n in text),None)
            if name and ("slay" in text or "help me" in text):
                p.ghost_quest.update(stage="active",target=name,depth=state["depth"])
                p.ghost_menu=None
                return p.decision({"type":"back"},f"quest: accept observed {name} request")
    elif plan["stage"] == "preview":
        value=stats({"description":text})
        strength=state["hero"]["strength"]
        score=-100
        if value:
            kind,damage,requirement=value
            if kind=='armor':
                score=100+damage-5*max(0,requirement-strength)
            elif kind=='melee':
                staff=next((i for i in state['inventory'] if 'IMBUE' in i.get('actions',[])),None)
                baseline=physical_score(staff,strength) if staff else 0
                candidate=physical_score({'name':plan['options'][plan['index']], 'description':text},strength)
                if candidate>baseline:score=candidate-baseline
        plan["scores"].append(score)
        cancel=next((b for b in buttons if b["label"].lower()=="cancel"),None)
        if cancel:
            plan["stage"]="next"
            return click(cancel,"quest: compare only rendered reward inspection stats")
    elif plan["stage"] == "next":
        plan["index"]+=1
        if plan["index"] < len(plan["options"]):
            plan["stage"]="preview"
            label=plan["options"][plan["index"]]
        else:
            if max(plan["scores"]) <= -100:
                p.ghost_menu=None
                return p.decision({"type":"back"},"quest: defer rewards whose inspected stats could not be parsed")
            plan["stage"]="confirm"
            label=plan["options"][max(range(len(plan["scores"])),key=lambda i:plan["scores"][i])]
        button=next((b for b in buttons if b["label"]==label),None)
        if button:
            plan["selected"]=label.lower()
            return click(button,"quest: select inspected reward for current Mage loadout")
    elif plan["stage"] == "confirm":
        confirm=next((b for b in buttons if b["label"].lower()=="confirm"),None)
        if confirm and plan["selected"] in text:
            selected=base_name({"name":plan["selected"]})
            count=sum(i.get("quantity",1) for i in state["inventory"] if selected in base_name(i))
            p.ghost_quest.update(stage="claiming",selected=selected,count_before=count)
            p.ghost_menu=None
            return click(confirm,"quest: confirm publicly inspected Sad Ghost reward")
    p.ghost_menu=None
    return p.decision({"type":"back"},"quest: dismiss unrecognized ghost dialogue without guessing rewards")


def quest_combat(p,state,enemies,distance,neighbors):
    foe=next((e for e in enemies if e["name"].lower() in TARGETS),None)
    if not foe:
        return None
    name=foe["name"].lower()
    hero=state["hero"]; pos=hero["cell"]; width=state["map"]["width"]
    buffs=" ".join(b["name"].lower() for b in hero.get("buffs",[]))
    if name == "great crab":
        try:
            from .great_crab_tactics import choose
        except ImportError:
            from great_crab_tactics import choose
        return choose(p,state,enemies)
    if name == "gnoll trickster":
        try:
            from .ranged_tactics import choose
        except ImportError:
            from ranged_tactics import choose
        if getattr(p,'unit_strategies_enabled',False):
            return choose(p,state,enemies)
        attack=p.best_attack(state,foe,allowed_kinds={"magic","thrown"})
        if attack:
            attack.reason="quest: gnoll trickster prioritize ranged damage"
            return attack
        if distance(pos,foe["cell"],width)==1:
            escape=p.retreat(state,enemies)
            if escape:return escape
            p.stop_tactical("quest-combat","Gnoll Trickster: no ranged answer or retreat; refusing melee")
        # Break its dart line rather than exchange shots or chase across open ground.
        paths=p.paths(state,{e["cell"] for e in enemies})
        cover=[c for c in paths if c!=pos and len(p.route(paths,c))<=4
               and not p.enemy_can_see(state,foe,c)]
        if cover and p.enemy_can_see(state,foe,pos):
            return p.toward(state,min(cover,key=lambda c:len(p.route(paths,c))),"quest: break trickster dart line and lure into close combat",paths)
        if not p.enemy_can_see(state,foe,pos):
            banks=[c for c in paths if c!=pos and len(p.route(paths,c))<=6
                   and not p.enemy_can_see(state,foe,c)
                   and distance(c,foe["cell"],width)<distance(pos,foe["cell"],width)]
            if banks:
                return p.toward(state,min(banks,key=lambda c:(distance(c,foe["cell"],width),len(p.route(paths,c)))),
                    "quest: approach trickster behind observed cover",paths)
        action=p.best_attack(state,foe)
        if action:
            return action
        p.stop_tactical("quest-combat","Gnoll Trickster: no safe cover or usable ranged answer; refusing melee chase")
    # Fetid rat: ranged damage avoids its melee ooze and local stench.
    if distance(pos,foe["cell"],width)<=1 and p.tiles[pos]["terrain"]!=29:
        banks=[c for c in neighbors(pos,width,state["map"]["height"]) if p.walkable(c,{e["cell"] for e in enemies})
               and distance(c,foe["cell"],width)>=2 and c not in p.loot]
        if banks:
            return p.cell(min(banks,key=lambda c:p.tiles[c]["terrain"]!=29),"quest: fetid rat keep stench distance and favor water")
    magic=[i for i in p.charged_magic(state) if p.target_allowed(i,foe)]
    if magic and p.shot_clear(state,foe["cell"]):
        return p.use(magic[0],"ZAP","quest: fetid rat ranged damage outside corrosive melee",target=foe["cell"])
    escape=p.retreat(state,enemies)
    if escape:
        return escape
    p.stop_tactical("quest-combat","Fetid rat: no ranged charge or safe stench-free retreat")
