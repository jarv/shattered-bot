"""Distant-well drops: rough public damage budget, verified protection and exit.

Unprotected bleed has a stochastic tail; an average is not a survival promise.
Prefer feather fall or pre-cleansing rather than betting a run on that average.
"""
import math

try:
    from .consumable_tactics import base_name
    from .room_tactics import remaining
except ImportError:
    from consumable_tactics import base_name
    from room_tactics import remaining


def fall_budget(hero):
    hp, maximum = hero["hp"],hero["max_hp"]
    direct = max(hp//2,math.ceil(maximum/4))
    initial_bleed = math.floor(maximum/(6+6*hp/max(1,maximum))+0.5)
    return {"direct_upper":direct,"initial_bleed_upper":initial_bleed,
            "rough_bleed_total":4*initial_bleed,"after_direct":hp-direct,
            "rough_after_bleed":hp-direct-4*initial_bleed}


def known_well_drop(p):
    return [c for c,t in p.tiles.items() if t["terrain"]==0
            and "distant well" in t.get("name","").lower()]


def prepare_drop(p,state,enemies,distance,neighbors):
    if "drop-room" in p.deferred_room_controllers:return None
    if enemies or p.drop_plan or state.get("danger_cells") or state["depth"]%5 in {0,4}:
        return None
    hero=state["hero"]
    buffs=" ".join(b["name"].lower() for b in hero.get("buffs",[]))
    if any(t in buffs for t in ("levitat","flying","vertigo","root","paral","poison","burning","bleed","starving")):
        return None
    drops=known_well_drop(p)
    if not drops:
        return None
    budget=fall_budget(hero)
    p.planner.report["fall_budget"]=budget
    inventory=state["inventory"]
    feather=next((i for i in inventory if base_name(i)=="elixir of feather fall" and "DRINK" in i.get("actions",[])),None)
    cleanse=next((i for i in inventory if base_name(i)=="potion of cleansing" and "DRINK" in i.get("actions",[])),None)
    protected=remaining(state,"feather fall")>12
    cleared=remaining(state,"cleansed")>3
    if not feather and not protected and not cleanse and not cleared:
        return None  # Raw seeds cannot neutralize bleeding under Barren Land.
    charges=sum(int(i["status"].split("/")[0]) for i in p.charged_magic(state)
                if (i.get("status") or "?").split("/")[0].isdigit())
    if charges<3:
        return None  # A haunted pile may guard the exit; never assume its contents.
    reserve=max(10,0.4*hero["max_hp"])
    can_feather=protected or feather is not None
    needs_health = hero["hp"] < reserve if can_feather else budget["after_direct"] < reserve
    if needs_health:
        # Only genuinely usable healing can improve the budget. Pharmacophobia
        # blocks known healing; never quietly poison the hero as "preparation".
        heal=next((i for i in inventory if base_name(i)=="potion of healing" and "DRINK" in i.get("actions",[])
                   and p.item_action_allowed(i,"DRINK")),None)
        if heal:
            return p.use(heal,"DRINK","drop: improve observed health budget with genuinely usable healing")
        return None
    paths=p.paths(state)
    width,height=state["map"]["width"],state["map"]["height"]
    choices=[]
    for drop in drops:
        if not p.tiles[drop].get("visible") or (state["depth"],drop) in p.drop_attempts:
            continue
        for bank in neighbors(drop,width,height):
            if bank in paths and len(p.route(paths,bank))<=8 and p.tiles[bank]["terrain"] in {1,2,6,9,11,14,19,20,29}:
                choices.append((len(p.route(paths,bank)),bank,drop))
    if not choices:
        return None
    _,bank,drop=min(choices)
    if hero["cell"]!=bank:
        return p.toward(state,bank,"drop: approach observed distant-well ledge before using protection",paths)
    if not protected and feather:
        try:
            from .room_supplies import use as use_room_supply
        except ImportError:
            from room_supplies import use as use_room_supply
        return use_room_supply(p,feather,"DRINK","drop: activate feather fall and verify its rendered buff before jumping",kind="fall")
    if not protected and not cleared and cleanse:
        try:
            from .room_supplies import use as use_room_supply
        except ImportError:
            from room_supplies import use as use_room_supply
        return use_room_supply(p,cleanse,"DRINK","drop: pre-cleanse to prevent landing bleed after budgeting direct damage",kind="fall")
    if not protected and not cleared:
        return None
    p.drop_attempts.add((state["depth"],drop))
    p.drop_plan={"depth":state["depth"],"bank":bank,"cell":drop,"stage":"confirm","steps":0}
    return p.cell(drop,"drop: request deliberate distant-well jump with verified protection and health reserve")


def drop_menu(p,state):
    plan=p.drop_plan
    plan["steps"]+=1
    text=" ".join(state["ui"].get("texts",[])).lower()
    valid=state.get("depth")==plan["depth"] and state["hero"]["cell"]==plan["bank"] \
        and "jump into the chasm" in text and plan["steps"]<=4
    valid=valid and (remaining(state,"feather fall")>12 or remaining(state,"cleansed")>3)
    label="yes, i know" if valid else "no, i changed"
    button=next((b for b in state["ui"]["buttons"] if b["label"].lower().startswith(label)),None)
    if button:
        if not valid:
            p.drop_plan=None
        return p.decision({"type":"button","id":button["id"]},"drop: confirm verified protected jump" if valid else "drop: reject changed or unprotected jump")
    p.drop_plan=None
    return p.decision({"type":"back"},"drop: cancel unexpected jump confirmation")


def recover_drop(p,state,enemies,distance,neighbors):
    plan=p.drop_plan
    if not plan or state.get("status")!="ready":
        return None
    if state["depth"]==plan["depth"]:
        # A rejected/unexecuted confirmation must never turn into blind walking.
        p.drop_plan=None
        return None
    if state["depth"]!=plan["depth"]+1:
        p.drop_plan=None
        return None
    plan["stage"]="landed"
    plan["steps"]+=1
    if plan["steps"]>80:
        p.stop_obligation("drop-room","Planned drop: landing/exit interaction budget exhausted")
    hero=state["hero"]
    buffs=" ".join(b["name"].lower() for b in hero.get("buffs",[]))
    if "bleed" in buffs:
        cleanse=next((i for i in state["inventory"] if base_name(i)=="potion of cleansing" and "DRINK" in i.get("actions",[])),None)
        if cleanse:
            try:
                from .room_supplies import use as use_room_supply
            except ImportError:
                from room_supplies import use as use_room_supply
            return use_room_supply(p,cleanse,"DRINK","drop: cleanse observed landing bleeding before looting",kind="fall")
        sandals=next((i for i in state["inventory"] if i.get("equipped") and "ROOT" in i.get("actions",[])
                      and "seed of mageroyal" in i.get("description","").replace("_","").lower()),None)
        if sandals:
            return p.use(sandals,"ROOT","drop: invoke inspected mageroyal artifact effect; no impossible seed planting",target=hero["cell"])
        if not getattr(p,'barren_land',False):
            try:
                from .seed_tactics import choose_seed
            except ImportError:
                from seed_tactics import choose_seed
            seed=choose_seed(p,state,enemies,distance,neighbors)
            if seed:return seed
        p.stop_obligation("drop-room","Planned drop: unexpected landing bleeding without a usable cleansing effect")
    if enemies:
        return None  # Ordinary wraith/enemy arbitration must handle an ambush.
    paths=p.paths(state)
    if p.keys.get("crystal",0):
        doors=[c for c,t in p.tiles.items() if t["terrain"]==31 and c in paths and len(p.route(paths,c))<=10]
        if len(doors)==1:
            door=doors[0]
            p.optional_locks.discard(door)
            action=p.toward(state,door,"drop: spend observed crystal exit key on the known local door",paths)
            if action:
                plan["exit_door"]=door
                return action
    if plan.get("exit_door") is not None and p.tiles.get(plan["exit_door"],{}).get("terrain")!=31:
        p.drop_plan=None
        return None
    # Collect actual keys first. If still locked in, inspect/open the observed
    # haunted remains with a charged anti-wraith reserve, not a hidden loot read.
    keys=[c for c,o in p.loot.items() if "crystal key" in o.get("top_item",o).get("name","").lower() and c in paths]
    if keys:
        return p.toward(state,min(keys,key=lambda c:len(p.route(paths,c))),"drop: collect visibly revealed crystal exit key",paths)
    charges=sum(int(i["status"].split("/")[0]) for i in p.charged_magic(state)
                if (i.get("status") or "?").split("/")[0].isdigit())
    if hero["hp"]>=max(10,0.4*hero["max_hp"]) and charges>=3:
        piles=[c for c,o in p.loot.items() if o["name"].lower() in {"skeleton","skeletal remains","remains"}]
        for cell in piles:
            banks=[c for c in paths if distance(c,cell,state["map"]["width"])==1 and len(p.route(paths,c))<=8]
            if not banks:
                continue
            bank=min(banks,key=lambda c:len(p.route(paths,c)))
            if hero["cell"]!=bank:
                return p.toward(state,bank,"drop: approach observed remains with reserved anti-wraith magic",paths)
            return p.cell(cell,"drop: open observed remains to seek the locked room's exit key")
    return None
