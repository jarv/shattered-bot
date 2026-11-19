import unittest

from tools.combat_items import equipment_upgrade, magic_score, physical_score
from tools.survival_bot import Finished, SurvivalPolicy
from tools.test_survival_bot import state


def gear(name, kind="melee", low=2, high=10, strength=10, **fields):
    phrase = {"melee": "melee weapon deals", "thrown": "thrown weapons deals", "armor": "armor blocks"}[kind]
    return dict(id=name, name=name, description=f"Typically this {phrase} _{low}-{high} damage_ and requires _{strength} strength_.",
                actions=["THROW"] if kind == "thrown" else ["EQUIP"], **fields)


def wand(name="wand of frost", low=2, high=8, **fields):
    return dict(id=name, name=name, description=f"Typically deals _{low}-{high} damage_.", actions=["ZAP"], **fields)


class ArsenalTests(unittest.TestCase):
    def test_usable_throwing_club_is_used_at_range(self):
        s=state();s['hero']['strength']=11
        club=gear('throwing club',kind='thrown',low=4,high=8,strength=11)
        s['inventory']=[club]
        enemy={'name':'gnoll scout','cell':26};s['objects']=[enemy]
        p=SurvivalPolicy();p.update(s)
        action=p.best_attack(s,enemy)
        self.assertEqual('THROW',action.action['action'])
        self.assertEqual('throwing club',action.action['id'])
        self.assertTrue(p.planner.report['thrown_weapon_options'][0]['eligible_strength'])

    def test_overstrength_throwing_club_is_logged_not_silently_used(self):
        s=state();s['hero']['strength']=10
        s['inventory']=[gear('throwing club',kind='thrown',low=4,high=8,strength=11)]
        enemy={'name':'gnoll scout','cell':26};s['objects']=[enemy]
        p=SurvivalPolicy();p.update(s)
        self.assertIsNone(p.best_attack(s,enemy))
        self.assertFalse(p.planner.report['thrown_weapon_options'][0]['eligible_strength'])

    def test_publicly_passive_gnoll_exile_is_not_an_ordinary_combat_target(self):
        s, p = state(), SurvivalPolicy()
        s["objects"] = [{"cell": 25, "name": "gnoll exile", "description":
                         "The gnoll exile isn't moving to attack. It doesn't seem as aggressive as the other gnolls."}]
        d = p.choose(s)
        self.assertFalse(d.reason.startswith("combat:"), d.reason)
        self.assertIn(25, p.neutral_actor_cells)
        self.assertNotIn(25, p.enemy_sightings)

    def test_provoked_gnoll_exile_without_passive_notice_is_fought(self):
        s = state()
        s["objects"] = [{"cell": 25, "name": "gnoll exile", "description": "This gnoll looks ready to fight."}]
        self.assertTrue(SurvivalPolicy().choose(s).reason.startswith("combat:"))

    def test_empty_magic_snake_can_use_known_invisibility_for_surprise(self):
        s, p = state(), SurvivalPolicy()
        s["inventory"][0]["status"] = "0/4"
        s["inventory"].append({"id": "invisible", "name": "potion of invisibility", "actions": ["DRINK"]})
        s["objects"] = [{"cell": 25, "name": "sewer snake"}]
        p.update(s)
        self.assertEqual("invisible", p.snake_combat(s, s["objects"], "").action["id"])
        d = p.snake_combat(s, s["objects"], "invisible")
        self.assertEqual("snake: surprise attack", d.reason)
        self.assertEqual(25, d.action["cell"])

    def test_hermit_crab_is_fought_instead_of_rested_beside(self):
        s = state()
        s["hero"]["hp"] = 12
        s["objects"] = [{"cell": 25, "name": "hermit crab", "health_bar": [36, 43]}]
        d = SurvivalPolicy().choose(s)
        self.assertTrue(d.reason.startswith("combat:"), d.reason)
        self.assertEqual("ZAP", d.action.get("action"))

    def test_public_variant_names_are_not_mistaken_for_loot(self):
        for name in ("hermit crab", "fungal spinner", "gnoll guard", "modified DM-100", "dwarven skeleton"):
            with self.subTest(name=name):
                s = state()
                s["objects"] = [{"cell": 25, "name": name}]
                self.assertTrue(SurvivalPolicy().choose(s).reason.startswith("combat:"))

    def setUp(self):
        self.s = state()
        self.s["hero"]["strength"] = 10

    def test_strength_required_for_armor_and_weapons(self):
        for kind in ("armor", "melee"):
            with self.subTest(kind=kind):
                self.s["inventory"].append(gear(kind, kind, strength=12))
                self.assertIsNone(equipment_upgrade(self.s))
                self.s["hero"]["strength"] = 12
                self.assertEqual(kind, equipment_upgrade(self.s)["name"])
                self.s["inventory"].pop()
                self.s["hero"]["strength"] = 10

    def test_better_armor_equips_before_identification(self):
        self.s["inventory"] += [gear("cloth", "armor", high=2, equipped=True),
                                gear("leather", "armor", high=6, identified=False)]
        self.assertEqual("leather", equipment_upgrade(self.s)["name"])
        self.assertEqual("EQUIP", SurvivalPolicy().choose(self.s).action["action"])

    def test_does_not_downgrade_or_replace_known_cursed_equipped_item(self):
        current = gear("current", high=20, equipped=True)
        self.s["inventory"] += [current, gear("weak")]
        self.assertIsNone(equipment_upgrade(self.s))
        current.update(known_cursed=True)
        self.s["inventory"].append(gear("strong", high=40))
        self.assertIsNone(equipment_upgrade(self.s))

    def test_known_cursed_candidates_are_never_equipped(self):
        self.s["inventory"].append(gear("cursed", high=40, known_cursed=True))
        self.assertIsNone(equipment_upgrade(self.s))

    def test_small_unknown_weapon_gain_does_not_risk_binding_curse(self):
        self.s["inventory"] = [gear("staff +2", low=3, high=10, strength=9, equipped=True),
                               gear("shortsword", low=2, high=15, strength=12, identified=False)]
        self.s["hero"]["strength"] = 12
        self.assertIsNone(equipment_upgrade(self.s))
        self.s["inventory"][1]["curse_known"] = True
        self.assertEqual("shortsword", equipment_upgrade(self.s)["name"])

    def test_substantial_unknown_weapon_gain_can_still_be_tried(self):
        self.s["inventory"] = [gear("staff", low=1, high=5, equipped=True),
                               gear("strong sword", low=5, high=15, identified=False)]
        self.assertEqual("strong sword", equipment_upgrade(self.s)["name"])

    def test_ring_fills_empty_slot_even_if_unidentified_artifacts_use_own_controller(self):
        ring = {"id": "ring", "name": "ring of energy", "identified": True, "actions": ["EQUIP"]}
        self.s["inventory"].append(ring)
        self.assertIs(ring, equipment_upgrade(self.s))
        ring["identified"] = False
        self.assertIs(ring,equipment_upgrade(self.s))
        ring.update(name="talisman of foresight", identified=True)
        self.assertIsNone(equipment_upgrade(self.s))

    def test_weapon_speed_affects_damage_per_time(self):
        fast = gear("fast")
        slow = gear("slow")
        fast["description"] += " This is a very fast weapon."
        slow["description"] += " This is a rather slow weapon."
        self.assertGreater(physical_score(fast, 10), physical_score(slow, 10))

    def test_unidentified_unknown_charge_wand_can_be_used(self):
        self.assertGreater(magic_score(wand(identified=False, status=None)), 0)
        self.assertGreater(magic_score(wand(status="?/3")), 0)

    def test_empty_or_known_cursed_wands_cannot_be_used(self):
        self.assertEqual(0, magic_score(wand(status="0/3")))
        self.assertEqual(0, magic_score(wand(known_cursed=True)))

    def test_low_hp_prefers_reliable_magic_over_small_nominal_melee_advantage(self):
        s, p = state(), SurvivalPolicy()
        s["hero"]["strength"] = 13
        s["inventory"] = [gear("staff +3", low=4, high=12, strength=8, equipped=True),
                          wand(low=5, high=14, status="6/7")]
        enemy = {"cell": 25, "name": "prison guard"}
        p.update(s)
        self.assertEqual("cell", p.best_attack(s, enemy).action["type"])
        s["hero"]["hp"] = 8
        self.assertEqual("ZAP", p.best_attack(s, enemy).action["action"])

    def test_unknown_charge_probe_does_not_repeat_immediately_after_fizzle(self):
        p = SurvivalPolicy()
        item = wand(status=None)
        self.s["inventory"] = [item]
        self.assertEqual([item], p.charged_magic(self.s))
        p.use(item, "ZAP", "probe unknown charge", target=26)
        self.assertEqual([], p.charged_magic(self.s))
        item["status"] = "2/3"
        self.assertEqual([item], p.charged_magic(self.s))

    def test_unsafe_wands_are_not_selected(self):
        for name in ("corrosion", "fireblast", "lightning", "blastwave", "transfusion"):
            self.assertEqual(0, magic_score(wand(f"wand of {name}")))

    def test_staff_magic_uses_wand_not_melee_description(self):
        item = wand("staff of magic missile", low=8, high=12)
        item["description"] = "Melee weapon deals 1-5 damage. " + item["description"]
        self.assertEqual(10, magic_score(item))

    def attack(self, items, cell=26):
        self.s["inventory"] = items
        enemy = {"cell": cell, "name": "gnoll scout"}
        self.s["objects"] = [enemy]
        p = SurvivalPolicy()
        p.update(self.s)
        return p.best_attack(self.s, enemy)

    def test_higher_damage_thrown_weapon_beats_wand(self):
        d = self.attack([wand(), gear("javelin", "thrown", low=12, high=20)])
        self.assertEqual("THROW", d.action["action"])

    def test_stronger_wand_beats_thrown_weapon(self):
        d = self.attack([wand(low=20, high=30), gear("javelin", "thrown")])
        self.assertEqual("ZAP", d.action["action"])

    def test_strong_melee_beats_wand_when_adjacent(self):
        d = self.attack([wand(), gear("sword", low=20, high=30, equipped=True)], cell=25)
        self.assertEqual("combat: melee", d.reason)

    def test_cursed_or_overweight_thrown_weapons_are_not_used(self):
        for fields in ({"known_cursed": True}, {"strength": 15}):
            d = self.attack([wand(), gear("javelin", "thrown", low=30, high=40, **fields)])
            self.assertEqual("ZAP", d.action["action"])

    def test_floor_four_requires_three_observed_descents(self):
        p = SurvivalPolicy(goal="floor-four")
        for depth in (1, 2, 3):
            self.s["depth"] = depth
            p.choose(self.s)
            p.cell(25, "stairs: descend", intent="descend")
        self.s["depth"] = 4
        with self.assertRaises(Finished) as error:
            p.choose(self.s)
        self.assertEqual("success", error.exception.outcome)
        self.assertEqual([1, 2, 3], p.cleared_floors)

    def test_attach_on_four_is_not_success(self):
        self.s["depth"] = 4
        with self.assertRaises(Finished) as error:
            SurvivalPolicy(goal="floor-four").choose(self.s)
        self.assertEqual("blocked", error.exception.outcome)

    def test_crowd_disables_charge_reserve_and_focuses_wounded_enemy(self):
        self.s["inventory"][0]["status"] = "2/4"
        self.s["objects"] = [{"cell": 25, "name": "marsupial rat"},
                             {"cell": 23, "name": "marsupial rat", "health_bar": [15, 32]}]
        p = SurvivalPolicy()
        # Boxed in: no safe reposition, so spend charges to open an escape.
        for tile in self.s["map"]["cells"]:
            if tile["cell"] not in (23, 24, 25):
                tile["terrain"] = 4
        d = p.choose(self.s)
        self.assertEqual("ZAP", d.action["action"])
        self.assertEqual(23, p.target)

    def test_repositions_before_attacking_multiple_adjacent_enemies(self):
        self.s["objects"] = [{"cell": 25, "name": "marsupial rat"},
                             {"cell": 32, "name": "marsupial rat"}]
        d = SurvivalPolicy().choose(self.s)
        self.assertEqual("combat: funnel enemies to fight one at a time", d.reason)
        from tools.survival_bot import distance
        self.assertLessEqual(sum(distance(d.action["cell"], e["cell"], 7) == 1
                                 for e in self.s["objects"]), 1)

    def test_single_enemy_does_not_cause_positioning_retreat(self):
        self.s["objects"] = [{"cell": 25, "name": "marsupial rat"}]
        self.assertNotIn("funnel", SurvivalPolicy().choose(self.s).reason)

    def test_known_cursed_equipped_weapon_is_not_used_for_melee(self):
        d = self.attack([wand(), gear("cursed sword", low=20, high=30,
                                    equipped=True, known_cursed=True)], cell=25)
        self.assertEqual("ZAP", d.action["action"])

    def test_two_approaching_enemies_favor_a_narrow_passage(self):
        # Hero in a chamber, with a one-tile corridor directly behind.
        for tile in self.s["map"]["cells"]:
            if tile["cell"] in (15, 16, 17, 29, 30, 31):
                tile["terrain"] = 4
        self.s["objects"] = [{"cell": 26, "name": "marsupial rat"},
                             {"cell": 33, "name": "marsupial rat"}]
        p = SurvivalPolicy()
        p.update(self.s)
        d = p.single_enemy_position(self.s, self.s["objects"])
        self.assertIsNotNone(d)
        self.assertEqual(23, d.action["cell"])

    def test_dead_end_with_no_safe_backstep_is_not_a_funnel(self):
        for tile in self.s["map"]["cells"]:
            if tile["cell"] in (15, 16, 22, 29, 30):
                tile["terrain"] = 4
        self.s["objects"] = [{"cell": 26, "name": "marsupial rat"},
                              {"cell": 33, "name": "marsupial rat"}]
        p = SurvivalPolicy()
        p.update(self.s)
        self.assertIsNone(p.single_enemy_position(self.s, self.s["objects"]))

    def test_distant_snake_does_not_preempt_adjacent_fly(self):
        for tile in self.s["map"]["cells"]:
            if tile["cell"] not in (24, 25, 26):
                tile["terrain"] = 4
        self.s["objects"] = [{"cell": 26, "name": "sewer snake"},
                             {"cell": 25, "name": "swarm of flies"}]
        d = SurvivalPolicy().choose(self.s)
        self.assertNotIn("snake:", d.reason)
        self.assertEqual("combat: best estimated damage", d.reason)

    def snake_queue(self):
        s = state()
        s["map"]["cells"] = [{"cell": c, "terrain": 1 if c in (24, 25, 26) else 4, "visible": True}
                             for c in range(49)]
        s["inventory"][0]["status"] = "2/4"
        s["objects"] = [{"cell": 25, "name": "gnoll scout", "health_bar": [19, 32]},
                        {"cell": 26, "name": "sewer snake"}]
        return s

    def test_wounded_gnoll_in_queue_does_not_consume_last_snake_charges(self):
        s = self.snake_queue()
        d = SurvivalPolicy().choose(s)
        self.assertEqual("combat: preserve magic for queued snake", d.reason)
        self.assertEqual({"type": "cell", "cell": 25}, d.action)

    def test_queue_reserve_is_abandoned_at_low_health(self):
        s = self.snake_queue()
        s["hero"]["hp"] = 10
        self.assertEqual("ZAP", SurvivalPolicy().choose(s).action["action"])

    def test_queue_reserve_does_not_force_melee_against_healthy_gnoll(self):
        s = self.snake_queue()
        s["objects"][0].pop("health_bar")
        self.assertEqual("ZAP", SurvivalPolicy().choose(s).action["action"])

    def test_preserved_magic_is_spent_when_snake_reaches_front(self):
        s = self.snake_queue()
        s["objects"] = [{"cell": 25, "name": "sewer snake"}]
        self.assertEqual("ZAP", SurvivalPolicy().choose(s).action["action"])

    def test_last_charge_is_not_spent_on_tiny_rat_blocker_under_mild_crowding(self):
        s = self.snake_queue()
        s["hero"]["hp"] = 10
        s["inventory"][0]["status"] = "1/4"
        s["objects"][0].update(name="marsupial rat", health_bar=[1, 10])
        s["objects"].append({"cell": 23, "name": "marsupial rat"})
        next(t for t in s["map"]["cells"] if t["cell"] == 23)["terrain"] = 1
        p = SurvivalPolicy()
        for _ in range(2):
            d = p.choose(s)
            self.assertEqual("combat: preserve magic for queued snake", d.reason)
            self.assertEqual(25, d.action["cell"])
        self.assertEqual("ZAP", p.choose(s).action["action"])  # Bounded, not endless misses.
