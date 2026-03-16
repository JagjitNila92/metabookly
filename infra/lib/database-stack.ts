import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

interface DatabaseStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
  dbSecurityGroup: ec2.SecurityGroup;
}

export class DatabaseStack extends cdk.Stack {
  public readonly cluster: rds.DatabaseCluster;
  public readonly secret: secretsmanager.ISecret;

  constructor(scope: Construct, id: string, props: DatabaseStackProps) {
    super(scope, id, props);

    // Aurora Serverless v2 PostgreSQL
    // Scales from 0.5 ACU (min) to 4 ACU (max) — cost-effective for MVP
    // 1 ACU ≈ 2GB RAM, ~$0.12/ACU-hour in eu-west-2
    this.cluster = new rds.DatabaseCluster(this, 'MetabooklyDatabase', {
      engine: rds.DatabaseClusterEngine.auroraPostgres({
        version: rds.AuroraPostgresEngineVersion.VER_16_4,
      }),
      serverlessV2MinCapacity: 0.5,
      serverlessV2MaxCapacity: 4,
      writer: rds.ClusterInstance.serverlessV2('Writer'),
      readers: [],  // No reader for MVP — add when read traffic grows
      vpc: props.vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
      },
      securityGroups: [props.dbSecurityGroup],
      defaultDatabaseName: 'metabookly',
      credentials: rds.Credentials.fromGeneratedSecret('metabookly_admin', {
        secretName: '/metabookly/database/master-credentials',
      }),
      backup: {
        retention: cdk.Duration.days(7),
        preferredWindow: '02:00-03:00',
      },
      storageEncrypted: true,
      deletionProtection: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    this.secret = this.cluster.secret!;

    new cdk.CfnOutput(this, 'DatabaseEndpoint', {
      value: this.cluster.clusterEndpoint.hostname,
      exportName: 'MetabooklyDbEndpoint',
    });

    new cdk.CfnOutput(this, 'DatabaseSecretArn', {
      value: this.secret.secretArn,
      exportName: 'MetabooklyDbSecretArn',
    });
  }
}
