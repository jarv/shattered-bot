"""Doorway-first ordinary combat, from public positions and observed geometry."""
try:
    from .challenge_combat import exposure, champion, enemy_line, reach
    from .consumable_tactics import choose_consumable, base_name
    from .policy_decision import Intent
    from .environment_tactics import trigger_trap
except ImportError:
    from challenge_combat import exposure, champion, enemy_line, reach
    from consumable_tactics import choose_consumable, base_name
    from policy_decision import Intent
    from environment_tactics import trigger_trap


def unexplored_door(p,state,enemies):
    """Approach/open/cross an observed door, never issue a move into an unseen tile."""
    width,height=state["map"]["width"],state["map"]["height"]
    paths=p.paths(state,{e["cell"] for e in enemies})
    options=[]
    for door in paths:
        terrain=p.tiles[door]["terrain"]
        key=(state["depth"],"doorway-scout",door,terrain)
        if terrain not in {5,6} or key in p.room_attempts or p.ambush_attempts[door]>=p.door_ambush_limit():
            continue
        route=p.route(paths,door)
        if not 2<=len(route)<=9:
            continue
        x,y=door%width,door//width
        unknown_far=any(0<=x+dx<width and 0<=y+dy<height
                        and (y+dy)*width+x+dx not in p.tiles
                        and (y-dy)*width+x-dx in paths
                        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)))
        if not unknown_far or any(p.tiles[c]["terrain"] in {7,8,21,22,31,37,38}
                or c in p.loot or p.tiles[c].get("plant") for c in route[1:]):
            continue
        options.append((len(route),door,route[1],key))
    if options:
        _,door,step,key=min(options)
        return p.cell(step,"doorway: approach observed door with unexplored far side; reobserve before hiding",intent=Intent.RETREAT),key if step==door else None
    return None,None


def hold_doorway(p,state,enemies,distance,neighbors,line_clear):
    """Keep the safe side of an established choke until the observed wave ends."""
    hold=p.doorway_hold
    if not hold:
        return None
    hero=state["hero"]
    pos,width=hero["cell"],state["map"]["width"]
    active=[e for e in enemies if not e.get("sleeping")]
    excluded={"fetid rat","gnoll trickster","great crab","demon spawner","crystal mimic"}
    if hold["depth"]!=state["depth"] or pos!=hold["hide"] or state.get("danger_cells") \
            or state.get("boss_health_text") or any(e["name"].lower() in p.boss_strategies
                or e["name"].lower() in excluded or "fist" in e["name"].lower() for e in active):
        p.doorway_hold=None
        return None
    current=exposure(p,state,active,pos,distance,line_clear)
    flanked=any(e["cell"]!=hold["door"] and distance(pos,e["cell"],width)<=reach(e) for e in active)
    extended=any(reach(e)>1 and distance(pos,e['cell'],width)<=reach(e) for e in active)
    if flanked or current["ranged"] or extended:
        p.doorway_hold=None
        p.planner.report["doorway_hold"]={"status":"abandon unsafe, extended-reach or flanked choke"}
        return None
    entry=next((e for e in active if e['cell']==hold['door']),None)
    if getattr(p,'unit_strategies_enabled',False) and entry and p.previous_position==hold['door'] \
            and hold['inputs']<40 and hero['hp']>=.5*hero['max_hp'] \
            and entry['name'].lower()!='swarm of flies':
        hold['inputs']+=1;hold['quiet']=hold['waits']=0
        return p.cell(hold['door'],'doorway: surprise attack attempt on observed entry after retreat behind choke')
    if hold["inputs"]>=40:
        p.stop_tactical("doorway-budget","Doorway hold: observed encounter unresolved after bounded combat budget")
    if active and (hero["hp"]<0.5*hero["max_hp"] or not p.charged_magic(state)):
        emergency=choose_consumable(p,state,enemies,distance,neighbors)
        if emergency:
            used=next((i for i in state["inventory"] if i.get("id")==emergency.action.get("id")),{})
            recharge=base_name(used)=="scroll of recharging" if used else False
            if not recharge or hero["hp"]>=0.35*hero["max_hp"]:
                if not recharge:p.doorway_hold=None
                return emergency
    trap=trigger_trap(p,state,enemies,distance,neighbors,line_clear)
    if trap:
        hold["inputs"]+=1
        return trap
    target=next((e for e in active if e["cell"]==hold["door"]),None)
    if target:
        evasive_empty=target["name"].lower()=="sewer snake" and not p.charged_magic(state)
        if evasive_empty and not target.get("health_bar") and hold.get("unconfirmed_snake_strikes",0)>=2:
            p.doorway_hold=p.ambush_plan=None
            p.planner.report["doorway_hold"]={"status":"two unconfirmed empty-staff snake strikes; replan instead of miss loop"}
            return None
        if hero["hp"]<0.35*hero["max_hp"] or evasive_empty:
            escape=p.retreat(state,enemies)
            if escape and escape.action.get("cell") not in p.loot \
                    and not exposure(p,state,active,escape.action["cell"],distance,line_clear)["exposure"]:
                if evasive_empty and len(active)==1 and not champion(target) \
                        and hero["hp"]>=0.45*hero["max_hp"] and p.snake_door_resets[hold["door"]]<2:
                    p.snake_door_resets[hold["door"]]+=1
                    p.snake_door_reset={"depth":state["depth"],"door":hold["door"],
                                        "hp":hero["hp"],"steps":0,"waits":0}
                    escape.reason="snake: draw pursuer off doorway before returning for renewed surprise"
                p.doorway_hold=p.ambush_plan=None
                if not p.snake_door_reset:
                    escape.reason="doorway: leave exhausted unsafe hold on verified unexposed ground"
                return escape
        if hero["hp"]<0.35*hero["max_hp"]:
            p.stop_tactical("doorway-pressure","Doorway hold: critical HP without a verified safe finishing attack")
        if champion(target)=="blazing" and p.tiles[pos]["terrain"]!=29:
            p.doorway_hold=None
            return None
        reserve=target["name"].lower() in {"marsupial rat","albino rat"} and not champion(target) \
            and hero["hp"]>=0.65*hero["max_hp"]
        # A choke limits approach slots, not armor, death blasts or evasion.
        # Preserve the species controller's attack preference after the first
        # surprise strike; ordinary melee scoring ignores wraith evasion.
        action=None
        if getattr(p,'unit_strategies_enabled',False):
            strategy=p.unit_strategies.profile(target).strategy
            if strategy=='wraith':
                action=p.best_attack(state,target,allowed_kinds={'magic'})
            # Linked skeletons dispatch as summoners, not undead. When one
            # visibly has adrenaline, use the existing skeleton ranged
            # preference rather than trading ordinary melee into fast pressure.
            elif strategy=='undead' or (target['name'].lower()=="necromancer's skeleton"
                                        and 'adrenaline' in target.get('status_icons',[])):
                action=p.best_attack(state,target,allowed_kinds={'magic','thrown'})
        if not action:
            action=p.best_attack(state,target,reserve=reserve,reserve_magic=reserve)
        if action:
            if evasive_empty and action.action.get("type")=="cell" and not target.get("health_bar"):
                hold["unconfirmed_snake_strikes"]=hold.get("unconfirmed_snake_strikes",0)+1
            elif target.get("health_bar"):
                hold["unconfirmed_snake_strikes"]=0
            hold.update(quiet=0,waits=0,inputs=hold["inputs"]+1)
            action.reason="doorway: hold established choke and fight doorway enemy"
            p.planner.report["doorway_hold"]={"status":"fight from safe side","door":hold["door"]}
            return action
    if current["exposure"]:
        p.doorway_hold=None
        return None
    # A lone summoner is not an ordinary pursuer: waiting for it to enter
    # lets it replace the minion just defeated at this choke. Intercept from
    # the established bank only with an already admitted stationary attack.
    # Never use this branch to approach, attack a memory, or break protection.
    buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    if getattr(p,'unit_strategies_enabled',False) and len(active)==1 \
            and active[0]['name'].lower() in {'necromancer','spectral necromancer'} \
            and p.tiles.get(active[0]['cell'],{}).get('visible') \
            and not any(b in buffs for b in ('invisib','cloaked')):
        attack=p.best_attack(state,active[0],allowed_kinds={'magic','thrown'})
        if attack:
            hold.update(quiet=0,waits=0,inputs=hold['inputs']+1)
            attack.reason='doorway: intercept visible summoner from established choke'
            return attack
    if getattr(p,'unit_strategies_enabled',False) and (active or p.seed_plan):
        try:
            from .seed_strategies import choose as choose_seed_setup
        except ImportError:
            from seed_strategies import choose as choose_seed_setup
        setup=choose_seed_setup(p,state,enemies)
        if setup:
            hold['inputs']+=1
            return setup
    sleepers=[e for e in enemies if e.get("sleeping")]
    if not active and sleepers:
        for enemy in sleepers:
            if hero["hp"]>=0.8*hero["max_hp"] and p.shot_clear(state,enemy["cell"]):
                action=p.best_attack(state,enemy)
                if action and action.action.get("action") in {"ZAP","THROW"}:
                    hold["inputs"]+=1
                    action.reason="doorway: draw observed sleeper while retaining established choke"
                    return action
        p.stop_tactical("doorway-sleeper","Doorway hold: observed sleeping enemy cannot be safely drawn to the choke")
    if active:
        hold["quiet"]=0
        hold["waits"]+=1
        if hold["waits"]>8:
            p.stop_tactical("doorway-stall","Doorway hold: observed pursuers did not enter within bounded lure wait; encounter unresolved")
    else:
        hold["quiet"]+=1
        if hold["quiet"]>3:
            p.doorway_hold=None
            p.planner.report["doorway_hold"]={"status":"observed wave quiet; resume room sweep, not unseen-room certification"}
            return None
    hold["inputs"]+=1
    p.planner.report["doorway_hold"]={"status":"wait safely at established choke","door":hold["door"]}
    return p.decision({"type":"wait"},"doorway: hold choke for remaining observed pursuers")


def reset_snake_door(p,state,enemies,distance,neighbors,line_clear):
    """Draw off the door, return, hide, then let ordinary doorway interception act."""
    plan=p.snake_door_reset
    if not plan:
        return None
    hero=state["hero"]
    pos,width,height=hero["cell"],state["map"]["width"],state["map"]["height"]
    active=[e for e in enemies if not e.get("sleeping")]
    plan["steps"]+=1
    if plan["depth"]!=state["depth"] or plan["steps"]>8 or plan["hp"]-hero["hp"]>3 \
            or hero["hp"]<0.45*hero["max_hp"] or state.get("danger_cells") \
            or p.tiles.get(plan["door"],{}).get("terrain") not in {5,6} \
            or any(e["name"].lower()!="sewer snake" or champion(e) for e in active) or len(active)>1:
        p.snake_door_reset=None
        return None
    if not active or active[0]["cell"]==plan["door"]:
        plan["waits"]+=1
        if plan["waits"]<=2:
            return p.decision({"type":"wait"},"snake: bounded wait for observed pursuer to leave doorway")
        p.snake_door_reset=None
        return None
    snake=active[0]
    if p.charged_magic(state):
        p.snake_door_reset=None
        return None
    door=plan["door"]
    if pos!=door and distance(snake["cell"],door,width)<=1:
        draws=[c for c in neighbors(pos,width,height) if p.walkable(c,{snake["cell"]})
               and c not in p.loot and p.tiles[c]["terrain"] not in {5,7,8,22,37}
               and distance(c,snake["cell"],width)>1 and distance(c,door,width)>distance(pos,door,width)]
        if draws and plan.get("draw_steps",0)<2:
            plan["draw_steps"]=plan.get("draw_steps",0)+1
            return p.cell(max(draws,key=lambda c:distance(c,door,width)),
                          "snake: draw farther off door before safe return",intent=Intent.RETREAT)
        p.snake_door_reset=None
        return None
    # Going straight back beside the snake merely trades another hit. Route
    # around its observed reach; the cleared door itself must be outside it.
    occupied={c for c in p.tiles if distance(c,snake["cell"],width)<=1}
    paths=p.paths(state,occupied)
    route_limit=7
    if door not in paths or len(p.route(paths,door))>route_limit:
        p.snake_door_reset=None
        return None
    if pos==door:
        closed=dict(p.tiles)
        closed[door]={"terrain":5}
        hides=[c for c in neighbors(door,width,height) if p.walkable(c,{e["cell"] for e in enemies})
               and c not in p.loot and not p.tiles[c].get("plant")
               and p.tiles[c]["terrain"] not in {5,7,8,22,37}
               and not line_clear(snake["cell"],c,width,closed)]
        p.snake_door_reset=None
        if hides:
            hide=min(hides,key=lambda c:-distance(c,snake["cell"],width))
            p.ambush_plan={"kind":"doorway","door":door,"hide":hide,"waits":0,"last_enemy":snake["cell"]}
            return doorway_first(p,state,enemies,distance,neighbors,line_clear)
        return None
    step=p.route(paths,door)[1]
    if step in p.loot or p.tiles[step].get("plant") or p.tiles[step]["terrain"] in {7,8,21,22,31,37,38}:
        p.snake_door_reset=None
        return None
    return p.cell(step,"snake: return to cleared doorway for a fresh sight break",intent=Intent.RETREAT)


def doorway_first(p,state,enemies,distance,neighbors,line_clear):
    if state.get("status")!="ready" or state.get("modal") or state.get("danger_cells"):
        return None
    held=hold_doorway(p,state,enemies,distance,neighbors,line_clear)
    if held:
        return held
    if p.pursuit_lure_exhausted:
        p.ambush_plan=None
        return None  # Replan combat/escape, not another long doorway setup.
    active=[e for e in enemies if not e.get("sleeping")]
    cost=p.doorway_lure_cost
    if cost.get("depth")!=state["depth"]:
        cost=p.doorway_lure_cost={"depth":state["depth"],"spent":0,"last_hp":None}
    if cost.get("last_hp") is not None:
        cost["spent"]+=max(0,cost["last_hp"]-state["hero"]["hp"])
        cost["last_hp"]=None
    if not active and not p.ambush_plan:
        cost["spent"]=0
    if active and cost["spent"]>=max(3,0.2*state["hero"]["max_hp"]):
        p.ambush_plan=None
        p.planner.report["doorway_first"]={"status":"attempted; observed lure damage budget exhausted","hp_lost":cost["spent"]}
        return None
    excluded={"fetid rat","gnoll trickster","great crab","demon spawner","crystal mimic"}
    if state.get("boss_health_text") or any(e["name"].lower() in p.boss_strategies or
            e["name"].lower() in excluded or "fist" in e["name"].lower() for e in active):
        p.planner.report["doorway_first"]={"status":"dedicated encounter controller"}
        return None
    plan=p.ambush_plan
    if not active and not (plan and plan.get("kind")=="doorway"):
        return None
    pos,width=state["hero"]["cell"],state["map"]["width"]
    current=exposure(p,state,active,pos,distance,line_clear)
    action=p.door_ambush(state,enemies,active,kind="doorway")
    scout_key=None
    scouting=False
    if not action and active:
        action,scout_key=unexplored_door(p,state,enemies)
        scouting=action is not None
    if not action:
        p.planner.report["doorway_first"]={"status":"attempted; no viable bounded doorway lure"}
        return None
    cell=action.action.get("cell",pos)
    try:
        from .escape_commitment import reverses
    except ImportError:
        from escape_commitment import reverses
    if cell!=pos and not any(e['cell']==cell for e in active) and reverses(p,state,cell):
        p.ambush_plan=None
        return None
    strike=next((e for e in active if e["cell"]==cell),None)
    if strike:
        if any(e is not strike and distance(pos,e["cell"],width)<=reach(e)
               and enemy_line(p,e,pos,width,line_clear) for e in active):
            p.ambush_plan=None
            p.planner.report["doorway_first"]={"status":"doorway strike flanked; defer to multi-threat safety"}
            return None
        if not p.attack_kind_allowed(state,strike,'melee'):
            action=p.best_attack(state,strike)
            if not action:
                p.stop_tactical('fly-pressure','Doorway strike would multiply fly pressure without a non-splitting attack')
        strike_reserve=0.5 if current["melee"]>=2 else 0.35
        if state["hero"]["hp"]<strike_reserve*state["hero"]["max_hp"]:
            escape=p.retreat(state,enemies)
            if escape and escape.action.get("cell") not in p.loot \
                    and not exposure(p,state,active,escape.action["cell"],distance,line_clear)["exposure"] \
                    and not any(champion(e)=="blazing" for e in active):
                p.ambush_plan=p.doorway_hold=None
                escape.reason="doorway: abandon critical entry strike for verified unexposed retreat"
                return escape
            bar=strike.get("health_bar")
            finish_key=(state["depth"],"critical-ranged-entry",cell,strike["name"])
            if state["hero"]["hp"]>=0.2*state["hero"]["max_hp"] and bar and bar[1]>0 \
                    and bar[0]/bar[1]<=0.2 and p.snake_melee_attempts[finish_key]<1 \
                    and not (champion(strike)=="blazing" and p.tiles[pos]["terrain"]!=29):
                wands=[i for i in p.charged_magic(state) if i.get("curse_known") and not i.get("known_cursed")
                       and (i.get("status") or "").split("/")[0].isdigit() and p.target_allowed(i,strike)]
                if wands and p.shot_clear(state,cell):
                    p.snake_melee_attempts[finish_key]+=1
                    if p.tiles.get(cell,{}).get("terrain") in {5,6}:
                        p.doorway_hold={"depth":state["depth"],"door":cell,"hide":pos,"inputs":0,"quiet":0,"waits":0}
                    return p.use(wands[0],"ZAP","doorway: one known-charge ranged finish against visibly weak entry threat",target=cell)
            p.stop_tactical("critical-entry","Doorway surprise at critical HP is not a verified kill; refusing lethal follow-up trade")
        if champion(strike)=="blazing" and p.tiles[pos]["terrain"]!=29:
            p.planner.report["doorway_first"]={"status":"unsafe dry blazing strike; defer to fire safety"}
            return None
        if "mimic" in strike["name"].lower() and state["hero"]["hp"]<0.65*state["hero"]["max_hp"]:
            ranged=p.best_attack(state,strike)
            if ranged and ranged.action.get("action")=="ZAP":
                action=ranged
                action.reason="doorway: use charged magic on durable doorway enemy while wounded"
        p.planner.report["doorway_first"]={"status":"doorway ranged interception" if action.action.get("action")=="ZAP" else "doorway surprise strike","cell":cell}
        if p.tiles.get(cell,{}).get("terrain") in {5,6}:
            p.doorway_hold={"depth":state["depth"],"door":cell,"hide":pos,"inputs":0,"quiet":0,"waits":0}
        return action
    if active and cell!=pos and cell==p.previous_position and p.last_decision \
            and p.last_decision.intent==Intent.RETREAT:
        p.ambush_plan=None
        p.planner.report['doorway_first']={'status':'decline immediate empty-step lure reversal','cell':cell}
        return None
    risk=exposure(p,state,active,cell,distance,line_clear)
    low_health=state["hero"]["hp"]<0.5*state["hero"]["max_hp"]
    water_guard=p.tiles[pos]["terrain"]==29 and any(champion(e)=="blazing" and distance(pos,e["cell"],width)<=2 for e in active)
    unsafe_water_exit=water_guard and p.tiles.get(cell,{}).get("terrain")!=29 \
        and any(enemy_line(p,e,cell,width,line_clear) for e in active) \
        and any(champion(e)=="blazing" and distance(cell,e["cell"],width)<=reach(e)+1 for e in active)
    dry_blazing_contact=p.tiles.get(cell,{}).get("terrain")!=29 \
        and any(champion(e)=="blazing" and distance(cell,e["cell"],width)<=reach(e) for e in active)
    violations={"higher_exposure":risk["exposure"]>current["exposure"],
                 "fast_pursuit_not_reduced":not current["melee"] and risk["fast_pursuit"]>0
                     and risk["fast_pursuit"]>=current["fast_pursuit"],
                "water_scout_no_gain":p.tiles[pos]["terrain"]==29 and scouting
                    and risk["exposure"]>0 and risk["exposure"]>=current["exposure"],
                "higher_ranged":risk["ranged"]>current["ranged"],
                "multiple_melee_not_reduced":current["melee"]>=2 and risk["melee"]>=current["melee"],
                "low_health_exposed":bool(low_health and risk["exposure"]),
                "leave_water":bool(unsafe_water_exit),"dry_blazing_contact":bool(dry_blazing_contact)}
    if any(violations.values()):
        p.ambush_plan=None
        p.planner.report["doorway_first"]={"status":"attempted; next step unsafe",
            "violations":[k for k,v in violations.items() if v],"current":current,"proposed":risk,
            "cell":cell,"hp":state["hero"]["hp"]}
        return None
    if action.action["type"]=="wait" and current["exposure"]:
        p.ambush_plan=None
        p.planner.report["doorway_first"]={"status":"attempted; exposed waiting unsafe"}
        return None
    p.planner.report["doorway_first"]={"status":"lure before ordinary attack","cell":cell}
    if scout_key:
        p.room_attempts.add(scout_key)
    cost["last_hp"]=state["hero"]["hp"]
    return action
