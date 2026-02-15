// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { Stack, StackProps, CfnOutput } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { IdentityProviderLakeFormation } from './identity-provider-lakeformation';


export class TenantUserManagementStack extends Stack {

  public readonly userPoolArn: string;
  public readonly authorizerFunctionArn: string;

  constructor(scope: Construct, id: string, props: StackProps) {
    super(scope, id, props);
    
    const identityProvider = new IdentityProviderLakeFormation(this, 'IdentityProvider');

    this.userPoolArn = identityProvider.identityDetails.details['userPoolArn']

    const identityDetails = identityProvider.identityDetails

    new CfnOutput(this, 'LakehouseTenantIdpName', {
      value: identityProvider.identityDetails.name,
      exportName: 'LakehouseTenantIdpName',
    });

    new CfnOutput(this, 'LakehouseTenantUserpoolId', {
      value: identityProvider.identityDetails.details['userPoolId'],
      exportName: 'LakehouseTenantUserpoolId',
    });

    new CfnOutput(this, 'LakehouseTenantUserpoolArn', {
      value: identityProvider.identityDetails.details['userPoolArn'],
      exportName: 'LakehouseTenantUserpoolArn',
    });

    new CfnOutput(this, 'LakehouseUserPoolClientId', {
      value: identityProvider.identityDetails.details['appClientId'],
      exportName: 'LakehouseUserPoolClientId',
    });

    new CfnOutput(this, 'LakehouseIdentityPoolId', {
      value: identityProvider.identityDetails.details['identityPoolId'],
      exportName: 'LakehouseIdentityPoolId',
    });
    
    //new TenantUserManagementStackNag(this, 'TenantUserManagementStackNag') */
    
  }
}