// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { aws_cognito, StackProps, Stack, RemovalPolicy } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { IdentityDetails } from '../interfaces/identity-details';
import * as iam from 'aws-cdk-lib/aws-iam';

export class IdentityProviderLakeFormation extends Construct {
  public readonly identityDetails: IdentityDetails;
  
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id);

    // Resources
    const tenantUserPool = new aws_cognito.UserPool(this, 'tenantUserPool', {
      autoVerify: { email: true },
      accountRecovery: aws_cognito.AccountRecovery.EMAIL_ONLY,
      userPoolName: 'LakehouseTenantsUserPool',
      advancedSecurityMode: aws_cognito.AdvancedSecurityMode.ENFORCED,
      removalPolicy: RemovalPolicy.DESTROY,
      passwordPolicy: {
        minLength: 8,
        requireDigits: true,
        requireSymbols: true,
        requireUppercase: true
      },
      standardAttributes: {
        email: {
          required: true,
          mutable: true,
        },
      },
      customAttributes: {
        tenantId: new aws_cognito.StringAttribute({
          mutable: true,
        }),
        userRole: new aws_cognito.StringAttribute({
          mutable: true,
        }),
        tenantTier: new aws_cognito.StringAttribute({
          mutable: true,
        }),
      },
    });

    const writeAttributes = new aws_cognito.ClientAttributes()
      .withStandardAttributes({ email: true })
      .withCustomAttributes('tenantId', 'userRole', 'tenantTier');

    const tenantUserPoolClient = new aws_cognito.UserPoolClient(this, 'tenantUserPoolClient', {
      userPool: tenantUserPool,
      generateSecret: false,
      authFlows: {
        userPassword: true,
        adminUserPassword: true,
        userSrp: true,
        custom: false,
      },
      writeAttributes: writeAttributes,
      readAttributes: new aws_cognito.ClientAttributes()
        .withStandardAttributes({ email: true })
        .withCustomAttributes('tenantId', 'userRole', 'tenantTier'),
      oAuth: {
        scopes: [
          aws_cognito.OAuthScope.EMAIL,
          aws_cognito.OAuthScope.OPENID,
          aws_cognito.OAuthScope.PROFILE,
        ],
        flows: {
          authorizationCodeGrant: true,
          implicitCodeGrant: true,
        },
      },
    });

    const cognitoIdentityPool = new aws_cognito.CfnIdentityPool(this, 'CognitoIdentityPool', {
      identityPoolName: 'LakehouseTenantsIdentityPool',
      allowUnauthenticatedIdentities: false,
      cognitoIdentityProviders: [
        {
          clientId: tenantUserPoolClient.userPoolClientId,
          providerName: tenantUserPool.userPoolProviderName,
          serverSideTokenCheck: true,
        },
      ],
    });

    // Enhanced IAM role for Lake Formation access with session tags
    const authenticatedPooledUserRole = new iam.CfnRole(this, 'AuthenticatedUserRole', {
      roleName: 'lakehouse-tenant-authenticated-user-role',
      assumeRolePolicyDocument: {
        Version: '2012-10-17',
        Statement: [
          {
            Effect: 'Allow',
            Principal: {
              Federated: 'cognito-identity.amazonaws.com',
            },
            Action: 'sts:AssumeRoleWithWebIdentity',
            Condition: {
              'ForAnyValue:StringLike': {
                'cognito-identity.amazonaws.com:amr': 'authenticated',
              },
              StringEquals: {
                'cognito-identity.amazonaws.com:aud': `${cognitoIdentityPool.attrId}`
              }
            },
          },
          {
            Effect: 'Allow',
            Principal: {
              Federated: 'cognito-identity.amazonaws.com',
            },
            Action: 'sts:TagSession',
            Condition: {
              'ForAnyValue:StringLike': {
                'cognito-identity.amazonaws.com:amr': 'authenticated',
              },
              StringEquals: {
                'cognito-identity.amazonaws.com:aud': `${cognitoIdentityPool.attrId}`
              }
            },
          },
        ]
      },
      managedPolicyArns:[
        "arn:aws:iam::aws:policy/AmazonAthenaFullAccess"
      ]
    });

    // Identity Pool Role Attachment
    const cognitoIdentityPoolRoleAttachement = new aws_cognito.CfnIdentityPoolRoleAttachment(this, 'CognitoIdentityPoolRoleAttachement', {
      identityPoolId: cognitoIdentityPool.attrId,
      roles: {
        authenticated: authenticatedPooledUserRole.attrArn,
      },
    });

    // Principal Tag Mapping - Critical for Lake Formation principal by attribute
    const pooledUserPrincipalTagMapping = new aws_cognito.CfnIdentityPoolPrincipalTag(this, 'PooledUserPrincipalTagMapping', {
      identityPoolId: cognitoIdentityPool.attrId,
      identityProviderName: tenantUserPool.userPoolProviderName,
      useDefaults: false,
      principalTags: {
        tenantId: 'custom:tenantId',
        userRole: 'custom:userRole',
        tenantTier: 'custom:tenantTier',
      },
    });

    // Ensure the principal tag mapping is created after the identity pool
    pooledUserPrincipalTagMapping.addDependency(cognitoIdentityPool);
    pooledUserPrincipalTagMapping.addDependency(cognitoIdentityPoolRoleAttachement);

    this.identityDetails = {
      name: 'CognitoLakeFormation',
      details: {
        userPoolId: tenantUserPool.userPoolId,
        userPoolArn: tenantUserPool.userPoolArn,
        appClientId: tenantUserPoolClient.userPoolClientId,
        identityPoolId: cognitoIdentityPool.attrId,
        authenticatedRoleArn: authenticatedPooledUserRole.attrArn
      },
    };
  }
}
