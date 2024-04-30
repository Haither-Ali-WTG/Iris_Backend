"""
Script removes the lines in Haproxy state file that cannot match the config.
"""
import argparse
import os
import filecmp
import shutil
import re
from typing import Dict, List


class StateFileUpdater: # pylint: disable=too-few-public-methods
    """ Class updating Haproxy state file according to config """

    # Key is "{backend_name/server_name}", value is [server port, check port]
    config_info: Dict[str, List[str]] = {}
    removed_lines: List[str] = []

    def __init__(self, state_file: str, config_file: str):
        self.state_file = state_file
        self.config_file = config_file


    def _parse_haproxy_config(self) -> None:
        """
        Parse the haproxy config.
        Concatenate the backend name and server name as the key, value is [server port, check port].
        sample:
            backend test_com
            server srv1 10.0.0.1:443 check
            server srv2 10.0.0.2:443 check port 8080
            server srv3 10.0.0.3:443 weight 8 check port 8080
            server srv4 10.0.0.4:443 check port 8080 send-proxy
        """
        check_port_pattern = r".*check\s+port\s+(\d+)"

        with open(self.config_file, 'r', encoding='utf-8') as file:
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
                        self.config_info[key] = [str(server_port), str(match_result.group(1))]
                    else:
                        self.config_info[key] = [str(server_port), "0"]


    def _check_and_generate_state(self, new_state: str) -> None:
        """
        According to the config info, filter out the lines where the port has changed,
        and save the remains to a new file.
        """
        with open(self.state_file, 'r', encoding='ascii') as file:
            state_lines = file.readlines()

        with open(new_state, 'w', encoding='ascii') as output_file:
            for line in state_lines:
                columns = line.split()
                if len(columns) == 25 and not columns[0].startswith("#"):
                    # columns[1] and columns[3] are backend name and server name
                    key_to_check = f"{columns[1]}/{columns[3]}"

                    # srv_port[18] and srv_port[21] are srv_port and srv_check_port
                    if (key_to_check in self.config_info and
                        (self.config_info[key_to_check][0] != columns[18] or
                        (self.config_info[key_to_check][1] != columns[21]))):
                        self.removed_lines.append(line)
                        continue
                output_file.write(line)


    def update(self) -> List[str]:
        """ Update state file """

        # Parse the haproxy config
        self._parse_haproxy_config()

        # Compare the haproxy config and state file, and generate a new state file
        new_state_file = self.state_file+'.temp'
        self._check_and_generate_state(new_state_file)

        # Only overwrite the state file if they are different with the old one
        if not filecmp.cmp(self.state_file, new_state_file):
            shutil.copyfile(new_state_file, self.state_file)

        os.remove(new_state_file)
        return self.removed_lines


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True, help="Haproxy config path")
    parser.add_argument('--state_file', type=str, required=True, help="Haproxy state file path")
    args = parser.parse_args()

    state_file_updater = StateFileUpdater(state_file=args.state_file, config_file=args.config)
    removed_lines = state_file_updater.update()

    for line in removed_lines:
        print(f"Removed: {line}")
