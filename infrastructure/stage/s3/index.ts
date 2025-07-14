import { AddFastqManagerCacheBucketProps, AddNtsmBucketProps } from './interfaces';
import { Duration, RemovalPolicy } from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { FASTQ_CACHE_PREFIX } from '../constants';
import { Bucket } from 'aws-cdk-lib/aws-s3';

function addTemporaryMetadataDataLifeCycleRuleToBucket(bucket: Bucket): void {
  bucket.addLifecycleRule({
    id: 'DeleteMetadataCacheDataAfterOneDay',
    enabled: true,
    expiration: Duration.days(1), // Delete objects older than 1 day
    prefix: FASTQ_CACHE_PREFIX, // Apply to objects with the 'cache/' prefix
  });
}

export function addNtsmBucket(scope: Construct, props: AddNtsmBucketProps) {
  return new s3.Bucket(scope, props.bucketName, {
    bucketName: props.bucketName,
    removalPolicy: RemovalPolicy.RETAIN_ON_UPDATE_OR_DELETE,
    eventBridgeEnabled: true, // So that the filemanager can listen to events
    enforceSSL: true,
  });
}

export function addFastqManagerCacheBucket(
  scope: Construct,
  props: AddFastqManagerCacheBucketProps
) {
  const cacheBucket = new s3.Bucket(scope, props.bucketName, {
    bucketName: props.bucketName,
    removalPolicy: RemovalPolicy.RETAIN_ON_UPDATE_OR_DELETE,
    enforceSSL: true,
  });
  addTemporaryMetadataDataLifeCycleRuleToBucket(cacheBucket);
}
