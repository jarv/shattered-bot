"""Location roles and cost witnesses, not potion identity or action permission."""
from dataclasses import dataclass, replace

try:
    from .objective_episodes import Scope
except ImportError:
    from objective_episodes import Scope


@dataclass(frozen=True)
class PreparationItinerary:
    scope: Scope
    kind: str
    test_bank: int
    work_origin: int
    work_target: int
    success_return: int
    failure_bank: int
    outbound: tuple
    return_route: tuple
    quoted_cost: float
    storage_cell: int | None = None
    handoff_route: tuple = ()
    unknown_test_admitted: bool = False

    def __post_init__(self):
        if not self.outbound or self.outbound[0]!=self.test_bank \
                or self.outbound[-1]!=self.work_target \
                or not self.return_route or self.return_route[0]!=self.work_target \
                or self.return_route[-1]!=self.success_return \
                or self.work_origin not in self.outbound:
            raise ValueError("Preparation location roles do not match the routes")
        if self.storage_cell is not None and (
                not self.handoff_route or self.handoff_route[0]!=self.success_return
                or self.handoff_route[-1]!=self.storage_cell):
            raise ValueError("Storage requires its own ordinary return handoff")

    def with_storage(self, cell, route):
        return replace(self,storage_cell=cell,handoff_route=tuple(route),
                       unknown_test_admitted=True)

    def record(self):
        return dict(depth=self.scope.depth,branch=self.scope.branch,kind=self.kind,
                    test_bank=self.test_bank,work_origin=self.work_origin,
                    work_target=self.work_target,success_return=self.success_return,
                    failure_bank=self.failure_bank,outbound=list(self.outbound),
                    return_route=list(self.return_route),quoted_cost=self.quoted_cost,
                    storage_cell=self.storage_cell,handoff_route=list(self.handoff_route),
                    unknown_test_admitted=self.unknown_test_admitted,
                    protection_is_prerequisite=True,collection_credited=False)


@dataclass(frozen=True)
class StorageItinerary:
    scope: Scope
    bank: int
    cell: int
    route: tuple
    doors: tuple
    quoted_inputs: int

    def __post_init__(self):
        if not self.route or self.route[0]!=self.bank or self.route[-1]!=self.cell \
                or self.cell in self.doors or self.bank in self.doors \
                or not set(self.doors)<=set(self.route) or not 0<self.quoted_inputs<=48:
            raise ValueError("Invalid bounded storage itinerary")

    def record(self):
        return dict(depth=self.scope.depth,branch=self.scope.branch,bank=self.bank,
                    cell=self.cell,route=list(self.route),doors=list(self.doors),
                    quoted_inputs=self.quoted_inputs,collection_credited=False)
