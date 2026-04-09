import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';

export class NetworkStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;
  public readonly dbSecurityGroup: ec2.SecurityGroup;
  public readonly appSecurityGroup: ec2.SecurityGroup;

  // Reserved for post-MVP:
  // public readonly searchSecurityGroup  — OpenSearch (when added)
  // public readonly cacheSecurityGroup   — ElastiCache Redis (when added)

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // VPC with 2 AZs (minimum for Aurora), 1 NAT instance (t4g.nano ~$3/month vs NAT GW ~$35/month)
    this.vpc = new ec2.Vpc(this, 'MetabooklyVpc', {
      maxAzs: 2,
      natGateways: 1,
      natGatewayProvider: ec2.NatProvider.instanceV2({
        instanceType: ec2.InstanceType.of(ec2.InstanceClass.T4G, ec2.InstanceSize.NANO),
      }),
      subnetConfiguration: [
        {
          cidrMask: 24,
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
        },
        {
          cidrMask: 24,
          name: 'Private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        },
        {
          cidrMask: 28,
          name: 'Isolated',
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
        },
      ],
    });

    // App servers security group (App Runner / Lambda)
    this.appSecurityGroup = new ec2.SecurityGroup(this, 'AppSecurityGroup', {
      vpc: this.vpc,
      description: 'Security group for Metabookly API application servers',
      allowAllOutbound: true,
    });

    // Database security group — only accepts connections from app servers
    this.dbSecurityGroup = new ec2.SecurityGroup(this, 'DbSecurityGroup', {
      vpc: this.vpc,
      description: 'Security group for Aurora PostgreSQL',
      allowAllOutbound: false,
    });
    this.dbSecurityGroup.addIngressRule(
      this.appSecurityGroup,
      ec2.Port.tcp(5432),
      'Allow PostgreSQL from app servers'
    );

    // VPC Flow Logs for security auditing
    this.vpc.addFlowLog('FlowLog');

    new cdk.CfnOutput(this, 'VpcId', {
      value: this.vpc.vpcId,
      exportName: 'MetabooklyVpcId',
    });
  }
}
