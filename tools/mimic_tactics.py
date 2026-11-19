"""Public-warning chest recognition and bounded, observation-only mimic spacing."""
try:
    from .policy_decision import Intent
    from .challenge_combat import exposure
    from .seed_tactics import choose_seed
except ImportError:
    from policy_decision import Intent
    from challenge_combat import exposure
    from seed_tactics import choose_seed


def suspicious_container(obj):
    text=obj.get("description", "").replace("_", "").lower()
    return "feels off" in text and "bad idea" in text


def fight_mimic(p,state,enemies,distance,neighbors,line_clear):
    active=[e for e in enemies if not e.get("sleeping")]
    mimics=[e for e in active if "mimic" in e["name"].lower() and e["name"].lower()!="crystal mimic"]
    if not mimics:
        p.mimic_kites=0
        return None
    hero=state["hero"]
    pos,width,height=hero["cell"],state["map"]["width"],state["map"]["height"]
    target=min(mimics,key=lambda e:distance(pos,e["cell"],width))
    if distance(pos,target["cell"],width)<=1:
        options=[c for c in neighbors(pos,width,height) if p.walkable(c,{e["cell"] for e in enemies})
                 and c not in p.loot and not p.tiles[c].get("plant")
                 and not exposure(p,state,active,c,distance,line_clear)["exposure"]
                 and distance(c,target["cell"],width)>=2
                 and sum(p.walkable(n,{e["cell"] for e in enemies}) for n in neighbors(c,width,height))>=2]
        if options and p.mimic_kites<6:
            doors=[c for c,t in p.tiles.items() if t["terrain"] in {5,6}]
            cell=min(options,key=lambda c:(min((distance(c,d,width) for d in doors),default=99),
                                          -distance(c,target["cell"],width)))
            p.mimic_kites+=1
            return p.cell(cell,"mimic: kite onto verified unexposed ground toward doorway",intent=Intent.RETREAT)
    attack=p.best_attack(state,target)
    if attack and attack.action.get("action") in {"ZAP","THROW"}:
        attack.reason="mimic: attack revealed durable pursuer from range"
        return attack
    seed=choose_seed(p,state,enemies,distance,neighbors)
    if seed:
        return seed
    if hero["hp"]<0.65*hero["max_hp"]:
        p.stop_tactical("mimic-pressure","Mimic: no verified ranged attack or bounded safe kite while wounded")
    return None
