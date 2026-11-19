import unittest
from unittest.mock import patch
from tools.workspace_launch import owned_window,move_command


class WorkspaceLaunchTests(unittest.TestCase):
    def test_move_targets_exact_address_without_following(self):
        cmd=move_command('0x123abc',1)
        self.assertIn('address:0x123abc',cmd[-1]);self.assertIn('follow = false',cmd[-1])
        self.assertIn('workspace = 1',cmd[-1])

    def test_invalid_address_does_not_become_lua_code(self):
        with self.assertRaises(ValueError):move_command('0x1"; hl.dsp.exit()',1)

    def test_no_unique_verified_owner_is_a_hard_launch_failure(self):
        with self.assertRaises(RuntimeError):owned_window([],25001,'/profile')
        windows=[{'pid':1,'mapped':True},{'pid':2,'mapped':True}]
        with patch('tools.workspace_launch.Path.read_bytes',return_value=b'SPD_API_PORT=25001\0SPD_DATA_DIR=/profile\0'):
            with self.assertRaises(RuntimeError):owned_window(windows,25001,'/profile')

    def test_foreign_window_is_not_moved(self):
        windows=[{'pid':1,'mapped':True},{'pid':2,'mapped':True}]
        with patch('tools.workspace_launch.Path.read_bytes',side_effect=[b'SPD_API_PORT=1\0SPD_DATA_DIR=/else\0',b'SPD_API_PORT=25001\0SPD_DATA_DIR=/profile\0']):
            self.assertEqual(2,owned_window(windows,25001,'/profile')['pid'])
