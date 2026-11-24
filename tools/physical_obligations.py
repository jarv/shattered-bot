"""Run-wide owned-item debts and exclusive workflow claims.

No action admission lives here. Only domain-validated accepted transfer receipts
change physical quantities. Releasing executable intent never releases a debt.
"""
from dataclasses import dataclass, field
from enum import Enum

try:
    from .objective_episodes import Scope
except ImportError:
    from objective_episodes import Scope


class ResourceKind(str, Enum):
    INVENTORY = "inventory-item"
    GROUND_SITE = "ground-site"
    STASH_SITE = "ground-site"  # Compatibility alias for the first pilot.


class PhysicalStatus(str, Enum):
    PLANNED = "planned"
    OUTSTANDING = "outstanding"
    UNVERIFIED = "unverified"
    SETTLED = "settled"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Resource:
    scope: Scope
    kind: ResourceKind
    identity: str | int


@dataclass(frozen=True)
class DropProposal:
    name: str
    quantity: int
    item_id: str = ""

    def record(self):
        return dict(name=self.name, quantity=self.quantity, item_id=self.item_id)


@dataclass(kw_only=True)
class OwnedItems:
    depth: int
    cell: int
    branch: int = 0
    owner: str = ""
    dropped: dict = field(default_factory=dict)
    retrieved: dict = field(default_factory=dict)
    active: bool = True
    deferred_reason: str = ""
    unverified_drop: DropProposal | None = None
    owner_kind: str = "stash"
    obligation_kind: str = "unretrieved potion stash"

    @property
    def scope(self):
        return Scope(self.depth, self.branch)

    @property
    def outstanding(self):
        return {n: q-self.retrieved.get(n, 0) for n, q in self.dropped.items()
                if q > self.retrieved.get(n, 0)}

    @property
    def unresolved(self):
        return bool(self.outstanding or self.unverified_drop)

    def obligation(self, kind=None):
        return dict(kind=kind or self.obligation_kind, owner=self.owner, cell=self.cell, branch=self.branch,
                    confirmed_drops=dict(self.dropped), retrieved=dict(self.retrieved),
                    outstanding=self.outstanding,
                    unverified_drop=self.unverified_drop.record() if self.unverified_drop else None)

    def physical_record(self):
        status = PhysicalStatus.UNVERIFIED if self.unverified_drop else \
                 PhysicalStatus.OUTSTANDING if self.outstanding else \
                 PhysicalStatus.SETTLED if self.dropped else \
                 PhysicalStatus.PLANNED if self.active else PhysicalStatus.CANCELLED
        return dict(depth=self.depth, branch=self.branch, owner=self.owner,
                    status=status.value,
                    active=self.active, reason=self.deferred_reason,
                    obligation=self.obligation())


@dataclass
class PhysicalLedger:
    entries: dict = field(default_factory=dict)
    claims: dict = field(default_factory=dict)
    receipts: set = field(default_factory=set)
    sequence: int = 0

    def available(self, resource, owner=None):
        held = self.claims.get(resource)
        return held is None or held == owner

    def site_available(self, scope, cell, owner=None):
        return self.available(Resource(scope, ResourceKind.GROUND_SITE, cell), owner)

    def inventory_available(self, scope, item_ids, owner=None):
        return all(self.available(Resource(scope, ResourceKind.INVENTORY, i), owner)
                   for i in item_ids)

    def register(self, account, item_ids=()):
        """Atomically acquire claims; registration alone creates no item debt."""
        if not account.active and item_ids:
            return False
        owner = account.owner or f"{account.owner_kind}:{self.sequence+1}"
        if owner in self.entries and self.entries[owner] is not account:
            return False
        resources = [Resource(account.scope, ResourceKind.GROUND_SITE, account.cell)]
        resources += [Resource(account.scope, ResourceKind.INVENTORY, i) for i in item_ids]
        if any(not self.available(r, owner) for r in resources):
            return False
        if not account.owner:
            self.sequence += 1
            account.owner = owner
        self.entries[owner] = account
        for resource in resources:
            self.claims[resource] = owner
        return True

    def at(self, scope, cell):
        owner = self.claims.get(Resource(scope, ResourceKind.GROUND_SITE, cell))
        return self.entries.get(owner)

    def _release(self, account):
        for resource, owner in list(self.claims.items()):
            if owner == account.owner and (
                    resource.kind == ResourceKind.INVENTORY or not account.unresolved):
                del self.claims[resource]

    def defer(self, account, reason, pending=None):
        if self.entries.get(account.owner) is not account:
            raise ValueError("Cannot defer another owner's physical obligation")
        account.active = False
        account.deferred_reason = reason
        if pending:
            account.unverified_drop = pending
        self._release(account)

    def finish(self, account):
        if self.entries.get(account.owner) is not account:
            raise ValueError("Cannot release another owner's physical obligation")
        if account.unresolved:
            raise ValueError("Cannot release unfinished physical obligations")
        account.active = False
        self._release(account)

    def seen(self, scope, token):
        return token is not None and (scope, token) in self.receipts

    def remember(self, scope, token):
        if token is not None:
            self.receipts.add((scope, token))

    def pickup(self, account, name, quantity, token):
        if self.entries.get(account.owner) is not account \
                or self.seen(account.scope, token) or quantity <= 0 \
                or quantity > account.outstanding.get(name, 0):
            return False
        account.retrieved[name] = account.retrieved.get(name, 0)+quantity
        self.remember(account.scope, token)
        if not account.active:
            self._release(account)
        return True

    def deferred_records(self):
        return [dict(depth=a.depth, branch=a.branch, status="deferred-unfinished",
                     obligation=a.obligation(), reason=a.deferred_reason)
                for a in self.entries.values() if not a.active and a.unresolved]

    def records(self):
        return [a.physical_record() for a in self.entries.values()]

    def has_unresolved(self):
        return any(a.unresolved for a in self.entries.values())

    def claim_records(self):
        return [dict(depth=r.scope.depth, branch=r.scope.branch, kind=r.kind.value,
                     resource=r.identity, owner=owner) for r, owner in self.claims.items()]
