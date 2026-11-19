import unittest
from tools.test_regular_feedback import arena
from tools.test_unit_strategies import enemy
from tools.test_consumable_tactics import potion
from tools.ranged_tactics import choose,ranged_enemy,exposed_wait


class GuardPullCoverTests(unittest.TestCase):
    def test_guard_has_public_pull_control_not_invented_projectile_damage(self):
        s,p=arena();guard=enemy('prison guard',43)
        profile=p.unit_strategies.profile(guard)
        self.assertIn('ranged-pull',profile.capabilities)
        self.assertNotIn('ranged-attacks',profile.capabilities)
        self.assertTrue(ranged_enemy(p,guard))

    def test_temporary_sheep_are_not_certified_cover_against_guard_pull(self):
        s,p=arena();s['hero']['hp']=6
        guard=enemy('prison guard',43);s['objects']=[guard,{'name':'sheep','cell':42}]
        next(t for t in s['map']['cells'] if t['cell']==31)['terrain']=4
        p.update(s)
        self.assertTrue(exposed_wait(p,s,[guard]))
        a=choose(p,s,[guard])
        self.assertEqual('cell',a.action['type']);self.assertIn('cover',a.reason)
        self.assertFalse(p.enemy_can_see(s,guard,p.ranged_plan['goal']))

    def test_low_health_known_escape_precedes_adjacent_damage_trade(self):
        s,p=arena();s['hero']['hp']=4;guard=enemy('prison guard',41);s['objects']=[guard]
        s['inventory'].append(potion('potion of invisibility'));p.update(s)
        a=choose(p,s,[guard])
        self.assertEqual('DRINK',a.action['action']);self.assertIn('escape',a.reason)


if __name__=='__main__':unittest.main()
