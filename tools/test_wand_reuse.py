import unittest

from tools.test_challenge_systems import ready, item
from tools.wand_tactics import observe_wand_cast


class WandReuseTests(unittest.TestCase):
    def test_shot_history_capacity_guess_and_public_charge_updates_remain_distinct(self):
        s,p=ready()
        wand=dict(item("wand of magic missile","ZAP"),id="spare",curse_known=True,known_cursed=False,identified=False)
        s["inventory"].append(wand)
        s["ui"]={"texts":[]}
        for _ in range(4):
            p.use(wand,"ZAP","cast",target=25)
            observe_wand_cast(p,s)
        usage=p.wand_usage[wand["name"]]
        self.assertEqual(4,usage["successful_shots"])
        self.assertEqual(1,usage["burst_level_guess"])
        self.assertTrue(usage["estimate_only"])
        self.assertNotIn("visible_capacity",usage)
        s["ui"]["texts"]=["Your wand fizzles; it must not have enough charge."]
        p.use(wand,"ZAP","cast",target=25)
        observe_wand_cast(p,s)
        self.assertEqual(0,usage["visible_remaining"])
        wand["status"]="2/5"
        observe_wand_cast(p,s)
        self.assertEqual(2,usage["visible_remaining"])
        self.assertEqual(5,usage["visible_capacity"])
        self.assertEqual(2,usage["capacity_level_guess"])
        self.assertFalse(wand["identified"])
    def test_non_cursed_wand_needs_no_level_or_charge_identification_to_cast(self):
        s,p=ready()
        s["inventory"][0]["status"]="0/4"
        wand=dict(item("wand of magic missile","ZAP"),id="spare",curse_known=True,known_cursed=False,identified=False)
        s["inventory"].append(wand)
        action=p.best_attack(s,{"name":"gnoll scout","cell":26})
        self.assertEqual("ZAP",action.action.get("action"))
        self.assertEqual("spare",action.action["id"])
        self.assertFalse(wand["identified"])
    def test_known_uncursed_unknown_charge_wand_reuses_after_cast_but_not_fizzle(self):
        for fizzle in (False,True):
            s,p=ready()
            wand=dict(item("wand of magic missile","ZAP"),id="spare",curse_known=True)
            s["inventory"].append(wand)
            p.use(wand,"ZAP","ordinary cast",target=25)
            s["ui"]={"texts":["Your wand fizzles; it must not have enough charge."] if fizzle else []}
            observe_wand_cast(p,s)
            self.assertEqual(30 if fizzle else 0,p.unknown_magic_cooldowns[wand["name"]])
            self.assertIsNone(p.pending_wand_test)
