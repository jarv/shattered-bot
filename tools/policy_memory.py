"""Tactic-owned memory and its lifetime, independent of API/UI code.

Floor-local fields declare their lifetime next to their default. Compatibility
properties let existing tactics/subclasses use p.target, p.tiles, etc.; each field
still has exactly one owner, also available as p.memory.<owner>.<field>.
"""
from collections import Counter
from dataclasses import dataclass, field, fields

try:
    from .policy_interaction import MenuPhase
except ImportError:
    from policy_interaction import MenuPhase

def local(factory):
    return field(default_factory=factory, metadata={"floor": True})


def value(default, *, floor=False):
    return field(default=default, metadata={"floor": floor})


@dataclass
class NavigationMemory:
    movement_batch_disabled: bool = value(False, floor=True)
    movement_batch_ready_at: float = value(0, floor=True)
    corruption_pending: object = value(None, floor=True)
    corruption_attempts: Counter = local(Counter)
    corruption_ready_at: dict = local(dict)
    maze_goals: dict = local(dict)
    completed_maze_cells: set = local(set)
    puzzle_hungry_frost: bool = value(False, floor=True)
    mapped_floors: set = field(default_factory=set)
    hungry_cooking_plan: object = value(None, floor=True)
    hungry_cooking_attempts: int = value(0, floor=True)
    well_cleanse_plan: object = value(None, floor=True)
    well_cleanse_attempts: set = local(set)
    rose_outfit_attempts: set = local(set)
    puzzle_flight_bank: object = value(None, floor=True)
    puzzle_sentry_bank: object = value(None, floor=True)
    artifact_extension_pending: object = value(None, floor=True)
    artifact_extension_attempts: Counter = local(Counter)
    artifact_pickup_routes: Counter = local(Counter)
    artifact_pickup_banks: dict = local(dict)
    puzzle_revisit_steps: Counter = local(Counter)
    known_burn_staging: Counter = local(Counter)
    friendly_passage_cells: set = local(set)
    unconfirmed_loot: dict = local(dict)
    loot_collection_receipts: set = local(set)
    burning_water_plan: object = value(None, floor=True)
    escape_commitment: object = value(None, floor=True)
    suspect_probe_plan: object = value(None, floor=True)
    suspect_failed_banks: set = local(set)
    suspect_staging_deferred: set = local(set)
    barrier_followup: object = value(None, floor=True)
    frost_view_plan: object = value(None, floor=True)
    frost_view_attempts: set = local(set)
    combat_deferred_loot: set = local(set)
    room_loot_plan: object = value(None, floor=True)
    room_loot_deferred: dict = local(dict)
    fire_buffer: set = local(set)
    fire_spread_buffer: set = local(set)
    depth: object = None
    tiles: dict = local(dict)
    loot: dict = local(dict)
    visits: Counter = local(Counter)
    exhausted: set = local(set)
    blocked: set = local(set)
    failed_moves: Counter = local(Counter)
    changed_door_cells: set = local(set)
    last_state: object = value(None, floor=True)
    previous_position: object = None
    keys: dict = field(default_factory=dict)
    room_actors: dict = local(dict)
    room_blocked: set = field(default_factory=set)
    room_skipped: set = field(default_factory=set)
    room_notes: list = field(default_factory=list)
    crystal_doors_seen: set = local(set)
    optional_locks: set = field(default_factory=set)
    neutral_actor_cells: set = field(default_factory=set)
    enemy_sightings: dict = local(dict)
    route_teleports: int = value(0, floor=True)


@dataclass
class ExplorationMemory:
    secret_search_goal: object = value(None, floor=True)
    corridor_tip_routes: Counter = local(Counter)
    trap_scan_cells: Counter = local(Counter)
    trap_scan_pending: object = value(None, floor=True)
    hazard_recheck_edges: Counter = local(Counter)
    hazard_recheck_pending: object = value(None, floor=True)
    secret_area_found: bool = value(False, floor=True)
    garden_steps: int = value(0, floor=True)
    garden_waits: int = value(0, floor=True)
    corridor_tip_searches: int = value(0, floor=True)
    exploration_goal: object = value(None, floor=True)
    exploration_declined: dict = local(dict)
    region_entry_anchor: object = value(None, floor=True)
    region_seen_anchors: set = local(set)
    searches: int = value(0, floor=True)
    wall_searches: Counter = local(Counter)
    searched_walls: set = local(set)
    secret_search_steps: int = value(0, floor=True)
    clear_steps: int = value(0, floor=True)
    drop_room_expected_on: set = field(default_factory=set)
    temporary_block_waits: int = value(0, floor=True)
    temporary_freeze_waits: int = value(0, floor=True)
    temporary_confusion_waits: int = value(0, floor=True)
    hazard_recheck_steps: int = value(0, floor=True)
    hazard_recheck_waits: int = value(0, floor=True)


@dataclass
class CombatMemory:
    seed_ready_at: dict = local(dict)
    seed_attempts: Counter = local(Counter)
    seed_pending: object = value(None, floor=True)
    multi_door_plan: object = value(None, floor=True)
    multi_door_attempts: Counter = local(Counter)
    multi_retreat_streak: int = value(0, floor=True)
    fly_attack_override: object = value(None, floor=True)
    fly_fallback_pending: object = value(None, floor=True)
    fly_fallback_attempts: Counter = local(Counter)
    multi_retreat_pending: object = value(None, floor=True)
    multi_retreat_edges: Counter = local(Counter)
    chain_setup_steps: int = value(0, floor=True)
    ranged_cover_waits: Counter = local(Counter)
    ranged_plan: object = value(None, floor=True)
    trickster_reposition: bool = value(False, floor=True)
    hunger_projection: object = value(None)
    ranged_failed_cover: set = local(set)
    unit_cover_moves: Counter = local(Counter)
    unit_pursuit_moves: Counter = local(Counter)
    unit_pending_movement: object = value(None, floor=True)
    incoming_damage_samples: dict = local(dict)
    weak_crab_finish_casts: int = value(0, floor=True)
    pursuit_outcome: object = value(None, floor=True)
    pursuit_reassessed_move: int = value(0, floor=True)
    pursuit_lure_exhausted: bool = value(False, floor=True)
    boxed_snake_escape: object = value(None, floor=True)
    boxed_snake_escape_uses: int = value(0, floor=True)
    fly_escape_plan: object = value(None, floor=True)
    pursuit_retreat_moves: int = value(0, floor=True)
    pursuit_interventions: int = value(0, floor=True)
    pursuit_last_intervention_move: int = value(0, floor=True)
    pursuit_quiet_moves: int = value(0, floor=True)
    soft_failures: Counter = local(Counter)
    soft_recovery_edges: Counter = local(Counter)
    snake_route: object = value(None, floor=True)
    snake_route_inputs: int = value(0, floor=True)
    snake_route_edges: Counter = local(Counter)
    damage_samples: dict = local(dict)
    damage_pending: object = value(None, floor=True)
    mimic_obligations: dict = local(dict)
    snake_door_reset: object = value(None, floor=True)
    snake_door_resets: Counter = local(Counter)
    mimic_kites: int = value(0, floor=True)
    recent_threats: dict = local(dict)
    combat_waits: Counter = field(default_factory=Counter)
    ambush_plan: object = value(None, floor=True)
    ambush_attempts: Counter = local(Counter)
    snake_melee_attempts: Counter = local(Counter)
    unknown_magic_cooldowns: Counter = field(default_factory=Counter)
    wand_test_retreat: object = value(None, floor=True)
    pending_wand_test: object = None
    necro_moves: int = value(0, floor=True)
    necro_blocker_attacks: int = value(0, floor=True)
    skeleton_retreats: int = value(0, floor=True)
    necro_escape_target: object = value(None, floor=True)
    critical_retreats: int = value(0, floor=True)
    invisible_withdraw_steps: int = value(0, floor=True)
    combat_approach_target: object = value(None, floor=True)
    combat_approach_steps: int = value(0, floor=True)


@dataclass
class ResourceMemory:
    wood_burn_plan: object = value(None, floor=True)
    wood_probe_attempts: Counter = local(Counter)
    inventory_pressure: object = value(None, floor=True)
    inventory_disposal_pending: object = value(None, floor=True)
    inventory_drop_count: int = value(0, floor=True)
    intentional_discards: dict = local(dict)
    trap_attempts: set = local(set)
    freeze_batches: int = value(0, floor=True)
    natural_healing_waits: int = value(0, floor=True)
    food_freeze_plan: object = value(None, floor=True)
    deferred_room_controllers: set = local(set)
    wand_usage: dict = field(default_factory=dict)
    wand_observation_clock: int = 0
    trap_payload_return: object = value(None, floor=True)
    food_recovery_until: int = value(0, floor=True)
    food_recovery_source: object = value(None, floor=True)
    transfusion_names: set = local(set)
    potion_stash: object = value(None, floor=True)
    rests: int = value(0, floor=True)
    meat_plan: object = value(None, floor=True)
    enchant_target: object = None
    enchant_choice: bool = False
    seed_plan: object = value(None, floor=True)
    seed_cooldown: int = value(0, floor=True)
    consumable_sources: dict = field(default_factory=dict)
    consumable_inventory_counts: dict = field(default_factory=dict)
    consumable_cooldown: int = 0
    consumable_menu_bags: set = field(default_factory=set)
    tested_scrolls: set = field(default_factory=set)
    failed_identify_context: object = None
    upgrade_known: bool = False
    upgrade_target: object = None


@dataclass
class ShopMemory:
    sell_plan: object = value(None, floor=True)
    shop_plan: object = value(None, floor=True)
    purchases: list = field(default_factory=list)
    allowed_chests: set = field(default_factory=set)
    entrance_cell: object = None
    entrance_doors_checked: set = local(set)
    entrance_visit_steps: int = value(0, floor=True)
    shop_visited_floors: set = field(default_factory=set)


@dataclass
class InteractionMemory:
    target: object = None
    menu_plan: MenuPhase | None = None
    tutorial_read: bool = False

    def __setattr__(self, name, value):
        if name == "menu_plan" and value is not None:
            value = MenuPhase(value)
        object.__setattr__(self, name, value)


@dataclass
class RunMemory:
    inventory_events: list = field(default_factory=list)
    continuation_errors: list = field(default_factory=list)
    missed_loot: list = field(default_factory=list)
    deferred_obligations: list = field(default_factory=list)
    cleared_floors: list = field(default_factory=list)
    last_decision: object = None
    boss_seen: bool = False
    max_depth: int = 0
    defeated_bosses: set = field(default_factory=set)


@dataclass
class PolicyMemory:
    navigation: NavigationMemory = field(default_factory=NavigationMemory)
    exploration: ExplorationMemory = field(default_factory=ExplorationMemory)
    combat: CombatMemory = field(default_factory=CombatMemory)
    resources: ResourceMemory = field(default_factory=ResourceMemory)
    shop: ShopMemory = field(default_factory=ShopMemory)
    interaction: InteractionMemory = field(default_factory=InteractionMemory)
    run: RunMemory = field(default_factory=RunMemory)

    def reset_floor(self, entrance):
        for owner in fields(self):
            memory = getattr(self, owner.name)
            defaults = type(memory)()
            for item in fields(memory):
                if item.metadata.get("floor"):
                    setattr(memory, item.name, getattr(defaults, item.name))
        self.shop.entrance_cell = entrance


def owns_memory(cls):
    """Expose old field names as explicit properties, not duplicate storage."""
    names = set()
    for owner in fields(PolicyMemory):
        for item in fields(owner.type):
            if item.name in names or hasattr(cls, item.name):
                raise TypeError(f"Duplicate policy memory field: {item.name}")
            names.add(item.name)

            def get(self, group=owner.name, name=item.name):
                return getattr(getattr(self.memory, group), name)

            def set_(self, value, group=owner.name, name=item.name):
                setattr(getattr(self.memory, group), name, value)

            setattr(cls, item.name, property(get, set_, doc=f"Alias for memory.{owner.name}.{item.name}"))
    return cls
