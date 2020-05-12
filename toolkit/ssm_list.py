#!/usr/bin/env python3

# The script can list available instances in i SSM inventory, resolve instance names,
# host names, and IP addresses.
#
# Author: Chris Heath
#
# Changelog:
# 2020-03-20 - SRE-1605 - Added command-line argument to filter results by instance tag

import os
import sys
import logging
import argparse
import botocore.exceptions
import boto3
import re
from botocore.exceptions import ClientError

streamHandler = logging.StreamHandler()
formatter = logging.Formatter(
    "[%(name)s] %(levelname)s: %(message)s"
)
streamHandler.setFormatter(formatter)
logger = logging.getLogger("ssm-list")
logger.addHandler(streamHandler)
logger.setLevel(logging.WARNING)
args = None

def get_ssm_inventory():
    instances = {}
    
    # Create boto3 client from session
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    ssm_client = session.client('ssm')

    # List instances from SSM
    paginator = ssm_client.get_paginator('describe_instance_information')
    response_iterator = paginator.paginate(
        InstanceInformationFilterList=[
            {
                'key': 'PingStatus',
                'valueSet': [
                    'Online',
                ]
            }
        ]
    )
    for instance_info in response_iterator:
        for instance in instance_info['InstanceInformationList']:
            try:
                # At the moment we only support EC2 Instances
                assert instance["ResourceType"] == "EC2Instance"

                # Add to the list
                instance_id = instance['InstanceId']
                instances.update({instance_id : {
                    "InstanceId": instance_id,
                    "HostName": instance.get("ComputerName", ""),
                    "InstanceName": "",
                    "Addresses": []
                    }
                })
            except (AssertionError, KeyError, ValueError):
                logger.debug("SSM inventory entity not recognised: %s", instance)
                continue

    instances = get_instance_details(instances)
    return instances

    
def get_instance_details(instances):
    # Create boto3 client from session
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    ec2_client = session.client('ec2')

    # Add attributes from EC2
    filters = get_filters()
    try:
        paginator = ec2_client.get_paginator('describe_instances')
        response_iterator = paginator.paginate(InstanceIds=list(instances.keys()), Filters=[filters])
   
        for reservations in response_iterator:
            for reservation in reservations.get('Reservations', []):
                for instance in reservation.get('Instances',[]):
                    instance_id = instance['InstanceId']
                    if not instance_id in instances:
                        continue

                    # Find instance IPs
                    instances[instance_id]['Addresses'].append(instance.get('PrivateIpAddress', ''))
                    instances[instance_id]['Addresses'].append(instance.get('PublicIpAddress', ''))

                    # Find instance name from tag Name
                    for tag in instance.get('Tags',[]):
                        if tag['Key'] == 'Name':
                            instances[instance_id]['InstanceName'] = tag['Value']

                    logger.debug("Updated instance: %s: %r", instance_id, instances[instance_id])
    except ClientError as c:
        # Handle edge case where Instance ID did not have the correct status and does not exist
        if c.response["Error"]["Code"] == "InvalidInstanceID.NotFound":
            id = re.search(r"The instance ID '(.*?)' does not exist", c.response["Error"]["Message"]).group(1)
            del instances[id]
            return get_instance_details(instances)
        else:
            raise Exception(c)
    # Filter instances that do not have a description
    for instance_id in list(instances):
        if not instances[instance_id]['Addresses']:
            del instances[instance_id]
    return instances

# Method uses ArgumentParser to retrieve command-line arguments and display help interface
def get_sys_args():
    parser = argparse.ArgumentParser()
    #parser.add_argument("-e", metavar="<ENVIRONMENT>", help="Specify AWS Environment: 'qa', 'amz1', or 'dev'")
    parser.add_argument("--region", metavar="REGION", help="Set / override AWS region")
    parser.add_argument("--profile", metavar="PROFILE", help="Configuration profile from ~/.aws/{credentials,config}")
    parser.add_argument("--filters", metavar="FILTERS", nargs='+', help="Filter results using awscli syntax (--filters Name=key,Values=value1,value2 Name=tag:Name,Values=fqdn.domain.com )")
    
    return parser.parse_args()


def print_list():
    cache_file = os.path.join(os.path.expanduser('~'),'.ssm_inventory_cache')
    inventory  = get_ssm_inventory().values()
    hostname_len = 1
    instname_len = 1

    if not inventory:
        logger.warning("No instances registered in SSM!")
        return

    items = list(inventory)
    items.sort(key=lambda x: x.get('InstanceName') or x.get('HostName'))

    # try caching the list for later use
    try:
        with open(cache_file, "w") as f:
            for item in items:
                f.write(f'{item}\n')
    except IOError:
        logger.error(f"File {cache_file} not accessible")
        
        
    for item in items:
        hostname_len = max(hostname_len, len(item['HostName']))
        instname_len = max(instname_len, len(item['InstanceName']))

    for item in items:
        print(f"{item['InstanceId']}   {item['HostName']:{hostname_len}}   {item['InstanceName']:{instname_len}}   {' '.join(item['Addresses'])}")


def get_filters():
    # Convert tag arguments to list of dicts
    if args.filters:
        for arg in args.filters:
            filters = arg.replace('=',',').split(',',3)
            filters = {filters[i]: filters[i + 1] for i in range(0, len(filters), 2)}
            filters.update({ 'Values': list(filters['Values'].split(','))})
    else:
        filters = {}
    return filters



def main():
    global args
    
    args = get_sys_args()
    try:
        print_list()
        quit(0)

    except (botocore.exceptions.BotoCoreError,
            botocore.exceptions.ClientError) as e:
        logger.error(e)
        quit(1)

if __name__ == "__main__":
    main()
