# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from constructs import Construct
from aws_cdk import (
    Stack,
    aws_iam as iam,
    Tags as tags
)
from . import mtlkhParameters as parameters

class mtlkhIamStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create EC2 MSK Cluster Role
        ec2_role_name = f"{parameters.project}-{parameters.env}-{parameters.app}-ec2MskClusterRole"
        self.ec2_msk_cluster_role = iam.Role(self, "ec2MskClusterRole",
            role_name = ec2_role_name,
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )
        tags.of(self.ec2_msk_cluster_role).add("name", f"{parameters.project}-{parameters.env}-{parameters.app}-ec2MskClusterRole")
        tags.of(self.ec2_msk_cluster_role).add("project", parameters.project)
        tags.of(self.ec2_msk_cluster_role).add("env", parameters.env)
        tags.of(self.ec2_msk_cluster_role).add("app", parameters.app)
        
        #self.ec2_msk_cluster_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess"))
        self.ec2_msk_cluster_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))
        self.ec2_msk_cluster_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchAgentServerPolicy"))
        self.ec2_msk_cluster_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("ReadOnlyAccess"))
        
        # Add inline policies for MSK and EC2 access
        self.ec2_msk_cluster_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "kafka:*",
                "kafka-cluster:*",
                "ec2:Describe*",
                "ec2:ModifyInstanceAttribute",
                "s3tables:*",
                "s3:*",
                "athena:*",
                "lakeformation:*",
                "iam:ListUsers",
                "iam:ListRoles",
                "iam:GetRole",
                "iam:GetRolePolicy",
                "cloudtrail:DescribeTrails",
                "cloudtrail:LookupEvents",
                "glue:CreateCatalog",
                "glue:UpdateCatalog",
                "glue:DeleteCatalog",
                "glue:GetCatalog",
                "glue:GetCatalogs",
                "glue:GetDatabase",
                "glue:GetDatabases",
                "glue:CreateDatabase",
                "glue:UpdateDatabase",
                "glue:DeleteDatabase",
                "glue:GetConnections",
                "glue:SearchTables",
                "glue:GetTable",
                "glue:CreateTable",
                "glue:UpdateTable",
                "glue:DeleteTable",
                "glue:GetTableVersions",
                "glue:GetPartitions",
                "glue:GetTables",
                "glue:ListWorkflows",
                "glue:BatchGetWorkflows",
                "glue:DeleteWorkflow",
                "glue:GetWorkflowRuns",
                "glue:StartWorkflowRun",
                "glue:GetWorkflow",
                "elasticmapreduce:AddJobFlowSteps",
                "elasticmapreduce:AddTags",
                "elasticmapreduce:CancelSteps",
                "elasticmapreduce:DescribeCluster",
                "elasticmapreduce:DescribeJobFlows",
                "elasticmapreduce:DescribeStep",
                "elasticmapreduce:ListBootstrapActions",
                "elasticmapreduce:ListClusters",
                "elasticmapreduce:ListInstances",                
                "elasticmapreduce:ListSteps",    
                "elasticmapreduce:TerminateJobFlows",
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret",                                                                                            
                "logs:*",
                "ssm:*"
            ],
            resources=["*"]
        ))
        
        # Add specific policy for accessing the tenant password secret
        self.ec2_msk_cluster_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret"
            ],
            resources=[
                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:lakehouse-tenant-user-password*"
            ]
        ))
        
        # Create EMR Service Role
        emr_service_role_name = f"{parameters.project}-{parameters.env}-{parameters.app}-emr-service-role"
        self.emr_service_role = iam.Role(self, "EmrServiceRole",
            role_name=emr_service_role_name,
            assumed_by=iam.ServicePrincipal("elasticmapreduce.amazonaws.com")
        )
        self.emr_service_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonElasticMapReduceRole")
        )
        
        # Create EMR Job Flow Role
        emr_job_flow_role_name = f"{parameters.project}-{parameters.env}-{parameters.app}-emr-job-flow-role"
        self.emr_job_flow_role = iam.Role(self, "EmrJobFlowRole",
            role_name=emr_job_flow_role_name,
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )
        self.emr_job_flow_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonElasticMapReduceforEC2Role")
        )
        self.emr_job_flow_role.assume_role_policy.add_statements(
            iam.PolicyStatement(
                actions=["sts:AssumeRole", "sts:SetContext", "sts:SetSourceIdentity"],
                principals=[iam.ServicePrincipal("lakeformation.amazonaws.com")]
            )
        )
        self.emr_job_flow_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonMSKFullAccess"))
        self.emr_job_flow_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))
        self.emr_job_flow_role.add_to_policy(iam.PolicyStatement(
            effect = iam.Effect.ALLOW,
            actions=[
                "s3tables:*",
                "kafka-cluster:*"
            ],
            resources= ["*"]
        ))
        
        # Create EMR Instance Profile
        emr_instance_profile_name = f"{parameters.project}-{parameters.env}-{parameters.app}-emr-instance-profile"
        self.emr_instance_profile = iam.CfnInstanceProfile(self, "EmrInstanceProfile",
            instance_profile_name=emr_instance_profile_name,
            roles=[self.emr_job_flow_role.role_name]
        )