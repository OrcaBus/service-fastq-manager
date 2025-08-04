/**
 * Use the PythonUvFunction script to build the lambda functions
 */
import {
  lambdaNameList,
  LambdaProps,
  lambdaRequirementsMap,
  LambdaResponse,
  LambdasProps,
} from './interfaces';
import { PythonUvFunction } from '@orcabus/platform-cdk-constructs/lambda';
import { Construct } from 'constructs';
import { camelCaseToSnakeCase } from '../utils';
import * as path from 'path';
import { Duration } from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { LAMBDA_DIR } from '../constants';
import { NagSuppressions } from 'cdk-nag';
import { DockerImageCode, DockerImageFunction } from 'aws-cdk-lib/aws-lambda';

function buildLambdaFunction(scope: Construct, props: LambdaProps): LambdaResponse {
  const lambdaNameToSnakeCase = camelCaseToSnakeCase(props.lambdaName);
  const lambdaRequirements = lambdaRequirementsMap[props.lambdaName];
  let lambdaObject: PythonUvFunction | DockerImageFunction;

  if (lambdaRequirements.needsDockerBuild) {
    lambdaObject = new DockerImageFunction(scope, props.lambdaName, {
      code: DockerImageCode.fromImageAsset(
        path.join(LAMBDA_DIR, lambdaNameToSnakeCase + '_docker')
      ),
      architecture: lambda.Architecture.ARM_64,
      timeout: Duration.seconds(60),
      memorySize: 2048,
    });
  } else {
    lambdaObject = new PythonUvFunction(scope, props.lambdaName, {
      entry: path.join(LAMBDA_DIR, lambdaNameToSnakeCase + '_py'),
      runtime: lambda.Runtime.PYTHON_3_12,
      architecture: lambda.Architecture.ARM_64,
      index: lambdaNameToSnakeCase + '.py',
      handler: 'handler',
      timeout: Duration.seconds(60),
      includeOrcabusApiToolsLayer: lambdaRequirements.needsOrcabusApiTools,
    });
  }

  if (lambdaRequirements.needsJobsTableWritePermissions) {
    props.jobsTable.grantReadWriteData(lambdaObject.currentVersion);
    // Add the JOB_TABLE_NAME environment variable
    lambdaObject.addEnvironment('JOB_TABLE_NAME', props.jobsTable.tableName);
  }

  if (lambdaRequirements.needsFastqCacheBucketAccess) {
    props.fastqCacheBucket.grantReadWrite(lambdaObject.currentVersion);
    // Add cdk nag stack suppressions
    NagSuppressions.addResourceSuppressions(
      lambdaObject,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason: 'We need access to the entire bucket',
        },
      ],
      true
    );
  }

  if (lambdaRequirements.needsNtsmCacheBucketAccess) {
    props.ntsmBucket.grantReadWrite(lambdaObject.currentVersion);
    // Add cdk nag stack suppressions
    NagSuppressions.addResourceSuppressions(
      lambdaObject,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason: 'We need access to the entire bucket',
        },
      ],
      true
    );
  }

  return {
    lambdaName: props.lambdaName,
    lambdaFunction: lambdaObject,
  };
}

export function buildAllLambdaFunctions(scope: Construct, props: LambdasProps): LambdaResponse[] {
  const lambdaList: LambdaResponse[] = [];
  for (const lambdaName of lambdaNameList) {
    lambdaList.push(
      buildLambdaFunction(scope, {
        ...props,
        lambdaName: lambdaName,
      })
    );
  }

  // Add cdk nag stack suppressions
  NagSuppressions.addResourceSuppressions(
    lambdaList.map((lambdaResponse) => lambdaResponse.lambdaFunction),
    [
      {
        id: 'AwsSolutions-IAM4',
        reason: 'We use the AWS Lambda basic execution role to run the lambdas.',
      },
      {
        id: 'AwsSolutions-L1',
        reason: 'Were currently using Python 3.12',
      },
    ],
    true
  );

  return lambdaList;
}
