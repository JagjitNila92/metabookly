#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { NetworkStack } from '../lib/network-stack';
import { StorageStack } from '../lib/storage-stack';
import { DatabaseStack } from '../lib/database-stack';
import { AuthStack } from '../lib/auth-stack';

const app = new cdk.App();

const env = {
  account: '562675430068',
  region: 'eu-west-2',
};

// 1. Network — VPC, subnets, security groups
const networkStack = new NetworkStack(app, 'MetabooklyNetwork', { env });

// 2. Storage — S3 buckets for ONIX feeds, book covers, assets
const storageStack = new StorageStack(app, 'MetabooklyStorage', { env });

// 3. Database — Aurora Serverless v2 (PostgreSQL)
//    Search: PostgreSQL full-text search (tsvector + GIN indexes) used for MVP.
//    OpenSearch will be added post-MVP when search demands justify the cost.
const databaseStack = new DatabaseStack(app, 'MetabooklyDatabase', {
  env,
  vpc: networkStack.vpc,
  dbSecurityGroup: networkStack.dbSecurityGroup,
});

// 4. Auth — Cognito User Pool for retailers and publishers
const authStack = new AuthStack(app, 'MetabooklyAuth', { env });

// Stack dependencies
databaseStack.addDependency(networkStack);

cdk.Tags.of(app).add('Project', 'Metabookly');
cdk.Tags.of(app).add('Environment', 'mvp');
