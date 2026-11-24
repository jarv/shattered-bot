"""Ordinary drop/retrieve actions protecting inventory from unknown frost drinks."""
try:
    from .consumable_tactics import base_name
    from .policy_decision import Intent
    from .policy_geometry import neighbors, distance
    from .stash_workflow import StashWorkflow, StashPhase, DropProposal, workflow
    from .objective_episodes import Scope
    from .owned_transfers import inventory_counts, observe_pickup
except ImportError:
    from consumable_tactics import base_name
    from policy_decision import Intent
    from policy_geometry import neighbors, distance
    from stash_workflow import StashWorkflow, StashPhase, DropProposal, workflow
    from objective_episodes import Scope
    from owned_transfers import inventory_counts, observe_pickup


STASH_TRANSIT = {1,2,3,9,11,14,15,19,20,29,30}
FLAMMABLE = {2,5,6,13,15,27,30}


def fire_footprint(p, state, bank):
    """Conservative liquid-flame footprint; unknown terrain can carry fire.

    Pinned Fire.evolve spreads cardinally onto flammable terrain. The potion
    seeds NEIGHBOURS9. Seeding walls here deliberately overestimates the cloud.
    Freezing itself never diffuses beyond its initially seeded footprint.
    """
    width, height = state["map"]["width"], state["map"]["height"]
    seen = {bank, *neighbors(bank, width, height)}
    queue = list(seen)
    while queue:
        cell = queue.pop()
        for n in neighbors(cell, width, height):
            if n % width != cell % width and n // width != cell // width:
                continue
            tile = p.tiles.get(n, {})
            if n not in seen and (not tile.get("observed", tile.get("visible", False))
                                  or tile.get("terrain") in FLAMMABLE or tile.get("plant")):
                seen.add(n)
                queue.append(n)
    return seen


def fire_reaches_stash(p, state, bank, stash):
    return stash in fire_footprint(p, state, bank)


def storage_safe(p, state, bank, cell, footprint=None):
    """A drop site need not be a drink site; protect it from test collateral."""
    tile = p.tiles.get(cell, {})
    if not tile.get("visible") or tile.get("terrain") not in STASH_TRANSIT \
            or any(tile.get(k) for k in ("effects", "trap", "plant")) \
            or cell in p.loot or cell in p.blocked or cell in p.room_blocked \
            or cell in p.neutral_actor_cells or cell in state.get("danger_cells", []):
        return False
    if any(distance(cell,o["cell"],state["map"]["width"]) <= 4
           for o in list(state.get("objects", [])) + list(p.recent_threats.values())
           if not o.get("top_item") and o["cell"] not in p.loot):
        return False
    return cell not in (fire_footprint(p,state,bank) if footprint is None else footprint)


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
               if t["terrain"] not in STASH_TRANSIT
              or t.get("trap") or t.get("plant") or t.get("effects") or c in p.loot}
    return p.paths(state,excluded)


def stash_cells(p,state,distance,neighbors,safe_bank,*,all_sites=False):
    """Read-only admission shared by test-bank preflight and actual stashing."""
    bank=state["hero"]["cell"]
    width=state["map"]["width"]
    paths=stash_paths(p,state)
    footprint=fire_footprint(p,state,bank)
    cells = [c for c in paths if p.physical_ledger.site_available(Scope.of(state),c)
             and 3<=distance(c,bank,width)<=5 and len(p.route(paths,c))<=7
             and (safe_bank(p,state,c,distance,neighbors,allow_dry=True)
                  or storage_safe(p,state,bank,c,footprint))
             and c not in footprint
             and all(p.tiles[n]["terrain"] in STASH_TRANSIT
                    and not p.tiles[n].get("trap") and not p.tiles[n].get("effects")
                     and n not in p.loot for n in p.route(paths,c))]
    preferred = [c for c in cells if safe_bank(p,state,c,distance,neighbors,allow_dry=True)]
    return cells if all_sites else preferred or cells


def fire_reaches_owned_items(p,state):
    return any(a.scope==Scope.of(state) and a.unresolved
               and fire_reaches_stash(p,state,state['hero']['cell'],a.cell)
               for a in p.physical_ledger.entries.values())


def can_protect_potions(p,state,candidate,distance,neighbors,safe_bank, *, isolated_stack=False):
    """No drops, receipts, or inferred effects: only preparation feasibility."""
    if p.potion_stash and workflow(p).pending:
        return False
    if not p.physical_ledger.inventory_available(
            Scope.of(state),[candidate["id"]],getattr(p.potion_stash,"owner",None)):
        return False
    if fire_reaches_owned_items(p,state):
        return False
    if bandolier_protected(p,state) and not p.potion_stash:
        return True
    if candidate.get("quantity",1)>1 and not isolated_stack:
        return False
    others=[i for i in potions(state) if i["id"]!=candidate["id"]]
    if not others:
        return True
    if p.potion_stash or any("DROP" not in i.get("actions",[]) for i in others):
        return False
    if not p.physical_ledger.inventory_available(
            Scope.of(state),[i["id"] for i in [candidate,*others]]):
        return False
    return bool(stash_cells(p,state,distance,neighbors,safe_bank))


def protect_potions(p,state,candidate,distance,neighbors,safe_bank, *, isolated_stack=False,preferred_cell=None):
    if p.potion_stash and workflow(p).pending:
        p.stop_obligation("potion-stash","Potion protection still lacks an accepted drop receipt")
    if not p.physical_ledger.inventory_available(
            Scope.of(state),[candidate["id"]],getattr(p.potion_stash,"owner",None)):
        p.stop_obligation("potion-stash","Potion candidate belongs to another workflow")
    if fire_reaches_owned_items(p,state):
        p.stop_obligation("potion-stash","Potion test collateral can now reach the stash; retrieve before replanning")
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
    stashes=stash_cells(p,state,distance,neighbors,safe_bank,all_sites=preferred_cell is not None)
    if preferred_cell is not None:
        stashes=[c for c in stashes if c==preferred_cell]
    if not stashes or any("DROP" not in i.get("actions",[]) for i in others):
        p.stop_obligation("potion-stash","Potential frost test has no verified remote potion stash/drop route")
    plan=StashWorkflow(
        depth=state["depth"],branch=state.get("branch",0),bank=bank,
        cell=min(stashes,key=lambda c:len(p.route(paths,c))),
        candidate=base_name(candidate))
    if not p.physical_ledger.register(plan,[i["id"] for i in [candidate,*others]]):
        p.stop_obligation("potion-stash","Potion stash resources already owned by another workflow")
    p.potion_stash=plan
    return advance_stash(p,state,[],distance)


def advance_stash(p,state,enemies,distance):
    plan=workflow(p)
    if not plan:
        return None
    if plan.scope!=Scope.of(state):
        p.stop_obligation("potion-stash","Potion stash was left on another floor")
    if enemies or state.get("danger_cells"):
        plan.retrieve()
        return None  # Combat interrupts; it never cancels the retrieval obligation.
    buffs=" ".join(b["name"].lower() for b in state["hero"].get("buffs",[]))
    if p.puzzle_probe or any(t in buffs for t in ("chill","frozen","burning","poison","paral","vertigo")):
        return None
    plan.steps+=1
    if plan.steps>48:
        p.stop_obligation("potion-stash","Potion stash exceeded bounded preparation/retrieval budget")
    pos=state["hero"]["cell"]
    if plan.pending:
        p.stop_obligation("potion-stash","Potion stash drop lacks a matching accepted-action receipt")
    if plan.phase==StashPhase.DROP:
        if pos!=plan.cell:
            return p.toward(state,plan.cell,"potion: approach remote safe stash",stash_paths(p,state),intent=Intent.REPOSITION)
        # Recheck after arrival, before changing inventory. Existing own drops
        # occupy this square on subsequent steps and are verified below.
        tile=p.tiles.get(pos,{})
        if tile.get("terrain") not in STASH_TRANSIT or not tile.get("visible") \
                or any(tile.get(k) for k in ("trap","plant","effects")) \
                or pos in p.room_blocked or pos in p.blocked \
                or pos in p.loot and not plan.outstanding \
                or fire_reaches_stash(p,state,plan.bank,pos):
            p.stop_obligation("potion-stash","Stash arrival lost its hazard/collateral admission")
        other=next((i for i in potions(state) if base_name(i)!=plan.candidate),None)
        if other:
            if not p.physical_ledger.register(plan,[other["id"]]):
                p.stop_obligation("potion-stash","Potion drop item belongs to another workflow")
            action=p.use(other,"DROP","potion: set other potions aside before potentially chilling drink")
            plan.pending=DropProposal(base_name(other),other.get("quantity",1),other["id"])
            action.stash_drop=plan.pending
            return action
        plan.ready()
    if plan.phase==StashPhase.READY:
        if pos!=plan.bank:
            return p.toward(state,plan.bank,"potion: leave stash outside frost-test radius",stash_paths(p,state),intent=Intent.REPOSITION)
        return None
    if plan.phase==StashPhase.RETRIEVE:
        if not plan.outstanding:
            plan.complete()
            p.physical_ledger.finish(plan)
            p.potion_stash=None
            return None
        paths=p.paths(state)
        if plan.cell not in paths or p.tiles[plan.cell].get("effects"):
            p.stop_obligation("potion-stash","Potion stash retrieval blocked by observed hazard or unreachable ground")
        return p.toward(state,plan.cell,"potion: retrieve protected potions before further exploration",paths,intent=Intent.LOOT)


def observe_drop(p,before,decision,after):
    """Reconcile physical transfers before dependent preparation observers run.

    Selection, matching carried names, heap disappearance and elapsed turns are
    not transfer receipts. Ambiguous transfers retain the unfinished obligation.
    """
    if not p.potion_stash:
        return None
    plan=workflow(p)
    if before.get("depth") is None:
        return None
    scope=Scope.of(before)
    if after.get("depth") is not None and Scope.of(after)!=scope:
        # Preserve physical facts before update() resets floor-local intent.
        # The transition itself proves neither pickup nor completion.
        if plan and plan.scope==scope:
            p.physical_ledger.defer(plan,"Accepted transition left the potion stash scope",plan.pending)
        return None
    if (after.get("depth"),after.get("branch",0))!=(scope.depth,scope.branch) \
            or "inventory" not in before or "inventory" not in after:
        return None
    token=after.get("observation_id")
    if p.physical_ledger.seen(scope,token):
        return None
    action=decision.action
    old,new=inventory_counts(before),inventory_counts(after)
    drop=getattr(decision,"stash_drop",None)
    kind=None
    if plan and plan.scope==scope and drop and drop==plan.pending \
            and action==dict(type="item",id=drop.item_id,action="DROP") \
            and before.get("hero",{}).get("cell")==after.get("hero",{}).get("cell")==plan.cell:
        item=next((i for i in potions(before) if i.get("id")==drop.item_id),None)
        ground=next((o.get("top_item") for o in after.get("objects",[])
                     if o.get("cell")==plan.cell and not o.get("for_sale")
                     and o.get("top_item") and base_name(o["top_item"])==drop.name),None)
        prior=next((o["top_item"].get("quantity",1) for o in before.get("objects",[])
                    if o.get("cell")==plan.cell and o.get("top_item")
                    and base_name(o["top_item"])==drop.name),0)
        if not item or base_name(item)!=drop.name \
                or item.get("quantity",1)!=drop.quantity \
                or old[drop.name]-new[drop.name]!=drop.quantity \
                or not ground or ground.get("quantity",1)<prior+drop.quantity:
            return None
        plan.dropped[drop.name]=plan.dropped.get(drop.name,0)+drop.quantity
        p.physical_ledger.remember(scope,token)
        plan.pending=None
        kind="drop"
        name,quantity=drop.name,drop.quantity
    if kind is None:
        return None
    return dict(kind=kind,name=name,quantity=quantity,stash=plan.record(),
                collection_credited=False)


def observe_accepted(p,before,decision,after):
    """Compatibility entry point; the runner calls each receipt stage once."""
    return observe_drop(p,before,decision,after) or observe_pickup(p,before,decision,after)
