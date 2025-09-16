/**
 * Lambda interfaces
 */
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { DockerImageFunction } from 'aws-cdk-lib/aws-lambda';
import { ITableV2 } from 'aws-cdk-lib/aws-dynamodb';
import { IBucket } from 'aws-cdk-lib/aws-s3';

export type LambdaNameList =
  // NTSM functions
  | 'ntsmEval'
  | 'checkRelatednessList'
  | 'getFastqObjectsInFastqSet'
  | 'getFastqObjectWithS3Objs'
  // Job updater functions
  | 'updateFastqObject'
  | 'updateJobObject'
  // Multiqc functions
  | 'generateNamesMapping'
  | 'generateDownloadParquetScript'
  | 'updateMultiqcJobStatus';

export const lambdaNameList: LambdaNameList[] = [
  // NTSM functions
  'ntsmEval',
  'checkRelatednessList',
  'getFastqObjectsInFastqSet',
  'getFastqObjectWithS3Objs',
  // Job updater functions
  'updateFastqObject',
  'updateJobObject',
  // Multiqc functions
  'generateNamesMapping',
  'generateDownloadParquetScript',
  'updateMultiqcJobStatus',
];

export interface LambdaRequirementsProps {
  needsOrcabusApiTools?: boolean;
  needsDockerBuild?: boolean;
  needsJobsTableWritePermissions?: boolean;
  needsSequaliBucketAccess?: boolean;
  needsFastqCacheBucketAccess?: boolean;
  needsNtsmCacheBucketAccess?: boolean;
  needsLargeEphemeralStorage?: boolean;
}

// Map of Lambda names to their requirements
export const lambdaRequirementsMap: Record<LambdaNameList, LambdaRequirementsProps> = {
  // NTSM functions
  ntsmEval: {
    needsDockerBuild: true,
    needsNtsmCacheBucketAccess: true,
    needsLargeEphemeralStorage: true,
  },
  checkRelatednessList: {},
  getFastqObjectsInFastqSet: {
    needsOrcabusApiTools: true,
  },
  getFastqObjectWithS3Objs: {
    needsOrcabusApiTools: true,
  },
  // Job updater functions
  updateFastqObject: {
    needsOrcabusApiTools: true,
  },
  updateJobObject: {
    needsJobsTableWritePermissions: true,
  },
  // Multiqc functions
  generateNamesMapping: {
    needsOrcabusApiTools: true,
    needsFastqCacheBucketAccess: true,
  },
  generateDownloadParquetScript: {
    needsOrcabusApiTools: true,
    needsFastqCacheBucketAccess: true,
  },
  updateMultiqcJobStatus: {
    needsOrcabusApiTools: true,
  },
};

export interface LambdaProps {
  lambdaName: LambdaNameList;
  jobsTable: ITableV2;
  sequaliBucket: IBucket;
  fastqCacheBucket: IBucket;
  ntsmBucket: IBucket;
}

export interface LambdaResponse {
  lambdaName: LambdaNameList;
  lambdaFunction: PythonFunction | DockerImageFunction;
}

export type LambdasProps = Omit<LambdaProps, 'lambdaName'>;
