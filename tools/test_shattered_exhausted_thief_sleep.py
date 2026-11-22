"""Run 000119 decision 2756: reduced public scene, not a gameplay replay."""
import unittest
from unittest.mock import patch

from tools.test_challenge_rules import verified
from tools.policy_decision import NoSafeAction
from tools import unit_strategies


def fixture():
    # The four accepted species-budget receipts are recorded at decisions
    # 2290, 2293, 2294 and 2295. This is explicit fixture bookkeeping, not
    # a reconstruction of the complete original runtime memory.
    s = dict(
        scene="GameScene", status="ready", modal=False, depth=6, branch=0,
        danger_cells=[], ui=dict(texts=[], buttons=[]),
        hero=dict(name="mage", hero_class="mage", cell=1099, hp=55,
                  max_hp=55, strength=13, level=8, gold=153,
                  buffs=[dict(name="hungry"), dict(name="barrier")], talents=[]),
        inventory=[
            dict(id="item-0", name="staff of magic missile +2", status="0/6",
                 equipped=True, identified=True, curse_known=True,
                 known_cursed=False, actions=["DROP", "THROW", "UNEQUIP", "IMBUE"],
                 description="This tier-1 melee weapon deals 3-10 damage and requires 9 strength."),
            dict(id="item-13", name="stone of deep sleep", identified=True,
                 actions=["DROP", "THROW"], quantity=1),
        ],
        map=dict(width=45, height=45, cells=[
            dict(cell=c, terrain=1, visible=True, observed=True, effects=[])
            for c in (1099, 1100, 1101, 1102, 1150)]),
        objects=[
            dict(cell=1100, name="gold", top_item=dict(name="gold")),
            dict(cell=1101, name="crazy thief", health_bar=[2, 16], status_icons=[]),
            dict(cell=1101, name="bolas", top_item=dict(name="bolas")),
            dict(cell=1150, name="shuriken", top_item=dict(name="shuriken")),
        ],
    )
    p = verified()
    p.update(s)
    p.unit_pursuit_moves["crazy thief"] = 4
    return s, p, s["objects"][1]


def select(s, p, foe):
    try:
        return unit_strategies.choose(p, s, [foe])
    except NoSafeAction:
        return None


class ExhaustedThiefSleepTests(unittest.TestCase):
    def test_full_selector_reaches_disable_before_no_safe_action(self):
        s, p, foe = fixture()
        try:
            decision = p.choose(s)
        except NoSafeAction:
            decision = None
        self.assertIsNotNone(decision, "The selecting controller must retain the known disable")
        self.assertEqual(dict(type="item", id="item-13", action="THROW"), decision.action)
        self.assertEqual("unit-engagement", decision.controller)
        self.assertEqual(foe["cell"], p.target)

    def test_known_sleep_is_not_excluded_by_full_health_or_spent_pursuit(self):
        s, p, foe = fixture()
        decision = select(s, p, foe)
        self.assertIsNotNone(decision, "Known single-target disable must precede thief exhaustion")
        self.assertEqual(dict(type="item", id="item-13", action="THROW"), decision.action)
        self.assertEqual(1101, p.target)
        self.assertEqual(4, p.unit_pursuit_moves["crazy thief"])
        self.assertIsNone(p.unit_pending_movement)
        self.assertEqual(8, p.stone_cooldown)
        self.assertNotIn("sleeping", foe)  # Selecting is not an effect receipt.

    def test_refusals_preserve_terminal_exhaustion_and_budget(self):
        for mode in ("missing", "unknown", "unthrowable", "cooldown", "danger",
                     "blocked", "unseen", "target_veto", "item_veto"):
            with self.subTest(mode=mode):
                s, p, foe = fixture()
                stone = s["inventory"][1]
                if mode == "missing": s["inventory"].remove(stone)
                if mode == "unknown": stone["identified"] = False
                if mode == "unthrowable": stone["actions"] = ["DROP"]
                if mode == "cooldown": p.stone_cooldown = 1
                if mode == "danger": s["danger_cells"] = [1099]
                if mode == "blocked": p.tiles[1100]["terrain"] = 4
                if mode == "unseen": p.tiles[1101]["visible"] = False
                with patch.object(p, "target_allowed", return_value=mode != "target_veto"), \
                     patch.object(p, "item_action_allowed", return_value=mode != "item_veto"):
                    self.assertIsNone(select(s, p, foe))
                self.assertEqual(4, p.unit_pursuit_moves["crazy thief"])
                self.assertIsNone(p.unit_pending_movement)

    def test_lone_and_exhausted_scope(self):
        s, p, foe = fixture()
        p.unit_pursuit_moves["crazy thief"] = 3
        # Refuse the existing route using real loot geometry; do not extend
        # the new fallback to every ordinary failure to find a chase route.
        self.assertIsNone(select(s, p, foe))
        p.unit_pursuit_moves["crazy thief"] = 4
        with self.assertRaises(NoSafeAction):
            unit_strategies.choose(p, s, [foe, dict(name="crazy thief", cell=1102)])
        self.assertEqual(0, p.stone_cooldown)

    def test_adjacent_melee_still_precedes_disable(self):
        s, p, foe = fixture()
        foe["cell"] = 1100
        decision = select(s, p, foe)
        self.assertEqual(dict(type="cell", cell=1100), decision.action)
        self.assertEqual(0, p.stone_cooldown)


if __name__ == "__main__":
    unittest.main()
