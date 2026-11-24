"""One accepted ground-pickup reconciler for every typed owned-item account."""
from collections import Counter
try:
    from .consumable_tactics import base_name
    from .objective_episodes import Scope
except ImportError:
    from consumable_tactics import base_name
    from objective_episodes import Scope


def inventory_counts(state):
    counts=Counter()
    for item in state.get("inventory",[]):
        counts[base_name(item)]+=item.get("quantity",1)
    return counts


def observe_pickup(p,before,decision,after):
    if before.get("depth") is None or after.get("depth") is None \
            or Scope.of(before)!=Scope.of(after) \
            or "inventory" not in before or "inventory" not in after:
        return None
    action=decision.action
    if action.get("type")!="cell" or after.get("hero",{}).get("cell")!=action.get("cell"):
        return None
    scope=Scope.of(before)
    account=p.physical_ledger.at(scope,action.get("cell"))
    if not account:
        return None
    ground=next((o["top_item"] for o in before.get("objects",[])
                 if o.get("cell")==account.cell and not o.get("for_sale") and o.get("top_item")),None)
    if not ground:
        return None
    name=base_name(ground)
    quantity=inventory_counts(after)[name]-inventory_counts(before)[name]
    credited=min(quantity,account.outstanding.get(name,0))
    if not 0<quantity<=ground.get("quantity",1) or credited<=0:
        return None
    remaining=next((o["top_item"].get("quantity",1) for o in after.get("objects",[])
                    if o.get("cell")==account.cell and o.get("top_item")
                    and base_name(o["top_item"])==name),0)
    if remaining>ground.get("quantity",1)-quantity \
            or not p.physical_ledger.pickup(account,name,credited,after.get("observation_id")):
        return None
    return dict(kind="pickup",name=name,quantity=credited,inventory_gain=quantity,owner=account.owner,
                account=account.physical_record(),collection_credited=False)


def unknown_execution(p,before,decision,reason):
    """Preserve uncertainty on an API failure; never retry or confirm a transfer."""
    ledger=getattr(p,"physical_ledger",None)
    if ledger is None:
        return []
    owners=[]
    for account in ledger.entries.values():
        hook=getattr(account,"unknown_transfer",None)
        pending=hook(before,decision) if account.active and hook else None
        if pending:
            ledger.defer(account,reason,pending)
            owners.append(account.owner)
    return owners
