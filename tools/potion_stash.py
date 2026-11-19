"""Ordinary drop/retrieve actions protecting inventory from unknown frost drinks."""
try:
    from .consumable_tactics import base_name
    from .policy_decision import Intent
except ImportError:
    from consumable_tactics import base_name
    from policy_decision import Intent


def potions(state):
    return [i for i in state["inventory"] if any(k in base_name(i) for k in ("potion", "elixir of ", " brew"))]


def protect_potions(p,state,candidate,distance,neighbors,safe_bank):
    others=[i for i in potions(state) if i["id"]!=candidate["id"]]
    # DROP detaches an entire stack. Do not pretend we can retain one dose of
    # an unknown stack while protecting its remaining doses through this API.
    if candidate.get("quantity",1)>1:
        p.stop_obligation("potion-stash","Potential frost test requires a single candidate dose; stack splitting unavailable")
    if not others:
        return None
    plan=p.potion_stash
    if plan:
        p.stop_obligation("potion-stash","Potion stash incomplete: other potions remain before potential frost drink")
    bank=state["hero"]["cell"]
    width=state["map"]["width"]
    paths=p.paths(state)
    stashes=[c for c in paths if 3<=distance(c,bank,width)<=5 and len(p.route(paths,c))<=7
             and safe_bank(p,state,c,distance,neighbors,allow_dry=True)
             and all(p.tiles[n]["terrain"] in {1,3,9,11,14,19,20,29}
                     and not p.tiles[n].get("trap") and not p.tiles[n].get("effects")
                     and n not in p.loot for n in p.route(paths,c))]
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
            return p.toward(state,plan["cell"],"potion: approach remote safe stash",intent=Intent.REPOSITION)
        other=next((i for i in potions(state) if base_name(i)!=plan["candidate"]),None)
        if other:
            plan["pending"]=(base_name(other),other.get("quantity",1))
            return p.use(other,"DROP","potion: set other potions aside before potentially chilling drink")
        plan["phase"]="ready"
    if plan["phase"]=="ready":
        if pos!=plan["bank"]:
            return p.toward(state,plan["bank"],"potion: leave stash outside frost-test radius",intent=Intent.REPOSITION)
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
