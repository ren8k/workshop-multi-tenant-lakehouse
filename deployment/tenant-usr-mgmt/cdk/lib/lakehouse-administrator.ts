// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { Construct } from 'constructs';
import * as lakeformation from 'aws-cdk-lib/aws-lakeformation';

export interface LakehouseAdministratorProps {
  /**
   * The IAM roles to be granted lakehouse administrator permissions
   */
  administratorRoleArns: string[];
  
}

export class LakehouseAdministrator extends Construct {
    public readonly administratorRoles: string[];
    public readonly dataLakeSettings: lakeformation.CfnDataLakeSettings;

    constructor(scope: Construct, id: string, props: LakehouseAdministratorProps) {
      super(scope, id);

      this.administratorRoles = props.administratorRoleArns;

      // Configure Lake Formation data lake settings to add all roles as administrators
      this.dataLakeSettings = new lakeformation.CfnDataLakeSettings(this, 'DataLakeSettings', {
        admins: this.administratorRoles.map(roleArn => ({
          dataLakePrincipalIdentifier: roleArn
        }))
      });
  }
}
