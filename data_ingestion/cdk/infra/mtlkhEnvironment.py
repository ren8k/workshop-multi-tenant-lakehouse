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
    aws_emr as emr,
#    Duration,
    Aws as AWS
)
import os
import random
from . import mtlkhParameters as parameters
import configparser

class mtlkhEnvironment(Stack):
    def __init__(self, scope: Construct, construct_id: str, ec2_role, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)    

################ VPC Configuration #####################

        # Fetch region and construct availability zones
        region = self.region
        #all_azs = self.availability_zones

        #region = AWS.REGION
        # This fail
        #az_a = all_azs[0]
        #az_b = all_azs[1]
        
        #availabilityZonesList = [az_a, az_b]
        vpc = ec2.Vpc (self, "vpc",
            vpc_name = f"{parameters.project}-{parameters.env}-{parameters.app}-vpc",
            ip_addresses = ec2.IpAddresses.cidr(parameters.cidrRange),
            enable_dns_hostnames = parameters.enableDnsHostnames,
            enable_dns_support = parameters.enableDnsSupport,
            max_azs=2,
            nat_gateways = parameters.numberOfNatGateways,
            subnet_configuration = [
                {
                    "name": f"{parameters.project}-{parameters.env}-{parameters.app}-publicSubnet1",
                    "subnetType": ec2.SubnetType.PUBLIC,
                    "cidrMask": parameters.cidrMaskForSubnets,
                },
                {
                    "name": f"{parameters.project}-{parameters.env}-{parameters.app}-privateSubnet1",
                    "subnetType": ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    "cidrMask": parameters.cidrMaskForSubnets,
                }
            ]
        )
        tags.of(vpc).add("name", f"{parameters.project}-{parameters.env}-{parameters.app}-vpc")
        tags.of(vpc).add("project", parameters.project)
        tags.of(vpc).add("env", parameters.env)
        tags.of(vpc).add("app", parameters.app)

#############       EC2 Key Pair Configurations      #############

       # keyPair = ec2.KeyPair.from_key_pair_name(self, "jp-aws-east1", parameters.producerEc2KeyPairName)

#################### Security Group Configuration #####################
        sgEc2MskCluster = ec2.SecurityGroup(self, "sgEc2MskCluster",
            security_group_name = f"{parameters.project}-{parameters.env}-{parameters.app}-sgEc2MskCluster",
            vpc=vpc,
            description="Security group associated with the EC2 instance of MSK Cluster",
            allow_all_outbound=True,
            disable_inline_rules=True
        )
        tags.of(sgEc2MskCluster).add("name", f"{parameters.project}-{parameters.env}-{parameters.app}-sgEc2MskCluster")
        tags.of(sgEc2MskCluster).add("project", parameters.project)
        tags.of(sgEc2MskCluster).add("env", parameters.env)
        tags.of(sgEc2MskCluster).add("app", parameters.app)

        sgMskCluster = ec2.SecurityGroup(self, "sgMskCluster",
            security_group_name = f"{parameters.project}-{parameters.env}-{parameters.app}-sgMskCluster",
            vpc=vpc,
            description="Security group associated with the MSK Cluster",
            allow_all_outbound=True,
            disable_inline_rules=True
        )
        tags.of(sgMskCluster).add("name", f"{parameters.project}-{parameters.env}-{parameters.app}-sgMskCluster")
        tags.of(sgMskCluster).add("project", parameters.project)
        tags.of(sgMskCluster).add("env", parameters.env)
        tags.of(sgMskCluster).add("app", parameters.app)

        # CloudFront managed prefix list IDs by region
        cloudfront_prefix_lists = {
            "us-east-1": "pl-3b927c52",
            "us-east-2": "pl-b6a144df", 
            "us-west-1": "pl-4ca14425",
            "us-west-2": "pl-82a045eb",
            "eu-west-1": "pl-4fa04526",
            "eu-west-2": "pl-93a247fa",
            "eu-west-3": "pl-75b1541c",
            "eu-central-1": "pl-a3a144ca",
            "ap-northeast-1": "pl-58a04531",
            "ap-northeast-2": "pl-22a6434b",
            "ap-southeast-1": "pl-31a34658",
            "ap-southeast-2": "pl-b8a742d1",
            "ap-south-1": "pl-9aa247f3",
            "sa-east-1": "pl-78a54011"
        }
        
        # Get CloudFront managed prefix list for current region
        cloudfront_prefix_list_id = cloudfront_prefix_lists.get(region, "pl-3b927c52")  # Default to us-east-1 if region not found
        
        # Add single ingress rule using CloudFront managed prefix list for HTTP and HTTPS traffic
        sgEc2MskCluster.add_ingress_rule(
            peer = ec2.Peer.prefix_list(cloudfront_prefix_list_id),
            connection = ec2.Port.tcp_range(80, 443),
            description = f"Allow HTTP/HTTPS traffic from CloudFront managed prefix list for region {region}"
        )

        sgEc2MskCluster.add_ingress_rule(
            peer = ec2.Peer.security_group_id(sgMskCluster.security_group_id),
            connection = ec2.Port.tcp_range(parameters.sgKafkaInboundPort, parameters.sgKafkaOutboundPort),
            description = "Allow Custom TCP traffic from sgEc2MskCluster to sgMskCluster"
        )

        sgMskCluster.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp_range(0, 65535),
            description="Allow VPC traffic to sgMskCluster"
        )

        sgMskCluster.add_ingress_rule(
            peer = ec2.Peer.security_group_id(sgMskCluster.security_group_id),
            connection = ec2.Port.tcp_range(parameters.sgMskClusterInboundPort, parameters.sgMskClusterOutboundPort),
            description = "Allow all TCP traffic from sgMskCluster to sgMskCluster"
        )            
        
#################### KMS Configuration #####################
        customerManagedKey = kms.Key(self, "customerManagedKey",
            alias = f"{parameters.project}-{parameters.env}-{parameters.app}-sasl/scram-key",
            description = "Customer managed key",
            enable_key_rotation = True,
            removal_policy = RemovalPolicy.DESTROY
        )
        tags.of(customerManagedKey).add("name", f"{parameters.project}-{parameters.env}-{parameters.app}-customerManagedKey")
        tags.of(customerManagedKey).add("project", parameters.project)
        tags.of(customerManagedKey).add("env", parameters.env)
        tags.of(customerManagedKey).add("app", parameters.app)

#################### MSK Logs Configuration #####################        
        mskClusterLogGroup = logs.LogGroup(self, "mskClusterLogGroup",
            log_group_name = f"{parameters.project}-{parameters.env}-{parameters.app}-mskClusterLogGroup",
            retention = logs.RetentionDays.ONE_WEEK,
            removal_policy = RemovalPolicy.DESTROY
        )
        tags.of(mskClusterLogGroup).add("name", f"{parameters.project}-{parameters.env}-{parameters.app}-mskClusterLogGroup")
        tags.of(mskClusterLogGroup).add("project", parameters.project)
        tags.of(mskClusterLogGroup).add("env", parameters.env)
        tags.of(mskClusterLogGroup).add("app", parameters.app)

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
            name = f"{parameters.project}-{parameters.env}-{parameters.app}-mskClusterConfiguration",
            server_properties = mskClusterConfigProperties,
            description = "MSK cluster configuration"
        )

        mskCluster = msk.CfnCluster(self, "mskCluster",
            cluster_name = f"{parameters.project}-{parameters.env}-{parameters.app}-mskCluster",
            kafka_version = parameters.mskVersion,
            number_of_broker_nodes = parameters.mskNumberOfBrokerNodes,
            broker_node_group_info = msk.CfnCluster.BrokerNodeGroupInfoProperty(
                instance_type = parameters.mskClusterInstanceType,
                client_subnets = vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS).subnet_ids[:2],
                security_groups = [sgMskCluster.security_group_id],
                connectivity_info=None,
                storage_info = msk.CfnCluster.StorageInfoProperty(  
                    ebs_storage_info = msk.CfnCluster.EBSStorageInfoProperty(
                        volume_size = parameters.mskClusterVolumeSize
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
                        enabled = parameters.mskIamPropertyEnable
                    )                    
                )
            ),
            configuration_info=msk.CfnCluster.ConfigurationInfoProperty(
                arn=mskClusterConfiguration.attr_arn,
                revision=mskClusterConfiguration.attr_latest_revision_revision
            ),
            encryption_info = msk.CfnCluster.EncryptionInfoProperty(
                encryption_in_transit = msk.CfnCluster.EncryptionInTransitProperty(
                    client_broker = parameters.mskEncryptionProducerBroker,
                    in_cluster = parameters.mskEncryptionInClusterEnable
                )
            )
        )

        tags.of(mskCluster).add("name", f"{parameters.project}-{parameters.env}-{parameters.app}-mskCluster")
        tags.of(mskCluster).add("project", parameters.project)
        tags.of(mskCluster).add("env", parameters.env)
        tags.of(mskCluster).add("app", parameters.app)
        

        mskClusterArnParamStore = ssm.StringParameter(self, "mskClusterArnParamStore",
            parameter_name = f"mtlkh-{parameters.env}-mskClusterArn-ssmParamStore",
            string_value = mskCluster.attr_arn,
            tier = ssm.ParameterTier.STANDARD
        )
        tags.of(mskClusterArnParamStore).add("name", f"{parameters.project}-{parameters.env}-{parameters.app}-mskClusterArnParamStore")
        tags.of(mskClusterArnParamStore).add("project", parameters.project)
        tags.of(mskClusterArnParamStore).add("env", parameters.env)
        tags.of(mskClusterArnParamStore).add("app", parameters.app)
        mskClusterArnParamStoreValue = mskClusterArnParamStore.string_value

        mskClusterBrokerUrlParamStore = ssm.StringParameter(self, "mskClusterBrokerUrlParamStore",
            parameter_name = f"mtlkh-{parameters.env}-mskClusterBrokerUrl-ssmParamStore",
            string_value = "dummy",         # We're passing a dummy value in this SSM parameter. The actual value will be replaced by EC2 userdata during the process
            tier = ssm.ParameterTier.STANDARD
        )
        tags.of(mskClusterBrokerUrlParamStore).add("name", f"{parameters.project}-{parameters.env}-{parameters.app}-mskClusterBrokerUrlParamStore")
        tags.of(mskClusterBrokerUrlParamStore).add("project", parameters.project)
        tags.of(mskClusterBrokerUrlParamStore).add("env", parameters.env)
        tags.of(mskClusterBrokerUrlParamStore).add("app", parameters.app)

        getAzIdsParamStore = ssm.StringParameter(self, "getAzIdsParamStore",
                parameter_name = f"mtlkh-{parameters.env}-getAzIdsParamStore-ssmParamStore",
                string_value = "dummy",         # We're passing a dummy value in this SSM parameter. The actual value will be replaced by EC2 userdata during the process
                tier = ssm.ParameterTier.STANDARD,
                type = ssm.ParameterType.STRING_LIST
            )
        tags.of(getAzIdsParamStore).add("name", f"{parameters.project}-{parameters.env}-{parameters.app}-getAzIdsParamStore")
        tags.of(getAzIdsParamStore).add("project", parameters.project)
        tags.of(getAzIdsParamStore).add("env", parameters.env)
        tags.of(getAzIdsParamStore).add("app", parameters.app)        

#We are unable to activate the SASL/Iam authentication method for producer authentication during the cluster creation process
        enableSaslIAMClientAuth = parameters.enableSaslIAMClientAuth
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
        enableClusterConfig = parameters.enableClusterConfig
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

#################### Use IAM Role from IAM Stack #####################        
        
        ec2MskClusterRole = ec2_role

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
        user_data_script = user_data_script.replace("${MSK_TOPIC_NAME_1}", parameters.mskTopicName1)
        user_data_script = user_data_script.replace("${MSK_TOPIC_NAME_2}", parameters.mskTopicName2)
        user_data_script = user_data_script.replace("${MSK_TOPIC_NAME_3}", parameters.mskTopicName3)
        user_data_script = user_data_script.replace("${MSK_TOPIC_NAME_4}", parameters.mskTopicName4)
        user_data_script = user_data_script.replace("${MSK_TOPIC_NAME_5}", parameters.mskTopicName5)
        user_data_script = user_data_script.replace("${MSK_TOPIC_NAME_6}", parameters.mskTopicName6)
        # Set environment variables in EC2 instance
        bucketName = f"{parameters.project}-{parameters.app}-emr-bucket".lower()
        bucketName = f"{bucketName}-{AWS.REGION}-{AWS.ACCOUNT_ID}"          
        user_data_script = user_data_script.replace("${EMR_BUCKET_NAME}", bucketName)   
        user_data_script = user_data_script.replace("${AWS_ACCOUNT_ID}", AWS.ACCOUNT_ID)

        user_data.add_commands(user_data_script)

        kafkaProducerEc2BlockDevices = ec2.BlockDevice(device_name="/dev/xvda", volume=ec2.BlockDeviceVolume.ebs(25))
        kafkaProducerEC2Instance = ec2.Instance(self, "kafkaProducerEC2Instance",
            instance_name = f"{parameters.project}-{parameters.env}-{parameters.app}-kafkaProducerEC2Instance",
            vpc = vpc,
            instance_type = ec2.InstanceType.of(ec2.InstanceClass(parameters.ec2InstanceClass), ec2.InstanceSize(parameters.ec2InstanceSize)),
            machine_image = ec2.MachineImage.latest_amazon_linux2023(),
            #availability_zone = vpc.availability_zones[1],
            block_devices = [kafkaProducerEc2BlockDevices],
            vpc_subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            #key_pair = keyPair,
            security_group = sgEc2MskCluster,
            user_data = user_data,
            role = ec2MskClusterRole
        )
        tags.of(kafkaProducerEC2Instance).add("name", f"{parameters.project}-{parameters.env}-{parameters.app}-kafkaProducerEC2Instance")
        tags.of(kafkaProducerEC2Instance).add("project", parameters.project)
        tags.of(kafkaProducerEC2Instance).add("env", parameters.env)
        tags.of(kafkaProducerEC2Instance).add("app", parameters.app)
        tags.of(kafkaProducerEC2Instance).add("LakehouseWorkshopLoadGenrator", "true")

        # Create S3 bucket for EMR logs and scripts
        bucketName = f"{parameters.project}-{parameters.app}-emr-bucket".lower()
        bucketName = f"{bucketName}-{AWS.REGION}-{AWS.ACCOUNT_ID}"        
        emr_bucket = s3.Bucket(self, "EmrBucket",
            bucket_name=bucketName,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )
        tags.of(emr_bucket).add("name", f"{parameters.project}-{parameters.env}-{parameters.app}-emr-bucket")
        tags.of(emr_bucket).add("project", parameters.project)
        tags.of(emr_bucket).add("env", parameters.env)
        tags.of(emr_bucket).add("app", parameters.app)

        # Create bootstrap script
        bootstrap_script = """
#!/bin/bash
cd /home/hadoop
wget https://github.com/aws/aws-msk-iam-auth/releases/download/v2.3.2/aws-msk-iam-auth-2.3.2-all.jar
"""
        
        bootstrap_deployment = s3deployment.BucketDeployment(self, "BootstrapScriptDeployment",
            sources=[s3deployment.Source.data("bootstrap.sh", bootstrap_script)],
            destination_bucket=emr_bucket,
            destination_key_prefix="scripts"
        )        
        
        # Expose resources for EMR stack
        self.vpc = vpc
        #self.msk_security_group = sgMskCluster
        self.emr_bucket = emr_bucket      
#################### Output Values #####################        
        CfnOutput(self, "vpcId",
            value = vpc.vpc_id,
            description = "VPC Id",
            export_name = f"{parameters.project}-{parameters.env}-{parameters.app}-vpcId"
        )
        CfnOutput(self, "sgMskClusterId",
            value = sgMskCluster.security_group_id,
            description = "Security group Id of MSK Cluster",
            export_name = f"{parameters.project}-{parameters.env}-{parameters.app}-sgMskClusterId"
        )
        CfnOutput(self, "mskClusterName",
            value = mskCluster.cluster_name,
            description = "Name of an MSK cluster",
            export_name = f"{parameters.project}-{parameters.env}-{parameters.app}-mskClusterName"
        )
        CfnOutput(self, "mskClusterArn",
            value = mskCluster.attr_arn,
            description = "ARN of an MSK cluster",
            export_name = f"{parameters.project}-{parameters.env}-{parameters.app}-mskClusterArn"
        )


        CfnOutput(self, "kafkaProducerInstanceId",
            value = kafkaProducerEC2Instance.instance_id,
            description = "Instance ID of Kafka Producer EC2",
            export_name = "kafkaProducer-InstanceId"
        )
        CfnOutput(self, "kafkaProducerPublicDnsName",
            value = kafkaProducerEC2Instance.instance_public_dns_name,
            description = "Public DNS name of Kafka Producer EC2",
            export_name = "kafkaProducer-InstanceUrl"
        )
