""" Check the configuration files against Yamale schemas """

import os
from collections import defaultdict
from fnmatch import fnmatch

import ruamel.yaml

from inventories.virgil_yamale import VirgilYamaleTestCase

BASE_CONFIG_DIR = 'data'
CONFIG_PATTERNS = [
    ('ansible/group_vars/individual_instances.yml', 'individual_instances'),
    ('data/acls/*.yaml', 'acls'),
    ('data/actions/*.yaml', 'actions'),
    ('data/ciphers/cipher_profiles.yml', 'cipher_profiles'),
    ('data/dynamic_backends/websites.yml', 'websites'),
    ('data/instances/*-clustered_instances.yml', 'clustered_instances'),
    ('data/instances/*-machines.yml', 'machines'),
    ('data/instances/*-tests.yml', 'instance_tests'),
    ('data/machine_clusters/*.yaml', 'machine_clusters'),
    ('data/static_backends/*.yaml', 'static_backends'),
    ('data/static_backends/sorry_pages/*.html', None),
]


class TestSchema(VirgilYamaleTestCase):
    """
    Check the configuration files against Yamale schemas
    """

    base_dir = ''  # for the VirgilYamaleTestCase class

    def test(self) -> None:
        """
        Check the configuration files against Yamale schemas
        """
        config_files = [
            # This is the only file to be checked outside the data directory
            'ansible/group_vars/individual_instances.yml',
        ]
        for path, _dirs, files in os.walk(BASE_CONFIG_DIR):
            for file in files:
                config_files.append(os.path.normpath(os.path.join(path, file)))

        by_kind = defaultdict(set)
        for fname in config_files:
            for pattern, kind in CONFIG_PATTERNS:
                if fnmatch(fname, pattern):
                    if kind is not None:
                        by_kind[kind].add(fname)
                    break
            else:
                with self.subTest(fname=fname):
                    self.fail(f"Unexpected file: {fname}")

        with open('tests/schema_common.yaml', encoding='utf-8') as fh:
            yaml = ruamel.yaml.YAML(typ='safe', pure=True)
            TestSchema.common = list(yaml.load_all(fh))

        for kind, fnames in by_kind.items():
            with self.subTest(kind=kind):
                schema = f"tests/schema_{kind}.yaml"
                self.validate(schema, fnames)
