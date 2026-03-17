import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

interface ApiStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
  appSecurityGroup: ec2.SecurityGroup;
  dbSecret: secretsmanager.ISecret;
}

export class ApiStack extends cdk.Stack {
  public readonly ecrRepository: ecr.Repository;
  public readonly ecsCluster: ecs.Cluster;
  public readonly ecsService: ecs.FargateService;
  public readonly albDnsName: string;

  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id, props);

    // ── ECR repository ──────────────────────────────────────────────────────
    this.ecrRepository = new ecr.Repository(this, 'ApiRepository', {
      repositoryName: 'metabookly-api',
      // Keep last 10 images to allow rollback; prune untagged images after 1 day
      lifecycleRules: [
        {
          description: 'Keep last 10 tagged images',
          maxImageCount: 10,
          tagStatus: ecr.TagStatus.TAGGED,
          tagPrefixList: ['sha-'],
        },
        {
          description: 'Remove untagged images after 1 day',
          maxImageAge: cdk.Duration.days(1),
          tagStatus: ecr.TagStatus.UNTAGGED,
        },
      ],
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // ── ECS cluster ─────────────────────────────────────────────────────────
    this.ecsCluster = new ecs.Cluster(this, 'MetabooklyCluster', {
      clusterName: 'metabookly',
      vpc: props.vpc,
      // containerInsightsV2 omitted — default is disabled, saves ~$3/month
    });

    // ── CloudWatch log group ─────────────────────────────────────────────────
    const logGroup = new logs.LogGroup(this, 'ApiLogGroup', {
      logGroupName: '/metabookly/api',
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // ── Task IAM role ────────────────────────────────────────────────────────
    const taskRole = new iam.Role(this, 'ApiTaskRole', {
      roleName: 'metabookly-api-task',
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });

    // Read DB credentials + retailer credentials from Secrets Manager
    taskRole.addToPolicy(new iam.PolicyStatement({
      actions: ['secretsmanager:GetSecretValue'],
      resources: [
        props.dbSecret.secretArn,
        `arn:aws:secretsmanager:${this.region}:${this.account}:secret:/metabookly/*`,
      ],
    }));

    // Read ONIX feeds, write/read assets
    taskRole.addToPolicy(new iam.PolicyStatement({
      actions: ['s3:GetObject', 's3:PutObject', 's3:DeleteObject', 's3:ListBucket'],
      resources: [
        `arn:aws:s3:::metabookly-onix-feeds-${this.account}`,
        `arn:aws:s3:::metabookly-onix-feeds-${this.account}/*`,
        `arn:aws:s3:::metabookly-assets-${this.account}`,
        `arn:aws:s3:::metabookly-assets-${this.account}/*`,
      ],
    }));

    // ── Task definition ──────────────────────────────────────────────────────
    // 256 CPU / 512 MB — cheapest Fargate tier, ~$7/month in eu-west-2
    const taskDefinition = new ecs.FargateTaskDefinition(this, 'ApiTaskDef', {
      family: 'metabookly-api',
      cpu: 256,
      memoryLimitMiB: 512,
      taskRole,
      // Execution role is auto-created (pulls from ECR, writes to CloudWatch)
    });

    taskDefinition.addContainer('api', {
      image: ecs.ContainerImage.fromEcrRepository(this.ecrRepository, 'latest'),
      containerName: 'api',
      portMappings: [{ containerPort: 8000, protocol: ecs.Protocol.TCP }],
      environment: {
        ENVIRONMENT: 'mvp',
        AWS_REGION: this.region,
        AWS_ACCOUNT_ID: this.account,
        COGNITO_USER_POOL_ID: 'eu-west-2_Hb5mR6Ugo',
        COGNITO_CLIENT_ID: '7khfisn3jq5iv9r1k27sgm5clt',
        ONIX_BUCKET_NAME: `metabookly-onix-feeds-${this.account}`,
        ASSETS_BUCKET_NAME: `metabookly-assets-${this.account}`,
        // DATABASE_URL left unset — config.py fetches from Secrets Manager
      },
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'api',
        logGroup,
      }),
      healthCheck: {
        command: ['CMD-SHELL', 'curl -f http://localhost:8000/health || exit 1'],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        retries: 3,
        startPeriod: cdk.Duration.seconds(60),  // Time for alembic migrate on cold start
      },
    });

    // ── ALB security group — internet-facing ────────────────────────────────
    const albSecurityGroup = new ec2.SecurityGroup(this, 'AlbSecurityGroup', {
      vpc: props.vpc,
      description: 'Allow HTTP traffic to the API ALB',
      allowAllOutbound: true,
    });
    albSecurityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(80), 'HTTP from internet');

    // Allow ALB → ECS on port 8000
    props.appSecurityGroup.addIngressRule(
      albSecurityGroup,
      ec2.Port.tcp(8000),
      'Allow ALB to reach API containers'
    );

    // ── Application Load Balancer ────────────────────────────────────────────
    const alb = new elbv2.ApplicationLoadBalancer(this, 'ApiAlb', {
      loadBalancerName: 'metabookly-api',
      vpc: props.vpc,
      internetFacing: true,
      securityGroup: albSecurityGroup,
      vpcSubnets: { subnetType: ec2.SubnetType.PUBLIC },
    });

    const listener = alb.addListener('HttpListener', {
      port: 80,
      open: false,  // already handled by security group
    });

    // ── ECS service ──────────────────────────────────────────────────────────
    this.ecsService = new ecs.FargateService(this, 'ApiService', {
      serviceName: 'metabookly-api',
      cluster: this.ecsCluster,
      taskDefinition,
      desiredCount: 1,
      securityGroups: [props.appSecurityGroup],
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      assignPublicIp: false,
      // Allow replacing tasks immediately (no 100% min healthy for MVP cost savings)
      minHealthyPercent: 0,
      maxHealthyPercent: 200,
    });

    listener.addTargets('ApiTargets', {
      targetGroupName: 'metabookly-api',
      port: 8000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targets: [this.ecsService],
      healthCheck: {
        path: '/health',
        interval: cdk.Duration.seconds(30),
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 3,
      },
    });

    // ── Outputs ──────────────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'EcrRepositoryUri', {
      value: this.ecrRepository.repositoryUri,
      exportName: 'MetabooklyEcrRepositoryUri',
    });

    new cdk.CfnOutput(this, 'EcsClusterName', {
      value: this.ecsCluster.clusterName,
      exportName: 'MetabooklyEcsClusterName',
    });

    new cdk.CfnOutput(this, 'EcsServiceName', {
      value: this.ecsService.serviceName,
      exportName: 'MetabooklyEcsServiceName',
    });

    new cdk.CfnOutput(this, 'ApiUrl', {
      value: `http://${alb.loadBalancerDnsName}`,
      exportName: 'MetabooklyApiUrl',
    });
  }
}
