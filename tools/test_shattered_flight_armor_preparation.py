"""Run 96's public final room, reduced; not recovered runtime memory.

Pinned to played a289397d56392a51d5c23da5bd664d50d7ebd2b4,
decision 1692. Ordinary approach geometry is simplified.
"""
import copy
import unittest

from tools.mage_policy import MagePolicy
from tools.policy_geometry import distance, neighbors
from tools.priority_resources import choose, targets
from tools.room_tactics import plan_journey


def fixture():
    cells = {}
    # Public coordinates: open entrance 609, chasm 568, key 528,
    # locked chests 605/606/685/686; ordinary approach at 650.
    for y in range(12, 21):
        for x in range(2, 13):
            c = y * 40 + x
            terrain = 4
            if 13 <= y <= 19 and 3 <= x <= 8:
                terrain = 0
            if x in {10, 11, 12} and y >= 13:
                terrain = 1
            cells[c] = dict(cell=c, terrain=terrain, observed=True,
                            visible=True, effects=[])
    for c, terrain in {609:6, 523:14, 528:14, 763:14,
                       605:14, 606:14, 685:14, 686:14}.items():
        cells[c]["terrain"] = terrain
    armor = dict(id="leather", name="leather armor of potential", equipped=True,
                 identified=False, curse_known=True, known_cursed=False,
                 actions=["UNEQUIP", "DROP", "THROW"],
                 description="Typically this _tier-2_ armor blocks _0-4 damage_ and requires _12 strength_ to use properly.")
    cloth = dict(id="cloth", name="cloth armor", equipped=False,
                 identified=True, curse_known=True, known_cursed=False,
                 actions=["EQUIP", "DROP", "THROW"],
                 description="This _tier-1_ armor blocks _0-2 damage_ and requires _10 strength_ to use properly.")
    s = dict(scene="GameScene", status="ready", modal=False, depth=4,
             branch=0, danger_cells=[], ui=dict(texts=[], buttons=[]),
             hero=dict(cell=609, hp=45, max_hp=45, strength=12, buffs=[]),
             inventory=[armor, cloth, dict(id="flight", name="potion of levitation x2",
                 identified=True, quantity=2, actions=["DRINK", "DROP", "THROW"])],
             objects=[dict(cell=c, name="golden key",
                           top_item=dict(name="golden key", quantity=1))
                      for c in (523, 528, 763)] +
                     [dict(cell=c, name="Locked chest")
                      for c in (605, 606, 685, 686)],
             map=dict(width=40, height=38, cells=list(cells.values())))
    p = MagePolicy()
    p.update(s)
    return p, s


class FlightArmorPreparationTests(unittest.TestCase):
    def test_known_safe_armor_prepares_blocked_key_trip_without_receipting_it(self):
        p, s = fixture()
        before = copy.deepcopy(s)
        self.assertIsNone(plan_journey(p, s, [], neighbors,
                                      probe_kind="flight", plan_only=True))
        # An isolated alternative on a copy, not a fabricated observation
        # following our changed EQUIP proposal.
        alternate = copy.deepcopy(s)
        alternate["inventory"][0]["equipped"] = False
        alternate["inventory"][1]["equipped"] = True
        self.assertIsNotNone(plan_journey(p, alternate, [], neighbors,
                                         probe_kind="flight", plan_only=True))
        d = choose(p, s, [])
        self.assertIsNotNone(d, "Known cloth armor must unblock flight preparation")
        self.assertEqual(dict(type="item", id="cloth", action="EQUIP"), d.action)
        self.assertEqual(before, s)
        self.assertIn(528, targets(p))
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.completed_room_rewards)
        self.assertIsNone(p.room_journey)
        self.assertFalse(p.room_attempts)

    def test_unsafe_or_unnecessary_swaps_decline(self):
        for case in ("cursed-current", "unknown-current-curse", "cursed-spare",
                     "unknown-spare", "heavy-spare", "no-equip", "threat",
                     "danger", "wounded", "no-supply", "no-trip", "enemy",
                     "poison", "unseen-damage"):
            with self.subTest(case=case):
                p, s = fixture()
                worn, spare = s["inventory"][:2]
                if case == "cursed-current": worn["known_cursed"] = True
                elif case == "unknown-current-curse": worn["curse_known"] = False
                elif case == "cursed-spare": spare["known_cursed"] = True
                elif case == "unknown-spare": spare["identified"] = False
                elif case == "heavy-spare": s["hero"]["strength"] = 9
                elif case == "no-equip": spare["actions"] = []
                elif case == "threat": p.recent_threats[650] = dict(cell=650, name="sewer crab")
                elif case == "danger": s["danger_cells"] = [609]
                elif case == "wounded": s["hero"]["hp"] = 30
                elif case == "enemy": s["objects"].append(dict(cell=650, name="sewer crab"))
                elif case == "poison": s["hero"]["buffs"] = [dict(name="poison")]
                elif case == "unseen-damage": p.unseen_damage_turns = 2
                elif case == "no-supply": s["inventory"].pop()
                elif case == "no-trip":
                    for c in (568, 569, 608, 648, 649):
                        if c in p.tiles: p.tiles[c]["terrain"] = 4
                enemies = [o for o in s["objects"] if o["name"] == "sewer crab"]
                d = choose(p, s, enemies)
                self.assertFalse(d and d.action.get("action") == "EQUIP")
                self.assertIn(528, p.loot)
                self.assertFalse(p.loot_collection_receipts)


if __name__ == "__main__":
    unittest.main()
