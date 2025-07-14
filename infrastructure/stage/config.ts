import {
  getDefaultApiGatewayConfiguration,
  HOSTED_ZONE_DOMAIN_PARAMETER_NAME,
} from '@orcabus/platform-cdk-constructs/api-gateway';
import { StageName } from '@orcabus/platform-cdk-constructs/shared-config/accounts';
import { StatefulApplicationStackConfig, StatelessApplicationStackConfig } from './interfaces';
import {
  API_NAME,
  API_SUBDOMAIN_NAME,
  EVENT_BUS_NAME,
  FASTQ_API_TABLE_NAME,
  FASTQ_DECOMPRESSION_CACHE_BUCKET,
  FASTQ_MANAGER_CACHE_BUCKET,
  FASTQ_SET_API_TABLE_NAME,
  JOB_API_TABLE_NAME,
  NTSM_BUCKET,
} from './constants';
import { PIPELINE_CACHE_BUCKET } from '@orcabus/platform-cdk-constructs/shared-config/s3';

export const getStatefulApplicationStackProps = (
  stage: StageName
): StatefulApplicationStackConfig => {
  return {
    /* S3 Stuff */
    ntsmBucketName: NTSM_BUCKET[stage],
    fastqManagerCacheBucketName: FASTQ_MANAGER_CACHE_BUCKET[stage],

    /* Table Stuff */
    fastqApiTableName: FASTQ_API_TABLE_NAME,
    fastqSetApiTableName: FASTQ_SET_API_TABLE_NAME,
    fastqJobApiTableName: JOB_API_TABLE_NAME,
  };
};

export const getStatelessApplicationStackProps = (
  stage: StageName
): StatelessApplicationStackConfig => {
  return {
    /* S3 */
    ntsmBucketName: NTSM_BUCKET[stage],
    fastqManagerCacheBucketName: FASTQ_MANAGER_CACHE_BUCKET[stage],
    fastqDecompressionBucketName: FASTQ_DECOMPRESSION_CACHE_BUCKET[stage],
    pipelineCacheBucketName: PIPELINE_CACHE_BUCKET[stage],

    /* Eventbus */
    eventBusName: EVENT_BUS_NAME,

    /* SSM */
    hostedZoneSsmParameterName: HOSTED_ZONE_DOMAIN_PARAMETER_NAME,

    /* DynamoDB */
    fastqApiTableName: FASTQ_API_TABLE_NAME,
    fastqSetApiTableName: FASTQ_SET_API_TABLE_NAME,
    fastqJobApiTableName: JOB_API_TABLE_NAME,

    /* API */
    apiGatewayCognitoProps: {
      ...getDefaultApiGatewayConfiguration(stage),
      apiName: API_NAME,
      customDomainNamePrefix: API_SUBDOMAIN_NAME,
    },
  };
};
