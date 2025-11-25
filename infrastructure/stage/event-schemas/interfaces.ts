export type SchemaNames = 'fastqStateChange' | 'fastqSetStateChange';

export const schemaNamesList: SchemaNames[] = ['fastqStateChange', 'fastqSetStateChange'];

export interface BuildSchemaProps {
  schemaName: SchemaNames;
}
