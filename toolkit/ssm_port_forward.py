#!/usr/bin/env python3

# For port forwarding
# Convenience wrapper around 'aws ssm start-session --document-name AWS-StartPortForwardingSession'
# can resolve instance id from Name tag, hostname, IP address, etc.
#
# Author: Justin Tang

import argparse
import boto3
from .common import *
import json
import logging
import os
import platform
import random
import socket
import signal
import subprocess
import sys
import time
import uuid

streamHandler = logging.StreamHandler()
formatter = logging.Formatter(
    "[%(name)s] %(levelname)s: %(message)s"
)
streamHandler.setFormatter(formatter)
logger = logging.getLogger("ssm-port-forward")
logger.addHandler(streamHandler)
logger.setLevel(logging.INFO)

def sigterm_handler(signal, frame):
    if create_user_command_id:
        # using the 'force' option so we can fail silently if file doesn't exist
        force_option = "-Force" if os.name == 'nt' else "-f"
        ssm_send_command(instance_id, "AWS-RunShellScript", {"commands": [
            f"userdel tunneluser_{uuid}", f"rm -rf /home/tunneluser_{uuid}/"]})
        subprocess.Popen(f"rm {force_option} {temp_user_private_key}", executable=executable, shell=True)

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
        '--target', '-t', help='Target instance:port to set up port forwarding to.  If the --remote option is specified, Target should only be the instance, without port', required=True)
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


# Parameter command is a list
def run_command(command):
    response = ssm.send_command(InstanceIds=[instance_id], DocumentName="AWS-RunShellScript", Parameters={
                                "commands": command, "executionTimeout": ["10"]})
    return response["Command"]["CommandId"]


def start_remote_ssh_tunnel(remote, region):
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName=f'arn:aws:ssm:{region}:249662433244:document/SSHTunnel',
        Parameters={
            "port": [port],
            "target": [remote],
            "user": [f"tunneluser_{uuid}"]
        }
    )
    return response['Command']['CommandId']


def port_forward_through_tunnel(session, local, remote):
    # establish a new ssh tunnel via the local port from the first port forward we set up
    command = f'{ssh} -N -L {local}:{remote} -i {temp_user_private_key} tunneluser_{uuid}@localhost -p {session} -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" -o "LogLevel=error"'

    # We need to wait for the session port to be established before running the ssh tunnel command
    if os.name == 'nt':
        command = f'while($true) {{ $check=(Get-NetTCPConnection -LocalPort {session} -State Listen -Erroraction silentlycontinue | Measure).count; if($check -gt 0) {{ break; }} }} {command}'
    else:
        command = f'while :; do check=$( lsof -i -P -n | grep {session}); output=$( echo $? ); case "$output" in 0) break ;; *) sleep 5 ;; esac done; {command}'

    logger.debug(f"port forward command: {command}")
    sp = subprocess.Popen(command, executable=executable, shell=True)

def port_forward(local, profile, region):
    params = f'{{\\"portNumber\\":[\\"{port}\\"],\\"localPortNumber\\":[\\"{local}\\"]}}' if os.name == 'nt' else f'\'{json.dumps({"portNumber": [port], "localPortNumber": [local]})}\''
    extra_args = ""
    extra_args += f"--profile {profile} " if profile else ""
    extra_args += f"--region {region} " if region else ""
    command = f'aws ssm start-session --target {instance_id} --document-name AWS-StartPortForwardingSession --parameters {params} {extra_args}'
    subprocess.call(command, shell=True)


def validate_args(args):
    error = False
    if int(args.local) < 1024:
        logger.error(
            f"[ERROR] Cannot use a privileged port locally, found {args.local}")
        logger.error("See https://www.w3.org/Daemon/User/Installation/PrivilegedPorts.html")
        error = True
    if not port_available(int(args.local)):
        logger.error(
            f"[ERROR] Local port {args.local} is not available.  Try again, or choose a different port.")
        error = True
    if ':' not in args.target and args.remote == None:
        logger.error(
            f'Target not in correct format. Please specify ports. Found target = {args.target}')
        logger.error('Format: instance:port')
        error = True
    if args.remote != None and ':' not in args.remote:
        logger.error(
            f'Remote not in correct format. Please specify ports. Found remote = {args.remote}')
        logger.error('Format: instance:port')
        error = True
    return error


def setup_signal_handlers():
    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGINT, sigterm_handler)
    signal.signal(signal.SIGABRT, sigterm_handler)
    signal.signal(signal.SIGABRT, sigterm_handler)


def setup_globals(target, args):
    global ssm, instance_id, port, uuid, create_user_command_id
    global ssh, executable, temp_user_private_key

    create_user_command_id = None
    ssm = get_ssm_client(args.profile, args.region)
    instance_id = get_instance(target.split(":")[0], args.profile, args.region)
    if not instance_id:
        raise Exception("Instance ID not found")
    port = target.split(":")[1] if len(target.split(":")) > 1 else None
    generated_uuid = str(uuid.uuid4())
    first_half = round(len(generated_uuid)/2)
    uuid = generated_uuid[:first_half]

    if os.name == 'nt':
        temp_user_private_key = os.path.join(os.environ['USERPROFILE'],f"tunneluser_{uuid}.pem")
        is_wow64 = (platform.architecture()[0] == '32bit' and 'ProgramFiles(x86)' in os.environ)
        system32 = os.path.join(os.environ['SystemRoot'], 'Sysnative' if is_wow64 else 'System32')
        powershell_path = os.path.join(os.environ['SystemRoot'], 'SysWOW64' if is_wow64 else 'System32')
        executable = os.path.join(powershell_path, 'WindowsPowerShell', 'v1.0', 'powershell.exe')
        ssh = os.path.join(system32, 'openSSH', 'ssh.exe')
    else:
        temp_user_private_key = os.path.join(os.path.expanduser('~'), f'tunneluser_{uuid}.pem')
        executable = "/bin/sh"
        ssh = "ssh"

def get_output_from_command(command_id):
    result = ssm.list_command_invocations(
                CommandId=command_id, InstanceId=instance_id, Details=True)
    logger.debug(result)
    return result['CommandInvocations'][0]["CommandPlugins"][0]["Output"]

def write_user_key(content):
    try:
        with open(temp_user_private_key, "w") as f:
            f.write(content)
        # For Windows, we don't need to restrict permissions for the private key
        if os.name != 'nt':
            subprocess.Popen([f"chmod 600 {temp_user_private_key}"], executable=executable, shell=True)
    except IOError:
        logger.error(f"File '{temp_user_private_key}' not accessible")

def get_available_local_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    found = False
    while not found:
        result = random.randint(1024,65535)
        try:
            sock.bind(("0.0.0.0", result))
            found = True
        except:
            result = random.randint(1024,65535)
    sock.close()
    return str(result)

def port_available(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("0.0.0.0", port))
        sock.close()
        return True
    except:
        sock.close()
        return False

def main():
    global port, create_user_command_id
    setup_signal_handlers()
    args = parse_args(sys.argv[1:])
    error = validate_args(args)
    if error:
        return
    try:
        setup_globals(args.target, args)
    except Exception as e:
        logger.error(e)
        return
    region = get_region() if not args.region else args.region
    if args.remote != None:
        # We need to create a temporary user and key pair on the remote host that we'll use to 
        # establish the ssh tunnel. By echoing the private key, we can retrieve and store it in a local file
        logger.debug(f"tunneluser_{uuid}")
        commands = [
            f"useradd tunneluser_{uuid}",
            f"su tunneluser_{uuid} -c \"ssh-keygen -t rsa -b 1024 -q -N '' -f ~/.ssh/id_rsa\"",
            f"su tunneluser_{uuid} -c \"cp ~/.ssh/id_rsa.pub ~/.ssh/authorized_keys\"",
            f"echo \"$(cat /home/tunneluser_{uuid}/.ssh/id_rsa)\""
        ]
        create_user_command_id = run_command(commands)
        if wait_for_command(ssm, create_user_command_id, instance_id):
            port = "22"
            # used by AWS-StartPortForwardingSession to establish the port fowarding session
            local_session_port = get_available_local_port()
            # retrieve the private key from the output of the AWS-RunShellScript commands above
            pem_key = get_output_from_command(create_user_command_id)
            # store private key in a temporary local file with appropriate permissions for ssh use
            write_user_key(pem_key)
            # Need to run this command first because the AWS-StartPortForwardingSession document is a blocks us from running it afterwards
            port_forward_through_tunnel(local_session_port, args.local, args.remote)
            # establish the local tunnel, which will trigger the second ssh tunnel creation once the port is listening
            port_forward(local_session_port, args.profile, args.region)
        else:
            logger.warning(f"Could not confirm the successful creation of user tunneluser_{uuid} on {instance_id}")
            return
    else:
        port_forward(args.local, args.profile, args.region)


if __name__ == "__main__":
    main()
