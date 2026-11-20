"""Run 000010, decision 2970 (log line 8392): known sleep was bypassed.

Reduced public fixture: the recorded map, enemy, empty staff, food and runestone.
No game dispatch, acquired-item assumption, or post-decision observation.
"""
import unittest
from unittest.mock import patch

from tools.policy_decision import NoSafeAction
from tools.priority_resources import targets
from tools.ranged_tactics import choose
from tools.test_challenge_rules import verified
from tools.test_dm100_door_ambush import doorway


TILES = {
    1: (634, 639, 641, 672, 709, 750, 780, 787, 825, 858, 895, 897, 900),
    2: (558, 600, 632, 635, 676, 713, 744, 748, 784, 820, 854, 892, 893,
        898, 929, 968, 1005, 1188),
    4: (520, 531, 557, 568, 605, 642, 679, 742, 753, 779, 790, 816, 827,
        853, 864, 890, 926, 927, 932, 933, 934, 935, 936, 937, 938, 963,
        1000, 1007, 1037, 1074, 1081, 1111, 1118, 1148, 1185, 1192, 1222,
        1223, 1224, 1225, 1227, 1228, 1229),
    5: (901, 1044, 1155, 1226),
    7: (1040,),
    9: (596, 597, 603, 604, 633, 636, 640, 671, 673, 675, 677, 678, 710,
        711, 712, 714, 745, 746, 749, 781, 783, 785, 786, 788, 789, 817,
        821, 823, 824, 857, 859, 860, 861, 862, 863, 896, 899),
    15: (521, 559, 560, 563, 566, 595, 598, 599, 602, 637, 638, 670, 674,
         706, 707, 708, 715, 743, 751, 752, 782, 819, 822, 826, 855, 856,
         891, 894, 930, 931, 967, 969, 1006, 1187),
    18: (747,),
    29: (530, 567, 928, 965, 966, 1002, 1003, 1004, 1039, 1041, 1042, 1043,
         1076, 1077, 1078, 1079, 1080, 1113, 1114, 1115, 1116, 1117, 1150,
         1151, 1152, 1153, 1154, 1189, 1190, 1191),
    33: (964, 1001, 1038, 1075, 1112, 1149, 1186),
}
HIDDEN = {
    530, 531, 566, 567, 568, 602, 603, 604, 605, 638, 639, 706, 707, 742,
    753, 853, 854, 855, 890, 891, 892, 897, 926, 927, 928, 929, 934, 963,
    964, 965, 966, 967, 968, 969, 1000, 1001, 1002, 1003, 1004, 1005, 1006,
    1007, 1037, 1038, 1039, 1040, 1041, 1042, 1043, 1044, 1074, 1075, 1076,
    1077, 1078, 1079, 1080, 1081, 1111, 1112, 1113, 1114, 1115, 1116, 1117,
    1118, 1148, 1149, 1150, 1151, 1152, 1153, 1154, 1155, 1185, 1186, 1187,
    1188, 1189, 1190, 1191, 1192, 1222, 1223, 1224, 1225, 1226, 1227, 1228, 1229,
}


def sleep_stone():
    return dict(id='item-15', name='stone of deep sleep', identified=True,
                quantity=1, equipped=False, actions=['DROP', 'THROW'],
                description='When this stone is thrown at an enemy, it will put '
                            'them into a deep magical sleep. Magically slept '
                            'enemies will sleep forever until disturbed.')


def exhausted_scene():
    cells = [dict(cell=c, terrain=terrain, visible=c not in HIDDEN,
                  observed=True, effects=[])
             for terrain, group in TILES.items() for c in group]
    next(t for t in cells if t['cell'] == 747)['trap'] = 'explosive trap'
    s = dict(
        scene='GameScene', status='ready', modal=False, depth=7, branch=0,
        danger_cells=[], boss_health_text=None,
        hero=dict(name='mage', hero_class='mage', cell=710, hp=36, max_hp=55,
                  level=8, strength=13, gold=292, buffs=[dict(name='hungry')],
                  talents=[]),
        inventory=[
            dict(id='item-0', name='staff of magic missile +3', status='0/7',
                 identified=True, equipped=True, actions=['ZAP', 'IMBUE']),
            dict(id='item-8', name='stewed meat', actions=['EAT'], quantity=1),
            sleep_stone(),
        ],
        keys=[dict(name='iron key', depth=7, quantity=1)],
        map=dict(width=37, height=42, cells=cells),
        objects=[
            dict(name='DM-100', cell=558, health_bar=[5, 21], status_icons=[]),
            dict(name='throwing club x2', cell=558,
                 top_item=dict(name='throwing club x2', quantity=2)),
            dict(name='potion of liquid flame', cell=710,
                 top_item=dict(name='potion of liquid flame')),
        ],
        ui=dict(texts=[], buttons=[]),
    )
    p = verified()
    p.update(s)
    return s, p


def admitted(p, s):
    """Treat an honest no-action veto as no selection, not a successful escape."""
    try:
        return choose(p, s, [o for o in s['objects'] if o['name'] == 'DM-100'])
    except NoSafeAction:
        return None


class ExhaustedDM100SleepTests(unittest.TestCase):
    def test_full_selector_uses_known_sleep_before_no_safe_action(self):
        s, p = exhausted_scene()
        try:
            decision = p.choose(s)
        except NoSafeAction:
            decision = None
        self.assertIsNotNone(decision, 'Known sleep must be considered before continuation')
        self.assertEqual(dict(type='item', id='item-15', action='THROW'), decision.action)
        self.assertEqual(558, p.target)
        self.assertEqual(8, p.stone_cooldown)
        self.assertFalse(p.continuation_errors)
        self.assertFalse(p.completed_room_rewards)

    def test_control_does_not_claim_or_remove_mandatory_progression_loot(self):
        s, p = exhausted_scene()
        upgrade = dict(name='scroll of upgrade', cell=711,
                       top_item=dict(name='scroll of upgrade'))
        s['objects'].append(upgrade)
        p.update(s)
        decision = admitted(p, s)
        self.assertIsNotNone(decision)
        self.assertEqual('THROW', decision.action.get('action'))
        self.assertIn(711, targets(p))
        self.assertFalse(p.loot_collection_receipts)
        self.assertFalse(p.completed_room_rewards)

    def test_usable_damage_still_precedes_exhausted_control(self):
        s, p = exhausted_scene()
        s['inventory'][0]['status'] = '1/7'
        self.assertEqual('ZAP', admitted(p, s).action['action'])
        self.assertEqual(0, p.stone_cooldown)

    def test_verified_cover_still_precedes_sleep(self):
        s, p = doorway()
        s['inventory'].append(sleep_stone())
        decision = choose(p, s, s['objects'])
        self.assertEqual(dict(type='cell', cell=40), decision.action)
        self.assertEqual('cover', p.ranged_plan['mode'])
        self.assertEqual(0, p.stone_cooldown)

    def test_unavailable_or_unidentified_control_is_not_guessed(self):
        for case in ('missing', 'no-throw', 'unidentified', 'cooldown'):
            with self.subTest(case=case):
                s, p = exhausted_scene()
                if case == 'missing':
                    s['inventory'].pop()
                elif case == 'no-throw':
                    s['inventory'][-1]['actions'] = ['DROP']
                elif case == 'unidentified':
                    s['inventory'][-1]['identified'] = False
                else:
                    p.stone_cooldown = 1
                self.assertIsNone(admitted(p, s))
                self.assertIsNone(p.target)

    def test_target_shot_and_item_vetoes_remain_binding(self):
        for method in ('shot_clear', 'target_allowed', 'item_action_allowed'):
            with self.subTest(method=method):
                s, p = exhausted_scene()
                with patch.object(p, method, return_value=False):
                    self.assertIsNone(admitted(p, s))
                self.assertEqual(0, p.stone_cooldown)

    def test_no_blind_throw_at_a_remembered_caster(self):
        s, p = exhausted_scene()
        s['objects'] = []
        self.assertIsNone(choose(p, s, []))
        self.assertIsNone(p.target)

    def test_rendered_warning_and_boss_controllers_are_not_bypassed(self):
        for field, value in (('danger_cells', [710]), ('boss_health_text', 'boss')):
            with self.subTest(field=field):
                s, p = exhausted_scene()
                s[field] = value
                self.assertIsNone(admitted(p, s))
                self.assertEqual(0, p.stone_cooldown)

    def test_single_dm100_scope_is_not_generalized_to_other_threats(self):
        for case in ('other-species', 'multiple'):
            with self.subTest(case=case):
                s, p = exhausted_scene()
                if case == 'other-species':
                    s['objects'][0]['name'] = 'gnoll shaman'
                else:
                    s['objects'].append(dict(name='DM-100', cell=559))
                enemies = [o for o in s['objects'] if not o.get('top_item')]
                try:
                    decision = choose(p, s, enemies)
                except NoSafeAction:
                    decision = None
                if decision is not None:
                    self.assertNotEqual(dict(type='item', id='item-15', action='THROW'),
                                        decision.action)
                self.assertEqual(0, p.stone_cooldown)


if __name__ == '__main__':
    unittest.main()
