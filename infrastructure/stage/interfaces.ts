/*
Interfaces for the application stacks
 */

import { OrcaBusApiGatewayProps } from '@orcabus/platform-cdk-constructs/api-gateway';

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
}

export interface StatelessApplicationStackConfig {
  /* S3 */
  ntsmBucketName: string;
  fastqSequaliBucketName: string;
  fastqManagerCacheBucketName: string;
  fastqDecompressionBucketName: string;
  pipelineCacheBucketName: string;

  /* Eventbus */
  eventBusName: string;

  /* SSM */
  hostedZoneSsmParameterName: string;

  /* DynamoDB */
  fastqApiTableName: string;
  fastqSetApiTableName: string;
  fastqJobApiTableName: string;
  multiqcJobApiTableName: string;

  /* API */
  apiGatewayCognitoProps: OrcaBusApiGatewayProps;
}
