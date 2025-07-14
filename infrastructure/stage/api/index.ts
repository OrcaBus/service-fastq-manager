/*
API Interface
 */

import {
  OrcaBusApiGateway,
  OrcaBusApiGatewayProps,
} from '@orcabus/platform-cdk-constructs/api-gateway';
import { Construct } from 'constructs';
import { HttpLambdaIntegration } from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import { BuildApiIntegrationProps, BuildHttpRoutesProps, LambdaApiProps } from './interfaces';
import {
  HttpMethod,
  HttpNoneAuthorizer,
  HttpRoute,
  HttpRouteKey,
} from 'aws-cdk-lib/aws-apigatewayv2';
import { NagSuppressions } from 'cdk-nag';
import {
  API_SUBDOMAIN_NAME,
  API_VERSION,
  EVENT_FASTQ_SET_STATE_CHANGE_DETAIL_TYPE,
  EVENT_FASTQ_STATE_CHANGE_DETAIL_TYPE,
  FASTQ_API_GLOBAL_SECONDARY_INDEX_NAMES,
  FASTQ_JOB_GLOBAL_SECONDARY_INDEX_NAMES,
  FASTQ_SET_API_GLOBAL_SECONDARY_INDEX_NAMES,
  INTERFACE_DIR,
  STACK_SOURCE,
} from '../constants';
import path from 'path';
import { PythonUvFunction } from '@orcabus/platform-cdk-constructs/lambda';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Duration } from 'aws-cdk-lib';
import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';

export function buildApiInterfaceLambda(scope: Construct, props: LambdaApiProps) {
  const lambdaApiFunction = new PythonUvFunction(scope, props.lambdaName, {
    entry: path.join(INTERFACE_DIR),
    runtime: lambda.Runtime.PYTHON_3_12,
    architecture: lambda.Architecture.ARM_64,
    index: 'handler.py',
    handler: 'handler',
    timeout: Duration.seconds(60),
    memorySize: 2048,
    includeOrcabusApiToolsLayer: true,
    includeFastApiLayer: true,
    environment: {
      /* DynamoDB env vars */
      DYNAMODB_HOST: `https://dynamodb.${cdk.Aws.REGION}.amazonaws.com`,
      DYNAMODB_FASTQ_TABLE_NAME: props.fastqTable.tableName,
      DYNAMODB_FASTQ_SET_TABLE_NAME: props.fastqSetTable.tableName,
      DYNAMODB_FASTQ_JOB_TABLE_NAME: props.jobsTable.tableName,

      /* SSM and Secrets Manager env vars */
      FASTQ_BASE_URL: `https://${API_SUBDOMAIN_NAME}.${props.hostedZoneSsmParameter.stringValue}`,

      /* Event bridge env vars */
      EVENT_BUS_NAME: props.eventBus.eventBusName,
      EVENT_SOURCE: STACK_SOURCE,

      /* Event detail types */
      EVENT_DETAIL_TYPE_FASTQ_LIST_ROW_STATE_CHANGE: EVENT_FASTQ_STATE_CHANGE_DETAIL_TYPE,
      EVENT_DETAIL_TYPE_FASTQ_SET_ROW_STATE_CHANGE: EVENT_FASTQ_SET_STATE_CHANGE_DETAIL_TYPE,
    },
  });

  // Give lambda function permissions to put events on the event bus
  props.eventBus.grantPutEventsTo(lambdaApiFunction.currentVersion);

  // Add in permissions and env vars to the six state machines
  for (const sfnObject of props.stepFunctions) {
    switch (sfnObject.stateMachineName) {
      // For nstm counts
      case 'runNtsmCount': {
        lambdaApiFunction.addEnvironment(
          'NTSM_COUNT_AWS_STEP_FUNCTION_ARN',
          sfnObject.stateMachineObj.stateMachineArn
        );
        sfnObject.stateMachineObj.grantStartExecution(lambdaApiFunction.currentVersion);
        break;
      }
      case 'runNtsmEvalX': {
        lambdaApiFunction.addEnvironment(
          'NTSM_EVAL_X_AWS_STEP_FUNCTION_ARN',
          sfnObject.stateMachineObj.stateMachineArn
        );
        sfnObject.stateMachineObj.grantStartSyncExecution(lambdaApiFunction.currentVersion);
        break;
      }
      case 'runNtsmEvalXY': {
        lambdaApiFunction.addEnvironment(
          'NTSM_EVAL_X_Y_AWS_STEP_FUNCTION_ARN',
          sfnObject.stateMachineObj.stateMachineArn
        );
        sfnObject.stateMachineObj.grantStartSyncExecution(lambdaApiFunction.currentVersion);
        break;
      }
      case 'runReadCountStats': {
        lambdaApiFunction.addEnvironment(
          'READ_COUNT_AWS_STEP_FUNCTION_ARN',
          sfnObject.stateMachineObj.stateMachineArn
        );
        sfnObject.stateMachineObj.grantStartExecution(lambdaApiFunction.currentVersion);
        break;
      }
      case 'runQcStats': {
        lambdaApiFunction.addEnvironment(
          'QC_STATS_AWS_STEP_FUNCTION_ARN',
          sfnObject.stateMachineObj.stateMachineArn
        );
        sfnObject.stateMachineObj.grantStartExecution(lambdaApiFunction.currentVersion);
        break;
      }
      case 'runFileCompressionStats': {
        lambdaApiFunction.addEnvironment(
          'FILE_COMPRESSION_AWS_STEP_FUNCTION_ARN',
          sfnObject.stateMachineObj.stateMachineArn
        );
        sfnObject.stateMachineObj.grantStartExecution(lambdaApiFunction.currentVersion);
        break;
      }
    }
  }

  // Allow read/write access to the dynamodb table
  props.fastqTable.grantReadWriteData(lambdaApiFunction.currentVersion);
  props.fastqSetTable.grantReadWriteData(lambdaApiFunction.currentVersion);
  props.jobsTable.grantReadWriteData(lambdaApiFunction.currentVersion);

  // Grant query permissions on indexes
  const fastq_api_table_index_arn_list: string[] = FASTQ_API_GLOBAL_SECONDARY_INDEX_NAMES.map(
    (index_name) => {
      return `arn:aws:dynamodb:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:table/${props.fastqTable.tableName}/index/${index_name}-index`;
    }
  );
  const fastq_set_api_table_index_arn_list: string[] =
    FASTQ_SET_API_GLOBAL_SECONDARY_INDEX_NAMES.map((index_name) => {
      return `arn:aws:dynamodb:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:table/${props.fastqSetTable.tableName}/index/${index_name}-index`;
    });
  const fastq_job_table_index_arn_list: string[] = FASTQ_JOB_GLOBAL_SECONDARY_INDEX_NAMES.map(
    (index_name) => {
      return `arn:aws:dynamodb:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:table/${props.jobsTable.tableName}/index/${index_name}-index`;
    }
  );

  lambdaApiFunction.currentVersion.addToRolePolicy(
    new iam.PolicyStatement({
      actions: ['dynamodb:Query'],
      resources: [
        ...fastq_api_table_index_arn_list,
        ...fastq_set_api_table_index_arn_list,
        ...fastq_job_table_index_arn_list,
      ],
    })
  );

  NagSuppressions.addResourceSuppressions(
    lambdaApiFunction,
    [
      {
        id: 'AwsSolutions-IAM5',
        reason: 'Need access to packaging look up bucket',
      },
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

  return lambdaApiFunction;
}

export function buildApiGateway(
  scope: Construct,
  props: OrcaBusApiGatewayProps
): OrcaBusApiGateway {
  return new OrcaBusApiGateway(scope, 'apiGateway', props);
}

export function buildApiIntegration(props: BuildApiIntegrationProps): HttpLambdaIntegration {
  return new HttpLambdaIntegration('ApiIntegration', props.lambdaFunction);
}

// Add the http routes to the API Gateway
export function addHttpRoutes(scope: Construct, props: BuildHttpRoutesProps) {
  // Routes for API schemas
  const schemaRoute = new HttpRoute(scope, 'GetSchemaHttpRoute', {
    httpApi: props.apiGateway.httpApi,
    integration: props.apiIntegration,
    authorizer: new HttpNoneAuthorizer(), // No auth needed for schema
    routeKey: HttpRouteKey.with(`/schema/{PROXY+}`, HttpMethod.GET),
  });
  NagSuppressions.addResourceSuppressions(
    schemaRoute,
    [
      {
        id: 'AwsSolutions-APIG4',
        reason: 'This is a public API endpoint for schema access, no auth needed.',
      },
    ],
    true
  );
  new HttpRoute(scope, 'GetHttpRoute', {
    httpApi: props.apiGateway.httpApi,
    integration: props.apiIntegration,
    routeKey: HttpRouteKey.with(`/api/${API_VERSION}/{PROXY+}`, HttpMethod.GET),
  });
  new HttpRoute(scope, 'PostHttpRoute', {
    httpApi: props.apiGateway.httpApi,
    integration: props.apiIntegration,
    authorizer: props.apiGateway.authStackHttpLambdaAuthorizer,
    routeKey: HttpRouteKey.with(`/api/${API_VERSION}/{PROXY+}`, HttpMethod.POST),
  });
  new HttpRoute(scope, 'PatchHttpRoute', {
    httpApi: props.apiGateway.httpApi,
    integration: props.apiIntegration,
    authorizer: props.apiGateway.authStackHttpLambdaAuthorizer,
    routeKey: HttpRouteKey.with(`/api/${API_VERSION}/{PROXY+}`, HttpMethod.PATCH),
  });
  new HttpRoute(scope, 'DeleteHttpRoute', {
    httpApi: props.apiGateway.httpApi,
    integration: props.apiIntegration,
    authorizer: props.apiGateway.authStackHttpLambdaAuthorizer,
    routeKey: HttpRouteKey.with(`/api/${API_VERSION}/{PROXY+}`, HttpMethod.DELETE),
  });
}
