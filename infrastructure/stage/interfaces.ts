/*
Interfaces for the application stacks
 */

import { OrcaBusApiGatewayProps } from '@orcabus/platform-cdk-constructs/api-gateway';
import { SsmParameterPaths, SsmParameterValues } from './ssm/interfaces';

export interface SsmParameters {
  ssmParameterPaths: SsmParameterPaths;
  ssmParameterValues: SsmParameterValues;
}

export interface StatefulApplicationStackConfig {
  /* S3 */
  ntsmBucketName: string;
  fastqSequaliBucketName: string;
  fastqManagerCacheBucketName: string;

  /* DynamoDB */
  fastqApiTableName: string;
  fastqSetApiTableName: string;
  fastqJobApiTableName: string;
  multiqcJobApiTableName: string;

  /* SSM */
  ssmParameters: SsmParameters;
}

export interface StatelessApplicationStackConfig {
  /* S3 */
  ntsmBucketName: string;
  fastqSequaliBucketName: string;
  fastqManagerCacheBucketName: string;
  fastqDecompressionBucketName: string;
  pipelineCacheBucketName: string;
  referenceDataBucketName: string;

  /* Eventbus */
  eventBusName: string;

  /* OrcaBus */
  hostedZoneSsmParameterName: string;
  orcabusTokenSecretId: string;

  /* DynamoDB */
  fastqApiTableName: string;
  fastqSetApiTableName: string;
  fastqJobApiTableName: string;
  multiqcJobApiTableName: string;

  /* API */
  apiGatewayCognitoProps: OrcaBusApiGatewayProps;

  /* SSM */
  ssmParameterPaths: SsmParameterPaths;
}
