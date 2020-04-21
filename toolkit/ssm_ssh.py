#!/usr/bin/env python3

# This script is a wrapper that provides the ability to establish SSH connections
# through Session Manager (for SSM enabled instances).
#
# The script also automatically resolves IP addresses, private instance DNS names, and "name" tag
# values to the corresponding instance ID, if provided in place of instance ID in the command arguments
#
# Author: Chris Heath
# Email: SRE@vonage.com

import argparse
import botocore.exceptions
import logging
import os
import re
from .common import *
from subprocess import Popen, PIPE


streamHandler = logging.StreamHandler()
formatter = logging.Formatter(
    "[%(name)s] %(levelname)s: %(message)s"
)
streamHandler.setFormatter(formatter)
logger = logging.getLogger("ssm-ssh")
logger.addHandler(streamHandler)
logger.setLevel(logging.WARNING)
args = None


# Method uses ArgumentParser to retrieve command-line arguments and display help interface
def get_sys_args():
    parser = argparse.ArgumentParser(
        "ssm-ssh [ssh-option]... \n\nAll standard SSH options are available.  See 'man ssh'")
    parser.add_argument("--region", metavar="REGION",
                        help="Set / override AWS region")
    parser.add_argument("--profile", metavar="PROFILE",
                        help="Configuration profile from ~/.aws/{credentials,config}")
    return parser.parse_known_args()


def start_session(arg_list):
    ssh_args = f"{arg_list.params} " if arg_list.params else ""
    extra_args = f"--profile {arg_list.profile} " if arg_list.profile else ""
    extra_args += f"--region {arg_list.region} " if arg_list.region else ""

    if os.name == 'nt':
        conf = f"{os.environ['USERPROFILE']}\.ssm_ssh_conf"
        executable = "{}\system32\WindowsPowerShell\{}1.0\powershell.exe".format(
            os.environ['SYSTEMROOT'], 'v')
        proxy_command = f"{executable} \"aws {extra_args} ssm start-session --target %h --document-name AWS-StartSSHSession --parameters portNumber=%p\""
    else:
        conf = os.path.join(os.path.expanduser('~'), '.ssm_ssh_conf')
        executable = "/bin/sh"
        proxy_command = f'sh -c "aws {extra_args} ssm start-session --target %h --document-name AWS-StartSSHSession --parameters \'portNumber=%p\'"'

    logger.debug(conf)

    # Create an SSH config file that will enable SSH connections through Session Manager
    try:
        with open(conf, "w") as f:
            f.write(f'# SSH over Session Manager\n')
            f.write(f'host i-* mi-*\n')
            f.write(f'\tProxyCommand {proxy_command}')
    except IOError:
        logger.error(f"File {conf} not accessible")
        quit(1)

    command = f'ssh -F {conf} {ssh_args}'
    logger.debug("Running: %s", command)
    subproc = Popen([command], executable=executable, shell=True)
    response = subproc.communicate()[1]

    return response


#
# Workaround: If the final argument is a command, it needs to have quotes around it to handles
# multiple execution statements.  The argparse Library strips off the quotes so we need to add
# them back. Also, if the final argument is the destination, ssh still will not complain.
def format_command_arg(arg_list):
    arg_length = len(args[1])

    if arg_length < 1:
        return arg_list
    else:
        last_arg = arg_list[arg_length - 1]
        arg_list[arg_length - 1] = f'"{last_arg}"'
        return arg_list


def ssh_option(opt):
    return re.match("^-[^BbcDEeFIiJLlmOopQRSWw]$", opt)


def ssh_non_boolean_option(opt):
    return re.match("^-[BbcDEeFIiJLlmOopQRSWw]$", opt)


def format_destination(content):
    return content.split('@')


def get_destination(args):
    arg_length = len(args)
    destination = None
    remote = None

    if arg_length == 1:
        destination = args[0]
    elif arg_length == 2 and ssh_non_boolean_option(args[0]):
        destination = None
    elif arg_length == 2 and ssh_option(args[0]):
        destination = args[1]
    elif arg_length == 2:
        destination = args[0]
        remote = args[1]
    elif arg_length > 2 and (ssh_non_boolean_option(args[arg_length-3]) or ssh_option(args[arg_length-2])):
        destination = args[arg_length-1]
    elif arg_length > 2 and ssh_non_boolean_option(args[arg_length-2]):
        destination = None
    elif arg_length > 0:
        destination = args[arg_length-2]
        remote = args[arg_length-1]

    logger.debug(
        f"destination: {destination}  --  remote command: \"{remote}\"")
    return destination


def main():
    global args
    args = get_sys_args()
    logger.debug(f"arg list: {args}, length: {len(args[1])}")
    destination = get_destination(args[1])

    try:
        # turn the args tuple into a list so that we can modify elements
        args_list = list(args)
        # Update the 'list' element so that the command args (if provided) is properly quoated
        args_list[1] = format_command_arg(args_list[1])
        # reassign the changed arg list back to the original args tuple
        args = tuple(args_list)

        vars(args[0])["params"] = " ".join(args[1])

        instance = None
        if destination:
            destination = format_destination(destination)
            target = destination[0] if len(destination) < 2 else destination[1]
            instance = get_instance(target, args[0].profile, args[0].region)

            if instance:
                vars(args[0])["params"] = args[0].params.replace(
                    target, instance)
            else:
                quit(1)

        res = start_session(args[0])

        if res:
            print(res.decode("utf-8"))

        quit(0)

    except (botocore.exceptions.BotoCoreError,
            botocore.exceptions.ClientError) as e:
        logger.error(e)
        quit(1)


if __name__ == "__main__":
    main()
