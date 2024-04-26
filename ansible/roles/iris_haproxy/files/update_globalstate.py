"""
Script removes the lines in Haproxy state file that cannot match the config.
"""
import argparse
import os
import sys
import filecmp
import shutil
import re
from typing import Dict, List


def parse_haproxy_config(filename: str) -> Dict[str, int]:
    """
    Parse the haproxy config.
    Concatenate the backend name and server name as the key, value is a list
    of server port and check port.
    sample:
        backend test_com
        server srv1 10.0.0.1:443 check
        server srv2 10.0.0.2:443 check port 8080
        server srv3 10.0.0.3:443 weight 8 check port 8080
        server srv4 10.0.0.4:443 check port 8080 send-proxy
    """
    result_dict = {}
    check_port_pattern = r".*check\s+port\s+(\d+)"

    with open(filename, 'r') as file:
        current_backend = None

        for line in file:
            line = line.strip()
            
            if line.startswith("backend "):
                current_backend = line.split(" ")[1]  # Extract the backend name
            elif line.startswith("server "):
                server_name = line.split(" ")[1]  # Extract the server name
                _, server_port = line.split(" ")[2].split(":")  # Get the port

                key = f"{current_backend}/{server_name}"
                match_result = re.match(check_port_pattern, line)
                if match_result:
                    result_dict[key] = [server_port, match_result.group(1)]
                else:
                    result_dict[key] = [server_port]

    return result_dict

def check_and_generate_state(config_info: Dict[str, List[int]], state_file: str, new_state: str) -> None:
    """
    According to the config info, filter out the lines where the port has changed,
    and save the remains to a new file.
    """
    with open(state_file, 'r') as file:
        state_lines = file.readlines()

    with open(new_state, 'w') as output_file:
        for line in state_lines:
            columns = line.split()
            if len(columns) == 25 and not columns[0].startswith("#"):
                # columns[1] and columns[3] are backend name and server name
                key_to_check = f"{columns[1]}/{columns[3]}"
                
                # srv_port[18] and srv_port[21] are srv_port and srv_check_port
                if (key_to_check in config_info and 
                    (config_info[key_to_check][0] != columns[18] or
                    (len(config_info[key_to_check]) == 2 and config_info[key_to_check][1] != columns[21]))):
                    print(f"Removed: {line}")
                    continue
            output_file.write(line)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True, help="Haproxy config path")
    parser.add_argument('--state_file', type=str, required=True, help="Haproxy state file path")
    args = parser.parse_args()

    # Parse the haproxy config
    config_info = parse_haproxy_config(args.config)
    
    # Compare the haproxy config and state file, and generate a new state file
    new_state_file = args.state_file+'.temp'
    check_and_generate_state(config_info, args.state_file, new_state_file)

    # Only overwrite the state file if they are different with the old one
    if not filecmp.cmp(args.state_file, new_state_file):
        shutil.copyfile(new_state_file, args.state_file)

    os.remove(new_state_file)

    return 0


if __name__ == "__main__":
    sys.exit(main())
