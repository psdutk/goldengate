#!/usr/bin/env python

"""
Script to automate the deplyoment of gg files
"""

from getpass import getpass
import argparse
import string
import time

import common
import gen_prms
import gg

from constants import VALID_ENVS


"""
Constants
"""


"""
"""


class PrmDeployer:
    def __init__(self, config, env, ggadmin_password, verbose=False):
        self.config = config
        self.env = env
        self.ggadmin_password = ggadmin_password
        self.verbose = verbose

    """
    generate all the needed prm files for the environment env
    """

    def generate_prms(self):
        if self.verbose:
            print("generating prms")
        gen_prms.gen_prms(self.config, self.env)

    """
    return True if the process exists, False otherwise
    """

    def process_exists(self, process_type, issue_cmd):
        process_name = self.config[self.env]["processes"][process_type]["process_name"]
        if self.verbose:
            print(
                f"Checking process_type: {process_type} process_name: {process_name} command: {issue_cmd}"
            )
        resp = gg.do_work(
            config=self.config,
            env=self.env,
            command=issue_cmd,
            password=self.ggadmin_password,
            verbose=self.verbose,
        ).json()
        if resp:
            for item in resp["response"]["items"]:
                if item["name"] == process_name:
                    if self.verbose:
                        print(f"Process {process_name} exists")
                    return True
            if self.verbose:
                print(f"Process {process_name} not found")
            return False
        else:
            raise Exception(
                f"Command: {issue_cmd} returned unexpected value {resp.status_code}"
            )

    """
    stops the given process and waits until the process status is stopped
    """

    def stop_process(
        self,
        process_type,
        issue_cmd,
        force,
        retrieve_status_cmd,
    ):
        process_name = self.config[self.env]["processes"][process_type]["process_name"]
        if self.verbose:
            print(f"Stopping {process_type} {process_name}")
        if force:
            stop_args_json = '{"command": "FORCESTOP"}'
        else:
            stop_args_json = '{"command": "STOP"}'
        gg.do_work(
            config=self.config,
            env=self.env,
            command=issue_cmd,
            command_arg=process_name,
            command_args_json=stop_args_json,
            password=self.ggadmin_password,
            verbose=self.verbose,
        )

        stopped = False
        while not stopped:
            resp = gg.do_work(
                config=self.config,
                env=self.env,
                command=retrieve_status_cmd,
                command_arg=process_name,
                password=self.ggadmin_password,
                verbose=self.verbose,
            ).json()
            if resp["response"]["status"] in ("stopped", "abended"):
                stopped = True
            else:
                if self.verbose:
                    print(f"Status returned: {resp['response']['status']}, waiting...")
                time.sleep(10)
        if self.verbose:
            print(f"{process_name} stopped")

    """
    strts the process given by process_name
    """

    def start_process(self, process_type):
        process_name = self.config[self.env]["processes"][process_type]["process_name"]
        if self.verbose:
            print(f"Starting process {process_name}")
        cmd_template = string.Template(
            '{"name": "start", "processName": "$process_name", "processType": "$process_type"}'
        )
        cmd_json = cmd_template.substitute(
            process_name=process_name, process_type=process_type
        )
        gg.do_work(
            config=self.config,
            env=self.env,
            command="execute_command",
            command_args_json=cmd_json,
            password=self.ggadmin_password,
            verbose=self.verbose,
        )
        if self.verbose:
            print(f"{process_name} started")

    """
    """

    def get_config_files(self):
        resp = gg.do_work(
            config=self.config,
            env=self.env,
            command="list_config_files",
            password=self.ggadmin_password,
            verbose=self.verbose,
        ).json()
        config_files = []
        for item in resp["response"]["items"]:
            config_files.append(item["name"])
        return config_files

    """
    """

    def upload_config_file(self, file_name, command):
        if self.verbose:
            print(f"Uploading file {file_name}")
        gg.do_work(
            config=self.config,
            env=self.env,
            command=command,
            command_arg=file_name,
            command_arg_fn=file_name,
            password=self.ggadmin_password,
            verbose=self.verbose,
        )
        if self.verbose:
            print(f"{file_name} deployed")

    """
    deploys the given file with the  associated command
    """

    def deploy_config_files(self, files):
        available_config_files = self.get_config_files()
        for file_name in files:
            if file_name in available_config_files:
                self.upload_config_file(file_name, "replace_configuration_file")
            else:
                self.upload_config_file(file_name, "create_configuration_file")


"""
returns a list containing all proccess file names
"""


def get_process_files(process_config):
    # this is for backward compatibility
    if isinstance(process_config["prm_table_file_name"], str):
        file_names = [process_config["prm_table_file_name"]]
    else:
        file_names = process_config["prm_table_file_name"]
    # now add just the process prm file
    file_names.append(process_config["prm_file_name"])
    return file_names


"""
do_work
"""


def do_work(args):
    config = common.read_json(args.config_file)
    ggadmin_password = args.password
    if not ggadmin_password:
        ggadmin_password = getpass("Enter GGADMIN Password:")
    #
    prm_deployer = PrmDeployer(config, args.env, ggadmin_password, args.verbose)
    prm_deployer.generate_prms()
    extract_exists = prm_deployer.process_exists("extract", "list_extracts")
    replicat_exists = prm_deployer.process_exists("replicat", "list_replicats")
    #
    if extract_exists:
        prm_deployer.stop_process(
            "extract",
            "extract_issue_command",
            args.force,
            "extract_retrieve_status",
        )
    if replicat_exists:
        prm_deployer.stop_process(
            "replicat",
            "replicat_issue_command",
            args.force,
            "replicat_retrieve_status",
        )
    source_files = get_process_files(config[args.env]["processes"]["extract"])
    target_files = get_process_files(config[args.env]["processes"]["replicat"])
    prm_deployer.deploy_config_files(source_files + target_files)
    if extract_exists:
        prm_deployer.start_process("extract")
    if replicat_exists:
        prm_deployer.start_process("replicat")


"""
initializes argparse
"""


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="""
Generates and deploys all prm files associated to the given environment
""",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
This script performs the following tasks:

1. the extract process is stopped
2. the replicat process stopped
3. all associated prm files are uploaded using the given command
4. the extract process is started
5. the replicat process is started

Example: create all prm files for the prod environment and uploads them

    ./deploy_prms.py config.json prod
""",
    )
    parser.add_argument("config_file", help="config file (json)")
    parser.add_argument("env", choices=VALID_ENVS, help="environment")
    parser.add_argument(
        "-f", "--force", action="store_true", help="stop the processes with force"
    )
    parser.add_argument("-p", "--password", help="GGADMIN password")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="increase output verbosity"
    )
    return parser


"""
main
"""


def main():
    parser = init_argparse()
    args = parser.parse_args()
    do_work(args)


"""
"""
if __name__ == "__main__":
    main()
