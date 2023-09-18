""" Example of a test module. """

import re
from glob import glob
from ipaddress import IPv4Address, IPv4Network
import json
from typing import Any, Mapping
from unittest import TestCase

from more_itertools import one
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

    def test(self):
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

    def test_machine_clusters(self):
        """Cross-check machine cluster configuration against Virgil."""
        yaml = ruamel.yaml.YAML(typ="safe", pure=True)

        for fname in glob("machine_clusters/*.yaml"):
            with self.subTest(file=fname):
                with open(fname, encoding="utf8") as fh:
                    iris_file = yaml.load(fh)

                for cluster, config in iris_file.items():
                    if not config["machines"]:
                        if config["floating_ips"]:
                            raise ValueError("Non-empty config for empty cluster!")

                        continue

                    with self.subTest(cluster=cluster):
                        virgil_vlans = {
                            (virgil_vlan["id"], virgil_vlan["subnet"])
                            for virgil_vlan in (
                                self.virgil_machines[name]["virgil_mgmt_vlan"]
                                for name in config["machines"]
                            )
                        }
                        virgil_vlan, subnet = one(
                            virgil_vlans,
                            too_long=ValueError(
                                f"Machines across multiple VLANs: {sorted(virgil_vlans)}"
                            ),
                        )
                        virgil_subnet = IPv4Network(subnet)

                    for floating_ip in config["floating_ips"]:
                        self.assertEqual(
                            floating_ip["vlan"],
                            virgil_vlan,
                            f"Floating IP VLAN {floating_ip['vlan']} "
                            f"does not match machine VLAN {virgil_vlan}",
                        )
                        self.assertIn(
                            IPv4Address(floating_ip["ip"]),
                            virgil_subnet,
                            f"Floating IP {floating_ip['ip']} "
                            f"is not in the VLAN subnet {virgil_subnet}",
                        )
                        self.assertCountEqual(
                            floating_ip["priority"],
                            set(floating_ip["priority"]),
                            f"Priority list has repeats: {floating_ip['priority']}",
                        )
                        self.assertLessEqual(
                            set(floating_ip["priority"]),
                            set(config["machines"]),
                            "Priority list has machines not in cluster: "
                            "{set(floating_ip['priority']) - set(config['machines'])}",
                        )
