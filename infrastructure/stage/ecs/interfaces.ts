/*
Interfaces for the ECS Fargate Applications
*/
import { IBucket } from 'aws-cdk-lib/aws-s3';
import { ISecret } from 'aws-cdk-lib/aws-secretsmanager';
import { IStringParameter } from 'aws-cdk-lib/aws-ssm/lib/parameter';

export type EcsContainerName =
  | 'getBaseCountEst'
  | 'getInsertSizeMetrics'
  | 'getRawMd5sum'
  | 'getReadCount'
  | 'getSequaliStats'
  | 'ntsmCount'
  | 'runMultiqc'
  | 'somalierExtract'
  | 'tinyAlignment';

export const ecsContainerNameList: EcsContainerName[] = [
  'getBaseCountEst',
  'getInsertSizeMetrics',
  'getRawMd5sum',
  'getReadCount',
  'getSequaliStats',
  'ntsmCount',
  'runMultiqc',
  'somalierExtract',
  'tinyAlignment',
];

export interface EcsTaskResources {
  nCpus: number;
  memoryLimitGiB: number;
}

// Default sizing shared by every ECS task. 16GB is the minimum memory for 8 vCPU
// on Fargate.
export const DEFAULT_ECS_RESOURCES: EcsTaskResources = {
  nCpus: 8,
  memoryLimitGiB: 16,
};

// Per-container sizing overrides. Any container not listed here uses
// DEFAULT_ECS_RESOURCES.
//
// getInsertSizeMetrics aligns a fixed ~10M-read sample to the full hg38 reference.
// Peak memory is dominated by the ~12GB minimap2 index plus the alignment/sort
// buffers for the 10M-read sample, which overruns the default 16GB and gets the
// task OOM-killed mid-pipe (surfacing as a samtools "error reading file -" /
// SAM parse error). Bump to 32GB while keeping 8 vCPU to match minimap2's thread
// count. On Fargate, 8 vCPU supports 16-60GB in 4GB steps.
export const ecsContainerNameToResourcesMap: Partial<Record<EcsContainerName, EcsTaskResources>> = {
  getInsertSizeMetrics: {
    nCpus: 8,
    memoryLimitGiB: 32,
  },
};

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
  getInsertSizeMetrics: {
    needsReferenceBucketReadAccess: true,
    needsFastqSequaliS3BucketAccess: true,
    needsFastqDecompressionBucketAccess: true,
    // Writes the insertSizeEstimate summary JSON to the fastq manager cache
    // bucket (cache/ prefix) for the proceeding step functions task to pick up.
    needsFastqCacheBucketAccess: true,
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
