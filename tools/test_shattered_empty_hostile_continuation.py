"""Regression checks for continuation without a visible retreat threat."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

try:
    from .continuation import best_effort
except ImportError:
    from continuation import best_effort


class EmptyHostileContinuationTests(unittest.TestCase):
    def state(self, danger=()):
        return {
            'status': 'ready',
            'hero': {'hp': 10, 'max_hp': 10, 'cell': 12},
            'map': {'width': 5, 'height': 5},
            'inventory': [],
            'danger_cells': list(danger),
        }

    def policy(self):
        p = SimpleNamespace(unit_strategies_enabled=False)
        p.emergency_transport = Mock(return_value=None)
        p.retreat = Mock(side_effect=ValueError('empty retreat threats'))
        p.decision = Mock(side_effect=lambda action, reason, **kw:
                          SimpleNamespace(action=action, reason=reason, **kw))
        return p

    def test_no_enemies_or_warning_returns_exhaustion_without_retreat(self):
        p = self.policy()
        result = best_effort(p, self.state(), [])
        self.assertIsNone(result)
        p.retreat.assert_not_called()

    def test_warning_without_enemies_still_requests_escape(self):
        p = self.policy()
        escape = SimpleNamespace(action={'type': 'cell', 'cell': 13}, reason='escape')
        p.retreat = Mock(return_value=escape)
        state = self.state([12])
        self.assertIs(best_effort(p, state, []), escape)
        p.retreat.assert_called_once_with(state, [], [12])

    def test_enemy_retreat_remains_available(self):
        p = self.policy()
        escape = SimpleNamespace(action={'type': 'cell', 'cell': 13}, reason='escape')
        p.retreat = Mock(return_value=escape)
        state = self.state()
        enemies = [{'name': 'marsupial rat', 'cell': 11}]
        self.assertIs(best_effort(p, state, enemies), escape)
        p.retreat.assert_called_once_with(state, enemies, [])


if __name__ == '__main__':
    unittest.main()
