"""
Collect sites data from IIS machines using winrm

Script collects data from all IIS machines using winrm module
"""

import argparse
import concurrent.futures
from dataclasses import dataclass
from datetime import datetime
import json
import logging
import os
import re
import socket
import sys
import yaml

import requests
from winrm.protocol import Protocol
from winrm.exceptions import InvalidCredentialsError

@dataclass
class ConnectionParameters:
    """Dataclass to store basic connection parameters"""
    user_name: str
    password: str
    validate_ca: str

def load_yaml_from_file(file_name):
    """Loading yaml file to dictionary."""
    with open(file_name, 'r', encoding="utf8") as stream:
        return yaml.safe_load(stream)

def get_websites_list(server_name, connection_params):
    """Read sites list from IIS box using winrm"""
    p = Protocol(
        endpoint='https://' + server_name +':5986/wsman',
        transport='ntlm',
        username=connection_params.user_name,
        password=connection_params.password,
        server_cert_validation=connection_params.validate_ca)
    shell_id = None
    try:
        shell_id = p.open_shell()
        command_id = p.run_command(shell_id, '%systemroot%\\system32\\inetsrv\\AppCmd.exe',
                                ['list sites /serverAutoStart:true /text:name'])
        std_out, std_err, _status_code = p.get_command_output(shell_id, command_id)
        p.cleanup_command(shell_id, command_id)
    finally:
        p.close_shell(shell_id)

    if std_err:
        raise ValueError(f"Error when executing AppCmd.exe: {str(std_err)}")

    #some minor manipulations required with output
    raw_output = std_out.decode("utf-8")
    #split string output by new lines
    sites_list = raw_output.split('\r\n')

    #because of new line at the end of raw output, check and cut last element as well
    if not sites_list[-1]:
        del sites_list[-1]
    sites_list.sort()
    return sites_list

def process_server(server_name, connection_params, output_path, logger):
    """Read and process all websites data from give IIS box"""
    try:
        sites_list = get_websites_list(server_name, connection_params)
    except (ValueError, InvalidCredentialsError, requests.exceptions.RequestException) as err:
        logger.error("%s: ERROR: %s", server_name, str(err))
        return {'status': 'error', 'server': server_name, 'error': str(err)}
    if len(sites_list) == 0:
        return {'status': 'empty', 'server': server_name, 'sites_count': 0}

    server_ip = socket.gethostbyname(server_name)

    websites = {}
    for site in sites_list:
        websites[site] = [server_ip]

    with open(f"{output_path}/{server_name}", 'w', encoding="utf8") as outfile:
        yaml.dump(websites, outfile, default_flow_style=False)

    return {'status': 'ok', 'server': server_name, 'sites_count': len(sites_list)}

    ##############################################################################################
def main():
    """Function collects all websites from all IIS boxes, applies configuration from websites.yml
    and dumps data to file named server_name.yml in servers folder"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--server_list', '-sl', help="Comma separated list of servers to process",
                        type=str)
    parser.add_argument('--threads', '-t', help="Number of parallel executions",
                        type=int, default='20')
    parser.add_argument('--output_path', '-o', help="Output file path",
                        type=str, default='servers')
    # TODO: make check certificate default behavior
    parser.add_argument('--validate_ca', '-ca', help="validate CA",
                        type=str, default='ignore')
    parser.add_argument('--user_name', '-u', help="User name",
                        type=str, default='s_lbwinrmquerier')
    parser.add_argument('--password', '-p', help="Password",
                        type=str)
    parser.add_argument('--debug_output', '-do', help="Output debug info",
                        type=int, default=1)
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug_output else logging.INFO,
                        format="%(name)s - %(levelname)s - %(message)s")

    logger = logging.getLogger("collect IIS sites data")
    logger.info('Server list: %s', args.server_list)
    logger.info('threads: %s', args.threads)
    logger.info('Output Path: %s', args.output_path)
    logger.info('Validating CA: %s', args.validate_ca)
    logger.info('Username: %s', args.user_name)

    start_time = datetime.now()
    server_list = args.server_list.lower().split(',')

    if not os.path.exists(args.output_path):
        os.mkdir(args.output_path)

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=args.threads)
    results = []

    for server in server_list:
        server = server.strip()
        logger.info("Adding to processing: %s", server)
        results.append(executor.submit(process_server, server,
                                       ConnectionParameters(args.user_name, args.password,
                                       args.validate_ca),
                                       args.output_path, logger))

    finished_results = [
        future.result()
        for future in concurrent.futures.as_completed(results)
    ]

    json.dump(
        {
            'results': finished_results,
            'wrote_files': any(result['status'] == 'ok' for result in finished_results),
        },
        sys.stdout,
        indent=4,
    )

    logger.info("Execution duration: %s", str(datetime.now() - start_time))
    return 0

if __name__ == "__main__":
    sys.exit(main())
