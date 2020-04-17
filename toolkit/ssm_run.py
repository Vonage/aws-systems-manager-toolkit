#!/usr/bin/env python3

# For running commands against multiple instances
#
# Author: Justin Tang

import argparse
import boto3
import json
import subprocess
import sys
import time
from .common import *
from sys import platform


def parse_args(argv):
    """
    Parse command line arguments
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, add_help=False)
    parser.add_argument("instances", nargs='+')
    add_general_parameters(parser)
    add_required_parameters(parser)
    args = parser.parse_args(argv)

    return args


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


def get_instance_ids(instances):
    i = [{get_instance(instance): instance} for instance in instances]
    return {k: v for d in i for k, v in d.items()}


def get_command_status(command_id):
    command_check = ssm.list_command_invocations(
        CommandId=command_id, Details=True)
    return command_check


def main():
    args = parse_args(sys.argv[1:])
    region = args.region if args.region else 'us-east-1'
    global ssm
    ssm = boto3.client('ssm', region_name=region)
    instances = get_instance_ids(args.instances)
    if any(i == None for i in instances):
        return
    response = ssm.send_command(
        InstanceIds=list(instances.keys()), DocumentName="AWS-RunShellScript", Parameters={'commands': args.commands})
    command_id = response["Command"]["CommandId"]
    command_check = get_response(command_id)
    for ci in command_check["CommandInvocations"]:
        print(f'{instances[ci["InstanceId"]]} | {ci["InstanceId"]}')
        for command in ci["CommandPlugins"]:
            print(command["Output"])


if __name__ == "__main__":
    main()
