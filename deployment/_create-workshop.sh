#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

install_dependencies(){
#docker
#PATH=$PATH:/home/workshop_user/.local/bin
#export PATH
  dnf update -y
  sudo dnf install nodejs20 -y
  mkdir ~/.npm-global
  npm config set prefix '~/.npm-global'
  echo 'PATH=$PATH:~/.npm-global/bin' >> ~/.bashrc
  echo 'export PATH' >> ~/.bashrc
  source ~/.bashrc

  npm install -g aws-cdk

  npm install -g typescript

  sudo dnf install -y jq

  #python

  sudo dnf install python3.12 -y
  sudo python3.12 -m ensurepip --upgrade
  echo 'alias python='/usr/bin/python3.12'' >> ~/.bashrc
  source ~/.bashrc


}


increase_disksize(){

# Specify the desired volume size in GiB as a command line argument. If not specified, default to 50 GiB.
SIZE=50

TOKEN=$(curl --request PUT "http://169.254.169.254/latest/api/token" --header "X-aws-ec2-metadata-token-ttl-seconds: 3600")

# Get the ID of the environment host Amazon EC2 instance.
INSTANCEID=$(curl http://169.254.169.254/latest/meta-data/instance-id --header "X-aws-ec2-metadata-token: $TOKEN")
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone --header "X-aws-ec2-metadata-token: $TOKEN" | sed 's/\(.*\)[a-z]/\1/')

# Get the ID of the Amazon EBS volume associated with the instance.
VOLUMEID=$(aws ec2 describe-instances \
  --instance-id $INSTANCEID \
  --query "Reservations[0].Instances[0].BlockDeviceMappings[0].Ebs.VolumeId" \
  --output text \
  --region $REGION)

# Resize the EBS volume.
aws ec2 modify-volume --volume-id $VOLUMEID --size $SIZE

# Wait for the resize to finish.
while [ \
  "$(aws ec2 describe-volumes-modifications \
    --volume-id $VOLUMEID \
    --filters Name=modification-state,Values="optimizing","completed" \
    --query "length(VolumesModifications)"\
    --output text)" != "1" ]; do
    sleep 1
done

#Check if we're on an NVMe filesystem
if [[ -e "/dev/xvda" && $(readlink -f /dev/xvda) = "/dev/xvda" ]]
then
  # Rewrite the partition table so that the partition takes up all the space that it can.
  sudo growpart /dev/xvda 1

  # Expand the size of the file system.
  # Check if we're on AL2
  STR=$(cat /etc/os-release)
  SUB="VERSION_ID=\"2023\""
  if [[ "$STR" == *"$SUB"* ]]
  then
    sudo xfs_growfs -d /
  else
    sudo resize2fs /dev/xvda1
  fi

else
  # Rewrite the partition table so that the partition takes up all the space that it can.
  sudo growpart /dev/nvme0n1 1

  # Expand the size of the file system.
  # Check if we're on AL2
  STR=$(cat /etc/os-release)
  SUB="VERSION_ID=\"2023\""
  if [[ "$STR" == *"$SUB"* ]]
  then
    sudo xfs_growfs -d /
  else
    sudo resize2fs /dev/nvme0n1p1
  fi
fi

}


install_tenantusermanagement()
{
    cd ~/$REPO_NAME/deployment/tenant-usr-mgmt/cdk

    npm install typescript
    npm install aws-cdk
    cdk bootstrap
    sleep 30
    
    npm install
    npm run build

    cdk deploy 'LakehouseTenantUserManagementStack' --require-approval never --concurrency 10 --asset-parallelism true

    cdk deploy 'LakeformationAdminStack' --require-approval never --concurrency 10 --asset-parallelism true

    
    cd ~/$REPO_NAME/deployment/tenant-usr-mgmt/scripts
    ./create_tenant_users.sh
    #./ingestion_lakehouse_permissions.sh
}


install_ingestion_services(){

    cd ~/$REPO_NAME/data_ingestion
    alias pip=pip3.12
    python3 -m venv .venv
    source .venv/bin/activate
    
    cd ./cdk

    pip install -r requirements.txt

    npm install typescript
    npm install aws-cdk

    cdk bootstrap
    sleep 60

    #export CDK_PARAM_AVP_STORE_ID=$(aws cloudformation describe-stacks --stack-name TenantAuthorizationStack --query "Stacks[0].Outputs[?OutputKey=='PolicyStoreId'].OutputValue" --output text 2> out.txt)
    #echo $CDK_PARAM_AVP_STORE_ID
    #export CDK_PARAM_AVP_NAMESPACE=$(aws cloudformation describe-stacks --stack-name TenantAuthorizationStack --query "Stacks[0].Outputs[?OutputKey=='AvpNamespace'].OutputValue" --output text 2> out.txt)
    #echo $CDK_PARAM_AVP_NAMESPACE
    
    cdk deploy --all --require-approval never --concurrency 10 --asset-parallelism true
    
}

install_security_agent(){
    cd ~/$REPO_NAME/deployment/security-agent/backend
    
    # Install SAM CLI if not present
    sudo pip3.12 install aws-sam-cli
    
    # Build the security agent backend
    chmod +x ./build.sh
    ./build.sh
    
    # Deploy the security agent backend
    chmod +x ./deploy.sh
    ./deploy.sh
    
    # Deploy the security agent frontend
    cd ../frontend
    chmod +x ./deploy-frontend.sh
    ./deploy-frontend.sh
}