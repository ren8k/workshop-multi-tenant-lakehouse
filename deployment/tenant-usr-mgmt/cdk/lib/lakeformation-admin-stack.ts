// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { Stack, StackProps, CfnOutput } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import {LakehouseAdministrator} from './lakehouse-administrator';


export class LakeformationAdminStack extends Stack {

  public readonly userPoolArn: string;
  public readonly authorizerFunctionArn: string;

  constructor(scope: Construct, id: string, props: StackProps) {
    super(scope, id, props);
    

    new LakehouseAdministrator(this,'LakeFormationAdmin',{
      administratorRoleArns: [
        `arn:aws:iam::${Stack.of(this).account}:role/CodeEditorInstanceBootstrapRole`,
        `arn:aws:iam::${Stack.of(this).account}:role/awsmtlkh-test-SaaSApp-ec2MskClusterRole`
        //`arn:aws:iam::${Stack.of(this).account}:role/LakeHouseCodeBuildRole`
      ]
    })

    //new TenantUserManagementStackNag(this, 'TenantUserManagementStackNag') */
    
  }
}