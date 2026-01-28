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
  MULTIQC_API_TABLE_NAME,
  NTSM_BUCKET,
  QC_HTML_BUCKET,
  REFERENCE_URIS,
  SITES_URIS,
  SSM_PARAMETER_PATH_REFERENCE_PATH_PREFIX,
  SSM_PARAMETER_PATH_SITES_PATH_PREFIX,
} from './constants';
import {
  PIPELINE_CACHE_BUCKET,
  REFERENCE_DATA_BUCKET,
} from '@orcabus/platform-cdk-constructs/shared-config/s3';
import { SsmParameterPaths, SsmParameterValues } from './ssm/interfaces';
import { DEFAULT_ORCABUS_TOKEN_SECRET_ID } from '@orcabus/platform-cdk-constructs/lambda/config';

export const getSsmParameterPaths = (): SsmParameterPaths => {
  return {
    referencePathsPrefix: SSM_PARAMETER_PATH_REFERENCE_PATH_PREFIX,
    sitesPathsPrefix: SSM_PARAMETER_PATH_SITES_PATH_PREFIX,
  };
};

export const getSsmParameterValues = (): SsmParameterValues => {
  return {
    referencePathsMap: {
      hg19: REFERENCE_URIS['hg19'],
      hg38: REFERENCE_URIS['hg38'],
    },
    sitesPathsMap: {
      hg19: SITES_URIS['hg19'],
      hg38: SITES_URIS['hg38'],
    },
  };
};

export const getStatefulApplicationStackProps = (
  stage: StageName
): StatefulApplicationStackConfig => {
  return {
    /* S3 Stuff */
    ntsmBucketName: NTSM_BUCKET[stage],
    fastqSequaliBucketName: QC_HTML_BUCKET[stage],
    fastqManagerCacheBucketName: FASTQ_MANAGER_CACHE_BUCKET[stage],

    /* Table Stuff */
    fastqApiTableName: FASTQ_API_TABLE_NAME,
    fastqSetApiTableName: FASTQ_SET_API_TABLE_NAME,
    fastqJobApiTableName: JOB_API_TABLE_NAME,
    multiqcJobApiTableName: MULTIQC_API_TABLE_NAME,

    /* SSM Stuff */
    ssmParameters: {
      ssmParameterPaths: getSsmParameterPaths(),
      ssmParameterValues: getSsmParameterValues(),
    },
  };
};

export const getStatelessApplicationStackProps = (
  stage: StageName
): StatelessApplicationStackConfig => {
  return {
    /* S3 */
    ntsmBucketName: NTSM_BUCKET[stage],
    fastqSequaliBucketName: QC_HTML_BUCKET[stage],
    fastqManagerCacheBucketName: FASTQ_MANAGER_CACHE_BUCKET[stage],
    fastqDecompressionBucketName: FASTQ_DECOMPRESSION_CACHE_BUCKET[stage],
    pipelineCacheBucketName: PIPELINE_CACHE_BUCKET[stage],
    referenceDataBucketName: REFERENCE_DATA_BUCKET,

    /* Eventbus */
    eventBusName: EVENT_BUS_NAME,

    /* SSM */
    hostedZoneSsmParameterName: HOSTED_ZONE_DOMAIN_PARAMETER_NAME,
    orcabusTokenSecretId: DEFAULT_ORCABUS_TOKEN_SECRET_ID,

    /* DynamoDB */
    fastqApiTableName: FASTQ_API_TABLE_NAME,
    fastqSetApiTableName: FASTQ_SET_API_TABLE_NAME,
    fastqJobApiTableName: JOB_API_TABLE_NAME,
    multiqcJobApiTableName: MULTIQC_API_TABLE_NAME,

    /* API */
    apiGatewayCognitoProps: {
      ...getDefaultApiGatewayConfiguration(stage),
      apiName: API_NAME,
      customDomainNamePrefix: API_SUBDOMAIN_NAME,
    },

    /* SSM Parameters */
    ssmParameterPaths: getSsmParameterPaths(),
  };
};
