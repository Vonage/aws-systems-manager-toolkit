#!/usr/bin/env python3

import argparse
import boto3
import logging
import os
import sys
from botocore.exceptions import ClientError
from .common import *

streamHandler = logging.StreamHandler()
formatter = logging.Formatter(
    "[%(name)s] %(levelname)s: %(message)s"
)
streamHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(streamHandler)
logger.setLevel(logging.WARNING)


def configure_session_client(profile, region):
    global session
    session = boto3.Session(profile_name=profile, region_name=region)


def parse_args(argv):
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, add_help=False)
    add_general_parameters(parser)
    parser.add_argument('instance',
                        help='Instance ID, Name, Host name or IP address')
    parser.description = 'Start SSM Shell Session to a given instance'
    args = parser.parse_args(argv)
    return args


def start_session(instance_id, profile=None, region=None):
    extra_args = ""
    if profile:
        extra_args += f"--profile {profile} "
    if region:
        extra_args += f"--region {region} "
    user = get_user()
    command = f'aws {extra_args} ssm start-session --target {instance_id} --document-name AWS-StartInteractiveCommand --parameters command="sudo su - {user}"'
    logger.info("Running: %s", command)
    if create_user(instance_id, user):
        os.system(command)
        quit(0)
    else:
        raise Exception(
            f"Failed to create user on instance {instance_id}")


def create_user(instance_id, user):
    ssm = session.client("ssm")
    try:
        response = ssm.send_command(InstanceIds=[
                                    instance_id], DocumentName="CreateRunAsUser", Parameters={"user": [user]})
        command_id = response["Command"]["CommandId"]
        if wait_for_command(ssm, command_id, instance_id):
            return True
    except ClientError:
        print("Document does not exist in account. Continuing")
        return True


def get_user():
    sts = session.client('sts')
    identity = sts.get_caller_identity()
    arn = identity['Arn']
    return str.split(arn, "/")[-1]


def main():
    args = parse_args(sys.argv[1:])
    try:
        configure_session_client(args.profile, args.region)
        instance_id = get_instance(args.instance, args.profile, args.region)
        if not instance_id:
            logger.warning(
                f"Could not resolve Instance ID for {args.instance}")
            logger.warning(f"Ensure {args.instance} is registered in SSM")
            quit(1)
        start_session(instance_id, profile=args.profile, region=args.region)
    except Exception as e:
        logger.error(e)
        quit(1)


if __name__ == "__main__":
    main()
