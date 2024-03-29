import cdk_nag
import os

from aws_cdk import (
    Aspects,
    CustomResource,
    Duration,
    RemovalPolicy,
    Stack,
    aws_ec2 as _ec2,
    aws_efs as _efs,
    aws_iam as _iam,
    aws_lambda as _lambda,
    aws_logs as _logs,
    aws_s3 as _s3,
    aws_s3_deployment as _deployment,
    aws_ssm as _ssm,
    custom_resources as _custom
)

from constructs import Construct

class BlueStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        Aspects.of(self).add(
            cdk_nag.AwsSolutionsChecks(
                log_ignores = True,
                verbose = True
            )
        )

        cdk_nag.NagSuppressions.add_stack_suppressions(
            self, suppressions = [
                {'id': 'AwsSolutions-L1','reason': 'GitHub Issue'},
                {'id': 'AwsSolutions-S1','reason': 'GitHub Issue'},
                {'id': 'AwsSolutions-IAM4','reason': 'GitHub Issue'},
                {'id': 'AwsSolutions-IAM5','reason': 'GitHub Issue'},
                {'id': 'AwsSolutions-EC23','reason': 'GitHub Issue'},
                {'id': 'AwsSolutions-EC28','reason': 'GitHub Issue'},
                {'id': 'AwsSolutions-EC29','reason': 'GitHub Issue'}
            ]
        )

        account = Stack.of(self).account
        region = Stack.of(self).region

################################################################################

        ebs_root = 8                            # <-- Enter Root Storage GBs

        ebs_data = 4                            # <-- Enter Data Storage GBs

        ec2_type = 't3a.nano'                   # <-- Enter EC2 Size

        vpc_id = 'vpc-0aa03892e4dcb8332'        # <-- Enter VPC ID

        availability_zones = [                  # <-- Enter Availability Zones
            'us-east-2a'
        ]

        subnet_ids = [                          # <-- Enter Subnet IDs
            'subnet-0e4585252960eaa13'
        ]

        route_table_ids = [                     # <-- Enter Route Table IDs
            'rtb-0f893a206d5d46654'
        ]

################################################################################
        
        archive_name = 'blue-'+str(account)+'-archive-'+region
        
        archive = _s3.Bucket(
            self, 'archive',
            bucket_name = archive_name,
            encryption = _s3.BucketEncryption.KMS_MANAGED,
            block_public_access = _s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy = RemovalPolicy.DESTROY,
            auto_delete_objects = True,
            enforce_ssl = True,
            versioned = True
        )

        distributor_name = 'blue-'+str(account)+'-distributor-'+region
        
        distributor = _s3.Bucket(
            self, 'distributor',
            bucket_name = distributor_name,
            encryption = _s3.BucketEncryption.KMS_MANAGED,
            block_public_access = _s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy = RemovalPolicy.DESTROY,
            auto_delete_objects = True,
            enforce_ssl = True,
            versioned = True
        )

        script_name = 'blue-'+str(account)+'-scripts-'+region

        os.system('echo "#!/usr/bin/bash" > script/blue.sh')
        os.system('echo "apt-get update" >> script/blue.sh')
        os.system('echo "apt-get upgrade -y" >> script/blue.sh')
        os.system('echo "apt-get install nfs-common python3-pip unzip -y" >> script/blue.sh')
        os.system('echo "wget https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -P /tmp/" >> script/blue.sh')
        os.system('echo "unzip /tmp/awscli-exe-linux-x86_64.zip -d /tmp" >> script/blue.sh')
        os.system('echo "/tmp/aws/install" >> script/blue.sh')
        os.system('echo "aws s3 cp s3://'+script_name+'/patch-reboot.sh /root/patch-reboot.sh" >> script/blue.sh')
        os.system('echo "chmod 750 /root/patch-reboot.sh" >> script/blue.sh')
        os.system('echo "aws s3 cp s3://'+script_name+'/crontab.txt /tmp/crontab.txt" >> script/blue.sh')
        os.system('echo "cat /tmp/crontab.txt >> /etc/crontab" >> script/blue.sh')
        os.system('echo "pip3 install boto3 requests" >> script/blue.sh')
        os.system('echo "aws s3 cp s3://'+script_name+'/blue.py /tmp/blue.py" >> script/blue.sh')
        os.system('echo "/usr/bin/python3 /tmp/blue.py" >> script/blue.sh')

        script = _s3.Bucket(
            self, 'script',
            bucket_name = script_name,
            encryption = _s3.BucketEncryption.KMS_MANAGED,
            block_public_access = _s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy = RemovalPolicy.DESTROY,
            auto_delete_objects = True,
            enforce_ssl = True,
            versioned = True
        )

        scripts = _deployment.BucketDeployment(
            self, 'scripts',
            sources = [_deployment.Source.asset('script')],
            destination_bucket = script,
            prune = False
        )

        vpc = _ec2.Vpc.from_vpc_attributes(
            self, 'vpc',
            vpc_id = vpc_id,
            availability_zones = availability_zones,
            #private_subnet_ids = subnet_ids,
            #private_subnet_route_table_ids = route_table_ids,
            public_subnet_ids = subnet_ids,
            public_subnet_route_table_ids = route_table_ids
        )

        efs = _efs.FileSystem(
            self, 'efs', 
            vpc = vpc,
            removal_policy = RemovalPolicy.DESTROY
        )

        storage = efs.add_access_point(
            'storage',
            path = '/export/datastore',
            create_acl = _efs.Acl(
                owner_uid = '1001',
                owner_gid = '1001',
                permissions = '750'
            ),
            posix_user = _efs.PosixUser(
                uid = '1001',
                gid = '1001'
            )
        )

        efsssm = _ssm.StringParameter(
            self, 'efsssm',
            description = 'Blue EFS File System',
            parameter_name = '/blue/efs/fsid',
            string_value = efs.file_system_id,
            tier = _ssm.ParameterTier.STANDARD
        )

        ### Ubuntu Server 20.04 LTS ###
        ubuntu = _ec2.MachineImage.generic_linux(
            {
                'us-east-1': 'ami-08d4ac5b634553e16',
                'us-east-2': 'ami-0960ab670c8bb45f3',
                'us-west-2': 'ami-0ddf424f81ddb0720'
            }
        )

        role = _iam.Role(
            self, 'role',
            assumed_by = _iam.ServicePrincipal(
                'ec2.amazonaws.com'
            )
        )

        role.add_managed_policy(
            _iam.ManagedPolicy.from_aws_managed_policy_name(
                'AmazonSSMManagedInstanceCore'
            )
        )

        role.add_to_policy(
            _iam.PolicyStatement(
                actions = [
                    'ssm:GetParameter'
                ],
                resources = [
                    '*'
                ]
            )
        )

        role.add_to_policy(
            _iam.PolicyStatement(
                actions = [
                    's3:GetObject',
                    's3:PutObject'
                ],
                resources = [
                    archive.bucket_arn,
                    archive.arn_for_objects('*'),
                    distributor.bucket_arn,
                    distributor.arn_for_objects('*'),
                    script.bucket_arn,
                    script.arn_for_objects('*')
                ]
            )
        )

        securitygroup = _ec2.SecurityGroup(
            self, 'securitygroup',
            vpc = vpc,
            allow_all_outbound = True
        )
        securitygroup.add_ingress_rule(_ec2.Peer.any_ipv4(), _ec2.Port.tcp(80), 'HTTP')
        securitygroup.add_ingress_rule(_ec2.Peer.any_ipv4(), _ec2.Port.tcp(443), 'HTTPS')

        instance = _ec2.Instance(
            self, 'instance',
            instance_type = _ec2.InstanceType(ec2_type),
            machine_image = ubuntu,
            vpc = vpc,
            role = role,
            security_group = securitygroup,
            require_imdsv2 = True,
            propagate_tags_to_volume_on_creation = True,
            block_devices = [
                _ec2.BlockDevice(
                    device_name = '/dev/sda1',
                    volume = _ec2.BlockDeviceVolume.ebs(
                        ebs_root,
                        encrypted = True
                    )
                ),
                _ec2.BlockDevice(
                    device_name = '/dev/sdf',
                    volume = _ec2.BlockDeviceVolume.ebs(
                        ebs_data,
                        encrypted = True
                    )
                )
            ]
        )

        efs.connections.allow_default_port_from(instance)

        eip = _ec2.CfnEIP(
            self, 'eip',
            instance_id = instance.instance_id
        )

        config = _iam.Role(
            self, 'config', 
            assumed_by = _iam.ServicePrincipal(
                'lambda.amazonaws.com'
            )
        )
        
        config.add_managed_policy(
            _iam.ManagedPolicy.from_aws_managed_policy_name(
                'service-role/AWSLambdaBasicExecutionRole'
            )
        )
        
        config.add_to_policy(
            _iam.PolicyStatement(
                actions = [
                    'ssm:SendCommand'
                ],
                resources = [
                    '*'
                ]
            )
        )

        compute = _lambda.Function(
            self, 'compute',
            code = _lambda.Code.from_asset('config'),
            handler = 'config.handler',
            runtime = _lambda.Runtime.PYTHON_3_9,
            timeout = Duration.seconds(30),
            environment = dict(
                INSTANCE = instance.instance_id,
                SCRIPTS3 = script_name
            ),
            memory_size = 512,
            role = config
        )
       
        logs = _logs.LogGroup(
            self, 'logs',
            log_group_name = '/aws/lambda/'+compute.function_name,
            retention = _logs.RetentionDays.ONE_DAY,
            removal_policy = RemovalPolicy.DESTROY
        )

        provider = _custom.Provider(
            self, 'provider',
            on_event_handler = compute
        )

        resource = CustomResource(
            self, 'resource',
            service_token = provider.service_token
        )
