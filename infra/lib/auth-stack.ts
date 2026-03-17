import * as cdk from 'aws-cdk-lib';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import { Construct } from 'constructs';

export class AuthStack extends cdk.Stack {
  public readonly retailerUserPool: cognito.UserPool;
  public readonly retailerUserPoolClient: cognito.UserPoolClient;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Retailer user pool — book retailers who use the platform to discover and order
    this.retailerUserPool = new cognito.UserPool(this, 'RetailerUserPool', {
      userPoolName: 'metabookly-retailers',
      selfSignUpEnabled: false,  // Retailers are invited, not self-signup
      signInAliases: {
        email: true,
      },
      autoVerify: {
        email: true,
      },
      standardAttributes: {
        email: { required: true, mutable: true },
        givenName: { required: true, mutable: true },
        familyName: { required: true, mutable: true },
      },
      customAttributes: {
        companyName: new cognito.StringAttribute({ mutable: true }),
        san: new cognito.StringAttribute({ mutable: true }),  // Standard Address Number
        country: new cognito.StringAttribute({ mutable: true }),
      },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: false,
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // App client for the web application
    this.retailerUserPoolClient = this.retailerUserPool.addClient('WebClient', {
      userPoolClientName: 'metabookly-web',
      authFlows: {
        userSrp: true,
        userPassword: true,  // Enabled for server-side NextAuth CredentialsProvider flow
      },
      oAuth: {
        flows: {
          authorizationCodeGrant: true,
        },
        scopes: [cognito.OAuthScope.EMAIL, cognito.OAuthScope.OPENID, cognito.OAuthScope.PROFILE],
        callbackUrls: ['http://localhost:3000/api/auth/callback/cognito'],  // Update with production URL later
        logoutUrls: ['http://localhost:3000'],
      },
      preventUserExistenceErrors: true,
    });

    // Groups for role-based access
    new cognito.CfnUserPoolGroup(this, 'RetailerGroup', {
      userPoolId: this.retailerUserPool.userPoolId,
      groupName: 'retailers',
      description: 'Book retailers who can browse catalog and place orders',
    });

    new cognito.CfnUserPoolGroup(this, 'AdminGroup', {
      userPoolId: this.retailerUserPool.userPoolId,
      groupName: 'admins',
      description: 'Metabookly platform administrators',
    });

    new cdk.CfnOutput(this, 'UserPoolId', {
      value: this.retailerUserPool.userPoolId,
      exportName: 'MetabooklyUserPoolId',
    });

    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: this.retailerUserPoolClient.userPoolClientId,
      exportName: 'MetabooklyUserPoolClientId',
    });
  }
}
