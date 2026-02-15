# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#https://github.com/aws-samples/msk-powered-financial-data-feed/blob/main/dataFeedMsk/parameters.py#L1
project = "awsmtlkh"             #Project name
env = "dev"                     #Environment name dev,prod,stag
app = "appIam"                     #App name

###   VPC Parameters   ###

cidrRange = "10.21.0.0/16"      #IPv4 CIDR range for VPC
numberOfNatGateways = 2         #Number of NAT Gateways
enableDnsHostnames = True       #Specify True to enable DNS support for VPC otherwise False
enableDnsSupport = True         #Specify True to enable DNS hostnames for VPC otherwise False
az1 = "us-east-1a"              #Availability Zone ID
az2 = "us-east-1b"              #Availability Zone ID
cidrMaskForSubnets = 24         #IPv4 CIDR Mask for Subnets

###   Security Group Parameters   ###

sgMskClusterInboundPort = 0                 #Inbound Port for MSK Cluster Security Group
sgMskClusterOutboundPort = 65535            #Outbound Port for MSK Cluster Security Group
sgKafkaInboundPort = 9092                   #Inbound Port for MSK Cluster Security Group from EC2 Kafka Producer
sgKafkaOutboundPort = 9098                  #Outbound Port for MSK Cluster Security Group from EC2 Kafka Producer

###   MSK Kafka Parameters   ###

mskVersion = "3.6.0"                        #Version of MSK cluster
mskNumberOfBrokerNodes = 2                  #Number of broker nodes of an MSK Cluster
mskClusterInstanceType = "kafka.m5.large"   #Instance type of MSK cluster
mskClusterVolumeSize = 100                  #Volume Size of MSK Cluster
#mskScramPropertyEnable = True               #Select True to enable (SASL/SCRAM) property for MSK Cluster otherwise False
mskIamPropertyEnable = True               #Select True to enable (SASL/SCRAM) property for MSK Cluster otherwise False
mskEncryptionProducerBroker = "TLS"         #Encryption protocol used for communication between producer and brokers in MSK Cluster
mskEncryptionInClusterEnable = True         #Select True to enable encryption in MSK Cluster otherwise False
#enableSaslScramClientAuth = True     #In the first iteration, disable SASL/SCRAM client authentication, and in the second iteration, enable it.
enableSaslIAMClientAuth = True     #In the first iteration, disable SASL/IAM client authentication, and in the second iteration, enable it.
enableClusterConfig = True             #In the first iteration, disable cluster configuration, and in the second iteration, enable it
enableClusterPolicy = True           #In the first iteration, disable cluster policy, and in the second iteration, enable it
mskTopicName1 = "networkevents"                      #Name of the first MSK topic
mskTopicName2 = "authenticationlogs"                      #Name of the second MSK topic
mskTopicName3 = "endpoints"              #Name of the third MSK topic
mskTopicName4 = "installedsoftware"              #Name of the fourth MSK topic
mskTopicName5 = 'cveinfo'       #Name of the fifth MSK topic
mskTopicName6 = "threatintelligence"    #Name of the sixth MSK topic

###   Secret Manager Parameters   ###

mskProducerUsername = "netsol"        #Producer username for MSK 
mskConsumerUsername = "consumer"      #Consumer username for MSK

###   MSK Producer EC2 Instance Parameters   ### 

ec2InstanceClass = "BURSTABLE2"             #Instance class for EC2 instances
ec2InstanceSize = "LARGE"                   #Size of the EC2 instance
#ec2AmiName = "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-20220420"   #AMI name for EC2 instances 
ec2AmiName = "ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-20250610"
producerEc2KeyPairName = "jp-aws-east1"