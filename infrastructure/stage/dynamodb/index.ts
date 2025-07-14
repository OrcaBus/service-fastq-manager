import { ApiTableProps, BuildGlobalIndexesProps } from './interfaces';
import {
  AttributeType,
  GlobalSecondaryIndexPropsV2,
  ProjectionType,
} from 'aws-cdk-lib/aws-dynamodb';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import {
  FASTQ_API_GLOBAL_SECONDARY_INDEX_NAMES,
  FASTQ_API_GLOBAL_SECONDARY_INDEX_NON_KEY_ATTRIBUTE_NAMES,
  FASTQ_JOB_GLOBAL_SECONDARY_INDEX_NAMES,
  FASTQ_SET_API_GLOBAL_SECONDARY_INDEX_NAMES,
  FASTQ_SET_API_GLOBAL_SECONDARY_INDEX_NON_KEY_ATTRIBUTE_NAMES,
  TABLE_REMOVAL_POLICY,
} from '../constants';
import { Construct } from 'constructs';

function getFastqApiSecondaryIndexes(
  props: BuildGlobalIndexesProps
): GlobalSecondaryIndexPropsV2[] {
  const secondaryIndexList: GlobalSecondaryIndexPropsV2[] = [];

  for (const indexName of FASTQ_API_GLOBAL_SECONDARY_INDEX_NAMES) {
    // Get all other elements in PACKAGING_JOB_API_GLOBAL_SECONDARY_INDEX_NAMES
    const otherIndexNames = FASTQ_API_GLOBAL_SECONDARY_INDEX_NAMES.filter(
      (name) => name !== indexName
    );

    // Get the non-key attributes for the current index
    const nonKeyAttributes = [
      ...otherIndexNames,
      ...FASTQ_API_GLOBAL_SECONDARY_INDEX_NON_KEY_ATTRIBUTE_NAMES,
    ];

    // If the indexName is 'instrument_run_id' we make an exception and extend the nonKeyAttributes
    // To include 'index' and 'lane'
    if (indexName === 'instrument_run_id') {
      nonKeyAttributes.push('index', 'lane');
    }

    secondaryIndexList.push({
      indexName: `${indexName}-index`,
      partitionKey: {
        name: indexName,
        type: AttributeType.STRING,
      },
      sortKey: {
        name: props.sortKey,
        type: AttributeType.STRING,
      },
      projectionType: ProjectionType.INCLUDE,
      nonKeyAttributes: nonKeyAttributes,
    });
  }

  return secondaryIndexList;
}

function getFastqSetSecondaryIndexes(
  props: BuildGlobalIndexesProps
): GlobalSecondaryIndexPropsV2[] {
  const secondaryIndexList: GlobalSecondaryIndexPropsV2[] = [];

  for (const indexName of FASTQ_SET_API_GLOBAL_SECONDARY_INDEX_NAMES) {
    // Get all other elements in PACKAGING_JOB_API_GLOBAL_SECONDARY_INDEX_NAMES
    const otherIndexNames = FASTQ_SET_API_GLOBAL_SECONDARY_INDEX_NAMES.filter(
      (name) => name !== indexName
    );

    // Get the non-key attributes for the current index
    const nonKeyAttributes = [
      ...otherIndexNames,
      ...FASTQ_SET_API_GLOBAL_SECONDARY_INDEX_NON_KEY_ATTRIBUTE_NAMES,
    ];

    secondaryIndexList.push({
      indexName: `${indexName}-index`,
      partitionKey: {
        name: indexName,
        type: AttributeType.STRING,
      },
      sortKey: {
        name: props.sortKey,
        type: AttributeType.STRING,
      },
      projectionType: ProjectionType.INCLUDE,
      nonKeyAttributes: nonKeyAttributes,
    });
  }

  return secondaryIndexList;
}

function getFastqJobApiTableSecondaryIndexes(
  props: BuildGlobalIndexesProps
): GlobalSecondaryIndexPropsV2[] {
  const secondaryIndexList: GlobalSecondaryIndexPropsV2[] = [];

  for (const indexName of FASTQ_JOB_GLOBAL_SECONDARY_INDEX_NAMES) {
    // Get all other elements in FASTQ_JOB_GLOBAL_SECONDARY_INDEX_NAMES
    const otherIndexNames = FASTQ_JOB_GLOBAL_SECONDARY_INDEX_NAMES.filter(
      (name) => name !== indexName
    );

    secondaryIndexList.push({
      indexName: `${indexName}-index`,
      partitionKey: {
        name: indexName,
        type: AttributeType.STRING,
      },
      sortKey: {
        name: props.sortKey,
        type: AttributeType.STRING,
      },
      projectionType: ProjectionType.INCLUDE,
      nonKeyAttributes: otherIndexNames,
    });
  }

  return secondaryIndexList;
}

export function buildFastqApiTable(scope: Construct, props: ApiTableProps) {
  new dynamodb.TableV2(scope, props.tableName, {
    tableName: props.tableName,
    partitionKey: {
      name: props.partitionKey,
      type: dynamodb.AttributeType.STRING,
    },
    removalPolicy: TABLE_REMOVAL_POLICY,
    pointInTimeRecoverySpecification: {
      pointInTimeRecoveryEnabled: true,
    },
    globalSecondaryIndexes: getFastqApiSecondaryIndexes({
      sortKey: props.partitionKey,
    }),
  });
}

export function buildFastqSetApiTable(scope: Construct, props: ApiTableProps) {
  new dynamodb.TableV2(scope, props.tableName, {
    tableName: props.tableName,
    partitionKey: {
      name: props.partitionKey,
      type: dynamodb.AttributeType.STRING,
    },
    removalPolicy: TABLE_REMOVAL_POLICY,
    pointInTimeRecoverySpecification: {
      pointInTimeRecoveryEnabled: true,
    },
    globalSecondaryIndexes: getFastqSetSecondaryIndexes({
      sortKey: props.partitionKey,
    }),
  });
}

export function buildFastqJobApiTable(scope: Construct, props: ApiTableProps) {
  new dynamodb.TableV2(scope, props.tableName, {
    tableName: props.tableName,
    partitionKey: {
      name: props.partitionKey,
      type: dynamodb.AttributeType.STRING,
    },
    removalPolicy: TABLE_REMOVAL_POLICY,
    pointInTimeRecoverySpecification: {
      pointInTimeRecoveryEnabled: true,
    },
    globalSecondaryIndexes: getFastqJobApiTableSecondaryIndexes({
      sortKey: props.partitionKey,
    }),
    timeToLiveAttribute: 'ttl',
  });
}
