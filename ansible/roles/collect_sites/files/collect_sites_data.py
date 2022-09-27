"""
Collect sites data from IIS machines using winrm

Script collects data from all IIS machines using winrm module
"""

import argparse
import concurrent.futures
from dataclasses import dataclass
from datetime import datetime
import logging
import os
import re
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

def get_websites_with_parameters(sites_list, website_config, logger):
    """Combine sites list with correspondent configuration from websites.yml"""
    websites = {}

    for site_name in sites_list:
        site_name = site_name.lower()
        # This regular expression copied directly from Nico bash script
        if not re.match(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}$)',
                        site_name):
            logger.info('%s: Site name contains an illegal character. Skipping................',
                        site_name)
            continue

        name_matched = False
        for config in website_config:
            if (site_name.startswith(tuple(config['starts_with']))
                 or any(like in site_name for like in config['name_like'])):
                websites[site_name] = config
                name_matched = True

        if not name_matched:
            logger.info('%s: Site name does not match any config. Skipping................',
                        site_name)

    return websites

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

def process_server(server_name, connection_params, website_config, output_path, logger):
    """Read and process all websites data from give IIS box"""
    try:
        sites_list = get_websites_list(server_name, connection_params)
    except (ValueError, InvalidCredentialsError, requests.exceptions.RequestException) as err:
        logger.info("%s: ERROR: %s", server_name, str(err))
        return
    if len(sites_list) == 0:
        return

    websites = get_websites_with_parameters(sites_list, website_config, logger)

    with open(f"{output_path}/{server_name}.yml", 'w', encoding="utf8") as outfile:
        yaml.dump(websites, outfile, default_flow_style=False)

    ##############################################################################################
def main():
    """Function collects all websites from all IIS boxes, applies configuration from websites.yml
    and dumps data to file named server_name.yml in servers folder"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--server_list', '-sl', help="Comma separated list of servers to process",
                        type=str)
    parser.add_argument('--server_config_file', '-sc', help="File with servers configuration",
                        type=str, default='config/servers.yml')
    parser.add_argument('--website_config_file', '-wc', help="File with websites configuration",
                        type=str, default='config/websites.yml')
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
    logger.info('Server Config File: %s', args.server_config_file)
    logger.info('Website Config File: %s', args.website_config_file)
    logger.info('Output Path: %s', args.output_path)
    logger.info('Validating CA: %s', args.validate_ca)
    logger.info('Username: %s', args.user_name)

    start_time = datetime.now()
    server_list = args.server_list.lower().split(',')

    server_config = load_yaml_from_file(args.server_config_file)
    websites_config = load_yaml_from_file(args.website_config_file)

    if not os.path.exists(args.output_path):
        os.mkdir(args.output_path)

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=args.threads)
    results = []

    for server in server_list:
        server = server.strip()
        if not server.startswith(tuple(server_config['computer_name_prefixes'])):
            logger.info("%s: Server name not matching template. Skipping...............",
                        server)
            continue

        logger.info("Adding to processing: %s", server)
        results.append(executor.submit(process_server, server,
                                       ConnectionParameters(args.user_name, args.password,
                                       args.validate_ca),
                                       websites_config, args.output_path, logger))

    for future in concurrent.futures.as_completed(results):
        future.result()

    logger.info("Execution duration: %s", str(datetime.now() - start_time))
    return 0

if __name__ == "__main__":
    sys.exit(main())
