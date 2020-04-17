# Commons functions used by SSM tools
#
#
# Email: SRE@vonage.com

import boto3
import logging
import re
import time
from botocore.exceptions import ClientError

__all__ = []


logger = logging.getLogger()
logger.setLevel(logging.WARNING)


def format_filters(target):
    if re.match('^(10|127|169\.254|172\.1[6-9]|172\.2[0-9]|172\.3[0-1]|192\.168)\.', target):
        return [{'Name': 'private-ip-address', 'Values': [target]}]
    elif re.match('[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', target):
        return [{'Name': 'ip-address', 'Values': [target]}]
    elif re.match('ip-[0-9]{1,3}-[0-9]{1,3}-[0-9]{1,3}-[0-9]{1,3}.ec2.internal', target):
        return [{'Name': 'private-dns-name', 'Values': [target]}]
    else:
        return [{'Name': 'tag:Name', 'Values': [target]}]


__all__.append("get_instance")


def get_instance(target, profile=None, region=None):
    # Is it a valid Instance ID?
    if re.match('^i-[a-f0-9]+$', target):
        return target
    else:
        # Create boto3 client from session
        session = boto3.Session(profile_name=profile, region_name=region)
        ec2_client = session.client('ec2')

        instance_ids = []
        filters = format_filters(target)
        logger.debug(f"EC2 describe-instance filters: {filters}")
        paginator = ec2_client.get_paginator('describe_instances')
        response_iterator = paginator.paginate(Filters=filters)
        for reservations in response_iterator:
            for reservation in reservations['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    if instance_id not in instance_ids:
                        instance_ids.append(instance_id)

        if not instance_ids:
            logger.warning(f"No instance-id found for destination {target}")
            return None

        if len(instance_ids) > 1:
            logger.warning("Found %d instances for '%s': %s", len(
                instance_ids), target, " ".join(instance_ids))
            logger.warning("Use INSTANCE_ID to connect to a specific one")
            quit(1)

        # Found only one instance - return it
        return instance_ids[0]


__all__.append("add_general_parameters")


def add_general_parameters(parser):
    general = parser.add_argument_group('General Parameters')
    general.add_argument('--help', '-h', action="help",
                         help='Print this help and exit')
    general.add_argument('--profile', '-p', dest='profile', type=str,
                         help='Configuration profile from ~/.aws/{credentials,config}')
    general.add_argument('--region', '-g', dest='region',
                         type=str, help='Set / override AWS region.')

    return general


__all__.append("wait_for_command")


# Parameters:
# ssm - SSM Boto3 Client
# command_id - CommandId to wait for either success or failure
# instance_id - InstanceId command is being run on
#
# Returns:
# True or False for pass and fail, respsectively
def wait_for_command(ssm, command_id, instance_id):
    status = get_status(ssm, command_id, instance_id)
    while len(status['CommandInvocations']) == 0 or status['CommandInvocations'][0]['Status'] not in ["Success", "Failed"]:
        time.sleep(1)
        status = get_status(ssm, command_id, instance_id)
        if status['CommandInvocations'][0]['Status'] == "Failed":
            return False
        elif status['CommandInvocations'][0]['Status'] == "Success":
            return True


def get_status(ssm, command_id, instance_id):
    return ssm.list_command_invocations(
        CommandId=command_id, InstanceId=instance_id, Details=True)


__all__.append("create_user")


def create_user(instance_id, user):
    ssm = boto3.client("ssm")
    try:
        response = ssm.send_command(InstanceIds=[
                                    instance_id], DocumentName="CreateRunAsUser", Parameters={"user": [user]})
        command_id = response["Command"]["CommandId"]
        if wait_for_command(ssm, command_id, instance_id):
            return True
    except ClientError:
        print("Document does not exist in account. Continuing")
        return True


__all__.append("get_user")


def get_user():
    sts = boto3.client('sts')
    identity = sts.get_caller_identity()
    arn = identity['Arn']
    return str.split(arn, "/")[-1]
