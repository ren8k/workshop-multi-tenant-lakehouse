# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# review this link https://programmaticponderings.com/2021/09/09/getting-started-with-spark-structured-streaming-and-kafka-on-aws-using-amazon-msk-and-amazon-emr%EF%BF%BC/
from constructs import Construct
from aws_cdk import (
    Stack,
    CfnOutput,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3 as s3,
    aws_msk as msk,
    aws_ssm as ssm,
    aws_secretsmanager as secretsmanager,
    aws_kms as kms,
    aws_logs as logs,
    Tags as tags,
    aws_s3_deployment as s3deployment,
    Aws as AWS
)
import os
from . import parametersIam
import configparser

class mskClusterIam(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)    

################ VPC Configuration #####################

        #availabilityZonesList = [parametersIam.az1, parametersIam.az2]
        vpc = ec2.Vpc (self, "vpc",
            vpc_name = f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-vpc",
            ip_addresses = ec2.IpAddresses.cidr(parametersIam.cidrRange),
            enable_dns_hostnames = parametersIam.enableDnsHostnames,
            enable_dns_support = parametersIam.enableDnsSupport,
            max_azs=2,
            #availability_zones = availabilityZonesList,
            nat_gateways = parametersIam.numberOfNatGateways,
            subnet_configuration = [
                {
                    "name": f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-publicSubnet1",
                    "subnetType": ec2.SubnetType.PUBLIC,
                    "cidrMask": parametersIam.cidrMaskForSubnets,
                },
                {
                    "name": f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-privateSubnet1",
                    "subnetType": ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    "cidrMask": parametersIam.cidrMaskForSubnets,
                }
            ]
        )
        tags.of(vpc).add("name", f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-vpc")
        tags.of(vpc).add("project", parametersIam.project)
        tags.of(vpc).add("env", parametersIam.env)
        tags.of(vpc).add("app", parametersIam.app)

#############       EC2 Key Pair Configurations      #############

        keyPair = ec2.KeyPair.from_key_pair_name(self, "jp-aws-east1", parametersIam.producerEc2KeyPairName)

#################### Security Group Configuration #####################
        sgEc2MskCluster = ec2.SecurityGroup(self, "sgEc2MskCluster",
            security_group_name = f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-sgEc2MskCluster",
            vpc=vpc,
            description="Security group associated with the EC2 instance of MSK Cluster",
            allow_all_outbound=True,
            disable_inline_rules=True
        )
        tags.of(sgEc2MskCluster).add("name", f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-sgEc2MskCluster")
        tags.of(sgEc2MskCluster).add("project", parametersIam.project)
        tags.of(sgEc2MskCluster).add("env", parametersIam.env)
        tags.of(sgEc2MskCluster).add("app", parametersIam.app)

        sgMskCluster = ec2.SecurityGroup(self, "sgMskCluster",
            security_group_name = f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-sgMskCluster",
            vpc=vpc,
            description="Security group associated with the MSK Cluster",
            allow_all_outbound=True,
            disable_inline_rules=True
        )
        tags.of(sgMskCluster).add("name", f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-sgMskCluster")
        tags.of(sgMskCluster).add("project", parametersIam.project)
        tags.of(sgMskCluster).add("env", parametersIam.env)
        tags.of(sgMskCluster).add("app", parametersIam.app)

        sgEc2MskCluster.add_ingress_rule(
            peer = ec2.Peer.any_ipv4(), 
            connection = ec2.Port.tcp(22), 
            description = "Allow SSH access from the internet"
        )

        sgEc2MskCluster.add_ingress_rule(
            peer = ec2.Peer.security_group_id(sgMskCluster.security_group_id),
            connection = ec2.Port.tcp_range(parametersIam.sgKafkaInboundPort, parametersIam.sgKafkaOutboundPort),
            description = "Allow Custom TCP traffic from sgEc2MskCluster to sgMskCluster"
        )

        sgMskCluster.add_ingress_rule(
            peer = ec2.Peer.security_group_id(sgEc2MskCluster.security_group_id),
            connection = ec2.Port.tcp_range(parametersIam.sgMskClusterInboundPort, parametersIam.sgMskClusterOutboundPort),
            description = "Allow all TCP traffic from sgEc2MskCluster to sgMskCluster"
        )

        sgMskCluster.add_ingress_rule(
            peer = ec2.Peer.security_group_id(sgMskCluster.security_group_id),
            connection = ec2.Port.tcp_range(parametersIam.sgMskClusterInboundPort, parametersIam.sgMskClusterOutboundPort),
            description = "Allow all TCP traffic from sgMskCluster to sgMskCluster"
        )        
        
#################### KMS Configuration #####################
        customerManagedKey = kms.Key(self, "customerManagedKey",
            alias = f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-sasl/scram-key",
            description = "Customer managed key",
            enable_key_rotation = True,
            removal_policy = RemovalPolicy.DESTROY
        )
        tags.of(customerManagedKey).add("name", f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-customerManagedKey")
        tags.of(customerManagedKey).add("project", parametersIam.project)
        tags.of(customerManagedKey).add("env", parametersIam.env)
        tags.of(customerManagedKey).add("app", parametersIam.app)

#################### MSK Logs Configuration #####################        
        mskClusterLogGroup = logs.LogGroup(self, "mskClusterLogGroup",
            log_group_name = f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-mskClusterLogGroup",
            retention = logs.RetentionDays.ONE_WEEK,
            removal_policy = RemovalPolicy.DESTROY
        )
        tags.of(mskClusterLogGroup).add("name", f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-mskClusterLogGroup")
        tags.of(mskClusterLogGroup).add("project", parametersIam.project)
        tags.of(mskClusterLogGroup).add("env", parametersIam.env)
        tags.of(mskClusterLogGroup).add("app", parametersIam.app)

#################### MSK Cluster Configuration #####################        
        mskClusterConfigProperties = [
            "auto.create.topics.enable=false",
            "default.replication.factor=3",
            "min.insync.replicas=2",
            "num.io.threads=8",
            "num.network.threads=5",
            "num.partitions=1",
            "num.replica.fetchers=2",
            "replica.lag.time.max.ms=30000",
            "socket.receive.buffer.bytes=102400",
            "socket.request.max.bytes=104857600",
            "socket.send.buffer.bytes=102400",
            "unclean.leader.election.enable=false",
            "zookeeper.session.timeout.ms=18000",
            "allow.everyone.if.no.acl.found=true"
        ]
        mskClusterConfigProperties = "\n".join(mskClusterConfigProperties)
        mskClusterConfiguration = msk.CfnConfiguration(self, "mskClusterConfiguration",
            name = f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-mskClusterConfiguration",
            server_properties = mskClusterConfigProperties,
            description = "MSK cluster configuration"
        )

        mskCluster = msk.CfnCluster(self, "mskCluster",
            cluster_name = f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-mskCluster",
            kafka_version = parametersIam.mskVersion,
            number_of_broker_nodes = parametersIam.mskNumberOfBrokerNodes,
            broker_node_group_info = msk.CfnCluster.BrokerNodeGroupInfoProperty(
                instance_type = parametersIam.mskClusterInstanceType,
                client_subnets = vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS).subnet_ids[:2],
                security_groups = [sgMskCluster.security_group_id],
                connectivity_info=None,
                storage_info = msk.CfnCluster.StorageInfoProperty(  
                    ebs_storage_info = msk.CfnCluster.EBSStorageInfoProperty(
                        volume_size = parametersIam.mskClusterVolumeSize
                    )
                )
            ),
            logging_info = msk.CfnCluster.LoggingInfoProperty(
                broker_logs = msk.CfnCluster.BrokerLogsProperty(
                    cloud_watch_logs = msk.CfnCluster.CloudWatchLogsProperty(
                        enabled = True,
                        log_group = mskClusterLogGroup.log_group_name
                    ),
                )
            ),
            client_authentication = msk.CfnCluster.ClientAuthenticationProperty(
                sasl = msk.CfnCluster.SaslProperty(
                    iam = msk.CfnCluster.IamProperty(
                        enabled = parametersIam.mskIamPropertyEnable
                    )                    
                )
            ),
            configuration_info=msk.CfnCluster.ConfigurationInfoProperty(
                arn=mskClusterConfiguration.attr_arn,
                revision=mskClusterConfiguration.attr_latest_revision_revision
            ),
            encryption_info = msk.CfnCluster.EncryptionInfoProperty(
                encryption_in_transit = msk.CfnCluster.EncryptionInTransitProperty(
                    client_broker = parametersIam.mskEncryptionProducerBroker,
                    in_cluster = parametersIam.mskEncryptionInClusterEnable
                )
            )
        )

        tags.of(mskCluster).add("name", f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-mskCluster")
        tags.of(mskCluster).add("project", parametersIam.project)
        tags.of(mskCluster).add("env", parametersIam.env)
        tags.of(mskCluster).add("app", parametersIam.app)

        mskClusterArnParamStore = ssm.StringParameter(self, "mskClusterArnParamStore",
            parameter_name = f"mtlkh-{parametersIam.env}-mskClusterArn-ssmParamStore",
            string_value = mskCluster.attr_arn,
            tier = ssm.ParameterTier.STANDARD
        )
        tags.of(mskClusterArnParamStore).add("name", f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-mskClusterArnParamStore")
        tags.of(mskClusterArnParamStore).add("project", parametersIam.project)
        tags.of(mskClusterArnParamStore).add("env", parametersIam.env)
        tags.of(mskClusterArnParamStore).add("app", parametersIam.app)
        mskClusterArnParamStoreValue = mskClusterArnParamStore.string_value

        mskClusterBrokerUrlParamStore = ssm.StringParameter(self, "mskClusterBrokerUrlParamStore",
            parameter_name = f"mtlkh-{parametersIam.env}-mskClusterBrokerUrl-ssmParamStore",
            string_value = "dummy",         # We're passing a dummy value in this SSM parameter. The actual value will be replaced by EC2 userdata during the process
            tier = ssm.ParameterTier.STANDARD
        )
        tags.of(mskClusterBrokerUrlParamStore).add("name", f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-mskClusterBrokerUrlParamStore")
        tags.of(mskClusterBrokerUrlParamStore).add("project", parametersIam.project)
        tags.of(mskClusterBrokerUrlParamStore).add("env", parametersIam.env)
        tags.of(mskClusterBrokerUrlParamStore).add("app", parametersIam.app)

        getAzIdsParamStore = ssm.StringParameter(self, "getAzIdsParamStore",
                parameter_name = f"mtlkh-{parametersIam.env}-getAzIdsParamStore-ssmParamStore",
                string_value = "dummy",         # We're passing a dummy value in this SSM parameter. The actual value will be replaced by EC2 userdata during the process
                tier = ssm.ParameterTier.STANDARD,
                type = ssm.ParameterType.STRING_LIST
            )
        tags.of(getAzIdsParamStore).add("name", f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-getAzIdsParamStore")
        tags.of(getAzIdsParamStore).add("project", parametersIam.project)
        tags.of(getAzIdsParamStore).add("env", parametersIam.env)
        tags.of(getAzIdsParamStore).add("app", parametersIam.app)        

#We are unable to activate the SASL/Iam authentication method for producer authentication during the cluster creation process
        enableSaslIAMClientAuth = parametersIam.enableSaslIAMClientAuth
        if enableSaslIAMClientAuth:
            mskCluster.add_property_override(
                'BrokerNodeGroupInfo.ConnectivityInfo',
                {
                    'VpcConnectivity': {
                        'ClientAuthentication': {
                            'Sasl': {
                                'Iam': {'Enabled': True}
                            },
                            'Tls': {'Enabled': False}
                        }
                    }
                }
            )
        else:
            print("SASL Iam is not associated with the MSK Cluster")         

#In the second iteration, we will implement cluster configurations since setting "allow.everyone.if.no.acl.found=true" prevents topic creation in the MSK Cluster
        enableClusterConfig = parametersIam.enableClusterConfig
        if enableClusterConfig:
            mskCluster.add_property_override(
                'ConfigurationInfo',
                {
                    "Arn": mskClusterConfiguration.attr_arn,
                    "Revision": mskClusterConfiguration.attr_latest_revision_revision
                }
            )
        else:
            print("Cluster Configuration is not associated with the MSK Cluster")        

#################### IAM Roles and Policy Configurations #####################        

        ec2MskClusterRole = iam.Role(self, "ec2MskClusterRole",
            role_name = f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-ec2MskClusterRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )
        tags.of(ec2MskClusterRole).add("name", f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-ec2MskClusterRole")
        tags.of(ec2MskClusterRole).add("project", parametersIam.project)
        tags.of(ec2MskClusterRole).add("env", parametersIam.env)
        tags.of(ec2MskClusterRole).add("app", parametersIam.app)
        
        ec2MskClusterRole.attach_inline_policy(
            iam.Policy(self, 'ec2MskClusterPolicy',
                statements = [
                    iam.PolicyStatement(
                        effect = iam.Effect.ALLOW,
                        actions=[
                            "kafka:ListClusters",
                            "kafka:DescribeCluster",
                            "kafka-cluster:Connect",
                            "kafka-cluster:ReadData",
                            "kafka:DescribeClusterV2",
                            "kafka-cluster:*Topic*",
                            "kafka-cluster:AlterCluster",
                            "kafka-cluster:WriteData",
                            "kafka-cluster:AlterGroup",
                            "kafka-cluster:DescribeGroup",
                            "kafka-cluster:DescribeClusterDynamicConfiguration",
                        ],
                        resources= [mskCluster.attr_arn,
                            f"arn:aws:kafka:{AWS.REGION}:{AWS.ACCOUNT_ID}:topic/{mskCluster.cluster_name}/*/*",
                            f"arn:aws:kafka:{AWS.REGION}:{AWS.ACCOUNT_ID}:group/{mskCluster.cluster_name}/*/*"
                        ]
                    ),
                    iam.PolicyStatement(
                        effect = iam.Effect.ALLOW,
                        actions=[
                            "ec2:DescribeInstances",
                            "ec2:DescribeInstanceAttribute",
                            "ec2:ModifyInstanceAttribute",
                            "ec2:DescribeVpcs",
                            "ec2:DescribeSecurityGroups",
                            "ec2:DescribeSubnets",
                            "ec2:DescribeTags"
                        ],
                        resources= [f"arn:aws:ec2:{AWS.REGION}:{AWS.ACCOUNT_ID}:instance/*",
                            f"arn:aws:ec2:{AWS.REGION}:{AWS.ACCOUNT_ID}:volume/*",
                            f"arn:aws:ec2:{AWS.REGION}:{AWS.ACCOUNT_ID}:security-group/*"
                        ]
                    ),
                    iam.PolicyStatement(
                        effect = iam.Effect.ALLOW,
                        actions=[
                            "ec2:DescribeSubnets"
                        ],
                        resources= ["*"]
                    ),
                    iam.PolicyStatement(
                        effect = iam.Effect.ALLOW,
                        actions=[
                            "kafka:GetBootstrapBrokers"
                        ],
                        resources= ["*"]
                    ),
                     iam.PolicyStatement(
                        effect = iam.Effect.ALLOW,
                        actions=[
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                        ],
                        resources= [f"arn:aws:logs:{AWS.REGION}:{AWS.ACCOUNT_ID}:log-group:okok:log-stream:*",
                            f"arn:aws:logs:{AWS.REGION}:{AWS.ACCOUNT_ID}:log-group:*"
                        ]
                    ),
                    iam.PolicyStatement(
                        effect = iam.Effect.ALLOW,
                        actions=[
                            "ssm:PutParameter",
                            "ssm:GetParameters",
                            "ssm:GetParameter"
                        ],
                        resources= [f"arn:aws:ssm:{AWS.REGION}:{AWS.ACCOUNT_ID}:parameter/{mskClusterBrokerUrlParamStore.parameter_name}",
                                    f"arn:aws:ssm:{AWS.REGION}:{AWS.ACCOUNT_ID}:parameter/{getAzIdsParamStore.parameter_name}"
                                    ]
                    )
                ]
            )
        )

#################### MSK Producer and Producer and EC2 Instance Configuration #####################        

        user_data = ec2.UserData.for_linux()
        script_path = os.path.join(os.path.dirname(__file__), 'kafkaProducerEC2InstanceIam.sh')
        with open(script_path, 'r') as file:
            user_data_script = file.read()

        user_data_script = user_data_script.replace("${MSK_CLUSTER_ARN}", mskCluster.attr_arn)
        user_data_script = user_data_script.replace("${MSK_CLUSTER_BROKER_URL_PARAM_NAME}", mskClusterBrokerUrlParamStore.parameter_name)
        user_data_script = user_data_script.replace("${AWS_REGION}", self.region)
        user_data_script = user_data_script.replace("${VPC_ID}", vpc.vpc_id)
        user_data_script = user_data_script.replace("${AZ_IDS_PARAM_NAME}", getAzIdsParamStore.parameter_name)
        user_data_script = user_data_script.replace("${AZ_IDS_PARAM_TYPE}", getAzIdsParamStore.parameter_type)
        user_data_script = user_data_script.replace("${MSK_TOPIC_NAME_1}", parametersIam.mskTopicName1)
        user_data_script = user_data_script.replace("${MSK_TOPIC_NAME_2}", parametersIam.mskTopicName2)
        user_data_script = user_data_script.replace("${MSK_TOPIC_NAME_3}", parametersIam.mskTopicName3)
        user_data_script = user_data_script.replace("${MSK_TOPIC_NAME_4}", parametersIam.mskTopicName4)
        user_data_script = user_data_script.replace("${MSK_TOPIC_NAME_4}", parametersIam.mskTopicName5)
        user_data_script = user_data_script.replace("${MSK_TOPIC_NAME_4}", parametersIam.mskTopicName6)

        user_data.add_commands(user_data_script)

        kafkaProducerEc2BlockDevices = ec2.BlockDevice(device_name="/dev/xvda", volume=ec2.BlockDeviceVolume.ebs(25))
        kafkaProducerEC2Instance = ec2.Instance(self, "kafkaProducerEC2Instance",
            instance_name = f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-kafkaProducerEC2Instance",
            vpc = vpc,
            instance_type = ec2.InstanceType.of(ec2.InstanceClass(parametersIam.ec2InstanceClass), ec2.InstanceSize(parametersIam.ec2InstanceSize)),
            machine_image = ec2.AmazonLinuxImage(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2023), #ec2.MachineImage().lookup(name = parametersIam.ec2AmiName),
            #machine_image = ec2.MachineImage().lookup(name = parametersIam.ec2AmiName), #ec2.MachineImage().lookup(name = parametersIam.ec2AmiName),
            #availability_zone = vpc.availability_zones[1],
            block_devices = [kafkaProducerEc2BlockDevices],
            vpc_subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            key_pair = keyPair,
            security_group = sgEc2MskCluster,
            user_data = user_data,
            role = ec2MskClusterRole
        )
        tags.of(kafkaProducerEC2Instance).add("name", f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-kafkaProducerEC2Instance")
        tags.of(kafkaProducerEC2Instance).add("project", parametersIam.project)
        tags.of(kafkaProducerEC2Instance).add("env", parametersIam.env)
        tags.of(kafkaProducerEC2Instance).add("app", parametersIam.app)

#################### Output Values #####################        
        CfnOutput(self, "vpcId",
            value = vpc.vpc_id,
            description = "VPC Id",
            export_name = f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-vpcId"
        )
        CfnOutput(self, "sgMskClusterId",
            value = sgMskCluster.security_group_id,
            description = "Security group Id of MSK Cluster",
            export_name = f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-sgMskClusterId"
        )
        CfnOutput(self, "mskClusterName",
            value = mskCluster.cluster_name,
            description = "Name of an MSK cluster",
            export_name = f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-mskClusterName"
        )
        CfnOutput(self, "mskClusterArn",
            value = mskCluster.attr_arn,
            description = "ARN of an MSK cluster",
            export_name = f"{parametersIam.project}-{parametersIam.env}-{parametersIam.app}-mskClusterArn"
        )
