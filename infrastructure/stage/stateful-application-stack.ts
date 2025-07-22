import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { addFastqManagerCacheBucket, addFastqSequaliBucket, addNtsmBucket } from './s3';
import { StatefulApplicationStackConfig } from './interfaces';
import {
  buildFastqApiTable,
  buildFastqJobApiTable,
  buildFastqMultiqcJobApiTable,
  buildFastqSetApiTable,
} from './dynamodb';
import { NagSuppressions } from 'cdk-nag';

export type StatefulApplicationStackProps = cdk.StackProps & StatefulApplicationStackConfig;

export class StatefulApplicationStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: StatefulApplicationStackProps) {
    super(scope, id, props);

    /**
     * Two parts to the stateful application:
     * Build the S3 Buckets
     * Deploy the dynamodb tables
     * Add in stack suppressions because we have event notifications enabled on the S3 buckets
     * */

    // S3 Buckets
    addNtsmBucket(this, {
      bucketName: props.ntsmBucketName,
    });
    addFastqSequaliBucket(this, {
      bucketName: props.fastqSequaliBucketName,
    });
    addFastqManagerCacheBucket(this, {
      bucketName: props.fastqManagerCacheBucketName,
    });

    // DynamoDB Tables
    buildFastqApiTable(this, {
      tableName: props.fastqApiTableName,
      partitionKey: 'id',
    });
    buildFastqSetApiTable(this, {
      tableName: props.fastqSetApiTableName,
      partitionKey: 'id',
    });
    buildFastqJobApiTable(this, {
      tableName: props.fastqJobApiTableName,
      partitionKey: 'id',
    });
    buildFastqMultiqcJobApiTable(this, {
      tableName: props.multiqcJobApiTableName,
      partitionKey: 'id',
    });

    // Add in global cdk nag suppressions
    NagSuppressions.addStackSuppressions(this, [
      {
        id: 'AwsSolutions-IAM5',
        reason: 'We have no control over the BucketNotificationsHandler',
      },
      {
        id: 'AwsSolutions-IAM4',
        reason:
          'We have no control over the BucketNotificationsHandler that uses an AWS managed policy',
      },
    ]);
  }
}
