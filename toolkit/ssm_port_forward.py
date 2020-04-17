#!/usr/bin/env python3

# For port forwarding
# Convenience wrapper around 'aws ssm start-session --document-name AWS-StartPortForwardingSession'
# can resolve instance id from Name tag, hostname, IP address, etc.
#
# Author: Justin Tang

import argparse
import boto3
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from .common import *
from sys import platform


def sigterm_handler(signal, frame):
    if command_id:
        print(f"Stopping remote SSH tunnel with Command ID {command_id}")
        ssm.cancel_command(CommandId=command_id)
        ssm_send_command(instance_id, "AWS-RunShellScript", {"commands": [
            f"userdel tunneluser_{uuid}", f"rm -rf /home/tunneluser_{uuid}/"]})
    sys.exit(0)


def parse_args(argv):
    """
    Parse command line arguments
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, add_help=False)
    add_general_parameters(parser)
    add_required_parameters(parser)
    add_optional_parameters(parser)
    args = parser.parse_args(argv)

    return args


def add_required_parameters(parser):
    required = parser.add_argument_group('Required Parameters')
    required.add_argument(
        '--target', '-t', help='Target instance:port to set up port forwarding too', required=True)
    required.add_argument('--local', '-l',
                          help='Local port to forward', required=True)

    return required


def add_optional_parameters(parser):
    optional = parser.add_argument_group('Optional Parameters')
    optional.add_argument('--remote', '-r',
                          help='Remote instance:port to forward to', required=False)

    return optional


def get_ssm_client(profile, region):
    profile = profile if profile != None else "default"
    region = region if region != None else "us-east-1"
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('ssm')


def ssm_send_command(instance_id, document_name, parameters):
    return ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName=document_name,
        Parameters=parameters
    )


def get_command_status(command_id):
    command_check = ssm.list_command_invocations(
        CommandId=command_id, InstanceId=instance_id, Details=True)
    return command_check


def wait_for_command(command):
    response = ssm_send_command(instance_id, "SSMValidate", {
                                "command": [command]})
    command_id = response['Command']['CommandId']
    status = get_command_status(command_id)
    while len(status['CommandInvocations']) == 0 or status['CommandInvocations'][0]['Status'] not in ["Success", "Failed"]:
        time.sleep(1)
        status = get_command_status(command_id)
    if status['CommandInvocations'][0]['Status'] == "Failed":
        return False
    elif status['CommandInvocations'][0]['Status'] == "Success":
        return True
    return None


def start_remote_ssh_tunnel(remote):
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName='SSHTunnel',
        Parameters={
            "port": [port],
            "target": [remote],
            "user": [f"tunneluser_{uuid}"]
        }
    )
    return response['Command']['CommandId']


def port_forward(local, profile, region):
    params = f'{{\\"portNumber\\":[\\"{port}\\"],\\"localPortNumber\\":[\\"{local}\\"]}}' if platform in [
        "win32", "win64"] else f'\'{json.dumps({"portNumber": [port], "localPortNumber": [local]})}\''
    extra_args = ""
    extra_args += f"--profile {profile}" if profile else ""
    extra_args += f"--region {region}" if region else ""
    command = f'aws ssm start-session --target {instance_id} --document-name AWS-StartPortForwardingSession --parameters {params} {extra_args}'
    subprocess.call(command, shell=True)


def validate_args(args):
    error = False
    if int(args.local) < 1024:
        print(
            f"[ERROR] Cannot use a privileged port locally, found {args.local}")
        print("See https://www.w3.org/Daemon/User/Installation/PrivilegedPorts.html")
        error = True
    if ':' not in args.target:
        print(
            f'Target not in correct format. Please specify ports. Found target = {args.target}')
        print('Format: instance:port')
        error = True
    if args.remote != None and ':' not in args.remote:
        print(
            f'Remote not in correct format. Please specify ports. Found remote = {args.remote}')
        print('Format: instance:port')
        error = True
    return error


def setup_signal_handlers():
    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGINT, sigterm_handler)
    signal.signal(signal.SIGABRT, sigterm_handler)
    signal.signal(signal.SIGABRT, sigterm_handler)


def setup_globals(target, args):
    global ssm
    global instance_id
    global port
    global uuid
    global command_id
    ssm = get_ssm_client(args.profile, args.region)
    instance_id = get_instance(target.split(":")[0])
    if not instance_id:
        raise Exception("Instance ID not found")
    port = target.split(":")[1]
    generated_uuid = str(uuid.uuid4())
    first_half = round(len(generated_uuid)/2)
    uuid = generated_uuid[:first_half]
    command_id = None


def main():
    setup_signal_handlers()
    args = parse_args(sys.argv[1:])
    error = validate_args(args)
    if error:
        return
    try:
        setup_globals(args.target, args)
    except:
        return
    if args.remote != None:
        if wait_for_command(f"exec 3<>/dev/tcp/127.0.0.1/{port}"):
            global command_id
            command_id = start_remote_ssh_tunnel(args.remote)
            wait_for_command(
                f'ps aux | grep "ssh -N -L {port}:{args.remote} tunneluser_{uuid}"')
        else:
            print(f"Port {port} in use on {instance_id}")
            return
    port_forward(args.local, args.profile, args.region)


if __name__ == "__main__":
    main()
