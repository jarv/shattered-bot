"""One successful curse-discovery cast per new wand, using visible safe targets.

An unidentified *level* does not imply an unknown curse. The game's curse_known
flag is player knowledge; it becomes true after a successful normal wand cast.
Empty fizzles do not reveal curses and must not be mistaken for a successful test.
"""
try:
    from .combat_items import magic_score
except ImportError:
    from combat_items import magic_score


def observe_wand_cast(p, state):
    p.wand_observation_clock+=1
    for wand in state.get("inventory",[]):
        name=wand["name"]
        if not name.lower().startswith("wand of ") or sum(i["name"]==name for i in state["inventory"])!=1:
            continue
        usage=p.wand_usage.setdefault(name,{"successful_shots":0,"burst":0,"longest_burst":0,"estimate_only":True})
        status=(wand.get("status") or "").split("/")
        if len(status)==2 and status[1].isdigit():
            maximum=int(status[1])
            base=3 if "magic missile" in name.lower() else 2
            usage.update(visible_capacity=maximum,capacity_level_guess=max(0,maximum-base),capacity_capped=maximum>=10)
            if status[0].isdigit():usage["visible_remaining"]=int(status[0])
    pending = p.pending_wand_test
    if not pending:
        if p.wand_usage:p.planner.report["wand_usage_estimates"]=p.wand_usage
        return
    item = next((i for i in state["inventory"] if i["id"] == pending["id"]
                 and i["name"] == pending["name"]), None)
    fizzled=any("wand fizzles" in t.lower() for t in state.get("ui",{}).get("texts",[]))
    if item and item.get("curse_known") and (not pending.get("curse_known_before") or not fizzled):
        # Successful normal casts reveal curse state even before level ID. Do
        # not suppress a proven charged wand for another 30 decisions.
        p.unknown_magic_cooldowns.pop(item["name"], None)
        usage=p.wand_usage.get(item["name"])
        if usage is not None and not item.get("known_cursed"):
            usage["successful_shots"]+=1
            usage["burst"]=usage["burst"]+1 if usage.get("last_cast_clock")==p.wand_observation_clock-1 else 1
            usage["last_cast_clock"]=p.wand_observation_clock
            usage["longest_burst"]=max(usage["longest_burst"],usage["burst"])
            base=3 if "magic missile" in item["name"].lower() else 2
            if any(k in item["name"].lower() for k in ("magic missile","frost","disintegration","prismatic light","living earth","transfusion")):
                usage["burst_level_guess"]=max(0,usage["longest_burst"]-base)
                usage["burst_caveat"]="Starting charge may be partial; passive recharge may add shots. Not a known level or capacity."
    elif item and fizzled and item["name"] in p.wand_usage:
        p.wand_usage[item["name"]].update(burst=0,visible_remaining=0)
    p.pending_wand_test = None  # A fizzle keeps its backoff, not a false success.
    if p.wand_usage:p.planner.report["wand_usage_estimates"]=p.wand_usage


def choose_wand_probe(p, state, enemies, distance, neighbors):
    hero = state["hero"]
    pos, width, height = hero["cell"], state["map"]["width"], state["map"]["height"]
    buffs = " ".join(b["name"].lower() for b in hero.get("buffs", []))
    active = [e for e in enemies if not e.get("sleeping")]
    if state.get("danger_cells") or ("magic" in buffs and "immun" in buffs):
        return None
    retreat = p.wand_test_retreat
    if retreat:
        target = retreat["target"]
        candidates = [c for c in neighbors(pos, width, height) if p.walkable(c, {e["cell"] for e in enemies})
                      and p.tiles[c]["terrain"] not in {5, 7, 8, 10, 21, 22, 31, 37, 38}
                      and not p.tiles[c].get("plant") and not p.tiles[c].get("effects")
                      and distance(c, target, width) > distance(pos, target, width)
                      and all(distance(c, e["cell"], width) > 1 for e in active)]
        if candidates and retreat["steps"] > 0:
            retreat["steps"] -= 1
            return p.cell(max(candidates, key=lambda c: distance(c, target, width)), "wand: retreat from test effect")
        p.wand_test_retreat = None
    if hero["hp"] < 0.75 * hero["max_hp"] or p.tiles[pos].get("effects"):
        return None
    wands = [i for i in state["inventory"] if "wand of " in i["name"].lower()
             and "ZAP" in i.get("actions", []) and not i.get("known_cursed")
             and not i.get("curse_known") and not i.get("identified")
             and (i.get("status") or "?").split("/")[0] != "0"
             and not p.unknown_magic_cooldowns[i["name"]]]
    for item in wands:
        # Direct-damage wands can earn their first test in useful ranged combat.
        targets = [e for e in active if distance(pos, e["cell"], width) >= 3
                   and p.shot_clear(state, e["cell"])] if magic_score(item) > 0 else []
        if active:
            if targets and all(distance(pos, e["cell"], width) >= 3 for e in active):
                p.unknown_magic_cooldowns[item["name"]] = 30
                return p.use(item, "ZAP", "wand: first cast to reveal curse state", target=targets[0]["cell"])
            continue
        # Test utility and area-effect wands as well, but not beside sleeping
        # enemies, guardians, loot, traps, or plants. A curse can still be harmful.
        objects = state.get("objects", [])
        if any(distance(pos, o["cell"], width) <= 3 for o in objects if "top_item" not in o):
            continue
        candidates = []
        for cell, tile in p.tiles.items():
            if not tile.get("visible") or tile["terrain"] not in {1, 9, 14, 29} \
                    or distance(pos, cell, width) < 5 or tile.get("trap") or tile.get("plant") \
                    or tile.get("effects") or cell in p.room_blocked or not p.shot_clear(state, cell):
                continue
            if any(distance(cell, o["cell"], width) <= 2 for o in objects):
                continue
            nearby = [p.tiles.get(n, {}) for n in neighbors(cell, width, height)]
            if any(not t.get("visible") or t.get("trap") or t.get("plant") or t.get("effects") for t in nearby):
                continue
            if "fireblast" in item["name"].lower():
                dx, dy = cell % width - pos % width, cell // width - pos // width
                def in_cone(c):
                    x, y = c % width - pos % width, c // width - pos // width
                    dot = x*dx + y*dy
                    return dot > 0 and abs(x*dy-y*dx) <= dot * 1.2 and distance(pos, c, width) <= 9
                if any(in_cone(o["cell"]) for o in objects) or any(in_cone(c) and
                        (t["terrain"] in {2, 5, 6, 13, 15, 27, 30} or t.get("trap") or t.get("plant"))
                        for c, t in p.tiles.items()):
                    continue
            candidates.append(cell)
        if candidates:
            target = max(candidates, key=lambda c: distance(pos, c, width))
            # Mark even numeric-charge tests for backoff if magic immunity or
            # another rejection prevents curse discovery. Successful casts expose
            # curse_known and are never repeated just because level is unknown.
            p.unknown_magic_cooldowns[item["name"]] = 30
            if any(name in item["name"].lower() for name in ("corrosion", "fireblast")):
                p.wand_test_retreat = {"target": target, "steps": 3}
            return p.use(item, "ZAP", "wand: first cast to reveal curse state", target=target)
    return None


def choose_transfusion(p,state,enemies,distance):
    """Use inspected hostile targets once per name/floor; never heal our charms."""
    try:
        from .challenge_combat import champion, visible_shield, reach
    except ImportError:
        from challenge_combat import champion, visible_shield, reach
    hero=state["hero"]
    buffs=" ".join(b["name"].lower() for b in hero.get("buffs",[]))
    if state.get("danger_cells") or hero["hp"]>=0.65*hero["max_hp"] \
            or p.charged_magic(state) or visible_shield(state)>=5 or "magic immun" in buffs:
        return None
    wand=next((i for i in state["inventory"] if "wand of transfusion" in i["name"].lower()
               and i.get("curse_known") and not i.get("known_cursed") and "ZAP" in i.get("actions",[])
               and (i.get("status") or "?").split("/")[0]!="0"
               and not p.unknown_magic_cooldowns[i["name"]]),None)
    if not wand:
        return None
    targets=[e for e in enemies if not e.get("sleeping") and e["name"].lower() not in p.transfusion_names
             and p.shot_clear(state,e["cell"]) and p.target_allowed(wand,e)]
    def priority(e):
        gap=distance(hero["cell"],e["cell"],state["map"]["width"])
        bar=e.get("health_bar")
        nearly_defeated=bool(bar and bar[1]>0 and bar[0]/bar[1]<=0.15)
        return (gap>reach(e),nearly_defeated,
                champion(e) not in {"projecting","blessed","blazing"},gap)
    for target in sorted(targets,key=priority):
        cache=p.inspection_cache
        if not cache or cache["cell"]!=target["cell"] or cache["name"]!=target["name"]:
            return p.inspect_enemy(target)
        if any("charm" in b.lower() for b in cache["buffs"]):
            continue
        p.transfusion_names.add(target["name"].lower())
        return p.use(wand,"ZAP","wand: transfuse inspected uncharmed threat for emergency shielding/control",target=target["cell"])
    return None
