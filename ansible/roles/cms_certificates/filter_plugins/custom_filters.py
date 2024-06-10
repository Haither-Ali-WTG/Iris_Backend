from typing import Dict, List, Optional


def from_iris_inventory_host_to_cms_zone(value: str) -> Optional[str]:
    dc = value[0:2].upper()
    domain = value[3:3 + 4].upper()
    if dc == "DE":
        dc = "EU"
    if dc not in {"EU", "AU", "US"}:
        return None
    if domain not in {"PROD", "SAND", "CORP"}:
        return None
    domain = domain.capitalize()
    return f"RG-{dc}-{domain}"


def assign_key_vault_name_from_cache(certs_data: List[Dict[str, str]],
                                     cache: Dict[str, Dict[str, str]]) -> List[Dict[str, str]]:
    for domain_name in certs_data:
        if domain_name['name'] in cache:
            domain_name['key_vault_name'] = cache[domain_name['name']]['key_vault_name']
    return certs_data


def update_cache(cache: Dict[str, Dict[str, str]], updated_certs: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    for domain_name in updated_certs:
        if domain_name['key_vault_name'] is not None and domain_name['key_vault_name'] != 'kv-wtg-iris-prod':
            if not cache.get(domain_name['name']):
                cache[domain_name['name']] = {}
            cache[domain_name['name']]['key_vault_name'] = domain_name['key_vault_name']
    return cache


def from_iris_inventory_to_certs_data(certs_data: List[Dict[str, str]],
                                      item: str, certificates: List[str]) -> List[Dict[str, str]]:
    item = from_iris_inventory_host_to_cms_zone(item)
    for domain_name in certificates:
        ans = {'domain': item, 'name': domain_name}
        certs_data.append(ans)
    return certs_data


def append_intermediate_certificate(secret_values: str, certificate: str) -> str:
    certs = certificate.split("-----END CERTIFICATE-----\n")
    for i in range(len(certs)):
        certs[i] += "-----END CERTIFICATE-----\n"
    certs.pop()
    return secret_values + certs[1] if len(certs) == 3 else secret_values


class FilterModule(object):
    def filters(self):
        return {
            'assign_key_vault_name_from_cache': assign_key_vault_name_from_cache,
            'update_cache': update_cache,
            'from_iris_inventory_to_certs_data': from_iris_inventory_to_certs_data,
            'append_intermediate_certificate': append_intermediate_certificate
        }

