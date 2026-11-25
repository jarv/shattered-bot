"""Reusable projectile custody; trap/plant activation remains a domain concern."""
from dataclasses import dataclass
from enum import Enum
try:
    from .consumable_tactics import base_name
    from .objective_episodes import Scope
    from .physical_obligations import OwnedItems, DropProposal
    from .owned_transfers import inventory_counts
except ImportError:
    from consumable_tactics import base_name
    from objective_episodes import Scope
    from physical_obligations import OwnedItems, DropProposal
    from owned_transfers import inventory_counts


REUSABLE={"waterskin","dew vial","dew pouch"}


class PayloadPhase(str, Enum):
    PROPOSED="proposed"
    AIMING="aiming"
    LANDED="landed"
    UNVERIFIED="unverified"
    COMPLETE="complete"
    CANCELLED="cancelled"


@dataclass(kw_only=True)
class PayloadReturn(OwnedItems):
    name: str
    item_id: str = ""
    origin: int = -1
    steps: int = 0
    reobserve_steps: int = 0
    disarm_required: bool = True
    phase: PayloadPhase = PayloadPhase.PROPOSED
    attempted_cell: int | None = None
    throw_witnessed: bool = True
    observed_inventory_removed: int | None = None
    owner_kind: str = "payload"
    obligation_kind: str = "unretrieved reusable trap payload"

    def __post_init__(self):
        self.phase=PayloadPhase(self.phase)

    @property
    def proposal(self):
        return DropProposal(self.name,1,self.item_id)

    def record(self):
        return dict(owner=self.owner,depth=self.depth,branch=self.branch,cell=self.cell,
                    name=self.name,item_id=self.item_id,origin=self.origin,steps=self.steps,
                    phase=self.phase.value,disarm_required=self.disarm_required,
                    attempted_cell=self.attempted_cell,
                    throw_witnessed=self.throw_witnessed,
                    observed_inventory_removed=self.observed_inventory_removed,
                    outstanding=self.outstanding,
                    unverified_drop=self.unverified_drop.record() if self.unverified_drop else None)

    def obligation(self,kind=None):
        return dict(super().obligation(kind),attempted_cell=self.attempted_cell,
                    observed_inventory_removed=self.observed_inventory_removed)

    def unknown_transfer(self,before,decision):
        if self.phase not in {PayloadPhase.PROPOSED,PayloadPhase.AIMING}:
            return None  # A later use of a recycled inventory ID is not this throw.
        same_source=decision.action==dict(type="item",id=self.item_id,action="THROW")
        targeted=self.phase==PayloadPhase.AIMING and before.get("status")=="targeting" \
            and decision.action.get("type")=="cell"
        if self.scope.depth==before.get("depth") and self.scope.branch==before.get("branch",0) \
                and (same_source or targeted):
            if same_source:
                self.throw_witnessed=getattr(decision,"payload_owner",None)==self.owner
            self.phase=PayloadPhase.UNVERIFIED
            self.attempted_cell=decision.action.get("cell",self.cell)
            return self.proposal
        return None

    def __getitem__(self,key):
        if key not in self.__dataclass_fields__:
            raise KeyError(key)
        return getattr(self,key)

    def get(self,key,default=None):
        return getattr(self,key,default)


def workflow(p):
    plan=p.trap_payload_return
    if isinstance(plan,dict):
        # Explicit reconstructed retrieval state, not evidence of a new throw.
        fields=dict(plan)
        fields.setdefault("dropped",{fields["name"]:1})
        fields.setdefault("phase",PayloadPhase.LANDED)
        p.trap_payload_return=plan=PayloadReturn(**fields)
    if plan and not plan.owner and not p.physical_ledger.register(plan):
        p.stop_obligation("trap-payload","Reusable payload location belongs to another workflow")
    return plan


def finish_if_settled(p):
    plan=p.trap_payload_return
    if isinstance(plan,PayloadReturn) and plan.phase==PayloadPhase.LANDED \
            and not plan.unresolved and p.physical_ledger.entries.get(plan.owner) is plan:
        plan.phase=PayloadPhase.COMPLETE
        p.physical_ledger.finish(plan)
        p.trap_payload_return=None
        return True
    return False


def throw(p,state,item,target,reason,*,disarm_required=True,track=None):
    """After domain admission, acquire claims and propose exactly one thrown unit."""
    finish_if_settled(p)  # A paid owner must not lock out combat-priority reuse.
    if track is None:
        track=base_name(item) in REUSABLE
    scope=Scope.of(state)
    if p.trap_payload_return or not p.physical_ledger.inventory_available(scope,[item["id"]]) \
            or not p.physical_ledger.site_available(scope,target) or target==state["hero"]["cell"]:
        return None
    action=p.use(item,"THROW",reason,target=target)
    if not track:
        return action
    plan=PayloadReturn(depth=state["depth"],branch=state.get("branch",0),cell=target,
                       name=base_name(item),item_id=item["id"],origin=state["hero"]["cell"],
                       disarm_required=disarm_required)
    if not p.physical_ledger.register(plan,[item["id"]]):
        return None
    p.trap_payload_return=plan
    action.payload_owner=plan.owner
    return action


def held_unchanged(before,after,plan):
    if "inventory" not in before or "inventory" not in after:
        return False
    def source(state):
        return next((i for i in state["inventory"] if i.get("id")==plan.item_id
                     and base_name(i)==plan.name),None)
    old,new=source(before),source(after)
    return bool(old and new and old.get("quantity",1)==new.get("quantity",1)
                and inventory_counts(before)[plan.name]==inventory_counts(after)[plan.name])


def observe_landing(p,before,decision,after):
    if not p.trap_payload_return:
        return None
    plan=workflow(p)
    if (before.get("depth"),before.get("branch",0))!=(plan.depth,plan.branch):
        return None
    action=decision.action
    same_source=action==dict(type="item",id=plan.item_id,action="THROW")
    selected=getattr(decision,"payload_owner",None)==plan.owner and same_source
    cancelled=(plan.phase==PayloadPhase.PROPOSED and not same_source) or (
        plan.phase==PayloadPhase.AIMING and before.get("status")=="targeting"
        and action==dict(type="back"))
    if cancelled and not plan.outstanding and held_unchanged(before,after,plan):
        plan.phase=PayloadPhase.CANCELLED
        plan.unverified_drop=None  # The accepted cancellation resolves only the proposal.
        p.physical_ledger.finish(plan)
        p.trap_payload_return=None
        return dict(kind="payload-cancelled",payload=plan.record(),collection_credited=False)
    if after.get("depth") is not None and Scope.of(after)!=plan.scope:
        pending=plan.proposal if plan.phase in {PayloadPhase.PROPOSED,PayloadPhase.AIMING,
                                               PayloadPhase.UNVERIFIED} else None
        p.physical_ledger.defer(plan,"Accepted transition left the reusable payload scope",pending)
        return None
    if plan.phase not in {PayloadPhase.PROPOSED,PayloadPhase.AIMING}:
        return None
    targeted=plan.phase==PayloadPhase.AIMING and before.get("status")=="targeting" \
        and action==dict(type="cell",cell=plan.cell)
    retargeted=plan.phase==PayloadPhase.AIMING and before.get("status")=="targeting" \
        and action.get("type")=="cell" and not targeted
    if not same_source and not targeted and not retargeted:
        return None
    if same_source:
        plan.throw_witnessed=selected
    if same_source and after.get("status")=="targeting":
        plan.phase=PayloadPhase.AIMING
        return None
    if after.get("status")!="ready" or after.get("modal"):
        return None
    plan.attempted_cell=action["cell"] if action.get("type")=="cell" else plan.cell
    token=after.get("observation_id")
    if p.physical_ledger.seen(plan.scope,token):
        return None
    removed=(inventory_counts(before)[plan.name]-inventory_counts(after)[plan.name]
             if "inventory" in before and "inventory" in after else None)
    plan.observed_inventory_removed=removed
    ground=next((o["top_item"] for o in after.get("objects",[])
                 if o.get("cell")==plan.cell and not o.get("for_sale") and o.get("top_item")
                 and base_name(o["top_item"])==plan.name),None)
    prior=next((o["top_item"].get("quantity",1) for o in before.get("objects",[])
                if o.get("cell")==plan.cell and o.get("top_item")
                and base_name(o["top_item"])==plan.name),0)
    if plan.throw_witnessed and not retargeted and after.get("depth") is not None \
            and removed==1 and ground and ground.get("quantity",1)>=prior+1:
        plan.dropped[plan.name]=plan.dropped.get(plan.name,0)+1
        plan.phase=PayloadPhase.LANDED
        kind="payload-landed"
    elif removed==0 and held_unchanged(before,after,plan) \
            and not (ground and ground.get("quantity",1)>prior):
        plan.phase=PayloadPhase.CANCELLED  # No owned unit left the inventory.
        p.physical_ledger.finish(plan)
        p.trap_payload_return=None
        kind="payload-not-transferred"
    else:
        plan.phase=PayloadPhase.UNVERIFIED
        plan.unverified_drop=plan.proposal
        kind="payload-landing-unverified"
    p.physical_ledger.remember(plan.scope,token)
    return dict(kind=kind,payload=plan.record(),collection_credited=False,
                trap_activation_verified=False)
