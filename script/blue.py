#!/usr/bin/python3
import boto3
import json
import os
import requests
from subprocess import run

os.system('mkfs -t ext4 /dev/nvme1n1')
os.system('mkdir /data /datastore')

ebs = run( [ 'blkid' ], capture_output=True )
drives = ebs.stdout.decode().split('\n')
for drive in drives:
    mount = drive.split(':')
    if mount[0] == '/dev/nvme1n1':
        parse = mount[1].split('"')
        os.system('echo "UUID='+parse[1]+' /data '+parse[3]+' defaults,nofail 0 2" >> /etc/fstab')

headers = {'X-aws-ec2-metadata-token-ttl-seconds': '30'}
token = requests.put('http://169.254.169.254/latest/api/token', headers=headers)

headers = {'X-aws-ec2-metadata-token': token.text}
r = requests.get('http://169.254.169.254/latest/dynamic/instance-identity/document', headers=headers)

j = json.loads(r.text)
region = j['region']

r = requests.get('http://169.254.169.254/latest/meta-data/placement/availability-zone', headers=headers)
zone = r.text

ssm_client = boto3.client('ssm', region_name = region)

response = ssm_client.get_parameter(
    Name = '/blue/efs/fsid'
)
fsid = response['Parameter']['Value']

os.system('echo "'+zone+'.'+fsid+'.efs.'+region+'.amazonaws.com:/ /datastore nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2 0 0" >> /etc/fstab')

os.system('mount -a')
