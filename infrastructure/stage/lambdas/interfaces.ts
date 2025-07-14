/**
 * Lambda interfaces
 */
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { DockerImageFunction } from 'aws-cdk-lib/aws-lambda';
import { ITableV2 } from 'aws-cdk-lib/aws-dynamodb';

export type LambdaNameList =
  // NTSM functions
  | 'ntsmEval'
  | 'checkRelatednessList'
  | 'getFastqObjectsInFastqSet'
  | 'getFastqObjectWithS3Objs'
  // Job updater functions
  | 'updateFastqObject'
  | 'updateJobObject';

export const lambdaNameList: LambdaNameList[] = [
  // NTSM functions
  'ntsmEval',
  'checkRelatednessList',
  'getFastqObjectsInFastqSet',
  'getFastqObjectWithS3Objs',
  // Job updater functions
  'updateFastqObject',
  'updateJobObject',
];

export interface LambdaRequirementsProps {
  needsOrcabusApiTools?: boolean;
  needsDockerBuild?: boolean;
  needsJobsTableWritePermissions?: boolean;
}

// Map of Lambda names to their requirements
export const lambdaRequirementsMap: Record<LambdaNameList, LambdaRequirementsProps> = {
  // NTSM functions
  ntsmEval: {
    needsDockerBuild: true,
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
};

export interface LambdaProps {
  lambdaName: LambdaNameList;
  jobsTable: ITableV2;
}

export interface LambdaResponse extends Omit<LambdaProps, 'jobsTable'> {
  lambdaFunction: PythonFunction | DockerImageFunction;
}

export type LambdasProps = Omit<LambdaProps, 'lambdaName'>;
