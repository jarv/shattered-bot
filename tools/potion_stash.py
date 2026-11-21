"""Ordinary drop/retrieve actions protecting inventory from unknown frost drinks."""
try:
    from .consumable_tactics import base_name
    from .policy_decision import Intent
except ImportError:
    from consumable_tactics import base_name
    from policy_decision import Intent


def potions(state):
    return [i for i in state["inventory"] if base_name(i) != "potion bandolier"
            and any(k in base_name(i) for k in ("potion", "elixir of ", " brew"))]


def bandolier_slots(state):
    return len(potions(state)) + sum(base_name(i) in {"waterskin", "liquid metal"}
                                     for i in state["inventory"])


def observe_bandolier(p,state):
    """Track public acquisition and any possible overflow, across floor changes.

    A snapshot of an already-owned bag is not proof of where potions are stored.
    Nor does later consuming a potion prove that earlier overflow was repacked.
    """
    if not state.get("hero") or "inventory" not in state:return
    owned=any(base_name(i)=="potion bandolier" for i in state["inventory"])
    before=getattr(p,"bandolier_inventory",None)
    if not owned:
        p.bandolier_inventory=(False,False)
    else:
        uncertain=before is None or before[0] and before[1]
        p.bandolier_inventory=(True,bool(uncertain or bandolier_slots(state)>19))


def bandolier_protected(p,state):
    """The known bag collects potions and protects them from cold.

    Inventory is flattened: require observed acquisition and no possible overflow
    since that acquisition. Count slots, not doses; include other bag liquids.
    """
    if not any(base_name(i) == "potion bandolier" and i.get("identified") for i in state["inventory"]):
        return False
    return getattr(p,"bandolier_inventory",None)==(True,False) and bandolier_slots(state)<=19


def stash_paths(p,state):
    """Search inside the admitted stash corridor, not through rejected shortcuts."""
    excluded={c for c,t in p.tiles.items()
              if t["terrain"] not in {1,3,9,11,14,19,20,29}
              or t.get("trap") or t.get("plant") or t.get("effects") or c in p.loot}
    return p.paths(state,excluded)


def stash_cells(p,state,distance,neighbors,safe_bank):
    """Read-only admission shared by test-bank preflight and actual stashing."""
    bank=state["hero"]["cell"]
    width=state["map"]["width"]
    paths=stash_paths(p,state)
    return [c for c in paths if 3<=distance(c,bank,width)<=5 and len(p.route(paths,c))<=7
            and safe_bank(p,state,c,distance,neighbors,allow_dry=True)
            and all(p.tiles[n]["terrain"] in {1,3,9,11,14,19,20,29}
                    and not p.tiles[n].get("trap") and not p.tiles[n].get("effects")
                    and n not in p.loot for n in p.route(paths,c))]


def can_protect_potions(p,state,candidate,distance,neighbors,safe_bank, *, isolated_stack=False):
    """No drops, receipts, or inferred effects: only preparation feasibility."""
    if bandolier_protected(p,state) and not p.potion_stash:
        return True
    if candidate.get("quantity",1)>1 and not isolated_stack:
        return False
    others=[i for i in potions(state) if i["id"]!=candidate["id"]]
    if not others:
        return True
    if p.potion_stash or any("DROP" not in i.get("actions",[]) for i in others):
        return False
    return bool(stash_cells(p,state,distance,neighbors,safe_bank))


def protect_potions(p,state,candidate,distance,neighbors,safe_bank, *, isolated_stack=False):
    if bandolier_protected(p,state) and not p.potion_stash:
        return None  # No remote drops, stack splitting or bag disposal are needed.
    others=[i for i in potions(state) if i["id"]!=candidate["id"]]
    # DROP detaches an entire stack. Do not pretend we can retain one dose of
    # an unknown stack while protecting its remaining doses through this API.
    # Discovery may explicitly accept risking only the tested color's remaining
    # doses if it is frost. Every OTHER color is still remotely protected.
    if candidate.get("quantity",1)>1 and not isolated_stack:
        p.stop_obligation("potion-stash","Potential frost test requires a single candidate dose; stack splitting unavailable")
    if not others:
        return None
    plan=p.potion_stash
    if plan:
        p.stop_obligation("potion-stash","Potion stash incomplete: other potions remain before potential frost drink")
    bank=state["hero"]["cell"]
    paths=stash_paths(p,state)
    stashes=stash_cells(p,state,distance,neighbors,safe_bank)
    if not stashes or any("DROP" not in i.get("actions",[]) for i in others):
        p.stop_obligation("potion-stash","Potential frost test has no verified remote potion stash/drop route")
    p.potion_stash={"depth":state["depth"],"bank":bank,"cell":min(stashes,key=lambda c:len(p.route(paths,c))),
                    "candidate":base_name(candidate),"phase":"drop","steps":0,"dropped":{},"pending":None}
    return advance_stash(p,state,[],distance)


def advance_stash(p,state,enemies,distance):
    plan=p.potion_stash
    if not plan:
        return None
    if plan["depth"]!=state["depth"]:
        p.stop_obligation("potion-stash","Potion stash was left on another floor")
    if enemies or state.get("danger_cells"):
        plan["phase"]="retrieve"
        return None  # Combat interrupts; it never cancels the retrieval obligation.
    buffs=" ".join(b["name"].lower() for b in state["hero"].get("buffs",[]))
    if p.puzzle_probe or any(t in buffs for t in ("chill","frozen","burning","poison","paral","vertigo")):
        return None
    plan["steps"]+=1
    if plan["steps"]>48:
        p.stop_obligation("potion-stash","Potion stash exceeded bounded preparation/retrieval budget")
    pos=state["hero"]["cell"]
    if plan["pending"]:
        name,quantity=plan["pending"]
        if any(base_name(i)==name for i in potions(state)) or plan["cell"] not in p.loot:
            p.stop_obligation("potion-stash","Potion stash drop not confirmed by public inventory and ground observation")
        plan["dropped"][name]=plan["dropped"].get(name,0)+quantity
        plan["pending"]=None
    if plan["phase"]=="drop":
        if pos!=plan["cell"]:
            return p.toward(state,plan["cell"],"potion: approach remote safe stash",stash_paths(p,state),intent=Intent.REPOSITION)
        other=next((i for i in potions(state) if base_name(i)!=plan["candidate"]),None)
        if other:
            plan["pending"]=(base_name(other),other.get("quantity",1))
            return p.use(other,"DROP","potion: set other potions aside before potentially chilling drink")
        plan["phase"]="ready"
    if plan["phase"]=="ready":
        if pos!=plan["bank"]:
            return p.toward(state,plan["bank"],"potion: leave stash outside frost-test radius",stash_paths(p,state),intent=Intent.REPOSITION)
        return None
    if plan["phase"]=="retrieve":
        counts={base_name(i):i.get("quantity",1) for i in potions(state)}
        if all(counts.get(n,0)>=q for n,q in plan["dropped"].items()) and not plan["pending"]:
            p.potion_stash=None
            return None
        paths=p.paths(state)
        if plan["cell"] not in paths or p.tiles[plan["cell"]].get("effects"):
            p.stop_obligation("potion-stash","Potion stash retrieval blocked by observed hazard or unreachable ground")
        return p.toward(state,plan["cell"],"potion: retrieve protected potions before further exploration",paths,intent=Intent.LOOT)
