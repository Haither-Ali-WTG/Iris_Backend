"""
Script removes the lines in Haproxy state file that cannot match the config.
"""
import argparse
import os
import sys
import filecmp
import shutil
from typing import Dict


def parse_haproxy_config(filename: str) -> Dict[str, int]:
    """
    Parse the haproxy config.
    Concatenate the backend name and server name as the key, and the port as the value.
    """
    result_dict = {}

    with open(filename, 'r') as file:
        current_backend = None

        for line in file:
            line = line.strip()
            
            if line.startswith("backend "):
                current_backend = line.split(" ")[1]  # Extract the backend name
            elif line.startswith("server "):
                server_name = line.split(" ")[1]  # Extract the server name
                _, port = line.split(" ")[2].split(":")  # Get the port
                result_dict[f"{current_backend}/{server_name}"] = port

    return result_dict

def check_and_generate_state(config_info: Dict[str, int], state_file: str, new_state: str) -> None:
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
                
                if key_to_check in config_info and config_info[key_to_check] != columns[18]:
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
