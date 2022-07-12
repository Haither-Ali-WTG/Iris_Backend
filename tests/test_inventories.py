"""
Check the schema of the YAML files, using Yamale
"""

from __future__ import annotations

import glob
import os
from collections import defaultdict
from unittest import TestCase

import ruamel.yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def collect_leaves(o):
    """ Given a nested structure of dicts and lists, produce all leaf values
    together with their paths.

    >>> list(collect_leaves({'foo': ['abc', 'def'], 'bar': 'ghi'}))
    [('abc', ['foo', '0']), ('def', ['foo', '1']), ('ghi', ['bar'])]
    """
    if isinstance(o, dict):
        for key, value in o.items():
            yield from ((leaf, [key] + path) for leaf, path in collect_leaves(value))
    elif isinstance(o, list):
        for i, value in enumerate(o):
            yield from ((leaf, [str(i)] + path) for leaf, path in collect_leaves(value))
    else:
        yield (o, [])


class TestInventoriesTest(TestCase):
    """ Test each of the inventory files """

    def test_inventories(self):
        """ Generate a test case for each inventory. """

        filenames = glob.glob("*/*/inventory.yml")

        self.assertTrue(filenames, "No inventories found")

        for filename in filenames:
            self.check_inventory(filename)

    def check_inventory(self, filename):
        """ Check an individual inventory file. """
        with open(filename, encoding='ascii') as fh:
            inventory = ruamel.yaml.safe_load(fh)

        seen = defaultdict(set)

        for name, instance in inventory["all"]["vars"]["instances"].items():
            for var in "frontend_ports", "stats_ports":
                for port, path in collect_leaves(instance[var]):
                    seen[int(port)].add(".".join([name, var] + path))

        problems = [
            f"Port {port} used for {' and '.join(where)}"
            for port, where in seen.items()
            if len(where) > 1
        ]

        if problems:
            problems.insert(0, f"In {filename}:")
            self.fail('\n'.join(problems))
