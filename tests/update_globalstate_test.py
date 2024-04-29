""" Test module for update_globalstate.py """

import subprocess
from unittest import TestCase

class TestUpdateStateFile(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.check_strings = [
            "changed2_testrig_sand_wtg_zone-glow 2 au2sp-tweb-port-change1",
            "changed2_testrig_sand_wtg_zone-glow 3 au2sp-tweb-port-change2",
            "changed2_testrig_sand_wtg_zone-glow 4 au2sp-tweb-port-change3",
            "changed2_testrig_sand_wtg_zone-glow 5 au2sp-tweb-port-change4",
            "changed2_testrig_sand_wtg_zone-glow 6 au2sp-tweb-port-change5",
            ]

    def test_update_statefile(self):
        # Run update_statefile.py
        process = subprocess.Popen(['python3',
                                    '../ansible/roles/iris_haproxy/files/update_globalstate.py',
                                    '--config', 'mock.cfg',
                                    '--state_file', 'mock_state'],
                                    stdout=subprocess.PIPE)
        output, _ = process.communicate()
        output = output.decode("utf-8")

        # All strings in check_strings should in output
        for string in self.check_strings:
            self.assertIn(string, output)

        # All strings in check_strings should not in updated mock_state file
        with open('mock_state', 'r') as f:
            state_file_content = f.read()
            for string in self.check_strings:
                self.assertNotIn(string, state_file_content)
