"""Run 000234 D2815 public reduction; hold bookkeeping is explicit fixture setup.

Not a gameplay replay or a reconstruction of complete original runtime memory.
"""
import copy
import unittest

from tools.doorway_tactics import hold_doorway
from tools.policy_geometry import distance, neighbors, line_clear
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s.update(depth=8, branch=0)
    s["hero"].update(cell=283, hp=33, max_hp=60, strength=13,
                     buffs=[dict(name="hungry"), dict(name="wands empowered"),
                            dict(name="magic charge")])
    terrain = {240: 1, 241: 1, 242: 1, 243: 1, 244: 4,
               280: 1, 281: 1, 282: 6, 283: 1, 284: 2, 285: 2,
               318: 1, 319: 1, 320: 4, 321: 4, 322: 4}
    s["map"] = dict(width=38, height=46, cells=[
        dict(cell=c, terrain=t, observed=True, visible=True, effects=[])
        for c, t in terrain.items()])
    s["inventory"] = [dict(
        id="item-0", name="staff of magic missile +3", status="1/7",
        equipped=True, identified=True, curse_known=True, known_cursed=False,
        actions=["DROP", "THROW", "UNEQUIP", "IMBUE", "ZAP"],
        description="This _tier-1_ melee weapon deals _4-12 damage_ and "
                    "requires _8 strength_ to use properly. Because of your "
                    "excess strength, you will deal _0-5 bonus damage_ with "
                    "this weapon. Each bolt from this wand deals _5-14 damage_.")]
    s["objects"] = [
        dict(name="necromancer", cell=240, health_bar=[16, 21], status_icons=[]),
        dict(name="necromancer's skeleton", cell=282, health_bar=[13, 16],
             status_icons=["adrenaline"],
             description="This skeleton has been summoned by a necromancer. "
                         "It behaves just like a regular skeleton, and will "
                         "die when the necromancer which summoned it is slain.")]
    p = verified()
    p.update(s)
    # D2813 retreat and D2814 entry strike establish this reduced hold.
    p.previous_position = 283
    p.doorway_hold = dict(depth=8, door=282, hide=283, inputs=1, quiet=0, waits=0)
    return s, p


def hold(s, p):
    return hold_doorway(p, s, s["objects"], distance, neighbors, line_clear)


class DoorwayLinkedSkeletonTests(unittest.TestCase):
    def test_adrenalized_linked_skeleton_uses_skeleton_ranged_preference(self):
        s, p = fixture()
        original = copy.deepcopy(s)
        self.assertFalse(p.shot_clear(s, 240))  # No invented shot at its caster.
        self.assertEqual("summoner", p.unit_strategies.profile(s["objects"][1]).strategy)
        self.assertEqual(dict(type="cell", cell=282),
                         copy.deepcopy(p).best_attack(s, s["objects"][1]).action)
        self.assertEqual(dict(type="item", id="item-0", action="ZAP"), hold(s, p).action)
        self.assertEqual(282, p.target)
        self.assertEqual(original, s)
        self.assertEqual(2, p.doorway_hold["inputs"])
        self.assertFalse(p.cleared_floors)

    def test_full_selector_uses_same_stationary_attack(self):
        s, p = fixture()
        self.assertEqual("ZAP", p.choose(s).action.get("action"))
        self.assertEqual(282, p.target)

    def test_without_admitted_ranged_attack_keep_existing_melee(self):
        s, p = fixture()
        s["inventory"][0].update(status="0/7", actions=["IMBUE"])
        self.assertEqual(dict(type="cell", cell=282), hold(s, p).action)
        self.assertIsNone(p.target)

    def test_flank_still_abandons_hold(self):
        s, p = fixture()
        s["objects"].append(dict(name="skeleton", cell=284))
        self.assertIsNone(hold(s, p))
        self.assertIsNone(p.doorway_hold)

    def test_first_surprise_and_unboosted_target_are_unchanged(self):
        for mode in ("first", "ordinary", "disabled", "unboosted", "missing-icons"):
            with self.subTest(mode=mode):
                s, p = fixture()
                if mode == "first":
                    p.previous_position = 282
                    s["hero"]["hp"] = 36
                elif mode == "ordinary":
                    s["objects"][1]["name"] = "gnoll scout"
                elif mode == "unboosted":
                    s["objects"][1]["status_icons"] = []
                elif mode == "missing-icons":
                    s["objects"][1].pop("status_icons")
                else:
                    p.unit_strategies_enabled = False
                self.assertEqual(dict(type="cell", cell=282), hold(s, p).action)


if __name__ == "__main__":
    unittest.main()
