#!/usr/bin/env python3

# For running commands against multiple instances
#
# Author: Justin Tang

import argparse
import boto3
import botocore.exceptions
from botocore.exceptions import ClientError
import json
import subprocess
import sys
import time
from .common import *
from sys import platform


def configure_session_client(profile, region):
    global session
    session = boto3.Session(profile_name=profile, region_name=region)


def parse_args(argv):
    """
    Parse command line arguments
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, usage=usage(), add_help=False)
    parser.add_argument("instances", nargs='+')
    add_general_parameters(parser)
    add_required_parameters(parser)
    args = parser.parse_args(argv)

    return args


def usage():
    msg = "ssm-run instances [instances ...] [--help] [--profile PROFILE] [--region REGION] --commands COMMANDS [COMMANDS ...]"
    return msg


def add_required_parameters(parser):
    required = parser.add_argument_group('Required Parameters')
    required.add_argument(
        '--commands', '-c', help='Commands to run against instances', required=True, nargs='+')
    return required


def get_response(command_id):
    command_check = get_command_status(command_id)
    while True:
        res = [ci["Status"] in ["Success", "Failed"]
               for ci in command_check["CommandInvocations"]]
        status = all(res)
        if len(command_check["CommandInvocations"]) == 0 or not status:
            time.sleep(1)
            command_check = get_command_status(command_id)
        else:
            return command_check


def get_instance_ids(instances, profile, region):
    i = [{get_instance(instance, profile, region): instance}
         for instance in instances]
    # remove any invalid or instances not found
    return {k: v for d in i for k, v in d.items() if k != None}


def get_command_status(command_id):
    command_check = ssm.list_command_invocations(
        CommandId=command_id, Details=True)
    return command_check


def main():
    args = parse_args(sys.argv[1:])
    configure_session_client(args.profile, args.region)
    global ssm
    try:
        ssm = session.client('ssm')
        instances = get_instance_ids(args.instances, args.profile, args.region)
        response = ssm.send_command(
            InstanceIds=list(instances.keys()), DocumentName="AWS-RunShellScript", Parameters={'commands': args.commands})
        command_id = response["Command"]["CommandId"]
        command_check = get_response(command_id)
        print("\n Output\n--------")
        for ci in command_check["CommandInvocations"]:
            print(f'{instances[ci["InstanceId"]]} | {ci["InstanceId"]}')
            for command in ci["CommandPlugins"]:
                print(command["Output"])
    except (botocore.exceptions.BotoCoreError,
            botocore.exceptions.ClientError) as e:
        print(e)
        quit(1)


if __name__ == "__main__":
    main()
