""" Test module for update_globalstate.py """

from unittest import TestCase
from update_globalstate import StateFileUpdater

class TestUpdateStateFile(TestCase):
    """
    Tests that check StateFileUpdater can delete the lines in state file
    """
    def setUp(self):
        self.check_strings = [
            "changed2_testrig_sand_wtg_zone-glow 2 au2sp-tweb-port-change1",
            "changed2_testrig_sand_wtg_zone-glow 3 au2sp-tweb-port-change2",
            "changed2_testrig_sand_wtg_zone-glow 4 au2sp-tweb-port-change3",
            "changed2_testrig_sand_wtg_zone-glow 5 au2sp-tweb-port-change4",
            "changed2_testrig_sand_wtg_zone-glow 6 au2sp-tweb-port-change5",
            ]

    def test(self):
        """
        Tests that check StateFileUpdater can delete the lines in state file
        """
        state_file_updater = StateFileUpdater(state_file='tests/mock_state',
                                              config_file='tests/mock.cfg')
        removed_lines = state_file_updater.update()

        self.assertEqual(len(self.check_strings), len(removed_lines),
                         "The number of lines was not match")

        # Check if check_strings were removed
        for string in self.check_strings:
            found = False
            for removed_line in removed_lines:
                if string in removed_line:
                    found = True
                    break
            self.assertTrue(found, f"{string} not found in removed strings")

        # Check if check_strings are not in mock_state file
        with open('tests/mock_state', 'r', encoding='ascii') as f:
            state_file_content = f.read()
            for string in self.check_strings:
                self.assertNotIn(string, state_file_content,
                                 f"{string} found in state file")
