#!/usr/bin/env python

import boto3
from pprint import pprint
import os
import argparse
import sys
import csv
import json
from itertools import izip
from csv import reader, writer
import collections

def createCsv(instanceData):
    OinstanceData = collections.OrderedDict(sorted(instanceData.items()))
    with open("out.csv", "wb") as f:
        writer = csv.writer(f)
        writer.writerow(OinstanceData.keys())
        writer.writerows(zip(*OinstanceData.values()))
    a = izip(*csv.reader(open("out.csv", "rb")))
    csv.writer(open("specs.csv", "wb")).writerows(a)

def get_disk_size_by_id(InstanceVolumeId):
    ec2client = boto3.client('ec2')
    response = ec2client.describe_volumes(
        VolumeIds=[
            InstanceVolumeId
        ]
    )
    response=response["Volumes"]
    response=response[0]
    disk_size=response["Size"]
    return disk_size

# require newer boto version
# def get_flavor_info(ec2Flavor):
#     ec2client = boto3.resource('ec2')
#     response = ec2client.describe_instance_types(
#         InstanceTypes=[
#             ec2Flavor
#         ]
#     )
#     response=response["InstanceTypes"]
#     response=response[0]
#     mem_size=response["MemoryInfo"]["SizeInMiB"]
#     return mem_size

def get_flavor_info(ec2Flavor):
    cmd="aws ec2 describe-instance-types --instance-types {} | jq '.InstanceTypes[].MemoryInfo.SizeInMiB' | tr -d '\n\t'".format(ec2Flavor)
    stream = os.popen(cmd)
    mem_size = stream.read()
    return mem_size

def list_instances_by_tag_value(tagkey, tagvalue):
    ec2client = boto3.client('ec2')
    response = ec2client.describe_instances(
        Filters=[
            {
                'Name': 'tag:'+tagkey,
                'Values': [tagvalue]
            }
        ]
    )
    # TODO: move that list away, decouple
    instanceList = []
    imageIdList = []
    instanceDevicesList = []
    instanceIpList = []
    instanceTypeList = []
    instanceVolumesList = []
    instanceNameList = []
    instanceCpuList = []
    instanceRamList = []
    instanceDevicesIdList = []
    instanceDevicesSizeList = []

    # TODO introduce a recurring logic with an iterator etc.
    for reservation in (response["Reservations"]):
        for instance in reservation["Instances"]:
            instanceList.append(instance["InstanceId"])
            imageIdList.append(instance["ImageId"])
            instanceCpuList.append(instance["CpuOptions"]["CoreCount"])
            instanceRamList.append(get_flavor_info(instance["InstanceType"]))
            instanceTypeList.append(instance["InstanceType"])
            for instanceIface in instance["NetworkInterfaces"]:
                instanceIpList.append(instance["PrivateIpAddress"])
            for instanceVolumes in instance["BlockDeviceMappings"]:
                instanceDevicesList.append(instanceVolumes["DeviceName"])
                instanceDevicesIdList.append(instanceVolumes["Ebs"]["VolumeId"])
                for it in instanceDevicesIdList:
                    instanceDevicesSizeList.append(get_disk_size_by_id(it))   
            instanceVolumesList.append(zip(instanceDevicesList,instanceDevicesIdList,instanceDevicesSizeList))
            instanceDevicesSizeList = []
            instanceDevicesList= []
            instanceDevicesIdList = []
            for tag in instance["Tags"]:
                if tag['Key'] == "Name":
                    instanceNameList.append(tag['Value'])
    merge_lists=zip(instanceList,instanceTypeList, instanceIpList, instanceCpuList, instanceRamList, imageIdList, instanceVolumesList)
    finalList=dict(zip(instanceNameList, merge_lists))
    return finalList

##################################################################
#################       MAIN      ################################
##################################################################

parser = argparse.ArgumentParser(description='Argument parsing')
parser.add_argument('--env_name', metavar = 'env_name', type = str,help = 'Specify the environment name tag')
args = parser.parse_args()
if len(sys.argv) < 2:
    parser.print_usage()
    sys.exit(1)

instances = list_instances_by_tag_value('env_name',args.env_name)
createCsv(instances)
