#!/usr/bin/env python

"""
Script to interact with Oracle GoldenGate Microservices Architecture (MA)
"""

from getpass import getpass
from pprint import pprint as pp
from requests.auth import HTTPBasicAuth

import argparse
import json
import posixpath
import requests
import string
import sys
import urllib.parse

import common
from constants import VALID_ENVS

"""
Constants
"""
GG_ADMIN_URL_PATH_PREFIX = "services/v2"
ALL_COMMANDS = common.read_json("ogg_rest_endpoints_def.json")
REST_OK_STATUS_CODE = [200, 201]


"""
gen_url
"""


def gen_url(gg_api_endpoint_url: str, url_suffix: str, command_arg: str | None) -> str:
    url_path = GG_ADMIN_URL_PATH_PREFIX

    if "$" in url_suffix and not command_arg:
        raise Exception(
            f"No --command_arg was given for the url_suffix replacement: {url_suffix}"
        )

    if "$" not in url_suffix and command_arg:
        raise Exception(
            f"Unnecessary --command_arg: {command_arg} for the url_suffix: {url_suffix}\nA command_arg needs to be specified in order to perform the correct operation"
        )

    url_template = string.Template(url_suffix)
    url_path = posixpath.join(url_path, url_template.substitute(url_arg=command_arg))
    url = urllib.parse.urljoin(gg_api_endpoint_url, url_path)
    return url


"""
gen_todo
"""


def gen_todo(command_args_dict: dict | None, command_arg_fn: str | None) -> dict | None:
    todo = None
    # command args
    if command_args_dict and command_arg_fn:
        print(
            "Arguments --command_arg_json and --command_arg_fn are mutually exclusive"
        )
        sys.exit(1)
    if command_args_dict:
        todo = command_args_dict
    elif command_arg_fn:
        with open(command_arg_fn) as fh:
            lines = fh.read().splitlines()
            todo = {"lines": lines}
    return todo


"""
do_call
"""


def do_http_call(
    url, gg_api_endpoint, op, todo, client_cert, client_key, verify_cert
) -> requests.Response:
    if op and url:
        op_call = getattr(requests, op)
        res = None
        if client_cert and client_key:
            if todo:
                res = op_call(
                    url, cert=(client_cert, client_key), json=todo, verify=verify_cert
                )
            else:
                res = op_call(url, cert=(client_cert, client_key), verify=verify_cert)
        else:
            auth_basic = HTTPBasicAuth(
                gg_api_endpoint["user"], gg_api_endpoint["password"]
            )
            if todo:
                res = op_call(url, auth=auth_basic, json=todo, verify=verify_cert)
            else:
                res = op_call(url, auth=auth_basic, verify=verify_cert)
        return res


"""
do_work
"""


def do_work(
    config: dict,
    env: str,
    command: str,
    command_arg: str | None = None,
    command_arg_fn: str | None = None,
    command_args_json: str | None = None,
    gg_api_endpoint_url: str | None = None,
    password: str | None = None,
    client_cert: str | None = None,
    client_key: str | None = None,
    verify_cert: str | None = None,
    verbose: bool = False,
    exit_on_http_err: bool = True,
) -> requests.Response:
    command_args_dict = None
    if command_args_json:
        command_args_dict = json.loads(command_args_json)
        if verbose:
            print("Read following JSON arguments:")
            pp(command_args_dict)

    gg_api_endpoint_env = config[env]["gg_endpoint"]
    gg_api_endpoint = config["gg_endpoints"][gg_api_endpoint_env]
    if gg_api_endpoint_url:
        url = gg_api_endpoint_url
    else:
        url = gg_api_endpoint["url"]
    if not client_cert or not client_key:
        if password:
            gg_api_endpoint["password"] = password
        else:
            gg_api_endpoint["password"] = getpass(
                f"Enter password for {gg_api_endpoint['user']}:"
            )
    command_info = ALL_COMMANDS[command]
    url = gen_url(url, command_info["url_suffix"], command_arg)
    if verbose:
        print(f"Using the following URL: {url}")
    todo = gen_todo(command_args_dict, command_arg_fn)
    if verbose:
        print(f"Generated following todo: {todo}")
        print(f"Will issue a {command_info['op']}")
    if not verify_cert:
        if "verify_cert" in gg_api_endpoint:
            verify_cert = gg_api_endpoint["verify_cert"]
        elif "default_verify_cert" in config:
            verify_cert = config["default_verify_cert"]
        else:
            verify_cert = False

    resp = do_http_call(
        url,
        gg_api_endpoint,
        command_info["op"],
        todo,
        client_cert,
        client_key,
        verify_cert,
    )

    if resp.status_code in REST_OK_STATUS_CODE or not exit_on_http_err:
        return resp
    else:
        sys.stderr.write("HTTP Call returned : " + str(resp.status_code) + "\n")
        sys.stderr.write("URL: " + url + "\n")
        sys.stderr.write("OP: " + command_info["op"] + "\n")
        if todo:
            sys.stderr.write("TODO: " + str(todo) + "\n")

        sys.exit(1)


"""
initializes argparse
"""


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="""
Communicates with Oracle GoldenGate Micrsoervices Architecture (GG MA) via ReST
        """,
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples Commands for Extracts

    ./gg.py config.json prod list_extracts
    ./gg.py config.json prod retrieve_extract --command_arg EXT
    ./gg.py config.json prod extract_retrieve_status --command_arg EXT
    ./gg.py config.json prod update_extract --command_arg EXT --command_args_json '{"credentials": {"alias": "SRC_DB", "domain": "OracleGoldenGate"}}'
    ./gg.py config.json prod extract_issue_command --command_arg EXT --command_args_json '{"command": "STOP"}'
    ./gg.py config.json prod extract_issue_command --command_arg EXT --command_args_json '{"command": "FORCESTOP"}'

Examples Commands for Replicats

    ./gg.py config.json prod list_replicats
    ./gg.py config.json prod retrieve_replicat --command_arg REP
    ./gg.py config.json prod replicat_retrieve_status --command_arg REP
    ./gg.py config.json prod update_replicat --command_arg REP --command_args_json '{"credentials": {"alias": "GGADMIN_TGT", "domain": "OracleGoldenGate"}}'
    ./gg.py config.json prod replicat_issue_command --command_arg REP --command_args_json '{"command": "STOP"}'
    ./gg.py config.json prod replicat_issue_command --command_arg REP --command_args_json '{"command": "FORCESTOP"}'

Examples Commands for Configuration Files

    ./gg.py config.json prod list_config_files
    ./gg.py config.json prod retrieve_configuration_file --command_arg EXT.prm --command_arg_fn EXT.prm
    ./gg.py config.json prod create_configuration_file --command_arg  TEST.prm --command_arg_fn TEST.prm
    ./gg.py config.json prod delete_configuration_file --command_arg  TEST.prm --command_arg_fn TEST.prm
    ./gg.py config.json prod replace_configuration_file --command_arg  TEST.prm --command_arg TEST.prm


Examples Commands for Configuration Data Types

    ./gg.py config.json prod list_configuration_data_types

Examples Commands for Configuration Values

    ./gg.py config.json prod list_configuration_values --command_arg collectionItem
    ./gg.py config.json prod list_configuration_values --command_arg authorizationProfile
    ./gg.py config.json prod list_configuration_values --command_arg managedProcessSettings

Common Commands

    ./gg.py config.json prod execute_command --command_args_json '{"name": "start", "processName": "REP", "processType": "replicat"}'
    ./gg.py config.json prod execute_command --command_args_json '{"name": "start", "processName": "EXT", "processType": "extract"}'
""",
    )
    parser.add_argument("config_file", help="config file (json)")
    parser.add_argument("env", choices=VALID_ENVS, help="environment")
    parser.add_argument("command", choices=list(ALL_COMMANDS), help="command")
    parser.add_argument("--client_cert", help="path to a client certificate file")
    parser.add_argument("--client_key", help="path to a client key file")
    parser.add_argument("--command_arg", help="single argument for the command")
    parser.add_argument("--command_arg_fn", help="file name as an argument")
    parser.add_argument("--command_args_json", help="json as an arguement")
    parser.add_argument("--gg_endpoint_url", help="overrides the url in the config")
    parser.add_argument(
        "--password", help="password for the gg api, if not given, will be asked"
    )
    parser.add_argument(
        "--verify_cert", help="path to a file to verify the server certificates"
    )
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
    config = common.read_json(args.config_file)
    resp = do_work(
        config,
        args.env,
        args.command,
        args.command_arg,
        args.command_arg_fn,
        args.command_args_json,
        args.gg_endpoint_url,
        args.password,
        args.client_cert,
        args.client_key,
        args.verify_cert,
        args.verbose,
    )
    print(json.dumps(resp.json(), indent=4))


"""
"""
if __name__ == "__main__":
    main()
