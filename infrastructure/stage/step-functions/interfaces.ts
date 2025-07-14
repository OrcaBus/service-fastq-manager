/*
Step Function Interfaces
*/

import { LambdaNameList, LambdaResponse } from '../lambdas/interfaces';
import { StateMachine } from 'aws-cdk-lib/aws-stepfunctions';
import { EcsFargateTaskConstruct } from '@orcabus/platform-cdk-constructs/ecs';
import { IEventBus } from 'aws-cdk-lib/aws-events';
import { IBucket } from 'aws-cdk-lib/aws-s3';
import { EcsContainerName } from '../ecs/interfaces';

export type StepFunctionName =
  // NSTM Counts
  | 'runNtsmCount'
  // NSTM Evaluations
  | 'runNtsmEvalX'
  | 'runNtsmEvalXY'
  // Read Count Calculation
  | 'runReadCountStats'
  | 'runQcStats'
  | 'runFileCompressionStats';

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
];

export interface StepFunctionRequirements {
  needsEcsPermissions?: boolean;
  needsPutEventPermissions?: boolean;
  needsFastqCacheS3BucketAccess?: boolean;
  needsDecompressionS3BucketAccess?: boolean;
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
  },
  runFileCompressionStats: {
    needsPutEventPermissions: true,
    needsEcsPermissions: true,
    needsDecompressionS3BucketAccess: true,
  },
};

// Map the lambda functions to their step function names
export const stepFunctionLambdaMap: Record<StepFunctionName, LambdaNameList[]> = {
  // NSTM Counts
  runNtsmCount: ['getFastqObjectWithS3Objs', 'updateFastqObject', 'updateJobObject'],
  // NSTM Evaluations
  runNtsmEvalX: ['ntsmEval'],
  runNtsmEvalXY: ['getFastqObjectsInFastqSet', 'ntsmEval'],
  // Read Count Calculation
  runReadCountStats: ['getFastqObjectWithS3Objs', 'updateJobObject', 'updateFastqObject'],
  // Sequali stats calculation
  runQcStats: ['getFastqObjectWithS3Objs', 'updateJobObject', 'updateFastqObject'],
  // File Compression Stats
  runFileCompressionStats: ['getFastqObjectWithS3Objs', 'updateJobObject', 'updateFastqObject'],
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
};

export interface SfnProps {
  stateMachineName: StepFunctionName;
  lambdaObjects: LambdaResponse[];
  eventBus: IEventBus;
  ecsFargateTasks: EcsFargateTaskConstruct[];
  fastqCacheBucket: IBucket;
  ntsmCountBucket: IBucket;
  fastqDecompressionBucket: IBucket;
}

export interface SfnObject extends SfnProps {
  stateMachineObj: StateMachine;
}

export type SfnsProps = Omit<SfnProps, 'stateMachineName'>;
