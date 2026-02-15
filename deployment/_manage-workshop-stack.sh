#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

create_workshop() {
    
    get_vscodeserver_id
    
    echo "Waiting for " $VSSERVER_ID
    aws ec2 start-instances --instance-ids "$VSSERVER_ID"
    aws ec2 wait instance-status-ok --instance-ids "$VSSERVER_ID"
    echo $VSSERVER_ID "ready"

    ##TODO
    #replace_instance_profile $BUILD_VSCODE_SERVER_PROFILE_PARAMETER_NAME
    
    run_ssm_command ". ~/.bashrc"
    run_ssm_command "cd ~ ; aws s3 cp s3://${ASSETS_ZIP_PATH} asset.zip ; unzip -o asset.zip"
    run_ssm_command "cd ~/$REPO_NAME && chmod +x . -R"
    run_ssm_command "cd ~/$REPO_NAME/deployment && ./create-workshop.sh | tee .ws-create.log"

    #replace_instance_profile $PARTICIPANT_VSCODE_SERVER_PROFILE_PARAMETER_NAME


    get_tenantload_generator_id
    
    echo "Waiting for " $TENANT_LOAD_SERVER_ID
    aws ec2 start-instances --instance-ids "$TENANT_LOAD_SERVER_ID"
    aws ec2 wait instance-status-ok --instance-ids "$TENANT_LOAD_SERVER_ID"
    echo $TENANT_LOAD_SERVER_ID "ready"

    run_ssm_command2 ". ~/.bashrc"
    run_ssm_command2 "cd ~ ; aws s3 cp s3://${ASSETS_ZIP_PATH} asset.zip ; unzip -o asset.zip"
    #run_ssm_command "cd ~/$REPO_NAME && git config core.filemode false"
    run_ssm_command2 "cd ~/$REPO_NAME && chmod +x . -R"
    run_ssm_command2 "cd ~/$REPO_NAME && rm -rf .git"



    if [ "$IS_WORKSHOP_STUDIO_ENV" = "yes" ]; then
        echo "Adding participant role as Lake Formation admin..."
        
        # Get current Lake Formation settings
        CURRENT_ADMINS=$(aws lakeformation get-data-lake-settings --query 'DataLakeSettings.DataLakeAdmins' --output json)
        
        # Create new admin entry
        NEW_ADMIN='{"DataLakePrincipalIdentifier": "'"$PARTICIPANT_ROLE_ARN"'"}'
        
        # Merge existing admins with new admin using jq
        UPDATED_ADMINS=$(echo "$CURRENT_ADMINS" | jq '. + ['"$NEW_ADMIN"']')
        
        # Get other current settings to preserve them
        CURRENT_SETTINGS=$(aws lakeformation get-data-lake-settings --query 'DataLakeSettings' --output json)
        
        # Update the DataLakeAdmins in the settings
        UPDATED_SETTINGS=$(echo "$CURRENT_SETTINGS" | jq '.DataLakeAdmins = '"$UPDATED_ADMINS"'')
        
        # Apply the updated settings
        aws lakeformation put-data-lake-settings --data-lake-settings "$UPDATED_SETTINGS"
        
        if [ $? -eq 0 ]; then
            echo "Successfully added $PARTICIPANT_ASSUMED_ROLE_ARN as Lake Formation admin"
        else
            echo "Failed to add Lake Formation admin"
            exit 1
        fi
    else
        echo "Not in Workshop Studio environment, skipping Lake Formation admin setup"
    fi
    
}


delete_workshop() {
    ##TODO
    ##./delete-workshop.sh
    echo "##TODO"
}
