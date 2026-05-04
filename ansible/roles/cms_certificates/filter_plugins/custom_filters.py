import os
import glob
import yaml
from typing import Dict, List, Optional


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


class FilterModule(object):
    def filters(self):
        return {
            'read_audit_certs': read_audit_certs,
            'append_intermediate_certificate': append_intermediate_certificate
        }
