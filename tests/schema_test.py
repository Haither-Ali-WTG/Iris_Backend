""" Check the configuration files against Yamale schemas """

import os
from collections import defaultdict
from fnmatch import fnmatch

import ruamel.yaml

from inventories.virgil_yamale import VirgilYamaleTestCase

BASE_CONFIG_DIR = '.'
CONFIG_DIRS = ['acls', 'actions', 'ciphers', 'dynamic_backends', 'instances',
               'inventories', 'machine_clusters', 'static_backends', 'test']
CONFIG_PATTERNS = [
    ('acls/*.yaml', 'acls'),
    ('actions/*.yaml', 'actions'),
    ('ansible/group_vars/individual_instances.yml', 'individual_instances'),
    ('artifacts.yml', None),
    ('azure-pipelines*.yml', None),
    ('ciphers/cipher_profiles.yml', 'cipher_profiles'),
    ('dynamic_backends/websites.yml', 'websites'),
    ('instances/*-clustered_instances.yml', 'clustered_instances'),
    ('instances/*-machines.yml', 'machines'),
    ('instances/*-tests.yml', 'instance_tests'),
    ('machine_clusters/*.yaml', 'machine_clusters'),
    ('static_backends/*.yaml', 'static_backends'),
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
        config_paths = {
            os.path.join(BASE_CONFIG_DIR, config_dir)
            for config_dir in CONFIG_DIRS
        }
        config_files = [
            # This is the only file to be checked under the ansible directory,
            # which is otherwise skipped
            'ansible/group_vars/individual_instances.yml',
        ]
        for path, dirs, files in os.walk(BASE_CONFIG_DIR):
            if path == BASE_CONFIG_DIR:
                dirs.remove('.git')
                dirs.remove('ansible')  # only one config file, hard-coded above
                dirs.remove('inventories')
                dirs.remove('reports')
                dirs.remove('tests')

            for file in files:
                if path in config_paths or os.path.splitext(file)[1] in ('.yml', '.yaml'):
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
