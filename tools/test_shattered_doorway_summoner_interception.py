"""Reduced public run 000129 decisions 3613-3614, not runtime-memory replay."""
import copy
import unittest

from tools.doorway_tactics import hold_doorway
from tools.policy_geometry import distance, neighbors, line_clear
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=8, branch=0)
    s["hero"].update(cell=535, hp=32, max_hp=65, strength=12)
    terrain = {528: 2, 529: 2, 530: 2, 531: 2, 532: 1, 533: 2,
               534: 6, 535: 2, 536: 2, 537: 5,
               492: 4, 493: 4, 494: 4, 576: 4, 577: 2, 578: 4}
    s["map"] = dict(width=42, height=37, cells=[
        dict(cell=c, terrain=t, observed=True, visible=True, effects=[])
        for c, t in terrain.items()])
    s["inventory"] = [dict(
        id="item-0", name="staff of magic missile +4", status="1/8",
        equipped=True, identified=True, curse_known=True, known_cursed=False,
        actions=["DROP", "THROW", "UNEQUIP", "IMBUE", "ZAP"],
        description="This _tier-1_ melee weapon deals _5-14 damage_ and "
                    "requires _8 strength_. Each bolt deals _6-16 damage_.")]
    s["objects"] = [dict(name="necromancer", cell=529, health_bar=[9, 21])]
    p = verified()
    p.update(s)
    # Explicit fixture setup from the earlier accepted retreat/hold inputs.
    # This is not a claim to recover the original complete runtime memory.
    p.previous_position = 535
    p.doorway_hold = dict(depth=8, door=534, hide=535,
                          inputs=6, quiet=0, waits=0)
    return s, p


def hold(s, p):
    return hold_doorway(p, s, s["objects"], distance, neighbors, line_clear)


class DoorwaySummonerInterceptionTests(unittest.TestCase):
    def test_recorded_lone_caster_gets_stationary_admitted_shot_not_free_wait(self):
        s, p = fixture()
        original = copy.deepcopy(s)
        d = hold(s, p)
        self.assertEqual(dict(type="item", id="item-0", action="ZAP"), d.action)
        self.assertEqual(529, p.target)
        self.assertEqual(original, s)
        self.assertEqual(0, p.doorway_hold["waits"])
        self.assertEqual(7, p.doorway_hold["inputs"])
        self.assertFalse(p.cleared_floors)

    def test_full_selector_preparation_does_not_preempt_with_wait(self):
        s, p = fixture()
        self.assertEqual("ZAP", p.choose(s).action.get("action"))
        self.assertEqual(529, p.target)

    def test_prior_entry_summon_still_receives_recorded_hold_attack(self):
        s, p = fixture()
        s["hero"]["hp"] = 41
        s["objects"][0]["cell"] = 528
        s["objects"].append(dict(name="necromancer's skeleton", cell=534,
                                 health_bar=[6, 16]))
        self.assertEqual(dict(type="cell", cell=534), hold(s, p).action)

    def test_no_charge_or_blocked_shot_does_not_invent_movement(self):
        for mode in ("empty", "blocked"):
            with self.subTest(mode=mode):
                s, p = fixture()
                if mode == "empty":
                    s["inventory"][0].update(status="0/8", actions=["IMBUE"])
                else:
                    p.tiles[534]["terrain"] = 5
                self.assertEqual(dict(type="wait"), hold(s, p).action)
                self.assertIsNone(p.target)

    def test_ordinary_pursuer_and_observed_protection_keep_existing_wait(self):
        for mode in ("ordinary", "invisible"):
            with self.subTest(mode=mode):
                s, p = fixture()
                if mode == "ordinary":
                    s["objects"][0]["name"] = "gnoll scout"
                else:
                    s["hero"]["buffs"] = [dict(name="invisible")]
                self.assertEqual(dict(type="wait"), hold(s, p).action)

    def test_flanking_still_invalidates_hold_before_interception(self):
        s, p = fixture()
        s["objects"].append(dict(name="skeleton", cell=536))
        self.assertIsNone(hold(s, p))
        self.assertIsNone(p.doorway_hold)

    def test_unseen_caster_or_remaining_minion_cannot_use_new_interception(self):
        for mode in ("unseen", "minion", "disabled"):
            with self.subTest(mode=mode):
                s, p = fixture()
                if mode == "unseen":
                    p.tiles[529]["visible"] = False
                elif mode == "minion":
                    s["objects"].append(dict(name="necromancer's skeleton",
                                             cell=531))
                else:
                    p.unit_strategies_enabled = False
                self.assertEqual(dict(type="wait"), hold(s, p).action)
                self.assertIsNone(p.target)


if __name__ == "__main__":
    unittest.main()
