import unittest
from tools.artifact_tactics import equip_artifact, use_artifact
from tools.combat_items import empty_ring_candidate, accessory_kind
from tools.consumable_tactics import discovery_menu
from tools.test_challenge_systems import ready, item


class AccessorySlotsTests(unittest.TestCase):
    def test_unidentified_ring_is_equipped_in_free_slot(self):
        s,p=ready()
        s['inventory'].append(item('agate ring','EQUIP'))
        action=use_artifact(p,s,[])
        self.assertEqual('EQUIP',action.action['action'])
        self.assertEqual('agate ring',action.action['id'])

    def test_known_cursed_ring_or_artifact_is_never_equipped(self):
        s,p=ready()
        s['inventory'] += [item('agate ring','EQUIP',known_cursed=True),
                           item('horn of plenty','EQUIP',known_cursed=True)]
        self.assertIsNone(empty_ring_candidate(s))
        self.assertIsNone(equip_artifact(p,s))

    def test_unknown_ring_counts_as_ring_not_artifact(self):
        s,p=ready()
        s['inventory'] += [item('agate ring','UNEQUIP',equipped=True),
                           item('opal ring','UNEQUIP',equipped=True),item('garnet ring','EQUIP')]
        self.assertIsNone(empty_ring_candidate(s))
        s['inventory'].append(item('horn of plenty','EQUIP'))
        self.assertEqual('EQUIP',equip_artifact(p,s).action['action'])

    def test_full_slots_do_not_trigger_unknown_artifact_swap(self):
        s,p=ready()
        s['inventory'] += [item('horn of plenty','UNEQUIP',equipped=True),
                           item('cape of thorns','UNEQUIP',equipped=True),item('ethereal chains','EQUIP')]
        self.assertIsNone(equip_artifact(p,s))

    def test_ring_mail_does_not_consume_accessory_slot(self):
        self.assertIsNone(accessory_kind(item('ring mail armor','EQUIP')))

    def test_unsupported_activation_artifact_can_still_fill_free_slot(self):
        s,p=ready()
        s['inventory'].append(item('unstable spellbook','EQUIP'))
        self.assertEqual('EQUIP',equip_artifact(p,s).action['action'])

    def test_worn_curse_is_cleansed_before_equipping_another_accessory(self):
        s,p=ready()
        s['inventory'] += [item('agate ring','UNEQUIP',equipped=True,known_cursed=True),
                           item('horn of plenty','EQUIP'),item('scroll of remove curse','READ')]
        action=use_artifact(p,s,[])
        self.assertEqual('READ',action.action['action'])
        self.assertEqual('scroll of remove curse',action.action['id'])

    def test_cleanse_menu_prioritizes_worn_accessory_over_pack_and_weapon(self):
        s,p=ready()
        s['inventory'] += [item('quarterstaff','UNEQUIP',equipped=True,known_cursed=True),
                           item('horn of plenty','EQUIP',known_cursed=True),
                           item('agate ring','UNEQUIP',equipped=True,known_cursed=True)]
        s['ui']={'texts':['Cleanse an item'], 'buttons':[
            {'id':'weapon','label':'quarterstaff'},{'id':'pack','label':'horn of plenty'},
            {'id':'worn','label':'agate ring'}]}
        self.assertEqual('worn',discovery_menu(p,s).action['id'])


if __name__=='__main__':unittest.main()
