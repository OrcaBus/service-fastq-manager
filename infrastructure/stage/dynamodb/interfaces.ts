import { GlobalSecondaryIndexPropsV2 } from 'aws-cdk-lib/aws-dynamodb';

export interface BuildGlobalIndexesProps {
  sortKey: string;
}

export interface ApiTableProps {
  tableName: string;
  partitionKey: string;
}

export interface FastqTableProps {
  tableName: string;
  partitionKey: string;
  globalSecondaryIndexes: GlobalSecondaryIndexPropsV2[];
}

export type FastqSetTableProps = FastqTableProps;

export interface JobTableProps {
  tableName: string;
  partitionKey: string;
  globalSecondaryIndexes: GlobalSecondaryIndexPropsV2[];
  ttlAttribute: string;
}
