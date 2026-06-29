/*
Step Function Interfaces
*/

import { LambdaNameList, LambdaResponse } from '../lambdas/interfaces';
import { StateMachine } from 'aws-cdk-lib/aws-stepfunctions';
import { EcsFargateTaskConstruct } from '@orcabus/platform-cdk-constructs/ecs';
import { IEventBus } from 'aws-cdk-lib/aws-events';
import { IBucket } from 'aws-cdk-lib/aws-s3';
import { EcsContainerName } from '../ecs/interfaces';
import { SsmParameterPaths } from '../ssm/interfaces';

export type StepFunctionName =
  // NSTM Counts
  | 'runNtsmCount'
  // NSTM Evaluations (express functions)
  | 'runNtsmEvalX'
  | 'runNtsmEvalXY'
  // Read Count Calculation
  | 'runReadCountStats'
  | 'runQcStats'
  | 'runFileCompressionStats'
  // Multiqc
  | 'runMultiqcCollector'
  // Fingerprinting
  | 'runSomalierExtract'
  | 'sendTinyBamToHolmes';

export const stepFunctionNames: StepFunctionName[] = [
  // NSTM Counts
  'runNtsmCount',
  // NSTM Evaluations
  'runNtsmEvalX',
  'runNtsmEvalXY',
  // Read Count Calculation
  'runReadCountStats',
  'runQcStats',
  'runFileCompressionStats',
  // Multiqc express
  'runMultiqcCollector',
  // Fingerprinting
  'runSomalierExtract',
  'sendTinyBamToHolmes',
];

export interface StepFunctionRequirements {
  needsEcsPermissions?: boolean;
  needsPutEventPermissions?: boolean;
  needsFastqCacheS3BucketAccess?: boolean;
  needsFastqSequaliS3BucketAccess?: boolean;
  needsDecompressionS3BucketAccess?: boolean;
  needsNestedSfnPermissions?: boolean;
  needsSsmParameterAccess?: boolean;
  isExpressSfn?: boolean;
}

export const stepFunctionRequirementsMap: Record<StepFunctionName, StepFunctionRequirements> = {
  runNtsmCount: {
    needsPutEventPermissions: true,
    needsEcsPermissions: true,
  },
  runNtsmEvalX: {
    isExpressSfn: true,
  },
  runNtsmEvalXY: {
    isExpressSfn: true,
  },
  runReadCountStats: {
    needsPutEventPermissions: true,
    needsEcsPermissions: true,
    needsFastqCacheS3BucketAccess: true,
  },
  runQcStats: {
    needsPutEventPermissions: true,
    needsEcsPermissions: true,
    needsFastqCacheS3BucketAccess: true,
    needsFastqSequaliS3BucketAccess: true,
  },
  runFileCompressionStats: {
    needsPutEventPermissions: true,
    needsEcsPermissions: true,
    needsDecompressionS3BucketAccess: true,
  },
  runMultiqcCollector: {
    needsEcsPermissions: true,
  },
  runSomalierExtract: {
    needsEcsPermissions: true,
    needsPutEventPermissions: true,
    needsNestedSfnPermissions: true,
    needsSsmParameterAccess: true,
  },
  sendTinyBamToHolmes: {
    needsNestedSfnPermissions: true,
  },
};

// Map the lambda functions to their step function names
export const stepFunctionLambdaMap: Record<StepFunctionName, LambdaNameList[]> = {
  // NSTM Counts
  runNtsmCount: [
    'getFastqObjectWithS3Objs',
    'updateFastqObject',
    'updateJobObject',
    'filemanagerSyncAndCheck',
  ],
  // NSTM Evaluations
  runNtsmEvalX: ['ntsmEval', 'getFastqObjectsInFastqSet', 'checkRelatednessList'],
  runNtsmEvalXY: ['getFastqObjectsInFastqSet', 'ntsmEval', 'checkRelatednessList'],
  // Read Count Calculation
  runReadCountStats: ['getFastqObjectWithS3Objs', 'updateJobObject', 'updateFastqObject'],
  // Sequali stats calculation
  runQcStats: [
    'getFastqObjectWithS3Objs',
    'updateJobObject',
    'updateFastqObject',
    'calculateEphemeralSize',
    'filemanagerSync',
  ],
  // File Compression Stats
  runFileCompressionStats: ['getFastqObjectWithS3Objs', 'updateJobObject', 'updateFastqObject'],
  // Multiqc express
  runMultiqcCollector: [
    'generateNamesMapping',
    'generateDownloadParquetScript',
    'updateMultiqcJobStatus',
  ],
  // Fingerprinting
  runSomalierExtract: [
    'getFastqObjectsInFastqSet',
    'getLibraryFromFastqSetId',
    // Not yet used in this SFN but reserved for future use since we will eventually move this to a job
    'updateJobObject',
    'updateFastqSetObject',
  ],
  // Send tiny bam to holmes service
  sendTinyBamToHolmes: ['getCloudmapService', 'getServiceInstances'],
};

export const stepFunctionEcsMap: Record<StepFunctionName, EcsContainerName[]> = {
  // NSTM Counts
  runNtsmCount: ['ntsmCount'],
  // NSTM Evaluations
  runNtsmEvalX: [],
  runNtsmEvalXY: [],
  // Read Count Calculation
  runReadCountStats: ['getReadCount', 'getBaseCountEst'],
  // Sequali stats calculation
  runQcStats: ['getSequaliStats'],
  // File Compression Stats
  runFileCompressionStats: ['getRawMd5sum'],
  // Multiqc express
  runMultiqcCollector: ['runMultiqc'],
  // Somalier Fingerprinting
  runSomalierExtract: ['somalierExtract', 'tinyAlignment'],
  sendTinyBamToHolmes: [],
};

export interface SfnProps {
  stateMachineName: StepFunctionName;
  lambdaObjects: LambdaResponse[];
  eventBus: IEventBus;
  ecsFargateTasks: EcsFargateTaskConstruct[];
  fastqCacheBucket: IBucket;
  ntsmCountBucket: IBucket;
  sequaliBucket: IBucket;
  fastqDecompressionBucket: IBucket;
  ssmParameters: SsmParameterPaths;
}

export interface SfnObject extends SfnProps {
  stateMachineObj: StateMachine;
}

export type SfnsProps = Omit<SfnProps, 'stateMachineName'>;
