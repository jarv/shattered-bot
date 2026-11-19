"""A suspicious chest disappearing is not evidence of its reward being collected."""
try:
    from .consumable_tactics import base_name
    from .policy_decision import Intent
except ImportError:
    from consumable_tactics import base_name
    from policy_decision import Intent


def matches(item,kind):
    return kind=="any" or f"{kind} of " in base_name(item)


def count(state,kind):
    return sum(i.get("quantity",1) for i in state["inventory"] if matches(i,kind))


def begin_hunt(p,state,cell,obj):
    text=obj.get("description", "").lower()
    kind="wand" if "a wand" in text else "ring" if "a ring" in text else "any"
    p.mimic_obligations[cell]={"last":cell,"kind":kind,"count":count(state,kind),
                               "reward_cells":set(),"steps":0,
                               "escape_log_before":tuple(t for t in state.get("ui",{}).get("texts",[]) if "crystal mimic has escaped" in t.lower())}


def observe_hunts(p,state,distance):
    mimics=[o for o in state.get("objects",[]) if "mimic" in o["name"].lower()]
    texts=" ".join(state.get("ui",{}).get("texts",[])).lower()
    width=state["map"]["width"]
    for origin,plan in list(p.mimic_obligations.items()):
        escape_log=tuple(t for t in state.get("ui",{}).get("texts",[]) if "crystal mimic has escaped" in t.lower())
        if escape_log and escape_log!=plan.get("escape_log_before",()):
            p.room_attempts.add((state["depth"],"mimic-escaped-reward-lost",origin))
            loss={'depth':state['depth'],'branch':state.get('branch',0),'cell':origin,'name':'Escaped crystal mimic reward',
                  'kind':plan['kind'],'status':'missed-unrecoverable','collected':False,
                  'evidence':'fresh public crystal-mimic escape message','messages':list(escape_log)}
            if not any(r['depth']==loss['depth'] and r['cell']==origin for r in p.missed_loot):
                p.missed_loot.append(loss)
            p.unconfirmed_loot.pop(origin,None)
            del p.mimic_obligations[origin]
            continue  # Publicly lost, not a collectible or a successful pickup.
        if mimics:
            plan["last"]=min(mimics,key=lambda o:distance(o["cell"],plan["last"],width))["cell"]
        for obj in state.get("objects",[]):
            item=obj.get("top_item")
            if item and matches(item,plan["kind"]) and min(distance(obj["cell"],origin,width),distance(obj["cell"],plan["last"],width))<=2:
                plan["reward_cells"].add(obj["cell"])
        if not mimics and state["hero"]["cell"] in plan["reward_cells"] \
                and count(state,plan["kind"])>plan["count"] and "you picked up:" in texts:
            del p.mimic_obligations[origin]


def hunt_missing_mimic(p,state,enemies,distance):
    if enemies or not p.mimic_obligations or state.get("danger_cells"):
        return None
    origin,plan=next(iter(p.mimic_obligations.items()))
    paths=p.paths(state)
    rewards=[c for c in plan["reward_cells"] if c in paths and c in p.loot]
    if rewards:
        return p.toward(state,min(rewards,key=lambda c:len(p.route(paths,c))),
                        "mimic: collect observed reward before leaving room",paths,intent=Intent.LOOT)
    if plan["steps"]>=16:
        p.stop_obligation("mimic-hunt","Suspicious mimic reward unresolved after bounded public-area search; not certified complete")
    if state["hero"]["hp"]<0.65*state["hero"]["max_hp"]:
        return None
    width=state["map"]["width"]
    choices=[c for c in paths if c!=state["hero"]["cell"] and distance(c,plan["last"],width)<=3
             and len(p.route(paths,c))<=12 and c not in p.loot
             and p.tiles[c]["terrain"] in {1,3,6,9,11,14,19,20,29}
             and not p.tiles[c].get("effects") and not p.tiles[c].get("plant")]
    if choices:
        plan["steps"]+=1
        target=min(choices,key=lambda c:(p.visits[c],distance(c,plan["last"],width),len(p.route(paths,c))))
        return p.toward(state,target,"mimic: reacquire vanished chest enemy; disappearance is not completion",paths,intent=Intent.REPOSITION)
    return None


def crystal_mimic(p,state,enemies,distance):
    target=next((e for e in enemies if e["name"].lower()=="crystal mimic"),None)
    if not target:
        return None
    # Its public description says it runs away and steals/repositions. Do not
    # kite it like a durable pursuer or wait at a door for it to chase us.
    attack=p.best_attack(state,target)
    if attack and attack.action.get("action") in {"ZAP","THROW"}:
        attack.reason="mimic: intercept fleeing crystal mimic immediately from range"
        return attack
    if len(enemies)==1 and state["hero"]["hp"]>=0.65*state["hero"]["max_hp"]:
        if distance(state["hero"]["cell"],target["cell"],state["map"]["width"])==1:
            return p.cell(target["cell"],"mimic: strike isolated fleeing crystal mimic before theft or escape")
        paths=p.paths(state,{e["cell"] for e in enemies})
        cells=[c for c in paths if distance(c,target["cell"],state["map"]["width"])==1
               and len(p.route(paths,c))<=4 and c not in p.loot]
        if cells:
            return p.toward(state,min(cells,key=lambda c:len(p.route(paths,c))),
                            "mimic: bounded interception of observed fleeing crystal mimic",paths,intent=Intent.APPROACH)
    return None
