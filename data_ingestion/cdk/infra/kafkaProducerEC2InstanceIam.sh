#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
sudo su
sudo yum update -y
sudo yum -y install java-11
sudo yum install jq -y
sudo yum -y install pip
export KAFKA_VERSION=3.6.0
if [[ $(pwd) == */ ]]; then
    echo "export KAFKA_ROOT=$(pwd)kafka_2.13-${KAFKA_VERSION}" >> ~/.bashrc
else
    echo "export KAFKA_ROOT=$(pwd)/kafka_2.13-${KAFKA_VERSION}" >> ~/.bashrc
fi
source ~/.bashrc
wget https://archive.apache.org/dist/kafka/3.6.0/kafka_2.13-$KAFKA_VERSION.tgz
tar -xzf kafka_2.13-$KAFKA_VERSION.tgz
cd $KAFKA_ROOT/libs
wget https://github.com/aws/aws-msk-iam-auth/releases/download/v2.3.2/aws-msk-iam-auth-2.3.2-all.jar
echo 'export CLASSPATH=$KAFKA_ROOT/libs/aws-msk-iam-auth-2.3.2-all.jar' >> ~/.bashrc
cd /home/ec2-user
BOOTSTRAP_SERVERS=$(aws kafka get-bootstrap-brokers --cluster-arn ${MSK_CLUSTER_ARN} --region ${AWS_REGION} | jq -r '.BootstrapBrokerStringSaslIam')
export BOOTSTRAP_SERVERS
echo "export BOOTSTRAP_SERVERS=${BOOTSTRAP_SERVERS}" >> ~/.bashrc
sleep 5
source ~/.bashrc
aws ssm put-parameter --name "${MSK_CLUSTER_BROKER_URL_PARAM_NAME}" --value "$BOOTSTRAP_SERVERS" --type "String" --overwrite --region "${AWS_REGION}"
ZOOKEEPER_CONNECTION=$(aws kafka describe-cluster --cluster-arn ${MSK_CLUSTER_ARN} --region ${AWS_REGION} | jq -r '.ClusterInfo.ZookeeperConnectString')
export ZOOKEEPER_CONNECTION
echo "export ZOOKEEPER_CONNECTION=${ZOOKEEPER_CONNECTION}" >> ~/.bashrc
cat <<EOF > /home/ec2-user/client_sasl.properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
EOF
echo 'export KAFKA_HEAP_OPTS="-Xmx512M -Xms512M"' >> ~/.bashrc
AZ_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=${VPC_ID}" --region ${AWS_REGION} | jq -r '.Subnets[].AvailabilityZoneId' | sort -u | tr "\n" ",")
export AZ_IDS
echo "export AZ_IDS=${AZ_IDS}" >> ~/.bashrc
echo "export AWS_REGION=${AWS_REGION}" >> ~/.bashrc
echo "export EMR_BUCKET_NAME=${EMR_BUCKET_NAME}" >> ~/.bashrc
echo "export AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}" >> ~/.bashrc
sleep 5
source ~/.bashrc
aws ssm put-parameter --name "${AZ_IDS_PARAM_NAME}" --value "$AZ_IDS" --type "${AZ_IDS_PARAM_TYPE}" --overwrite --region "${AWS_REGION}"
$KAFKA_ROOT/bin/kafka-topics.sh --bootstrap-server $BOOTSTRAP_SERVERS --command-config /home/ec2-user/client_sasl.properties --create --topic ${MSK_TOPIC_NAME_1} --replication-factor 2
$KAFKA_ROOT/bin/kafka-topics.sh --bootstrap-server $BOOTSTRAP_SERVERS --command-config /home/ec2-user/client_sasl.properties --create --topic ${MSK_TOPIC_NAME_2} --replication-factor 2
$KAFKA_ROOT/bin/kafka-topics.sh --bootstrap-server $BOOTSTRAP_SERVERS --command-config /home/ec2-user/client_sasl.properties --create --topic ${MSK_TOPIC_NAME_3} --replication-factor 2
$KAFKA_ROOT/bin/kafka-topics.sh --bootstrap-server $BOOTSTRAP_SERVERS --command-config /home/ec2-user/client_sasl.properties --create --topic ${MSK_TOPIC_NAME_4} --replication-factor 2
$KAFKA_ROOT/bin/kafka-topics.sh --bootstrap-server $BOOTSTRAP_SERVERS --command-config /home/ec2-user/client_sasl.properties --create --topic ${MSK_TOPIC_NAME_5} --replication-factor 2
$KAFKA_ROOT/bin/kafka-topics.sh --bootstrap-server $BOOTSTRAP_SERVERS --command-config /home/ec2-user/client_sasl.properties --create --topic ${MSK_TOPIC_NAME_6} --replication-factor 2
$KAFKA_ROOT/bin/kafka-topics.sh --bootstrap-server $BOOTSTRAP_SERVERS --list --command-config ./client_sasl.properties
sed -n '/^export KAFKA_ROOT/,$p' ~/.bashrc >> /home/ec2-user/.my_custom_env
pip install confluent-kafka aws-msk-iam-sasl-signer-python
pip install fastavro