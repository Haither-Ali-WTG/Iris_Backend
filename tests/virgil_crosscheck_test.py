""" Example of a test module. """

import re
from glob import glob
import json
from typing import Any, Mapping
from unittest import TestCase

import ruamel.yaml


class TestVirgilCrosscheck(TestCase):
    """
    Cross-check our machine configuration against Virgil information.
    """

    virgil_machines: Mapping[str, Any]

    @classmethod
    def setUpClass(cls):
        cls.virgil_machines = {}
        for fname in glob("inventories/inventory-*-*.yaml"):
            with open(fname, encoding="utf8") as fh:
                # Note: these files are nominally YAML, but in practice they're JSON and
                # loading them as JSON is much faster
                virgil_file = json.load(fh)
                cls.virgil_machines.update(virgil_file["all"]["hosts"])

    def test_against_virgil(self):
        """Cross-check our machine configuration against Virgil information."""
        yaml = ruamel.yaml.YAML(typ="safe", pure=True)
        fname_pat = re.compile(r"^instances/([a-z]{2}[0-9])-machines\.yml$")

        for fname in glob("instances/*-machines.yml"):
            with self.subTest(file=fname):
                m = fname_pat.match(fname)
                self.assertIsNotNone(m)
                dc = m.group(1).upper()  # type: ignore  # false positive

                with open(fname, encoding="utf8") as fh:
                    iris_file = yaml.load(fh)

                iris_machines = iris_file["machines"]["hosts"]

                for machine, iris_config in iris_machines.items():
                    with self.subTest(machine=machine):
                        self.assertIn(
                            machine,
                            self.virgil_machines,
                            f"{machine} is not in the {dc} Virgil inventory",
                        )

                        virgil_info = self.virgil_machines[machine]

                        self.assertEqual(
                            iris_config["ansible_host"],
                            virgil_info["virgil_ip_primary"],
                            "Mismatched IP address compared to Virgil",
                        )

                        self.assertEqual(
                            iris_config["os"],
                            virgil_info["virgil_os_variant"],
                            "Mismatched OS compared to Virgil",
                        )

                        self.assertEqual(
                            iris_config["dc"],
                            dc,
                            f"Incorrect DC setting, should be {dc} in {fname}",
                        )

                        self.assertEqual(
                            iris_config["dc"],
                            virgil_info["virgil_dc_name"],
                            "Mismatched DC setting compared to Virgil",
                        )

                        self.assertEqual(
                            virgil_info["virgil_role"],
                            "server_loadbalancer_iris",
                            "Virgil role must be server_loadbalancer_iris",
                        )
