import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as opensearch from 'aws-cdk-lib/aws-opensearchservice';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

interface SearchStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
  searchSecurityGroup: ec2.SecurityGroup;
}

export class SearchStack extends cdk.Stack {
  public readonly domain: opensearch.Domain;

  constructor(scope: Construct, id: string, props: SearchStackProps) {
    super(scope, id, props);

    // OpenSearch Service — single t3.small.search node for MVP (~$25/month)
    // Handles full-text search, faceted filtering, and vector search for AI recommendations
    this.domain = new opensearch.Domain(this, 'MetabooklySearch', {
      domainName: 'metabookly-search',
      version: opensearch.EngineVersion.OPENSEARCH_2_13,
      capacity: {
        dataNodes: 1,
        dataNodeInstanceType: 't3.small.search',
        multiAzWithStandbyEnabled: false,
      },
      ebs: {
        volumeSize: 20,  // 20GB — plenty for MVP book catalog
        volumeType: ec2.EbsDeviceVolumeType.GP3,
      },
      vpc: props.vpc,
      vpcSubnets: [
        {
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          availabilityZones: [props.vpc.availabilityZones[0]],
        },
      ],
      securityGroups: [props.searchSecurityGroup],
      encryptionAtRest: { enabled: true },
      nodeToNodeEncryption: true,
      enforceHttps: true,
      logging: {
        slowSearchLogEnabled: true,
        appLogEnabled: true,
        slowIndexLogEnabled: true,
      },
      accessPolicies: [
        new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          principals: [new iam.AccountRootPrincipal()],
          actions: ['es:*'],
          resources: [`arn:aws:es:${this.region}:${this.account}:domain/metabookly-search/*`],
        }),
      ],
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    new cdk.CfnOutput(this, 'SearchDomainEndpoint', {
      value: this.domain.domainEndpoint,
      exportName: 'MetabooklySearchEndpoint',
    });
  }
}
