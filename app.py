#!/usr/bin/env python3
import os

import aws_cdk as cdk

from blue.blue_stack import BlueStack

app = cdk.App()

BlueStack(
    app, 'BlueStack',
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = os.environ['CDK_DEFAULT_REGION']
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = '4n6ir'
    )
)

cdk.Tags.of(app).add('Alias','Velociraptor')
cdk.Tags.of(app).add('GitHub','https://github.com/4n6ir/blue.git')

app.synth()
