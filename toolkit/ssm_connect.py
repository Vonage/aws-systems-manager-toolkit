#!/usr/bin/env python3

import argparse
import logging
import os
import sys
from .common import *

streamHandler = logging.StreamHandler()
formatter = logging.Formatter(
    "[%(name)s] %(levelname)s: %(message)s"
)
streamHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(streamHandler)
logger.setLevel(logging.WARNING)


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
    command = f'aws {extra_args} ssm start-session --target {instance_id}'
    logger.info("Running: %s", command)
    user = get_user()
    if create_user(instance_id, user):
        os.system(command)
        quit(0)
    else:
        raise Exception(
            f"Failed to create user on instance {instance_id}")


def main():
    args = parse_args(sys.argv[1:])
    try:
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
