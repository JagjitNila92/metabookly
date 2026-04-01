import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as apprunner from 'aws-cdk-lib/aws-apprunner';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

interface ApiStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
  appSecurityGroup: ec2.SecurityGroup;
  dbSecret: secretsmanager.ISecret;
  ecrRepository: ecr.Repository;
}

export class ApiStack extends cdk.Stack {
  public readonly appRunnerServiceArn: string;
  public readonly appRunnerServiceUrl: string;

  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id, props);

    // ── CloudWatch log group ─────────────────────────────────────────────────
    const logGroup = new logs.LogGroup(this, 'ApiLogGroup', {
      logGroupName: '/metabookly/api',
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // ── Access role — App Runner uses this to pull images from ECR ───────────
    const accessRole = new iam.Role(this, 'AppRunnerAccessRole', {
      roleName: 'metabookly-apprunner-access',
      assumedBy: new iam.ServicePrincipal('build.apprunner.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'service-role/AWSAppRunnerServicePolicyForECRAccess'
        ),
      ],
    });

    // ── Instance role — runtime permissions for the running container ─────────
    const instanceRole = new iam.Role(this, 'AppRunnerInstanceRole', {
      roleName: 'metabookly-apprunner-instance',
      assumedBy: new iam.ServicePrincipal('tasks.apprunner.amazonaws.com'),
    });

    // Secrets Manager: DB credentials + per-retailer distributor credentials
    instanceRole.addToPolicy(new iam.PolicyStatement({
      actions: ['secretsmanager:GetSecretValue'],
      resources: [
        props.dbSecret.secretArn,
        `arn:aws:secretsmanager:${this.region}:${this.account}:secret:/metabookly/*`,
      ],
    }));

    // S3: ONIX feed ingestion + asset storage
    instanceRole.addToPolicy(new iam.PolicyStatement({
      actions: ['s3:GetObject', 's3:PutObject', 's3:DeleteObject', 's3:ListBucket'],
      resources: [
        `arn:aws:s3:::metabookly-onix-feeds-${this.account}`,
        `arn:aws:s3:::metabookly-onix-feeds-${this.account}/*`,
        `arn:aws:s3:::metabookly-assets-${this.account}`,
        `arn:aws:s3:::metabookly-assets-${this.account}/*`,
      ],
    }));

    // CloudWatch Logs
    instanceRole.addToPolicy(new iam.PolicyStatement({
      actions: ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
      resources: [logGroup.logGroupArn, `${logGroup.logGroupArn}:*`],
    }));

    // ── VPC connector — App Runner egress into private subnets to reach Aurora
    const vpcConnector = new apprunner.CfnVpcConnector(this, 'VpcConnector', {
      vpcConnectorName: 'metabookly-api',
      subnets: props.vpc.selectSubnets({
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      }).subnetIds,
      securityGroups: [props.appSecurityGroup.securityGroupId],
    });

    // ── App Runner service ────────────────────────────────────────────────────
    // 0.25 vCPU / 0.5 GB — cheapest tier, suitable for MVP traffic
    // autoDeploymentsEnabled: false — CI/CD triggers deploys explicitly via start-deployment
    const service = new apprunner.CfnService(this, 'ApiService', {
      serviceName: 'metabookly-api',
      sourceConfiguration: {
        authenticationConfiguration: {
          accessRoleArn: accessRole.roleArn,
        },
        autoDeploymentsEnabled: false,
        imageRepository: {
          imageRepositoryType: 'ECR',
          imageIdentifier: `${props.ecrRepository.repositoryUri}:latest`,
          imageConfiguration: {
            port: '8000',
            runtimeEnvironmentVariables: [
              { name: 'ENVIRONMENT', value: 'mvp' },
              { name: 'AWS_REGION', value: this.region },
              { name: 'AWS_ACCOUNT_ID', value: this.account },
              { name: 'COGNITO_USER_POOL_ID', value: 'eu-west-2_Hb5mR6Ugo' },
              { name: 'COGNITO_CLIENT_ID', value: '7khfisn3jq5iv9r1k27sgm5clt' },
              { name: 'ONIX_BUCKET_NAME', value: `metabookly-onix-feeds-${this.account}` },
              { name: 'ASSETS_BUCKET_NAME', value: `metabookly-assets-${this.account}` },
            ],
          },
        },
      },
      instanceConfiguration: {
        cpu: '0.25 vCPU',
        memory: '0.5 GB',
        instanceRoleArn: instanceRole.roleArn,
      },
      networkConfiguration: {
        egressConfiguration: {
          egressType: 'VPC',
          vpcConnectorArn: vpcConnector.attrVpcConnectorArn,
        },
        ingressConfiguration: {
          isPubliclyAccessible: true,
        },
      },
      healthCheckConfiguration: {
        protocol: 'HTTP',
        path: '/health',
        interval: 20,  // App Runner max is 20s
        timeout: 5,
        healthyThreshold: 2,
        unhealthyThreshold: 3,
      },
    });

    this.appRunnerServiceArn = service.attrServiceArn;
    this.appRunnerServiceUrl = service.attrServiceUrl;

    // ── GitHub Actions IAM user — permissions to trigger App Runner deploys ──
    // User was created manually; imported here so permissions are managed as code.
    const githubActionsUser = iam.User.fromUserName(
      this, 'GithubActionsUser', 'metabookly-github-actions'
    );

    githubActionsUser.addToPrincipalPolicy(new iam.PolicyStatement({
      sid: 'AppRunnerDeploy',
      actions: [
        'apprunner:ListServices',
        'apprunner:StartDeployment',
        'apprunner:ListOperations',
      ],
      // App Runner list/trigger actions don't support resource-level restrictions
      resources: ['*'],
    }));

    // ── Outputs ──────────────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'AppRunnerServiceArn', {
      value: service.attrServiceArn,
      exportName: 'MetabooklyAppRunnerServiceArn',
    });

    new cdk.CfnOutput(this, 'ApiUrl', {
      value: `https://${service.attrServiceUrl}`,
      exportName: 'MetabooklyApiUrl',
    });
  }
}
