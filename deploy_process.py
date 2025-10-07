#!/usr/bin/env python

"""
Script to automate the deplyoment of gg processes
"""

from string import Template

from common.common import read_json

import argparse
import time

import gen_prms
import gg


"""
Constants
"""
COMMAND_MAPPING = {
    "extract": {
        "issue_command": "extract_issue_command",
        "retrieve_status_command": "extract_retrieve_status",
    },
    "replicat": {
        "issue_command": "replicat_issue_command",
        "retrieve_status_command": "replicat_retrieve_status",
    },
}


class ProcessDeployer:
    def __init__(self, config, env, process_type, password):
        self.config = config
        self.env = env
        self.process_type = process_type
        self.password = password
        #
        self.process_config = config[env][process_type]
        self.process_name = self.process_config["process_name"]
        #
        self.commands = COMMAND_MAPPING[process_type]
        self.issue_command = self.commands["issue_command"]
        self.retrieve_status_command = self.commands["retrieve_status_command"]

    def stop(self, force):
        if force:
            stop_args_json = '{"command": "FORCESTOP"}'
        else:
            stop_args_json = '{"command": "STOP"}'
        print(f"Stopping process {self.process_name}")
        gg.do_work(
            self.config,
            self.env,
            self.issue_command,
            self.process_name,
            command_args_json=stop_args_json,
            password=self.password,
        )
        stopped = False
        while not stopped:
            r = gg.do_work(
                self.config,
                self.env,
                self.retrieve_status_command,
                command_arg=self.process_name,
                password=self.password,
            ).json()
            if r["status"] == "stopped":
                stopped = True
            else:
                print(f"Status returned: {r['status']}, waiting...")
                time.sleep(10)
        print("done")

    def start(self):
        print(f"Starting process {self.process_name}")
        cmd_template = Template(
            '{"name": "start", "processName": "process_name", "processType": "$process_type"}'
        )
        cmd_json = cmd_template.substitute(
            process_name=self.process_name, process_type=self.process_type
        )
        gg.do_work(
            self.config,
            self.env,
            "execute_command",
            command_arg=self.process_name,
            command_args_json=cmd_json,
            password=self.password,
        )
        print("done")

    def process_exists(self):
        r = gg.do_work(
            self.config,
            self.env,
            self.issue_cmd,
            self.process_name,
            password=self.password,
        ).json()
        for item in r["items"]:
            if item["name"] == self.process_name:
                print(f"Process {self.process_name} exists")
                return True
        print(f"Process {self.process_name} not found")
        return False


class ExtractDeployer(ProcessDeployer):
    def __init__(self, config, env, password):
        super().__init__(self, config, env, "extract", password)


class RepicatDeployer(ProcessDeployer):
    def __init__(self, config, env, password):
        super().__init__(self, config, env, "replicat", password)


"""
do_work
"""


def do_work(config, env, command, force, password=None):
    None


"""
initializes argparse
"""


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="deploys the prm files")
    parser.add_argument("config_file", help="config file (json)")
    parser.add_argument("env", choices=gen_prms.VALID_ENVS, help="environment")
    parser.add_argument(
        "command", choices=gg.CONFIGURATION_FILES_COMMANDS, help="command"
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="stop the processes with force"
    )
    parser.add_argument("-p", "--password", help="GGADMIN password")
    return parser


"""
main
"""


def main():
    parser = init_argparse()
    args = parser.parse_args()
    config = read_json(args.config_file)
    do_work(config, args.env, args.command, args.force, args.password)


"""
"""
if __name__ == "__main__":
    main()
