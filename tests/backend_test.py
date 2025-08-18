"""Backend-related tests."""

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
