"""
CMS Certificates Audit Script.

This script parses all `*-clustered_instances.yml` files, queries the CMS API
for certificate metadata (including Key Vault names), and generates flattened,
deduplicated YAML audit reports for each data center.
"""

import os
import glob
from typing import Dict, List, Any, Set, Tuple, Optional
import requests
import yaml
import urllib3
import ruamel.yaml

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CMS_ENDPOINT: str = "https://cms.gis.wtg.zone"
DEFAULT_KV: str = "kv-wtg-iris-prod"

class CMSCache:
    """
    Cache for CMS API responses to minimize network requests.
    """
    
    def __init__(self) -> None:
        self.rg_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.cert_cache: Dict[str, str] = {}

    def get_rg_certs(self, resource_group: str) -> List[Dict[str, Any]]:
        """Fetch all certificates for a given resource group from the CMS API."""
        if resource_group in self.rg_cache:
            return self.rg_cache[resource_group]
        
        url: str = f"{CMS_ENDPOINT}/v1/certificates/{resource_group}"
        try:
            resp: requests.Response = requests.get(url, verify=False, timeout=10)
            if resp.status_code == 200:
                data: List[Dict[str, Any]] = resp.json()
                self.rg_cache[resource_group] = data
                return data
        except Exception as e:
            print(f"Error fetching RG {resource_group}: {e}")
            
        self.rg_cache[resource_group] = []
        return []

    def get_cert_kv(self, resource_group: str, name: str) -> str:
        """Fetch the Key Vault name for a specific certificate."""
        cache_key: str = f"{resource_group}/{name}"
        if cache_key in self.cert_cache:
            return self.cert_cache[cache_key]
        
        url: str = f"{CMS_ENDPOINT}/cms/v1/certificate/{resource_group}/{name}"
        try:
            resp: requests.Response = requests.get(url, verify=False, timeout=10)
            if resp.status_code in [200, 201]:
                data: Dict[str, Any] = resp.json()
                kv: str = data.get('keyvault', DEFAULT_KV)
                self.cert_cache[cache_key] = kv
                return kv
        except Exception:
            pass
            
        self.cert_cache[cache_key] = DEFAULT_KV
        return DEFAULT_KV


def process_host_certificates(
    certificates: List[Any], 
    cache: CMSCache
) -> List[Dict[str, str]]:
    """
    Process the certificates list for a single host.
    
    Returns a sorted, deduplicated list of resolved certificates.
    """
    instance_certs: List[Dict[str, str]] = []
    seen_certs: Set[str] = set()

    def add_cert(name: str, rg: str, kv: str) -> None:
        """Helper to deduplicate and append a certificate."""
        if name not in seen_certs:
            seen_certs.add(name)
            instance_certs.append({
                'name': name,
                'resource_group': rg,
                'keyvault': kv
            })

    for cert in certificates:
        if not isinstance(cert, dict):
            continue

        c_name: Optional[str] = cert.get('name')
        c_file_name: Optional[str] = cert.get('file_name')
        cms_rg: Optional[str] = cert.get('cms_resource_group')

        # 1. Handle certificates defined by file_name
        if c_file_name and cms_rg:
            rg_data: List[Dict[str, Any]] = cache.get_rg_certs(cms_rg)
            for item in rg_data:
                if item.get('config_filename') == c_file_name:
                    cert_name: str = item.get('name', '')
                    kv: str = item.get('keyvault', DEFAULT_KV)
                    add_cert(cert_name, cms_rg, kv)
        
        # 2. Handle certificates defined by direct name
        if c_name:
            rg: str = cms_rg if cms_rg else "UNKNOWN"
            kv = DEFAULT_KV
            if cms_rg:
                kv = cache.get_cert_kv(cms_rg, c_name)
            add_cert(c_name, rg, kv)

    # Sort the list of dictionaries alphabetically by the 'name' key
    instance_certs.sort(key=lambda x: x['name'])
    return instance_certs


def parse_cluster_files(cache: CMSCache) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
    """
    Parse all `-clustered_instances.yml` files and process their certificates.
    
    Returns a nested dictionary organized by: { dc: { host_name: [certificates] } }
    """
    instances_dir: str = os.path.join(os.getcwd(), 'data', 'instances')
    pattern: str = os.path.join(instances_dir, '*-clustered_instances.yml')
    files: List[str] = glob.glob(pattern)

    dc_results: Dict[str, Dict[str, List[Dict[str, str]]]] = {}

    for file_path in files:
        file_name: str = os.path.basename(file_path)
        dc: str = file_name.split('-')[0]
        
        try:
            with open(file_path, 'r') as f:
                data: Dict[str, Any] = yaml.safe_load(f)
        except Exception as e:
            print(f"Error reading {file_name}: {e}")
            continue

        if not data or 'clustered_instances' not in data or 'hosts' not in data['clustered_instances']:
            continue

        if dc not in dc_results:
            dc_results[dc] = {}

        hosts: Dict[str, Any] = data['clustered_instances']['hosts']
        for host_name, host_data in hosts.items():
            if not host_data:
                continue
            
            certificates: List[Any] = host_data.get('certificates', [])
            if not certificates:
                continue

            # Process certificates for the current host
            resolved_certs: List[Dict[str, str]] = process_host_certificates(certificates, cache)
            if resolved_certs:
                dc_results[dc][host_name] = resolved_certs

    return dc_results


def write_audit_files(dc_results: Dict[str, Dict[str, List[Dict[str, str]]]]) -> None:
    """
    Write the processed results out to the YAML audit files.
    """
    audit_dir: str = os.path.join(os.getcwd(), 'data', 'certificates_audit')
    os.makedirs(audit_dir, exist_ok=True)

    # Initialize ruamel.yaml for strict formatting (matches yamllint rules)
    ryaml = ruamel.yaml.YAML()
    ryaml.indent(mapping=2, sequence=4, offset=2)

    for dc, hosts_data in dc_results.items():
        if not hosts_data:
            continue
            
        out_file: str = os.path.join(audit_dir, f"{dc}-certificates.yaml")
        with open(out_file, 'w') as f:
            f.write("---\n")
            ryaml.dump(hosts_data, f)
            print(f"Written {out_file}")


def main() -> None:
    """
    Main execution point for the CMS certificate audit pipeline.
    """
    cache = CMSCache()
    
    # 1. Parse and resolve all certificates
    dc_results = parse_cluster_files(cache)
    print(dc_results)
    
    # 2. Generate the final audit files
    write_audit_files(dc_results)


if __name__ == "__main__":
    main()
