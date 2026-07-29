import * as path from 'path';
import { RemovalPolicy } from 'aws-cdk-lib';
import {
  ACCOUNT_ID_ALIAS,
  REGION,
  StageName,
} from '@orcabus/platform-cdk-constructs/shared-config/accounts';
import { REFERENCE_DATA_BUCKET } from '@orcabus/platform-cdk-constructs/shared-config/s3';

// Directory constants
export const APP_ROOT = path.join(__dirname, '../../app');
export const LAMBDA_DIR = path.join(APP_ROOT, 'lambdas');
export const ECS_DIR = path.join(APP_ROOT, 'ecs');
export const STEP_FUNCTIONS_DIR = path.join(APP_ROOT, 'step-functions-templates');
export const INTERFACE_DIR = path.join(APP_ROOT, 'api');

// API Constants
export const API_VERSION = 'v1';
export const API_SUBDOMAIN_NAME = 'fastq';
export const API_NAME = 'FastqManagerAPI';

// Table constants
export const TABLE_REMOVAL_POLICY = RemovalPolicy.RETAIN_ON_UPDATE_OR_DELETE; // We need to retain the table on update or delete to avoid data loss
export const FASTQ_API_TABLE_NAME = 'FastqDataTable';
export const FASTQ_SET_API_TABLE_NAME = 'FastqSetDataTable';
export const JOB_API_TABLE_NAME = 'FastqJobsTable';
export const MULTIQC_API_TABLE_NAME = 'FastqMultiqcJobsTable';

// Table indexes
export const FASTQ_API_GLOBAL_SECONDARY_INDEX_NAMES = [
  'rgid_ext',
  'instrument_run_id',
  'library_orcabus_id',
  'fastq_set_id',
];
export const FASTQ_API_GLOBAL_SECONDARY_INDEX_NON_KEY_ATTRIBUTE_NAMES = ['is_valid'];

export const FASTQ_SET_API_GLOBAL_SECONDARY_INDEX_NAMES = ['library_orcabus_id'];

export const FASTQ_SET_API_GLOBAL_SECONDARY_INDEX_NON_KEY_ATTRIBUTE_NAMES = [
  'is_current_fastq_set',
  'allow_additional_fastq',
];

export const FASTQ_JOB_GLOBAL_SECONDARY_INDEX_NAMES = ['fastq_id', 'job_type', 'status'];

export const MULTIQC_JOB_GLOBAL_SECONDARY_INDEX_NAMES = ['status'];

// Event Constants
export const EVENT_BUS_NAME = 'OrcaBusMain';
export const STACK_SOURCE = 'orcabus.fastqmanager';
export const EVENT_FASTQ_STATE_CHANGE_DETAIL_TYPE = 'FastqStateChange';
export const EVENT_FASTQ_SET_STATE_CHANGE_DETAIL_TYPE = 'FastqSetStateChange';
export const EVENT_MULTIQC_JOB_STATE_CHANGE_DETAIL_TYPE = 'FastqMultiqcJobStateChange';

// Step Function Constants
export const STACK_PREFIX = 'fastq-manager';

// S3 Constants
export const FASTQ_MANAGER_CACHE_BUCKET: Record<StageName, string> = {
  BETA: `fastq-manager-cache-${ACCOUNT_ID_ALIAS.BETA}-${REGION}`,
  GAMMA: `fastq-manager-cache-${ACCOUNT_ID_ALIAS.GAMMA}-${REGION}`,
  PROD: `fastq-manager-cache-${ACCOUNT_ID_ALIAS.PROD}-${REGION}`,
};
export const FASTQ_CACHE_PREFIX = 'cache/';
export const FASTQ_MULTIQC_CACHE_PREFIX = 'multiqc-cache/';

export const NTSM_BUCKET: Record<StageName, string> = {
  BETA: `ntsm-fingerprints-${ACCOUNT_ID_ALIAS.BETA}-${REGION}`,
  GAMMA: `ntsm-fingerprints-${ACCOUNT_ID_ALIAS.GAMMA}-${REGION}`,
  PROD: `ntsm-fingerprints-${ACCOUNT_ID_ALIAS.PROD}-${REGION}`,
};
export const NTSM_BUCKET_PREFIX = 'ntsm/';
export const SOMALIER_BUCKET_PREFIX = 'somalier/';
export const HOLMES_SERVICE_NAME = 'fingerprint';
export const HOLMES_EXTRACT_SFN_PREFIX = 'SomalierExtractStateMachine';

export const QC_HTML_BUCKET: Record<StageName, string> = {
  BETA: `fastq-manager-sequali-outputs-${ACCOUNT_ID_ALIAS.BETA}-${REGION}`,
  GAMMA: `fastq-manager-sequali-outputs-${ACCOUNT_ID_ALIAS.GAMMA}-${REGION}`,
  PROD: `fastq-manager-sequali-outputs-${ACCOUNT_ID_ALIAS.PROD}-${REGION}`,
};
export const SEQUALI_HTML_PREFIX = 'sequali-html/';
export const SEQUALI_PARQUET_PREFIX = 'sequali-parquet/';

export const MULTIQC_HTML_PREFIX = 'multiqc-html/';
export const MULTIQC_PARQUET_PREFIX = 'multiqc-parquet/';

// External buckets
export const FASTQ_DECOMPRESSION_CACHE_BUCKET: Record<StageName, string> = {
  BETA: `fastq-decompression-jobs-${ACCOUNT_ID_ALIAS.BETA}-${REGION}`,
  GAMMA: `fastq-decompression-jobs-${ACCOUNT_ID_ALIAS.GAMMA}-${REGION}`,
  PROD: `fastq-decompression-jobs-${ACCOUNT_ID_ALIAS.PROD}-${REGION}`,
};
export const S3_DECOMPRESSION_PREFIX = `decompression-data/`;
export const BYOB_ICAV2_PREFIX = 'byob-icav2/';

// External Event Constants
export const ORA_DECOMPRESSION_REQUEST_SYNC = 'OraDecompressionRequestSync';
export const GZIP_FILE_SIZE_CALCULATION_SYNC = 'GzipFileSizeCalculationRequestSync';
export const ORA_TO_RAW_MD5SUM_CALCULATION_SYNC = 'OraToRawMd5sumCalculationRequestSync';
export const READ_COUNT_CALCULATION_SYNC = 'ReadCountCalculationRequestSync';
export const FASTQ_SYNC_EVENT_DETAIL_TYPE = 'FastqSync';

// Miscellaneous Constants
export const MAX_BASE_COUNT_READS = 1_000_000; // Maximum base count for reads
export const MIN_SEQUALI_READS = 50_000_000; // Minimum reads needed for Sequali stats
export const MAX_SEQUALI_READS = 500_000_000; // Maximum reads needed for Sequali stats
// 20 GB is the minimum ephemeral storage size for ECS tasks
// However 21 is the minimum ephemeral storage size for an Override
export const DEFAULT_EPHEMERAL_STORAGE_SIZE = 21;
export const MAX_NTSM_READS = 36_000_000; // 36 million reads ~ 3x coverage
export const MAX_SOMALIER_READS = 180_000_000; // 180 million reads ~ 15x coverage

/* SSM Parameter Paths */
export const SSM_PARAMETER_PATH_PREFIX = path.join(`/orcabus/services/${STACK_PREFIX}/`);

// Somalier Reference paths
export const SSM_PARAMETER_PATH_REFERENCE_PATH_PREFIX = path.join(
  SSM_PARAMETER_PATH_PREFIX,
  'reference-paths/'
);
export const SSM_PARAMETER_PATH_SITES_PATH_PREFIX = path.join(
  SSM_PARAMETER_PATH_PREFIX,
  'sites-paths/'
);

// Reference Data Constants
export type Reference = 'hg19' | 'hg38';

export const REFERENCE_DATA_PREFIX = 'refdata';

export const REFERENCE_URIS: Record<Reference, string> = {
  hg19: `s3://${REFERENCE_DATA_BUCKET}/${REFERENCE_DATA_PREFIX}/genomes/hg19/hg19.fa`,
  hg38: `s3://${REFERENCE_DATA_BUCKET}/${REFERENCE_DATA_PREFIX}/genomes/GRCh38_umccr/GRCh38_full_analysis_set_plus_decoy_hla.fa`,
};

export const SITES_URIS: Record<Reference, string> = {
  hg19: `s3://${REFERENCE_DATA_BUCKET}/${REFERENCE_DATA_PREFIX}/somalier/hg19/sites.hg19.rna.vcf.gz`,
  hg38: `s3://${REFERENCE_DATA_BUCKET}/${REFERENCE_DATA_PREFIX}/somalier/hg38/sites.hg38.rna.vcf.gz`,
};

// Event Schema Constants
export const EVENT_SCHEMAS_DIR = path.join(APP_ROOT, 'event-schemas');
export const SCHEMA_REGISTRY_NAME = 'orcabus.events';
export const SSM_SCHEMA_ROOT = path.join(SSM_PARAMETER_PATH_PREFIX, 'event-schemas');
export const DEFAULT_PAYLOAD_VERSION = '2025.06.04';
