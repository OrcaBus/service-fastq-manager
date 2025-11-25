/*
Interfaces for the ECS Fargate Applications
*/
import { IBucket } from 'aws-cdk-lib/aws-s3';
import { ISecret } from 'aws-cdk-lib/aws-secretsmanager';
import { IStringParameter } from 'aws-cdk-lib/aws-ssm/lib/parameter';

export type EcsContainerName =
  | 'getBaseCountEst'
  | 'getRawMd5sum'
  | 'getReadCount'
  | 'getSequaliStats'
  | 'ntsmCount'
  | 'runMultiqc'
  | 'somalierExtract'
  | 'tinyAlignment';

export const ecsContainerNameList: EcsContainerName[] = [
  'getBaseCountEst',
  'getRawMd5sum',
  'getReadCount',
  'getSequaliStats',
  'ntsmCount',
  'runMultiqc',
  'somalierExtract',
  'tinyAlignment',
];

export interface EcsRequirementsMap {
  needsNtsmBucketAccess?: boolean;
  needsFastqCacheBucketAccess?: boolean;
  needsFastqDecompressionBucketAccess?: boolean;
  needsPipelineCacheBucketReadAccess?: boolean;
  needsReferenceBucketReadAccess?: boolean;
  needsFastqSequaliS3BucketAccess?: boolean;
  needsOrcabusPermissions?: boolean;
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
    needsFastqSequaliS3BucketAccess: true,
  },
  ntsmCount: {
    needsNtsmBucketAccess: true,
    needsFastqDecompressionBucketAccess: true,
    needsPipelineCacheBucketReadAccess: true,
  },
  runMultiqc: {
    needsFastqSequaliS3BucketAccess: true,
    needsFastqCacheBucketAccess: true,
  },
  somalierExtract: {
    needsFastqDecompressionBucketAccess: true,
    needsNtsmBucketAccess: true,
    needsOrcabusPermissions: true,
    needsReferenceBucketReadAccess: true,
  },
  tinyAlignment: {
    needsFastqDecompressionBucketAccess: true,
    needsNtsmBucketAccess: true,
    needsReferenceBucketReadAccess: true,
  },
};

export interface BuildFastqFargateEcsProps {
  containerName: EcsContainerName;
  fastqCacheS3Bucket: IBucket;
  fastqDecompressionS3Bucket: IBucket;
  ntsmS3Bucket: IBucket;
  fastqSequaliS3Bucket: IBucket;
  pipelineCacheS3Bucket: IBucket;
  referenceDataS3Bucket: IBucket;
  orcabusTokenSecret: ISecret;
  hostedZoneSsmParameter: IStringParameter;
}

export type BuildFastqFargateTasks = Omit<BuildFastqFargateEcsProps, 'containerName'>;
