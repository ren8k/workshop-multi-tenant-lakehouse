# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from constructs import Construct
from aws_cdk import (
    Stack,
    CfnOutput,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ssm as ssm,
    aws_emr as emr,
    Tags as tags,
    aws_s3_deployment as s3deployment,
    Aws as AWS
)
from . import mtlkhParameters as parameters

class mtlkhEmrStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc, emr_bucket, emr_service_role, emr_instance_profile, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Use EMR roles from IAM stack
        emr_instance_profile_arn = emr_instance_profile.ref                        
        
        # Create security group for EMR cluster
        sg_emr_cluster = ec2.SecurityGroup(self, "sgEmrCluster",
            security_group_name=f"{parameters.project}-{parameters.env}-{parameters.app}-sgEmrCluster",
            vpc=vpc,
            description="Security group for EMR cluster",
            allow_all_outbound=True
        )
        
        # Allow communication between EMR and MSK using CIDR blocks to avoid cyclic dependency
        sg_emr_cluster.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp_range(0, 65535),
            description="Allow Kafka traffic from VPC"
        )      
        
        # Create EMR cluster
        emr_cluster = emr.CfnCluster(self, "EmrCluster",
            name=f"{parameters.project}-{parameters.env}-{parameters.app}-emr-cluster",
            applications=[{"name": "Spark"}, {"name": "Hadoop"}, {"name": "Hive"}, {"name": "Livy"}, {"name": "JupyterEnterpriseGateway"}],
            release_label="emr-7.9.0",
            step_concurrency_level=14,
            service_role=emr_service_role.role_name,
            job_flow_role=emr_instance_profile_arn,
            log_uri=f"s3://{emr_bucket.bucket_name}/logs/",
            visible_to_all_users=True,
            instances=emr.CfnCluster.JobFlowInstancesConfigProperty(
                ec2_subnet_id=vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS).subnet_ids[0],
                additional_master_security_groups=[sg_emr_cluster.security_group_id],
                additional_slave_security_groups=[sg_emr_cluster.security_group_id],
                master_instance_fleet=emr.CfnCluster.InstanceFleetConfigProperty(
                    instance_type_configs=[
                        emr.CfnCluster.InstanceTypeConfigProperty(
                            instance_type="m5.4xlarge",   # Primary choice
                        ),
                        emr.CfnCluster.InstanceTypeConfigProperty(
                            instance_type="c5.4xlarge",
                        ),
                        emr.CfnCluster.InstanceTypeConfigProperty(
                            instance_type="r5.4xlarge",
                        ),
                        emr.CfnCluster.InstanceTypeConfigProperty(
                            instance_type="m5a.4xlarge",
                        ),
                        emr.CfnCluster.InstanceTypeConfigProperty(
                            instance_type="c5a.4xlarge",
                        )
                    ],
                    target_on_demand_capacity=1, # Master fleet must be 1 and on-demand or spot only
                ),
                core_instance_fleet=emr.CfnCluster.InstanceFleetConfigProperty(
                    instance_type_configs=[
                        emr.CfnCluster.InstanceTypeConfigProperty(
                            instance_type="m5.4xlarge",   # Primary choice
                        ),
                        emr.CfnCluster.InstanceTypeConfigProperty(
                            instance_type="c5.4xlarge",
                        ),
                        emr.CfnCluster.InstanceTypeConfigProperty(
                            instance_type="r5.4xlarge",
                        ),
                        emr.CfnCluster.InstanceTypeConfigProperty(
                            instance_type="m5a.4xlarge",
                        ),
                        emr.CfnCluster.InstanceTypeConfigProperty(
                            instance_type="c5a.4xlarge",
                        )
                    ],
                    target_on_demand_capacity=3,
                ),
                termination_protected=False
            ),
            configurations=[
                {
                    "classification": "spark",
                    "properties": {
                        "maximizeResourceAllocation": "true"
                    }
                },
                {
                    "classification": "iceberg-defaults",
                    "properties": {
                        "iceberg.enabled": "true"
                    }
                }
            ],
            bootstrap_actions=[
                emr.CfnCluster.BootstrapActionConfigProperty(
                    name="InstallDependencies",
                    script_bootstrap_action=emr.CfnCluster.ScriptBootstrapActionConfigProperty(
                        path=f"s3://{emr_bucket.bucket_name}/scripts/bootstrap.sh",
                        args=[]
                    )
                )
            ],
            tags=[
                {"key": "name", "value": f"{parameters.project}-{parameters.env}-{parameters.app}-emr-cluster"},
                {"key": "project", "value": parameters.project},
                {"key": "env", "value": parameters.env},
                {"key": "app", "value": parameters.app}
            ]
        )
                               
        # Outputs
        CfnOutput(self, "emrClusterId",
            value = emr_cluster.ref,
            description = "ID of the EMR cluster",
            export_name = f"{parameters.project}-{parameters.env}-{parameters.app}-emrClusterId"
        )
        
        CfnOutput(self, "emrBucketName",
            value = emr_bucket.bucket_name,
            description = "Name of the S3 bucket for EMR logs and scripts",
            export_name = f"{parameters.project}-{parameters.env}-{parameters.app}-emrBucketName"
        )