"""Relative damage evidence from public health pixels, never hidden HP totals."""
try:
    from .combat_items import stats
    from .challenge_combat import champion
except ImportError:
    from combat_items import stats
    from challenge_combat import champion


def context(state,enemy):
    return (state["depth"],enemy["name"].lower(),champion(enemy))


def retire_defeated_escape_edge(p, before, after, pending, before_texts):
    """Retire only the immediate reverse edge occupied by a confirmed last foe.

    A kill is not floor clearance. Other edges, loot receipts and movement
    admission remain independent; disappearance alone never releases a route.
    """
    try:
        from .survival_policy import is_hostile
    except ImportError:
        from survival_policy import is_hostile
    plan = getattr(p, "escape_commitment", None)
    cell, name = pending["cell"], pending["name"].lower()
    pos = after["hero"]["cell"]
    if not plan or (cell, pos) not in plan["edges"]:
        return
    if before["depth"] != after["depth"] or before.get("branch", 0) != after.get("branch", 0) \
            or before["hero"]["cell"] != pos or after.get("status") != "ready" \
            or after.get("modal") or after.get("danger_cells") \
            or getattr(p, "unseen_damage_turns", 0):
        return
    if not any(t.strip().lower() == "you defeated " + name + "."
               for t in after.get("ui", {}).get("texts", []) if t not in before_texts):
        return
    active = [o for o in before.get("objects", []) if is_hostile(o)]
    if len(active) != 1 or active[0]["cell"] != cell or active[0]["name"].lower() != name \
            or any(is_hostile(o) for o in after.get("objects", [])):
        return
    if any(c != cell or e.get("name", "").lower() != name
           for c, e in getattr(p, "recent_threats", {}).items()):
        return
    if any(k in b["name"].lower() for b in after["hero"].get("buffs", [])
           for k in ("poison", "burn", "bleed", "vertigo", "blind", "paral")):
        return
    tile = next((t for t in after.get("map", {}).get("cells", []) if t["cell"] == cell), {})
    if not tile.get("visible"):
        return
    plan["edges"] = [edge for edge in plan["edges"] if edge != (cell, pos)]


def source(state,item=None,action=None):
    if item is None:
        item=next((i for i in state["inventory"] if i.get("equipped") and stats(i) and stats(i)[0]=="melee"),None)
        kind="melee"
    else:
        kind="magic" if action=="ZAP" else "thrown"
    if item is None:return (kind,"unarmed","")
    if sum(i["name"]==item["name"] for i in state["inventory"])>1:
        return None  # Do not merge indistinguishable unidentified duplicates.
    return (kind,item["name"],item.get("description",""))


def fraction(enemy):
    bar=enemy.get("health_bar")
    return bar[0]/bar[1] if bar and len(bar)==2 and bar[1]>0 else None


def capture(state,enemy,key):
    before=fraction(enemy)
    tile=next((t for t in state["map"]["cells"] if t["cell"]==enemy["cell"]),{})
    if before is None or key is None or tile.get("effects"):
        return None
    return {"cell":enemy["cell"],"name":enemy["name"],"context":context(state,enemy),"source":key,"before":before}


def dm100_missile_receipt(before,after,pending):
    """Narrow public kill receipt when floating XP replaces the defeat text.

    A normal DM-100 grants six XP. Require a known single-target missile,
    one turn, and visibility over its entire one-step neighborhood, not just
    disappearance into fog. This is not an exact damage sample.
    """
    if pending["name"].lower()!="dm-100" or pending["source"][0]!="magic":
        return False
    item=next((i for i in before.get("inventory",[])
               if i["name"]==pending["source"][1]),None)
    if not item or not item.get("identified") or not item.get("curse_known") \
            or item.get("known_cursed") or "of magic missile" not in item["name"].lower():
        return False
    actors=[o for o in before.get("objects",[]) if not o.get("top_item")]
    if len(actors)!=1 or actors[0].get("cell")!=pending["cell"] \
            or actors[0].get("name","").lower()!="dm-100" or actors[0].get("sleeping") \
            or actors[0].get("status_icons") or pending["context"][2]:
        return False
    if before["depth"]!=after["depth"] or before.get("branch",0)!=after.get("branch",0) \
            or before["hero"]["cell"]!=after["hero"]["cell"] \
            or before["hero"].get("level")!=after["hero"].get("level") \
            or not 1<=before["hero"].get("level",0)<=13:
        return False
    b=before.get("evaluation_stats",{});a=after.get("evaluation_stats",{})
    if not all(isinstance(s.get(k),(int,float)) for s in (b,a)
               for k in ("experience","elapsed_turns")) \
            or a["experience"]-b["experience"]!=6 or a["elapsed_turns"]-b["elapsed_turns"]!=1:
        return False
    try:
        from .policy_geometry import neighbors,distance
    except ImportError:
        from policy_geometry import neighbors,distance
    width=after["map"]["width"];height=after["map"]["height"]
    if before["map"]["width"]!=width or before["map"]["height"]!=height \
            or distance(before["hero"]["cell"],pending["cell"],width)!=1:
        return False
    tiles={t["cell"]:t for t in after["map"]["cells"]}
    region={pending["cell"],*neighbors(pending["cell"],width,height)}
    return all(tiles.get(c,{}).get("visible") is True
               and tiles[c].get("observed") is not False and not tiles[c].get("effects")
               for c in region) and not any(o.get("name","").lower()=="dm-100"
                                            for o in after.get("objects",[]))


def dm100_arcane_missile_levelup_receipt(before,after,pending):
    """One consumed, clear-ray missile with Arcane Vision and six XP.

    Tracking rules out a struck survivor hiding beyond the old neighborhood.
    Accept either unchanged level or one rollover, with public XP thresholds.
    Keep the older adjacent/no-level-up receipt unchanged.
    """
    import re
    if pending["name"].lower()!="dm-100" or pending["source"][0]!="magic" \
            or pending["context"][2]:
        return False
    hero=before["hero"];level=hero.get("level",0)
    after_level=after["hero"].get("level")
    if hero.get("hero_class")!="mage" or not 1<=level<=13 \
            or after_level not in (level,level+1) \
            or not any(t.get("name")=="arcane vision" and t.get("points",0)>0
                       for t in hero.get("talents",[])):
        return False
    if before["depth"]!=after["depth"] or before.get("branch",0)!=after.get("branch",0) \
            or hero["cell"]!=after["hero"]["cell"]:
        return False
    b=before.get("evaluation_stats",{});a=after.get("evaluation_stats",{})
    if not all(isinstance(s.get(k),(int,float)) for s in (b,a)
               for k in ("experience","experience_to_level","elapsed_turns")) \
            or b["experience_to_level"]!=5+5*level \
            or a["experience_to_level"]!=5+5*after_level \
            or not 0<=b["experience"]<b["experience_to_level"] \
            or not 0<=a["experience"]<a["experience_to_level"] \
            or a["experience"]+(b["experience_to_level"] if after_level==level+1 else 0)-b["experience"]!=6 \
            or a["elapsed_turns"]-b["elapsed_turns"]!=1:
        return False
    item=next((i for i in before.get("inventory",[])
               if i["name"]==pending["source"][1]),None)
    if not item or not item.get("identified") or not item.get("curse_known") \
            or item.get("known_cursed") or "of magic missile" not in item["name"].lower():
        return False
    used=next((i for i in after.get("inventory",[])
               if i.get("id")==item.get("id") and i["name"]==item["name"]),None)
    bc=re.fullmatch(r"(\d+)/(\d+)",item.get("status",""))
    ac=re.fullmatch(r"(\d+)/(\d+)",used.get("status","")) if used else None
    if not bc or not ac or int(bc[1])-int(ac[1])!=1 or bc[2]!=ac[2]:
        return False
    actors=[o for o in before.get("objects",[]) if not o.get("top_item")]
    if len(actors)!=1 or actors[0].get("cell")!=pending["cell"] \
            or actors[0].get("name","").lower()!="dm-100" or actors[0].get("sleeping") \
            or actors[0].get("status_icons") \
            or any(o.get("name","").lower()=="dm-100" for o in after.get("objects",[])):
        return False
    try:
        from .policy_geometry import projectile_line_clear
    except ImportError:
        from policy_geometry import projectile_line_clear
    if any(before["map"][k]!=after["map"][k] for k in ("width","height")):
        return False
    tiles={t["cell"]:t for t in before["map"]["cells"]
           if t.get("visible") is True and t.get("observed") is not False and not t.get("effects")}
    return pending["cell"] in tiles and projectile_line_clear(
        hero["cell"],pending["cell"],before["map"]["width"],tiles)


def dm100_arcane_disintegration_receipt(before,after,pending):
    """A struck survivor remains publicly tracked by Arcane Vision.

    Disintegration pierces walls and cannot miss a target within its beam.
    A public Magic Charge level supplies a minimum range even when the wand's
    own level is unknown. Do not generalize this to curses, other wands, or
    mere disappearance: the existing missile neighborhood proof stays intact.
    """
    import re
    if pending["name"].lower()!="dm-100" or pending["source"][0]!="magic":
        return False
    item=next((i for i in before.get("inventory",[])
               if i["name"]==pending["source"][1]),None)
    if not item or item["name"].lower()!="wand of disintegration" \
            or not item.get("curse_known") or item.get("known_cursed"):
        return False
    hero=before["hero"]
    if hero.get("hero_class")!="mage" or not any(
            t.get("name")=="arcane vision" and t.get("points",0)>0
            for t in hero.get("talents",[])):
        return False
    charge=next((b.get("description","") for b in hero.get("buffs",[])
                 if b.get("name")=="magic charge"),"")
    boost=re.search(r"Your wands are boosted to: \+(\d+)\.",charge)
    turns=re.search(r"Turns of magic charge remaining: (\d+)\.",charge)
    # Consumption of a non-expiring boost distinguishes an executed zap from
    # an empty-wand selection while some unrelated actor grants experience.
    if not boost or not turns or int(turns[1])<=1 or any(
            b.get("name")=="magic charge" for b in after["hero"].get("buffs",[])):
        return False
    try:
        from .policy_geometry import distance
    except ImportError:
        from policy_geometry import distance
    if distance(hero["cell"],pending["cell"],before["map"]["width"])>6+2*int(boost[1]):
        return False
    actors=[o for o in before.get("objects",[]) if not o.get("top_item")]
    if len(actors)!=1 or actors[0].get("cell")!=pending["cell"] \
            or actors[0].get("name","").lower()!="dm-100" or actors[0].get("sleeping") \
            or actors[0].get("status_icons") or pending["context"][2]:
        return False
    if before["depth"]!=after["depth"] or before.get("branch",0)!=after.get("branch",0) \
            or hero["cell"]!=after["hero"]["cell"] \
            or hero.get("level")!=after["hero"].get("level") \
            or not 1<=hero.get("level",0)<=13:
        return False
    b=before.get("evaluation_stats",{});a=after.get("evaluation_stats",{})
    if not all(isinstance(s.get(k),(int,float)) for s in (b,a)
               for k in ("experience","elapsed_turns")) \
            or a["experience"]-b["experience"]!=6 or a["elapsed_turns"]-b["elapsed_turns"]!=1:
        return False
    # Tracking follows the struck actor, not its old square. A living DM-100
    # anywhere in the public observation makes this receipt ambiguous.
    return not any(o.get("name","").lower()=="dm-100" for o in after.get("objects",[]))


def observe_accepted_attack(p,before,decision,after):
    """Called only after a confirmed API execution; targeting menus cost no sample."""
    action=decision.action
    if action.get("type")=="item" and action.get("action") in {"ZAP","THROW"}:
        p.damage_pending=None
        item=next((i for i in before.get("inventory",[]) if i["id"]==action["id"]),None)
        target=next((o for o in before.get("objects",[]) if o["cell"]==p.target and not o.get("top_item")),None)
        if item and target and (action["action"]=="ZAP" or stats(item) and stats(item)[0]=="thrown"):
            p.damage_pending=capture(before,target,source(before,item,action["action"]))
        if after.get("status")=="targeting":return
    elif before.get("status")=="targeting":
        if action.get("type")!="cell" or not p.damage_pending or action.get("cell")!=p.damage_pending["cell"]:
            p.damage_pending=None
            return
    elif before.get("status")=="ready" and action.get("type")=="cell":
        target=next((o for o in before.get("objects",[]) if o["cell"]==action.get("cell")
                     and not o.get("top_item") and o.get("health_bar")),None)
        if not target:return
        p.damage_pending=capture(before,target,source(before))
    else:
        return
    pending=p.damage_pending
    p.damage_pending=None
    if not pending or after.get("status")!="ready":return
    before_texts=set(before.get("ui",{}).get("texts",[]))
    memory=getattr(p,"dm100_threat",None)
    if memory and memory["cell"]==pending["cell"] and (
            dm100_missile_receipt(before,after,pending)
            or dm100_arcane_missile_levelup_receipt(before,after,pending)
            or dm100_arcane_disintegration_receipt(before,after,pending)):
        p.dm100_threat=None
        if p.ranged_plan and p.ranged_plan.get("name")=="dm-100":
            p.ranged_plan=None
    defeated=any("you defeated" in t.lower() and pending["name"].lower() in t.lower()
                 for t in after.get("ui",{}).get("texts",[]) if t not in before_texts)
    key=(pending["context"],pending["source"])
    if defeated:
        retire_defeated_escape_edge(p, before, after, pending, before_texts)
        # The separate lightning-lane memory outlives ordinary visible-cell
        # threat tracking. Retire it on this accepted, newly confirmed kill,
        # not on disappearance or a defeat message retained from an old fight.
        memory=getattr(p,"dm100_threat",None)
        if pending["name"].lower()=="dm-100" and memory and memory["cell"]==pending["cell"] \
                and before["depth"]==after["depth"] and before.get("branch",0)==after.get("branch",0) \
                and any(t.strip().lower()=="you defeated dm-100."
                        for t in after.get("ui",{}).get("texts",[]) if t not in before_texts) \
                and not any(o.get("cell")==pending["cell"] and o.get("name","").lower()=="dm-100"
                            for o in after.get("objects",[])):
            p.dm100_threat=None
            if p.ranged_plan and p.ranged_plan.get("name")=="dm-100":
                p.ranged_plan=None
        sample=p.damage_samples.setdefault(key,{"count":0,"bar_loss":0.0})
        sample["censored_count"]=sample.get("censored_count",0)+1
        sample["censored_bar_loss_lower_bound"]=sample.get("censored_bar_loss_lower_bound",0)+pending["before"]
        return {"enemy":pending["name"],"depth":before["depth"],"method":pending["source"][0],
                "item":pending["source"][1],"bar_loss_lower_bound":pending["before"],"censored":True,
                "note":"Confirmed kill; total damage may exceed remaining visible health. Not actual HP."}
    target=next((o for o in after.get("objects",[]) if o["cell"]==pending["cell"] and o["name"]==pending["name"]),None)
    if not target or context(after,target)!=pending["context"]:return
    after_fraction=fraction(target)
    tile=next((t for t in after.get("map",{}).get("cells",[]) if t["cell"]==target["cell"]),{})
    if tile.get("effects") or any("you defeated" in t.lower() for t in after.get("ui",{}).get("texts",[]) if t not in before_texts):
        return  # Death/replacement, fire and clouds confound single-hit attribution.
    if after_fraction is None or after_fraction>pending["before"]:return
    if after_fraction==pending["before"] and pending["source"][0]=="magic" \
            and any("wand fizzles" in t.lower() for t in after.get("ui",{}).get("texts",[])):
        return  # Empty/immunity fizzles are availability evidence, not weak damage rolls.
    sample=p.damage_samples.setdefault(key,{"count":0,"bar_loss":0.0})
    sample["count"]+=1
    sample["bar_loss"]+=pending["before"]-after_fraction  # Zero includes observed misses/blocked hits.
    return {"enemy":pending["name"],"depth":before["depth"],"method":pending["source"][0],
            "item":pending["source"][1],"before_fraction":pending["before"],"after_fraction":after_fraction,
            "bar_loss":pending["before"]-after_fraction,"censored":False,"note":"Visible bar fraction, not actual HP."}


def compare_options(p,state,enemy,options):
    measured=[]
    ctx=context(state,enemy)
    for score,item,action in options:
        key=source(state,item,action)
        sample=p.damage_samples.get((ctx,key),{})
        mean=sample.get("bar_loss",0)/max(1,sample.get("count",0))
        count=sample.get("count",0)
        lower_only=count<2 and sample.get("censored_count",0)>=2
        if lower_only:
            count=sample["censored_count"]
            mean=sample["censored_bar_loss_lower_bound"]/count
        measured.append((score,item,action,key,count,mean,lower_only))
    anchors=[o for o in measured if o[4]>=2 and o[5]>0 and not o[6]]
    if not anchors or sum(o[4]>=2 for o in measured)<2:return options
    anchor=max(anchors,key=lambda o:(o[1] is None or o[1].get("equipped",False),o[4]))
    output=[]
    audit=[]
    for score,item,action,key,count,mean,lower_only in measured:
        adjusted=score
        if count>=2:
            empirical=anchor[0]*mean/anchor[5]
            adjusted=max(0.25*score,min(2*score,0.5*score+0.5*empirical))
            if lower_only:adjusted=max(score,adjusted)
            audit.append({"method":key[0],"item":key[1],"samples":count,
                          "mean_visible_bar_loss":mean,"lower_bound_only":lower_only,"prior":score,"adjusted":adjusted})
        output.append((adjusted,item,action))
    p.planner.report["observed_damage_comparison"]=audit
    return output
