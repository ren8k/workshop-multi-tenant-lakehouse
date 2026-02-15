#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os

import aws_cdk as cdk
from aws_cdk import Aspects
from infra.mtlkhEnvironment import mtlkhEnvironment
from infra.mtlkhEmrStack import mtlkhEmrStack
from infra.mtlkhIamStack import mtlkhIamStack
from infra import mtlkhParameters as parameters 
from cdk_nag import AwsSolutionsChecks, NagSuppressions

def add_nag_suppressions(iam_stack, main_stack, emr_stack, env):
    """Add CDK-Nag suppressions for acceptable security findings"""
    
    # Get dynamic account and region values
    account = env.account
    region = env.region
    
    # IAM Stack Suppressions
    # AWS Managed Policies - These are standard AWS policies for EMR and EC2 operations
    NagSuppressions.add_resource_suppressions(
        iam_stack.ec2_msk_cluster_role,
        [
            {
                "id": "AwsSolutions-IAM4",
                "reason": "AmazonSSMManagedInstanceCore is required for EC2 instance management via Systems Manager",
                "appliesTo": ["Policy::arn:<AWS::Partition>:iam::aws:policy/AmazonSSMManagedInstanceCore"]
            },
            {
                "id": "AwsSolutions-IAM4", 
                "reason": "CloudWatchAgentServerPolicy is required for CloudWatch monitoring",
                "appliesTo": ["Policy::arn:<AWS::Partition>:iam::aws:policy/CloudWatchAgentServerPolicy"]
            }
        ]
    )
    
    # EMR Service Role - Standard AWS managed policy for EMR
    NagSuppressions.add_resource_suppressions_by_path(
        iam_stack,
        f"/{iam_stack.stack_name}/EmrServiceRole/Resource",
        [
            {
                "id": "AwsSolutions-IAM4",
                "reason": "AmazonElasticMapReduceRole is the standard AWS managed policy for EMR service operations",
                "appliesTo": ["Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AmazonElasticMapReduceRole"]
            }
        ]
    )
    
    # EMR Job Flow Role - Standard AWS managed policies for EMR EC2 instances
    NagSuppressions.add_resource_suppressions_by_path(
        iam_stack,
        f"/{iam_stack.stack_name}/EmrJobFlowRole/Resource", 
        [
            {
                "id": "AwsSolutions-IAM4",
                "reason": "AmazonElasticMapReduceforEC2Role is the standard AWS managed policy for EMR EC2 instances",
                "appliesTo": ["Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AmazonElasticMapReduceforEC2Role"]
            },
            {
                "id": "AwsSolutions-IAM4",
                "reason": "AmazonSSMManagedInstanceCore is required for EC2 instance management via Systems Manager", 
                "appliesTo": ["Policy::arn:<AWS::Partition>:iam::aws:policy/AmazonSSMManagedInstanceCore"]
            }
        ]
    )
    
    # Wildcard permissions for service operations - These are necessary for EMR and MSK operations
    NagSuppressions.add_resource_suppressions_by_path(
        iam_stack,
        f"/{iam_stack.stack_name}/ec2MskClusterRole/DefaultPolicy/Resource",
        [
            {
                "id": "AwsSolutions-IAM5",
                "reason": "EC2 Describe* permissions are required for EMR cluster operations and resource discovery",
                "appliesTo": ["Action::ec2:Describe*"]
            },
            {
                "id": "AwsSolutions-IAM5", 
                "reason": "Kafka cluster wildcard permissions are required for MSK cluster operations",
                "appliesTo": ["Action::kafka-cluster:*", "Action::kafka:*"]
            },
            {
                "id": "AwsSolutions-IAM5",
                "reason": "S3 wildcard permissions are required for EMR data processing operations",
                "appliesTo": ["Action::s3:*"]
            },
            {
                "id": "AwsSolutions-IAM5",
                "reason": "CloudWatch Logs wildcard permissions are required for EMR logging",
                "appliesTo": ["Action::logs:*"]
            },
            {
                "id": "AwsSolutions-IAM5",
                "reason": "Athena wildcard permissions are required for data querying operations",
                "appliesTo": ["Action::athena:*"]
            },
            {
                "id": "AwsSolutions-IAM5",
                "reason": "Lake Formation wildcard permissions are required for data lake operations",
                "appliesTo": ["Action::lakeformation:*"]
            },
            {
                "id": "AwsSolutions-IAM5",
                "reason": "S3 Tables wildcard permissions are required for table operations",
                "appliesTo": ["Action::s3tables:*"]
            },
            {
                "id": "AwsSolutions-IAM5",
                "reason": "SSM wildcard permissions are required for Systems Manager operations",
                "appliesTo": ["Action::ssm:*"]
            },
            {
                "id": "AwsSolutions-IAM5",
                "reason": "Wildcard resource permissions are required for dynamic resource access in workshop environment",
                "appliesTo": ["Resource::*"]
            },
            {
                "id": "AwsSolutions-IAM5",
                "reason": "Secrets Manager wildcard permissions are required for accessing tenant secrets",
                "appliesTo": [
                    f"Resource::arn:aws:secretsmanager:{region}:{account}:secret:lakehouse-tenant-user-password*"
                ]
            }
        ]
    )
    
    # EMR Job Flow Role wildcard permissions
    NagSuppressions.add_resource_suppressions_by_path(
        iam_stack,
        f"/{iam_stack.stack_name}/EmrJobFlowRole/DefaultPolicy/Resource",
        [
            {
                "id": "AwsSolutions-IAM5",
                "reason": "Kafka cluster wildcard permissions are required for MSK operations in EMR",
                "appliesTo": ["Action::kafka-cluster:*"]
            },
            {
                "id": "AwsSolutions-IAM5",
                "reason": "S3 Tables wildcard permissions are required for table operations in EMR",
                "appliesTo": ["Action::s3tables:*"]
            },
            {
                "id": "AwsSolutions-IAM5",
                "reason": "Wildcard resource permissions are required for dynamic resource access in EMR jobs",
                "appliesTo": ["Resource::*"]
            }
        ]
    )
    
    # CDK Bucket Deployment Lambda suppressions
    NagSuppressions.add_resource_suppressions_by_path(
        main_stack,
        f"/{main_stack.stack_name}/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/ServiceRole/Resource",
        [
            {
                "id": "AwsSolutions-IAM4",
                "reason": "AWSLambdaBasicExecutionRole is the standard AWS managed policy for Lambda execution",
                "appliesTo": ["Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
            }
        ]
    )
    
    # CDK Bucket Deployment Lambda policy suppressions
    NagSuppressions.add_resource_suppressions_by_path(
        main_stack,
        f"/{main_stack.stack_name}/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/ServiceRole/DefaultPolicy/Resource",
        [
            {
                "id": "AwsSolutions-IAM5",
                "reason": "CDK Bucket Deployment requires S3 wildcard permissions for asset deployment",
                "appliesTo": [
                    "Action::s3:GetBucket*",
                    "Action::s3:GetObject*", 
                    "Action::s3:List*",
                    "Action::s3:Abort*",
                    "Action::s3:DeleteObject*"
                ]
            },
            {
                "id": "AwsSolutions-IAM5",
                "reason": "CDK Bucket Deployment requires wildcard resource permissions for asset and target bucket access",
                "appliesTo": [
                    f"Resource::arn:aws:s3:::cdk-hnb659fds-assets-{account}-{region}/*",
                    "Resource::<EmrBucket77B88852.Arn>/*"
                ]
            }
        ]
    )
    
    # Security Group validation failures due to intrinsic functions
    NagSuppressions.add_resource_suppressions_by_path(
        main_stack,
        f"/{main_stack.stack_name}/sgMskCluster",
        [
            {
                "id": "CdkNagValidationFailure",
                "reason": "AwsSolutions-EC23 validation fails due to VPC CIDR being resolved at runtime via intrinsic function",
                "appliesTo": ["AwsSolutions-EC23"]
            }
        ]
    )
    
    NagSuppressions.add_resource_suppressions_by_path(
        emr_stack,
        f"/{emr_stack.stack_name}/sgEmrCluster/Resource",
        [
            {
                "id": "CdkNagValidationFailure", 
                "reason": "AwsSolutions-EC23 validation fails due to VPC CIDR being resolved at runtime via intrinsic function",
                "appliesTo": ["AwsSolutions-EC23"]
            }
        ]
    )
    
    # EMR Security Suppressions - Workshop Environment with Sample Data
    NagSuppressions.add_resource_suppressions_by_path(
        emr_stack,
        f"/{emr_stack.stack_name}/EmrCluster",
        [
            {
                "id": "AwsSolutions-EMR4",
                "reason": "Workshop environment using sample/dummy data - local disk encryption not required for demo purposes"
            },
            {
                "id": "AwsSolutions-EMR5", 
                "reason": "Workshop environment using sample/dummy data - encryption in transit not required for demo purposes"
            },
            {
                "id": "AwsSolutions-EMR6",
                "reason": "Workshop environment using sample/dummy data - authentication via EC2 Key Pair or Kerberos not required for demo purposes"
            }
        ]
    )
    
    # Additional Workshop Environment Suppressions
    # ReadOnlyAccess policy suppression for workshop
    NagSuppressions.add_resource_suppressions(
        iam_stack.ec2_msk_cluster_role,
        [
            {
                "id": "AwsSolutions-IAM4",
                "reason": "Workshop environment - ReadOnlyAccess policy used for demonstration purposes with sample data",
                "appliesTo": ["Policy::arn:<AWS::Partition>:iam::aws:policy/ReadOnlyAccess"]
            }
        ]
    )
    
    # MSK Full Access policy suppression for workshop
    NagSuppressions.add_resource_suppressions_by_path(
        iam_stack,
        f"/{iam_stack.stack_name}/EmrJobFlowRole/Resource",
        [
            {
                "id": "AwsSolutions-IAM4",
                "reason": "Workshop environment - AmazonMSKFullAccess policy used for demonstration purposes with sample data",
                "appliesTo": ["Policy::arn:<AWS::Partition>:iam::aws:policy/AmazonMSKFullAccess"]
            }
        ]
    )
    
    # EC2 Instance security suppressions for workshop
    NagSuppressions.add_resource_suppressions_by_path(
        main_stack,
        f"/{main_stack.stack_name}/kafkaProducerEC2Instance/Resource",
        [
            {
                "id": "AwsSolutions-EC26",
                "reason": "Workshop environment - EBS encryption not required for demo with sample data"
            },
            {
                "id": "AwsSolutions-EC28",
                "reason": "Workshop environment - Detailed monitoring not required for demo purposes"
            },
            {
                "id": "AwsSolutions-EC29",
                "reason": "Workshop environment - Termination protection disabled for easy cleanup after workshop"
            }
        ]
    )
    
    # S3 Bucket security suppressions for workshop
    NagSuppressions.add_resource_suppressions_by_path(
        main_stack,
        f"/{main_stack.stack_name}/EmrBucket/Resource",
        [
            {
                "id": "AwsSolutions-S1",
                "reason": "Workshop environment - Server access logs not required for demo with sample data"
            },
            {
                "id": "AwsSolutions-S10",
                "reason": "Workshop environment - SSL enforcement not required for demo with sample data"
            }
        ]
    )
    
    # S3 Bucket Policy suppression for workshop
    NagSuppressions.add_resource_suppressions_by_path(
        main_stack,
        f"/{main_stack.stack_name}/EmrBucket/Policy/Resource",
        [
            {
                "id": "AwsSolutions-S10",
                "reason": "Workshop environment - SSL enforcement not required for demo with sample data"
            }
        ]
    )
    
    # VPC Flow Logs suppression for workshop
    NagSuppressions.add_resource_suppressions_by_path(
        main_stack,
        f"/{main_stack.stack_name}/vpc/Resource",
        [
            {
                "id": "AwsSolutions-VPC7",
                "reason": "Workshop environment - VPC Flow Logs not required for demo purposes"
            }
        ]
    )
    
    # Lambda runtime suppression for CDK deployment
    NagSuppressions.add_resource_suppressions_by_path(
        main_stack,
        f"/{main_stack.stack_name}/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/Resource",
        [
            {
                "id": "AwsSolutions-L1",
                "reason": "CDK managed Lambda function - runtime version managed by CDK framework"
            }
        ]
    )

app = cdk.App()
env = cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION'))

# Create IAM stack first
iam_stack = mtlkhIamStack(app, f"{parameters.project}-{parameters.env}-{parameters.app}-iamStack", env=env)

# Create main environment stack
main_stack = mtlkhEnvironment(app, f"{parameters.project}-{parameters.env}-{parameters.app}-mtlkhEnv", 
                             ec2_role=iam_stack.ec2_msk_cluster_role, env=env)
main_stack.add_dependency(iam_stack)

# Create EMR stack with dependencies on main stack
emr_stack = mtlkhEmrStack(app, f"{parameters.project}-{parameters.env}-{parameters.app}-emrStack", 
                         vpc=main_stack.vpc, 
                         emr_bucket=main_stack.emr_bucket,
                         emr_service_role=iam_stack.emr_service_role,
                         emr_instance_profile=iam_stack.emr_instance_profile,
                         env=env)
emr_stack.add_dependency(main_stack)

# Add CDK-Nag suppressions for acceptable findings
add_nag_suppressions(iam_stack, main_stack, emr_stack, env)

# Add cdk-nag checks with verbose reporting
Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

try:
    app.synth()
except Exception as e:
    print(f"CDK synthesis failed: {e}")
    raise

