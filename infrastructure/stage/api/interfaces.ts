import { ITableV2 } from 'aws-cdk-lib/aws-dynamodb';
import { IEventBus } from 'aws-cdk-lib/aws-events';
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { OrcaBusApiGateway } from '@orcabus/platform-cdk-constructs/api-gateway';
import { HttpLambdaIntegration } from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import { SfnObject } from '../step-functions/interfaces';
import { IStringParameter } from 'aws-cdk-lib/aws-ssm/lib/parameter';

export interface LambdaApiProps {
  /* The lambda name */
  lambdaName: string;

  /* Table(s) to use */
  // Fastq
  fastqTable: ITableV2;
  // Fastq Set
  fastqSetTable: ITableV2;
  // Jobs
  jobsTable: ITableV2;
  // Multiqc Jobs
  multiqcJobsTable: ITableV2;

  /* Step Functions */
  stepFunctions: SfnObject[];

  /* Event Bus */
  eventBus: IEventBus;

  /* Hosted Zone SSM Parameter */
  hostedZoneSsmParameter: IStringParameter;
}

/** API Interfaces */
/** API Gateway interfaces **/
export interface BuildApiIntegrationProps {
  lambdaFunction: PythonFunction;
}

export interface BuildHttpRoutesProps {
  apiGateway: OrcaBusApiGateway;
  apiIntegration: HttpLambdaIntegration;
}
