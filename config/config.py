import boto3
import json
import os

def handler(event, context):

    ssm_client = boto3.client('ssm')

    ssm_client.send_command(
        Targets = [{
            'Key': 'InstanceIds',
            'Values': [os.environ['INSTANCE']]
        }],
        DocumentName = 'AWS-RunRemoteScript',
        DocumentVersion = '1',
        TimeoutSeconds = 600,
        Parameters = {"sourceType":["S3"],"sourceInfo":["{\"path\":\"https://s3.amazonaws.com/"+os.environ['SCRIPTS3']+"/blue.sh\"}"],"commandLine":["blue.sh"],"workingDirectory":[""],"executionTimeout":["3600"]},
        MaxConcurrency = '50',
        MaxErrors = '0'
    )

    return {
        'statusCode': 200,
        'body': json.dumps('Blue Configuration')
    }