import os
import glob
import subprocess
import yaml
from typing import Dict, List, Optional, Set, Tuple


def read_audit_certs(playbook_dir: str, target_dc: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Reads the certificates_audit YAML files for the given target_dc (or all of them)
    and aggregates/deduplicates all certificates.
    
    Returns a list of dicts in the legacy format:
    [{'name': str, 'key_vault_name': str}]
    """
    certs_dict = {}
    audit_dir = os.path.normpath(os.path.join(playbook_dir, '../data/certificates_audit'))
    
    if target_dc:
        files = [os.path.join(audit_dir, f"{target_dc.lower()}-certificates.yaml")]
    else:
        files = glob.glob(os.path.join(audit_dir, '*-certificates.yaml'))
        
    for f in files:
        if not os.path.exists(f):
            continue
        try:
            with open(f, 'r') as fp:
                data = yaml.safe_load(fp)
                if not data:
                    continue
                # data is expected to be a dict: { "hostname": [ {"name": "...", "resource_group": "...", "keyvault": "..."}, ... ] }
                for host, certs in data.items():
                    if not isinstance(certs, list):
                        continue
                    for cert in certs:
                        name = cert.get('name')
                        if not name:
                            continue
                        
                        if name not in certs_dict:
                            certs_dict[name] = {
                                'name': name,
                                'key_vault_name': cert.get('keyvault', 'kv-wtg-iris-prod')
                            }
        except Exception as e:
            print(f"Error reading {f}: {e}")
            
    # Return as list sorted by name
    return sorted(list(certs_dict.values()), key=lambda x: x['name'])


def append_intermediate_certificate(secret_values: str, certificate: str) -> str:
    certs = certificate.split("-----END CERTIFICATE-----\n")
    for i in range(len(certs)):
        certs[i] += "-----END CERTIFICATE-----\n"
    certs.pop()
    return secret_values + certs[1] if len(certs) == 3 else secret_values


def _extract_cms_certs_from_data(data: Optional[Dict]) -> Set[Tuple[str, str]]:
    """
    Extract (name, cms_resource_group) tuples from clustered_instances YAML data.
    Excludes file_name-type certificates and those without cms_resource_group.
    """
    certs: Set[Tuple[str, str]] = set()
    if not data or 'clustered_instances' not in data:
        return certs
    hosts = data['clustered_instances'].get('hosts', {}) or {}
    for host_data in hosts.values():
        if not host_data:
            continue
        for cert in host_data.get('certificates', []) or []:
            if not isinstance(cert, dict):
                continue
            if cert.get('file_name'):
                continue
            name: Optional[str] = cert.get('name')
            rg: Optional[str] = cert.get('cms_resource_group')
            if name and rg:
                certs.add((name, rg))
    return certs


def _diff_certs_for_file(rel_path: str, repo_root: str) -> Set[Tuple[str, str]]:
    """Return the set of (name, rg) certs added in rel_path vs origin/master."""
    full_path: str = os.path.join(repo_root, rel_path)
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            new_data = yaml.safe_load(f)
    except OSError as e:
        raise RuntimeError(f"Error reading {rel_path}: {e}") from e

    old_result = subprocess.run(
        ['git', 'show', f'origin/master:{rel_path}'],
        capture_output=True, text=True, cwd=repo_root, check=False
    )
    old_data = yaml.safe_load(old_result.stdout) if old_result.returncode == 0 else None

    return _extract_cms_certs_from_data(new_data) - _extract_cms_certs_from_data(old_data)


def get_new_cms_certs(playbook_dir: str) -> List[Dict[str, str]]:
    """
    Compare clustered_instances files against origin/master and return newly
    added non-file_name certificates that have a cms_resource_group.

    Returns a deduplicated, sorted list of dicts:
      [{'name': str, 'cms_resource_group': str}, ...]
    """
    repo_root: str = os.path.normpath(os.path.join(playbook_dir, '..'))
    instances_dir: str = os.path.join('data', 'instances')

    try:
        result = subprocess.run(
            ['git', 'diff', '--name-only', 'origin/master', 'HEAD', '--', instances_dir],
            capture_output=True, text=True, cwd=repo_root, check=False
        )
    except FileNotFoundError as exc:
        raise RuntimeError("git executable not found") from exc

    if result.returncode != 0:
        raise RuntimeError(f"git diff failed: {result.stderr.strip()}")

    changed_files = [
        f for f in result.stdout.strip().split('\n')
        if f.strip().endswith('-clustered_instances.yml')
    ]

    seen: Set[Tuple[str, str]] = set()
    for rel_path in changed_files:
        seen.update(_diff_certs_for_file(rel_path, repo_root))

    return [
        {'name': name, 'cms_resource_group': rg}
        for name, rg in sorted(seen)
    ]


class FilterModule(object):
    def filters(self):
        return {
            'read_audit_certs': read_audit_certs,
            'append_intermediate_certificate': append_intermediate_certificate,
            'get_new_cms_certs': get_new_cms_certs,
        }
