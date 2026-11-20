"""The policy's priority contract. Read this before changing arbitration.

The ordering intentionally matches the original engines, including preparation
before combat against sleepers and boss/special-enemy safety before utility AI.
"""
try:
    from .policy_runtime import Leaf, Selector
    from . import policy_nodes as n
except ImportError:
    from policy_runtime import Leaf, Selector
    import policy_nodes as n


POLICY = Selector("survival", (
    Selector("immediate-safety", (
        Leaf("toxic-gas-escape", n.toxic_gas),
        Leaf("burning-recovery", n.burning),
        Leaf("hazardous-room-escape", lambda c: c.policy.escape_special_room(c.state)),
        Leaf("boss-telegraph", n.boss_escape),
        Leaf("warning-escape", n.warned_cell),
        Leaf("harmful-effect-escape", n.harmful_effect),
        Leaf("dm100-door-escape", n.dm100_door_escape),
    )),
    Selector("survival-and-preparation", (
        Leaf("rule-preparation", lambda c: c.policy.preparation(c.state, c.enemies)),
        Leaf("healing-well", n.well),
        Leaf("emergency-healing", n.healing),
        Leaf("multi-threat-emergency-item", lambda c: n.emergency_consumable(c)
              if getattr(c.policy,'unit_strategies_enabled',False) and len(c.active)>1 else None),
        Leaf("critical-transport", n.critical_transport),
        Leaf("corruption-control", n.corruption),
        Leaf("multi-threat-retreat", n.multi_threat_retreat),
        Leaf("equipped-curse", n.cleanse),
        Leaf("rinse", n.rinse),
        Leaf("invisible-withdrawal", n.invisible_escape),
        Leaf("ranged-survival", n.ranged_survival),
        Leaf("starvation", n.starvation),
        Leaf("priority-progression-pickup", n.priority_resource),
        Leaf("piranha-room-supplies", n.piranha_supplies),
        Leaf("ghost-reward", n.ghost_reward),
        Leaf("wandmaker-quest", n.wandmaker),
        Leaf("exhausted-room-supply-descent", n.exhausted_room_descent),
        Leaf("blandfruit", n.blandfruit),
        Leaf("peaceful-preparation", n.peaceful_preparation),
    )),
    Selector("combat-and-tactics", (
        Leaf("emergency-consumable", n.emergency_consumable),
        Leaf("seed-preparation", n.seed_preparation),
        Leaf("combat-mode", n.select_combat_mode),
        Leaf("combat-override", lambda c: c.policy.combat_override(c.state, c.enemies)),
        Leaf("melee-funnel", n.funnel),
        Leaf("necromancer", n.necromancer),
        Leaf("skeleton-spacing", n.skeleton),
        Leaf("ranged-gap-close", n.zapper),
        Leaf("combat-consumable", n.consumable),
        Leaf("critical-withdrawal", n.critical_withdrawal),
        Leaf("unit-engagement", n.unit_engagement),
        Leaf("wand-probe", n.wand_probe),
        Leaf("seed-tactic", n.seed),
        Leaf("temporary-blockage", lambda c: c.policy.temporary_blockage(c.state, c.enemies)),
        Leaf("utility-combat", n.tactical),
        Leaf("continue-ambush", n.continue_ambush),
        Leaf("engagement", n.select_engagement),
        Leaf("cursed-weapon-combat", n.cursed_combat),
        Leaf("wraith", n.wraith),
        Leaf("snake", n.snake),
        Leaf("talent", n.talent),
        Leaf("require-staff", n.require_staff),
        Leaf("boss-combat", n.boss_combat),
        Leaf("ordinary-combat", n.ordinary_combat),
    )),
    Leaf("preparation-and-recovery", n.preparation_and_recovery),
    Leaf("exploration", n.exploration),
))
