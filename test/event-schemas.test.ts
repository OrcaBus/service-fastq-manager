import * as path from 'path';
import * as fs from 'fs';
import { App, Stack } from 'aws-cdk-lib';
import { DEFAULT_PAYLOAD_VERSION, EVENT_SCHEMAS_DIR } from '../infrastructure/stage/constants';
import { schemaNamesList, SchemaNames } from '../infrastructure/stage/event-schemas/interfaces';
import { camelCaseToKebabCase } from '../infrastructure/stage/utils';
import { buildSchema } from '../infrastructure/stage/event-schemas';

describe('Event Schema Structure Tests', () => {
  // Load all schema files once for use across tests
  const schemas: Record<string, Record<string, unknown>> = {};

  beforeAll(() => {
    for (const schemaName of schemaNamesList) {
      const kebabName = camelCaseToKebabCase(schemaName);
      const schemaFilePath = path.join(
        EVENT_SCHEMAS_DIR,
        kebabName,
        DEFAULT_PAYLOAD_VERSION,
        'schema.json'
      );
      const content = fs.readFileSync(schemaFilePath, 'utf-8');
      schemas[schemaName] = JSON.parse(content);
    }
  });

  describe('Schema files are valid JSON with correct $schema declaration', () => {
    test.each(schemaNamesList)('%s schema is valid JSON', (schemaName) => {
      const kebabName = camelCaseToKebabCase(schemaName);
      const schemaFilePath = path.join(
        EVENT_SCHEMAS_DIR,
        kebabName,
        DEFAULT_PAYLOAD_VERSION,
        'schema.json'
      );
      const content = fs.readFileSync(schemaFilePath, 'utf-8');
      expect(() => JSON.parse(content)).not.toThrow();
    });

    test.each(schemaNamesList)(
      '%s schema declares $schema as JSON Schema 2020-12',
      (schemaName) => {
        expect(schemas[schemaName]['$schema']).toBe('https://json-schema.org/draft/2020-12/schema');
      }
    );
  });

  describe('FastqStateChange schema required fields and enum values', () => {
    const expectedStatuses = [
      'FASTQ_CREATED',
      'FASTQ_DELETED',
      'READ_SET_ADDED',
      'READ_SET_DELETED',
      'FILE_COMPRESSION_UPDATED',
      'QC_UPDATED',
      'NTSM_UPDATED',
      'READ_COUNT_UPDATED',
      'LIBRARY_UPDATED',
      'FASTQ_IS_VALID',
      'FASTQ_IS_INVALID',
      'FASTQ_SET_UPDATED',
    ];

    test('has correct required fields', () => {
      expect(schemas['fastqStateChange']['required']).toEqual(
        expect.arrayContaining(['id', 'status', 'library', 'index', 'lane', 'instrumentRunId'])
      );
      expect(schemas['fastqStateChange']['required']).toHaveLength(6);
    });

    test('status enum matches expected values', () => {
      const properties = schemas['fastqStateChange']['properties'] as Record<string, unknown>;
      const statusField = properties['status'] as Record<string, unknown>;
      expect(statusField['enum']).toEqual(expectedStatuses);
    });
  });

  describe('FastqSetStateChange schema required fields and enum values', () => {
    const expectedStatuses = [
      'FASTQ_SET_CREATED',
      'FASTQ_SET_DELETED',
      'FASTQ_LINKED',
      'FASTQ_UNLINKED',
      'FASTQ_SET_IS_CURRENT',
      'FASTQ_SET_IS_NOT_CURRENT',
      'FASTQ_SET_ADDITIONAL_FASTQS_ALLOWED',
      'FASTQ_SET_ADDITIONAL_FASTQS_DISALLOWED',
      'FASTQ_SET_MERGED',
      'SOMALIER_UPDATED',
    ];

    test('has correct required fields', () => {
      expect(schemas['fastqSetStateChange']['required']).toEqual(
        expect.arrayContaining(['id', 'status', 'library', 'fastqSet'])
      );
      expect(schemas['fastqSetStateChange']['required']).toHaveLength(4);
    });

    test('status enum matches expected values', () => {
      const properties = schemas['fastqSetStateChange']['properties'] as Record<string, unknown>;
      const statusField = properties['status'] as Record<string, unknown>;
      expect(statusField['enum']).toEqual(expectedStatuses);
    });
  });

  describe('FastqMultiqcJobStateChange schema required fields and enum values', () => {
    const expectedStatuses = ['PENDING', 'RUNNING', 'FAILED', 'ABORTED', 'SUCCEEDED'];

    test('has correct required fields', () => {
      expect(schemas['fastqMultiqcJobStateChange']['required']).toEqual(
        expect.arrayContaining(['id', 'status', 'fastqIdList'])
      );
      expect(schemas['fastqMultiqcJobStateChange']['required']).toHaveLength(3);
    });

    test('status enum matches expected values', () => {
      const properties = schemas['fastqMultiqcJobStateChange']['properties'] as Record<
        string,
        unknown
      >;
      const statusField = properties['status'] as Record<string, unknown>;
      expect(statusField['enum']).toEqual(expectedStatuses);
    });
  });

  describe('Pattern constraints on ID fields', () => {
    test('fastqStateChange id pattern matches ^fqr\\.', () => {
      const properties = schemas['fastqStateChange']['properties'] as Record<string, unknown>;
      const idField = properties['id'] as Record<string, unknown>;
      expect(idField['pattern']).toMatch(/^\^fqr\\\./);
    });

    test('fastqSetStateChange id pattern matches ^fqs\\.', () => {
      const properties = schemas['fastqSetStateChange']['properties'] as Record<string, unknown>;
      const idField = properties['id'] as Record<string, unknown>;
      expect(idField['pattern']).toMatch(/^\^fqs\\\./);
    });

    test('fastqMultiqcJobStateChange id pattern matches ^mqj\\.', () => {
      const properties = schemas['fastqMultiqcJobStateChange']['properties'] as Record<
        string,
        unknown
      >;
      const idField = properties['id'] as Record<string, unknown>;
      expect(idField['pattern']).toMatch(/^\^mqj\\\./);
    });
  });

  describe('$defs contains expected reusable definitions', () => {
    test('fastqStateChange $defs contains Library, FileStorageObject, FastqStorageObject, FastqPairStorageObject, QcInformation', () => {
      const defs = schemas['fastqStateChange']['$defs'] as Record<string, unknown>;
      expect(defs).toHaveProperty('Library');
      expect(defs).toHaveProperty('FileStorageObject');
      expect(defs).toHaveProperty('FastqStorageObject');
      expect(defs).toHaveProperty('FastqPairStorageObject');
      expect(defs).toHaveProperty('QcInformation');
    });

    test('fastqSetStateChange $defs contains FastqResponse', () => {
      const defs = schemas['fastqSetStateChange']['$defs'] as Record<string, unknown>;
      expect(defs).toHaveProperty('FastqResponse');
    });

    test('fastqMultiqcJobStateChange $defs contains FileStorageObject', () => {
      const defs = schemas['fastqMultiqcJobStateChange']['$defs'] as Record<string, unknown>;
      expect(defs).toHaveProperty('FileStorageObject');
    });
  });

  describe('DEFAULT_PAYLOAD_VERSION format', () => {
    test('matches YYYY.MM.DD format', () => {
      expect(DEFAULT_PAYLOAD_VERSION).toMatch(/^\d{4}\.\d{2}\.\d{2}$/);
    });
  });

  describe('schemaNamesList', () => {
    test('contains exactly three expected schema names', () => {
      expect(schemaNamesList).toHaveLength(3);
      expect(schemaNamesList).toContain('fastqStateChange');
      expect(schemaNamesList).toContain('fastqSetStateChange');
      expect(schemaNamesList).toContain('fastqMultiqcJobStateChange');
    });
  });

  describe('camelCaseToKebabCase conversions', () => {
    test('fastqStateChange converts to fastq-state-change', () => {
      expect(camelCaseToKebabCase('fastqStateChange')).toBe('fastq-state-change');
    });

    test('fastqSetStateChange converts to fastq-set-state-change', () => {
      expect(camelCaseToKebabCase('fastqSetStateChange')).toBe('fastq-set-state-change');
    });

    test('fastqMultiqcJobStateChange converts to fastq-multiqc-job-state-change', () => {
      expect(camelCaseToKebabCase('fastqMultiqcJobStateChange')).toBe(
        'fastq-multiqc-job-state-change'
      );
    });
  });

  describe('buildSchema error handling', () => {
    test('throws when schema file is missing for non-existent version', () => {
      const app = new App();
      const stack = new Stack(app, 'TestStack');

      expect(() => {
        buildSchema(stack, 'fastqStateChange' as SchemaNames, '9999.01.01');
      }).toThrow(/Schema file not found/);
    });
  });
});
