""" Example of a test module. """

import re
from glob import glob
import json
from unittest import TestCase

import ruamel.yaml


class TestVirgilCrosscheck(TestCase):
    """
    Cross-check our machine configuration against Virgil information.
    """

    def test(self):
        """Cross-check our machine configuration against Virgil information."""
        yaml = ruamel.yaml.YAML(typ="safe", pure=True)
        fname_pat = re.compile(r"^instances/([a-z]{2}[0-9])-machines\.yml$")

        for fname in glob("instances/*-machines.yml"):
            with self.subTest(file=fname):
                m = fname_pat.match(fname)
                self.assertIsNotNone(m)
                dc = m.group(1).upper()

                with open(fname, encoding="utf8") as fh:
                    iris_file = yaml.load(fh)

                with open(f"inventories/inventory-{dc}-A.yaml", encoding="utf8") as fh:
                    # Note: this file is nominally YAML, but in practice it's JSON and
                    # loading it as JSON is much faster
                    virgil_file = json.load(fh)

                iris_machines = iris_file["machines"]["hosts"]
                virgil_machines = virgil_file["all"]["hosts"]

                for machine, iris_config in iris_machines.items():
                    with self.subTest(machine=machine):
                        self.assertIn(
                            machine,
                            virgil_machines,
                            f"{machine} is not in the {dc} Virgil inventory",
                        )

                        virgil_info = virgil_machines[machine]

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
                            virgil_info["virgil_role"],
                            "server_loadbalancer_iris",
                            "Virgil role must be server_loadbalancer_iris",
                        )
