"""Reduced public 000249 D3470/3471 inputs; local receipt memory only.

This is not recovered run memory or a gameplay replay.
"""
import copy
import unittest

from tools.combat_observation import observe_accepted_attack
from tools.dm100_escape import exposed_memory
from tools.policy_nodes import dm100_door_escape
from tools.policy_runtime import Context
from tools.test_challenge_rules import verified
from tools.test_survival_bot import state


def fixture():
    before = state()
    before.update(depth=9, branch=0)
    before["hero"].update(cell=611, hp=44, max_hp=75, level=11,
        hero_class="mage", talents=[dict(name="arcane vision", points=1)],
        buffs=[dict(name="starving")])
    before["inventory"] = [dict(id="item-0", name="staff of disintegration +4",
        identified=True, visible_upgrade=4, curse_known=True,
        known_cursed=False, equipped=True, status="3/7",
        actions=["ZAP", "DROP", "THROW", "UNEQUIP", "IMBUE"])]
    before["map"] = dict(width=33, height=55, cells=[
        dict(cell=c, terrain=1, visible=True, observed=True, effects=[])
        for c in (545, 578, 611, 643)])
    before["objects"] = [dict(cell=643, name="DM-100",
        health_bar=[10, 21], status_icons=[])]
    before["evaluation_stats"] = dict(experience=41,
        experience_to_level=60, elapsed_turns=3365)
    before["ui"]["texts"] = ["Badge unlocked: Expert Monster Hunter (Defeat 100 enemies in one game).",
        "You are starving!", "You picked up: turquoise potion.",
        "You collect the dewdrop into your waterskin.",
        "You picked up: seed of swiftthistle."]
    targeting = copy.deepcopy(before)
    targeting["status"] = "targeting"
    after = copy.deepcopy(before)
    after["objects"] = []
    after["inventory"][0]["status"] = "2/7"
    after["evaluation_stats"].update(experience=47, elapsed_turns=3366)
    return before, targeting, after


class StaffDisintegrationRetirementTests(unittest.TestCase):
    def accept(self, before, targeting, after, other_memory=False):
        p = verified()
        p.update(before)
        if other_memory:
            p.dm100_threat["cell"] = 673
        # Validate the two locally reconstructed attack inputs against D3470/3471.
        d = dm100_door_escape(Context(p, before, enemies=before["objects"]))
        self.assertEqual(d.action, dict(type="item", id="item-0", action="ZAP"))
        observe_accepted_attack(p, before, d, targeting)
        d = p.cell(643, "target")
        self.assertEqual(d.action, dict(type="cell", cell=643))
        observe_accepted_attack(p, targeting, d, after)
        return p

    def test_consumed_adjacent_staff_zap_retires_tracked_caster(self):
        before, targeting, after = fixture()
        p = self.accept(before, targeting, after)
        self.assertIsNone(p.dm100_threat)
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.cleared_floors)
        p.update(after)
        # Isolated alternative arbitration, no subsequent recorded inputs fed.
        probe = copy.deepcopy(after)
        probe["hero"]["cell"] = 578
        self.assertFalse(exposed_memory(p, probe))
        self.assertIsNone(dm100_door_escape(Context(p, probe)))

    def test_ambiguous_receipts_keep_memory(self):
        for mode in ("no-talent", "unknown", "cursed", "unknown-curse",
                     "no-charge", "capacity", "other-item", "other-id",
                     "range", "degrade", "survivor", "other-actor", "status",
                     "no-xp", "long-turn", "level", "floor", "branch",
                     "moved", "other-memory"):
            with self.subTest(mode=mode):
                before, targeting, after = fixture()
                item = targeting["inventory"][0]
                if mode == "no-talent": targeting["hero"]["talents"] = []
                elif mode == "unknown": item["identified"] = False
                elif mode == "cursed": item["known_cursed"] = True
                elif mode == "unknown-curse": item["curse_known"] = False
                elif mode == "no-charge": after["inventory"][0]["status"] = "3/7"
                elif mode == "capacity": after["inventory"][0]["status"] = "2/8"
                elif mode == "other-item": item["name"] = "staff of lightning +4"
                elif mode == "other-id": after["inventory"][0]["id"] = "item-99"
                elif mode == "range": targeting["hero"]["cell"] = after["hero"]["cell"] = 545
                elif mode == "degrade": targeting["hero"]["buffs"].append(dict(name="degraded"))
                elif mode == "survivor": after["objects"] = copy.deepcopy(before["objects"])
                elif mode == "other-actor": targeting["objects"].append(dict(name="skeleton", cell=578))
                elif mode == "status": targeting["objects"][0]["status_icons"] = ["terror"]
                elif mode == "no-xp": after["evaluation_stats"]["experience"] = 41
                elif mode == "long-turn": after["evaluation_stats"]["elapsed_turns"] = 3367
                elif mode == "level": after["hero"]["level"] = 12
                elif mode == "floor": after["depth"] = 10
                elif mode == "branch": after["branch"] = 1
                elif mode == "moved": after["hero"]["cell"] = 578
                p = self.accept(before, targeting, after, mode == "other-memory")
                self.assertIsNotNone(p.dm100_threat)


if __name__ == "__main__":
    unittest.main()
