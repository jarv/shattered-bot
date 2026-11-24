"""Run 252: a spent crystal alternative must not reserve a trap-room supply.

Reduced public geometry/accepted key-spend sequence, not a gameplay completion.
"""
import copy
import unittest

from tools.keyed_rooms import record_spend, observe as observe_keys
from tools.puzzle_supplies import demands
from tools.policy_geometry import distance
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    s = state()
    s["hero"].update(cell=1039, hp=25, max_hp=25)
    terrain = {1039:14, 1038:1, 1037:14, 1008:18}
    s["map"] = dict(width=29, height=40, cells=[
        dict(cell=c, terrain=t, observed=True, visible=True,
             **({"trap":"worn dart trap"} if t==18 else {}))
        for c,t in terrain.items()])
    s["keys"] = [dict(name="Crystal key", depth=1, quantity=1)]
    s["objects"] = [
        dict(cell=1037, name="Crystal chest", description="You can see an artifact inside."),
        dict(cell=1039, name="Crystal chest", description="You can see a ring inside.")]
    p = verified()
    p.update(s)
    return s,p


def spend_last_key(s,p):
    record_spend(p,s,1039,"chest",{1037})
    after = copy.deepcopy(s)
    after["keys"] = []
    after["objects"][1] = dict(cell=1039,name="emerald ring",
                               top_item=dict(name="emerald ring",quantity=1))
    p.update(after)
    observe_keys(p,after)
    return after


class ResolvedChoiceSupplyTests(unittest.TestCase):
    def test_receipt_resolved_alternative_does_not_manufacture_flight_demand(self):
        s,p = fixture()
        self.assertIn("flight",{d.kind for d in demands(p,s,distance)})
        after = spend_last_key(s,p)
        self.assertIn(1037,p.resolved_crystal_alternatives)
        self.assertNotIn("flight",{d.kind for d in demands(p,after,distance)})
        self.assertIn(1037,p.loot)  # Physically present; not falsely collected.
        self.assertFalse(p.completed_room_rewards)
        self.assertFalse(p.strength_identified)

    def test_selected_but_unspent_choice_still_reserves_supply(self):
        s,p = fixture()
        record_spend(p,s,1039,"chest",{1037})
        observe_keys(p,s)
        self.assertFalse(p.resolved_crystal_alternatives)
        self.assertIn("flight",{d.kind for d in demands(p,s,distance)})

    def test_new_key_reopens_reward_and_its_supply_demand(self):
        s,p = fixture()
        after = spend_last_key(s,p)
        after["keys"] = s["keys"]
        p.update(after)
        observe_keys(p,after)
        self.assertFalse(p.resolved_crystal_alternatives)
        self.assertTrue(1037 in p.paths(after) or
                        "flight" in {d.kind for d in demands(p,after,distance)})

    def test_real_unresolved_reward_keeps_trap_and_gas_demands(self):
        s,p = fixture()
        after = spend_last_key(s,p)
        p.loot[1007] = dict(cell=1007,name="Chest")
        p.tiles[1007] = dict(cell=1007,terrain=14,observed=True,visible=True)
        p.room_blocked.add(1007)
        self.assertIn("flight",{d.kind for d in demands(p,after,distance)})
        p.tiles[1008].update(terrain=1,trap=None,effects=["cloud of toxic gas"])
        self.assertIn("gas",{d.kind for d in demands(p,after,distance)})


if __name__ == "__main__":
    unittest.main()
