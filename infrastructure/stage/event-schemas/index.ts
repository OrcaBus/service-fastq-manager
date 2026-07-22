import { Construct } from 'constructs';
import * as schemas from 'aws-cdk-lib/aws-eventschemas';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as fs from 'fs';
import * as path from 'path';
import { SchemaNames, schemaNamesList } from './interfaces';
import {
  EVENT_SCHEMAS_DIR,
  SCHEMA_REGISTRY_NAME,
  SSM_SCHEMA_ROOT,
  DEFAULT_PAYLOAD_VERSION,
  STACK_PREFIX,
} from '../constants';
import { camelCaseToKebabCase } from '../utils';

export function buildSchema(
  scope: Construct,
  schemaName: SchemaNames,
  payloadVersion: string = DEFAULT_PAYLOAD_VERSION
): void {
  const kebabName = camelCaseToKebabCase(schemaName);
  const schemaFilePath = path.join(EVENT_SCHEMAS_DIR, kebabName, payloadVersion, 'schema.json');

  if (!fs.existsSync(schemaFilePath)) {
    throw new Error(
      `Schema file not found: ${schemaFilePath}. ` +
        `Expected schema for '${schemaName}' at version '${payloadVersion}'.`
    );
  }

  const schemaContent = fs.readFileSync(schemaFilePath, 'utf-8');
  const registeredSchemaName = `${STACK_PREFIX}--${schemaName}--${payloadVersion}`;

  new schemas.CfnSchema(scope, `Schema-${schemaName}`, {
    registryName: SCHEMA_REGISTRY_NAME,
    schemaName: registeredSchemaName,
    type: 'JSONSchemaDraft4',
    content: schemaContent,
  });

  // SSM Parameters for schema discovery
  const ssmBasePath = path.join(SSM_SCHEMA_ROOT, schemaName);

  new ssm.StringParameter(scope, `SsmSchemaRegistryName-${schemaName}`, {
    parameterName: path.join(ssmBasePath, 'registry-name'),
    stringValue: SCHEMA_REGISTRY_NAME,
  });

  new ssm.StringParameter(scope, `SsmSchemaName-${schemaName}`, {
    parameterName: path.join(ssmBasePath, 'schema-name'),
    stringValue: registeredSchemaName,
  });

  new ssm.StringParameter(scope, `SsmSchemaPayloadVersion-${schemaName}`, {
    parameterName: path.join(ssmBasePath, 'payload-version'),
    stringValue: payloadVersion,
  });
}

export function buildSchemas(scope: Construct): void {
  for (const schemaName of schemaNamesList) {
    buildSchema(scope, schemaName, DEFAULT_PAYLOAD_VERSION);
  }
}
