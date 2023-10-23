""" Example of a test module. """

import json
import re
from glob import glob
from ipaddress import IPv4Address, IPv4Network
from typing import Any, List, Mapping
from unittest import TestCase

import ruamel.yaml
from more_itertools import one


def checked_glob(pathname: str) -> List[str]:
    """ Call glob, checking that at least one file matched """
    res = glob(pathname)
    if not res:
        raise ValueError(f"{pathname} did not match any files")
    return res


class TestVirgilCrosscheck(TestCase):
    """
    Cross-check our machine configuration against Virgil information.
    """

    virgil_machines: Mapping[str, Any]

    @classmethod
    def setUpClass(cls):
        cls.virgil_machines = {}
        for fname in checked_glob("inventories/inventory-*-*.yaml"):
            with open(fname, encoding="utf8") as fh:
                # Note: these files are nominally YAML, but in practice they're JSON and
                # loading them as JSON is much faster
                virgil_file = json.load(fh)
                cls.virgil_machines.update(virgil_file["all"]["hosts"])
        if not cls.virgil_machines:
            raise ValueError("Virgil inventories empty or failed to load")

    def test_against_virgil(self):
        """Cross-check our machine configuration against Virgil information."""
        yaml = ruamel.yaml.YAML(typ="safe", pure=True)
        fname_pat = re.compile(r"^data/instances/([a-z]{2}[0-9])-machines\.yml$")

        for fname in checked_glob("data/instances/*-machines.yml"):
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

    def test_machine_clusters(self):
        """Cross-check machine cluster configuration against Virgil."""
        yaml = ruamel.yaml.YAML(typ="safe", pure=True)

        for fname in checked_glob("data/machine_clusters/*.yaml"):
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
