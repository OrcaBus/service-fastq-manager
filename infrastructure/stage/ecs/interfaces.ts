/*
Interfaces for the ECS Fargate Applications
*/
import { IBucket } from 'aws-cdk-lib/aws-s3';

export type EcsContainerName =
  | 'getBaseCountEst'
  | 'getRawMd5sum'
  | 'getReadCount'
  | 'getSequaliStats'
  | 'ntsmCount';

export const ecsContainerNameList: EcsContainerName[] = [
  'getBaseCountEst',
  'getRawMd5sum',
  'getReadCount',
  'getSequaliStats',
  'ntsmCount',
];

export interface EcsRequirementsMap {
  needsNtsmBucketAccess?: boolean;
  needsFastqCacheBucketAccess?: boolean;
  needsFastqDecompressionBucketAccess?: boolean;
  needsPipelineCacheBucketReadAccess?: boolean;
}

export const ecsContainerNameToRequirementsMap: Record<EcsContainerName, EcsRequirementsMap> = {
  getBaseCountEst: {
    needsFastqCacheBucketAccess: true,
    needsFastqDecompressionBucketAccess: true,
    needsPipelineCacheBucketReadAccess: true,
  },
  getRawMd5sum: {
    needsFastqCacheBucketAccess: true,
    needsFastqDecompressionBucketAccess: true,
    needsPipelineCacheBucketReadAccess: true,
  },
  getReadCount: {
    needsFastqCacheBucketAccess: true,
    needsFastqDecompressionBucketAccess: true,
    needsPipelineCacheBucketReadAccess: true,
  },
  getSequaliStats: {
    needsFastqCacheBucketAccess: true,
    needsFastqDecompressionBucketAccess: true,
    needsPipelineCacheBucketReadAccess: true,
  },
  ntsmCount: {
    needsNtsmBucketAccess: true,
    needsFastqDecompressionBucketAccess: true,
    needsPipelineCacheBucketReadAccess: true,
  },
};

export interface BuildFastqFargateEcsProps {
  containerName: EcsContainerName;
  fastqCacheS3Bucket: IBucket;
  fastqDecompressionS3Bucket: IBucket;
  ntsmS3Bucket: IBucket;
  pipelineCacheS3Bucket: IBucket;
}

export type BuildFastqFargateTasks = Omit<BuildFastqFargateEcsProps, 'containerName'>;
