"""Typed views of public facts and narrowly scoped derived-veto invalidation.

These views do not authorize actions, identify hidden traps or infer actor death.
Domain receipt validators must establish a retirement before the reducer runs.
"""
from dataclasses import dataclass, field
from enum import Enum

try:
    from .objective_episodes import Scope
except ImportError:
    from objective_episodes import Scope


class Mechanism(str, Enum):
    UNKNOWN = "unknown"
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass(frozen=True)
class TileEvidence:
    terrain: int | None
    visible: bool
    observed: bool
    mapped: bool
    trap_identity: str | None
    mechanism: Mechanism
    effects: tuple
    plant: str | None

    @classmethod
    def of(cls, tile):
        visible=bool(tile.get("visible"))
        observed=bool(tile.get("observed",visible))
        public=visible or observed
        mechanism=Mechanism.ACTIVE if public and tile.get("terrain")==18 else \
                  Mechanism.INACTIVE if public and tile.get("terrain")==19 else Mechanism.UNKNOWN
        return cls(tile.get("terrain"),visible,observed,bool(tile.get("mapped")),
                   tile.get("trap"),mechanism,tuple(tile.get("effects",())),tile.get("plant"))

    def record(self):
        return dict(terrain=self.terrain,visible=self.visible,observed=self.observed,
                    mapped=self.mapped,trap_identity=self.trap_identity,
                    mechanism=self.mechanism.value,effects=list(self.effects),plant=self.plant)


@dataclass(frozen=True)
class ThreatRef:
    scope: Scope
    cell: int
    name: str
    observation_id: object = None
    turn: float | None = None

    @classmethod
    def observed(cls,state,cell,name="dm-100"):
        return cls(Scope.of(state),cell,name.lower(),state.get("observation_id"),
                   (state.get("evaluation_stats") or {}).get("elapsed_turns"))

    @classmethod
    def from_record(cls,record):
        return cls(Scope(record["depth"],record.get("branch",0)),record["cell"],
                   record["name"].lower(),record.get("observation_id"),record.get("turn"))

    def record(self):
        return dict(depth=self.scope.depth,branch=self.scope.branch,cell=self.cell,
                    name=self.name,observation_id=self.observation_id,turn=self.turn)

    def supported_before(self,proof):
        if (self.scope,self.cell,self.name)!=(proof.target.scope,proof.target.cell,proof.target.name):
            return False
        before=proof.target
        timed=isinstance(self.turn,(int,float)) and isinstance(before.turn,(int,float))
        if timed and self.turn>before.turn:
            return False
        if self.observation_id is None or self.observation_id==before.observation_id:
            return True
        if isinstance(self.observation_id,(int,float)) and isinstance(before.observation_id,(int,float)):
            return self.observation_id<=before.observation_id
        return timed and self.turn<=before.turn


class RetirementRule(str, Enum):
    FRESH_DEFEAT_TEXT = "fresh-matching-defeat-text"
    ADJACENT_MISSILE_XP = "dm100-adjacent-missile-public-xp"
    ARCANE_MISSILE_XP = "dm100-arcane-missile-public-xp"
    ARCANE_DISINTEGRATION_XP = "dm100-arcane-disintegration-public-xp"


def bind_threat(p,state,slot,cell):
    """Bind a plan to a sighting, or reuse its remembered source.

    Planning an approach never manufactures a sighting of an unseen foe.
    """
    visible=any(o.get("cell")==cell and o.get("name","").lower()=="dm-100"
                and not o.get("top_item") and not o.get("sleeping")
                for o in state.get("objects",[]))
    memory=getattr(p,"dm100_threat",None)
    if visible:
        ref=ThreatRef.observed(state,cell)
    elif memory and memory.get("threat_ref"):
        ref=ThreatRef.from_record(memory["threat_ref"])
        if ref.scope!=Scope.of(state) or ref.cell!=cell:
            return slot
    else:
        return slot
    slot["threat_ref"]=ref.record()
    return slot


def binding_in_scope(slot,state):
    if not slot:
        return False
    if slot.get("threat_ref"):
        return ThreatRef.from_record(slot["threat_ref"]).scope==Scope.of(state)
    return (slot.get("depth",state["depth"]),slot.get("branch",state.get("branch",0)))==(
        state["depth"],state.get("branch",0))


@dataclass(frozen=True)
class RetirementProof:
    target: ThreatRef
    rule: RetirementRule
    after_observation_id: object
    after_turn: float | None

    def record(self):
        return dict(target=self.target.record(),rule=self.rule.value,
                    after_observation_id=self.after_observation_id,after_turn=self.after_turn,
                    collection_credited=False,floor_clear_claimed=False)


@dataclass
class EvidenceReducer:
    retirements: list = field(default_factory=list)
    seen: set = field(default_factory=set)

    def retire(self,p,proof):
        """Invalidate only supported, matching actor-derived state.

        Public actor IDs are not available: a receipt concerns this observed
        site/context, not every future DM-100 or every remembered caster.
        """
        token=proof.after_observation_id
        key=(proof.target.scope,token,proof.target.cell,proof.target.name)
        if token is not None and key in self.seen:
            return None
        if token is not None:
            self.seen.add(key)
        target=proof.target
        invalidated=[]
        memory=getattr(p,"dm100_threat",None)
        lane_matches=False
        if memory and memory.get("cell")==target.cell:
            ref=ThreatRef.from_record(memory["threat_ref"]) if memory.get("threat_ref") else \
                ThreatRef(Scope(memory.get("depth",target.scope.depth),
                                memory.get("branch",target.scope.branch)),
                          memory["cell"],"dm-100",turn=memory.get("turn"))
            lane_matches=ref.supported_before(proof)
            if lane_matches:
                p.dm100_threat=None
                invalidated.append("dm100-lightning-lane")
        plan=getattr(p,"ranged_plan",None)
        if plan and plan.get("name")=="dm-100":
            ref=ThreatRef.from_record(plan["threat_ref"]) if plan.get("threat_ref") else None
            # Old fixture plans may have no source binding. Adopt only the
            # matching lane, never a different explicitly remembered source.
            legacy_matches=lane_matches and plan.get("last_seen",target.cell)==target.cell \
                and plan.get("depth",target.scope.depth)==target.scope.depth \
                and plan.get("branch",target.scope.branch)==target.scope.branch
            if ref and ref.supported_before(proof) or ref is None and legacy_matches:
                p.ranged_plan=None
                invalidated.append("dm100-ranged-plan")
        recent=getattr(p,"recent_threats",{}).get(target.cell)
        if recent and recent.get("name","").lower()==target.name:
            ref=ThreatRef.from_record(recent["threat_ref"]) if recent.get("threat_ref") else \
                ThreatRef(target.scope,target.cell,target.name)
            if ref.supported_before(proof):
                del p.recent_threats[target.cell]
                invalidated.append("recent-threat")
        event=dict(proof.record(),invalidated=invalidated)
        self.retirements.append(event)
        p.planner.report["threat_retirement"]=event
        return event
