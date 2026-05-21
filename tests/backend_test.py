"""Backend-related tests."""

import os
import re
from glob import glob
from typing import List
from unittest import TestCase

import ruamel.yaml


def checked_glob(pathname: str) -> List[str]:
    """Call glob, checking that at least one file matched"""
    res = glob(pathname)
    if not res:
        raise ValueError(f"{pathname} did not match any files")
    return res


class BackendTest(TestCase):
    """Backend-related tests."""

    def _check_port(self, port, encryption):
        msg = f"server port is {port}, but encryption is {encryption}"
        if port in (443, 8443):
            self.assertTrue(encryption, msg)
        elif port in (80, 8080):
            self.assertFalse(encryption, msg)
        else:
            pass

    def test_dynamic_be_ports(self):
        """Test dynamic backend port number sanity."""

        yaml = ruamel.yaml.YAML(typ="safe", pure=True)

        for fname in checked_glob("data/dynamic_backends/*.y*ml"):
            with self.subTest(file=fname):
                with open(fname, encoding="utf8") as fh:
                    cfg = yaml.load(fh)
                for be_cfg in cfg:
                    with self.subTest(name_regex=be_cfg.get('name_regex', ''),
                                      server_regex=be_cfg.get('server_regex', '')):
                        encryption = be_cfg.get('encryption', False)
                        self._check_port(be_cfg['port'], encryption)

    def test_static_be_ports(self):
        """Test static backend port number sanity."""

        yaml = ruamel.yaml.YAML(typ="safe", pure=True)
        re_ssl = re.compile(r'\bssl\b')

        for fname in checked_glob('data/static_backends/*.y*ml'):
            with self.subTest(file=fname):
                with open(fname, encoding="utf8") as fh:
                    cfg = yaml.load(fh)
                for be, be_cfg in cfg.items():
                    with self.subTest(backend=be):
                        for se in be_cfg.get('servers', []):
                            with self.subTest(server=se.get('name', ''),
                                              ip=se.get('ip', ''),
                                              port=se.get('port', -1)):
                                encryption = be_cfg.get('encryption', False)

                                # Does 'settings' contain the 'ssl' flag?
                                if (not encryption) and re_ssl.search(se.get('settings', '')):
                                    encryption = True

                                self._check_port(se.get('port', -1), encryption)

    def test_iris_stats_entries_present_in_dc_central_files(self):
        """Ensure iris-stats backends exist in the designated per-DC static backend file."""

        yaml = ruamel.yaml.YAML(typ="safe", pure=True)

        # Per-DC file that hosts the iris-stats service keys.
        dc_iris_stats_file = {
            'us2': 'data/static_backends/us2corpinternal1.yaml',
            'au2': 'data/static_backends/au2prodinternal1corpservices35.yaml',
            'cn1': 'data/static_backends/au2prodinternal1corpservices35.yaml',
            'de1': 'data/static_backends/de1prodinternal1services30.yaml',
            'sa1': 'data/static_backends/de1prodinternal1services30.yaml',
        }

        for instances_file in checked_glob('data/instances/*-clustered_instances.yml'):
            dc = os.path.basename(instances_file).split('-')[0]
            central_file = dc_iris_stats_file.get(dc)
            if not central_file:
                continue

            with open(instances_file, encoding='utf8') as fh:
                cfg = yaml.load(fh)

            instances = cfg.get('clustered_instances', {}).get('hosts', {})

            with open(central_file, encoding='utf8') as fh:
                central_cfg = yaml.load(fh)

            for instance_name, instance_cfg in instances.items():
                stats_ports = instance_cfg.get('stats', {}).get('ports', {})
                if 'web' not in stats_ports:
                    continue

                expected_key = f'{instance_name}.iris-stats.wtg.zone'
                with self.subTest(dc=dc, instance=instance_name, file=central_file):
                    self.assertTrue(
                        expected_key in central_cfg,
                        f"Missing iris-stats entry '{expected_key}' in {central_file}",
                    )
