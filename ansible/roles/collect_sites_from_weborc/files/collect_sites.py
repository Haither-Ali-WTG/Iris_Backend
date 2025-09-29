"""
Collect sites data from WebORC service

Fetches IIS sites data from WebORC service and saves to individual files
"""

import argparse
import ipaddress
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List
import requests


LOGGER = logging.getLogger("collect_sites_weborc")


def parse_arguments() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Fetch and save IIS sites data.")
    parser.add_argument(
        "--weborc_url", "-s",
        help="Weborc service",
        type=str,
        required=True
    )
    parser.add_argument(
        "--output_path", "-o",
        help="Output file path",
        type=str,
        default="iis_sites_v2",
    )
    parser.add_argument(
        "--debug_output", "-d",
        help="Output debug info (0=INFO, 1=DEBUG)",
        type=int,
        choices=[0, 1],
        default=0,
    )
    parser.add_argument(
        "--ca_cert",
        help="Path to CA cert(PEM). If provided, SSL verification is enabled.",
        type=str,
        default=None,
    )
    return parser.parse_args()


def setup_logging(debug: int) -> None:
    """Configure logging level and format."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )


def validate_response(data: Any) -> bool:
    """
    Validate response structure:
      - top-level must be a list
      - each item is a dict with keys:
        - hostName (non-empty str)
        - hostIP (valid IP address)
        - sites (list; can be empty)
    """
    if not isinstance(data, list):
        LOGGER.error("Response is not a list.")
        return False

    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            LOGGER.error("Item %d is not an object.", idx)
            return False

        hostname = item.get("hostName")
        hostip = item.get("hostIP")
        sites = item.get("sites")

        if not hostname or not isinstance(hostname, str):
            LOGGER.error("Item %d has invalid hostName.", idx)
            return False

        try:
            ipaddress.ip_address(str(hostip))
        except ValueError:
            LOGGER.error("Item %d has invalid hostIP: %r", idx, hostip)
            return False

        if not isinstance(sites, list):
            LOGGER.error("Item %d has invalid sites (must be a list).", idx)
            return False

    return True


def fetch_env_cache(weborc_url: str, verify_param: str | bool) -> List[Dict[str, Any]]:
    """GET IIS data from weborc with 60s timeout and parse JSON."""
    LOGGER.info("Requesting EnvCache from %s", weborc_url)

    try:
        resp = requests.get(weborc_url, timeout=60, verify=verify_param)
    except requests.RequestException as exc:
        LOGGER.error("HTTP request failed: %s", exc)
        raise

    if resp.status_code != 200:
        LOGGER.error("Unexpected HTTP status: %s", resp.status_code)
        raise RuntimeError(f"Non-200 status: {resp.status_code}")

    try:
        data = resp.json()
    except json.JSONDecodeError as exc:
        LOGGER.error("JSON decoding failed: %s", exc)
        raise

    return data


def save_items(items: List[Dict[str, Any]], output_dir: str) -> None:
    """Save each item to <output_dir>/<hostName>."""
    for item in items:
        path = f"{output_dir}/{item['hostName']}"
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(item, fh, indent=4)
            LOGGER.info("Saved %s", path)
        except OSError as exc:
            LOGGER.error("Failed to save %s: %s", path, exc)
            raise


def main() -> int:
    """
    Main function to fetch IIS sites data from WebORC service.
    
    Returns: 0 for success, 1 for failure
    """
    args = parse_arguments()
    setup_logging(args.debug_output)

    start_time = datetime.now()

    verify_param = args.ca_cert if args.ca_cert else False

    try:
        data = fetch_env_cache(args.weborc_url, verify_param)

        if not validate_response(data):
            return 1

        os.makedirs(args.output_path, exist_ok=True)

        save_items(data, args.output_path)

        LOGGER.info("Successfully processed %d items.", len(data))
        LOGGER.info("Execution duration: %s", str(datetime.now() - start_time))
        return 0

    except Exception:  # pylint: disable=broad-except
        LOGGER.exception("Execution failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
