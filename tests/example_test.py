""" Example of a test module. """

from unittest import TestCase

class TestExample(TestCase):
    """
    Example of how to write a test.

    Each class groups together logically-related tests; it can also do common
    setup and cleanup.

    TODO: Remove this example once we have enough real examples.
    """
    def test(self):
        """ Example individual test case. """
        self.assertEqual(1 + 1, 2)
