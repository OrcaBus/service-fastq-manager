import * as path from 'path';
import * as fs from 'fs';
import fc from 'fast-check';
import Ajv2020 from 'ajv/dist/2020';
import addFormats from 'ajv-formats';
import { EVENT_SCHEMAS_DIR, DEFAULT_PAYLOAD_VERSION } from '../infrastructure/stage/constants';
import { schemaNamesList } from '../infrastructure/stage/event-schemas/interfaces';
import { camelCaseToKebabCase } from '../infrastructure/stage/utils';

/**
 * Property-Based Tests for Event Schemas
 *
 * Feature: event-schemas
 * Property 1: Valid payload acceptance
 *
 * Validates: Requirements 7.1, 7.2, 7.3, 7.7, 7.8
 */

// Set up Ajv with 2020-12 support and format validation
const ajv = new Ajv2020({ strict: false });
addFormats(ajv);

// Load all schema files
const schemas: Record<string, object> = {};
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

// --- Generators ---

// Generate a 26-char ULID string (uppercase letters and digits)
const ulidArb = fc.stringMatching(/^[A-Z0-9]{26}$/);

// Generate an OrcaBus ID: 3 lowercase alphanums + dot + 26 upper alphanums
const orcabusIdArb = fc.stringMatching(/^[a-z0-9]{3}\.[A-Z0-9]{26}$/);

// Generate a valid fqr ID
const fqrIdArb = ulidArb.map((ulid: string) => `fqr.${ulid}`);

// Generate a valid fqs ID
const fqsIdArb = ulidArb.map((ulid: string) => `fqs.${ulid}`);

// Generate a valid mqj ID
const mqjIdArb = ulidArb.map((ulid: string) => `mqj.${ulid}`);

// Generate a valid date string (YYYY-MM-DD)
const dateArb = fc
  .tuple(
    fc.integer({ min: 2000, max: 2099 }),
    fc.integer({ min: 1, max: 12 }),
    fc.integer({ min: 1, max: 28 })
  )
  .map(
    ([year, month, day]: [number, number, number]) =>
      `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
  );

// Generate a non-empty string
const nonEmptyStringArb = fc.string({ minLength: 1, maxLength: 50 });

// Generate a Library object
const libraryArb = fc.record({
  orcabusId: orcabusIdArb,
  libraryId: nonEmptyStringArb,
});

// Generate a FileStorageObject with optional fields
const fileStorageObjectArb = fc
  .record({
    ingestId: nonEmptyStringArb,
    s3Uri: fc.option(nonEmptyStringArb, { nil: undefined }),
    storageClass: fc.option(nonEmptyStringArb, { nil: undefined }),
    sha256: fc.option(nonEmptyStringArb, { nil: undefined }),
  })
  .map(stripUndefined);

// Generate a FastqStorageObject with optional fields
const fastqStorageObjectArb = fc
  .record({
    ingestId: nonEmptyStringArb,
    s3Uri: fc.option(nonEmptyStringArb, { nil: undefined }),
    storageClass: fc.option(nonEmptyStringArb, { nil: undefined }),
    sha256: fc.option(nonEmptyStringArb, { nil: undefined }),
    gzipCompressionSizeInBytes: fc.option(fc.nat(), { nil: undefined }),
    rawMd5sum: fc.option(nonEmptyStringArb, { nil: undefined }),
  })
  .map(stripUndefined);

// Generate a FastqPairStorageObject
const fastqPairStorageObjectArb = fc
  .record({
    r1: fastqStorageObjectArb,
    r2: fc.option(fastqStorageObjectArb, { nil: undefined }),
    compressionFormat: fc.option(fc.constantFrom('GZIP' as const, 'ORA' as const), {
      nil: undefined,
    }),
  })
  .map(stripUndefined);

// Generate a QcInformation object (all fields optional)
const qcInformationArb = fc
  .record({
    insertSizeEstimate: fc.option(fc.double({ min: 0, max: 10000, noNaN: true }), {
      nil: undefined,
    }),
    rawWgsCoverageEstimate: fc.option(fc.double({ min: 0, max: 1000, noNaN: true }), {
      nil: undefined,
    }),
    r1Q20Fraction: fc.option(fc.double({ min: 0, max: 1, noNaN: true }), { nil: undefined }),
    r2Q20Fraction: fc.option(fc.double({ min: 0, max: 1, noNaN: true }), { nil: undefined }),
    r1GcFraction: fc.option(fc.double({ min: 0, max: 1, noNaN: true }), { nil: undefined }),
    r2GcFraction: fc.option(fc.double({ min: 0, max: 1, noNaN: true }), { nil: undefined }),
    duplicationFractionEstimate: fc.option(fc.double({ min: 0, max: 1, noNaN: true }), {
      nil: undefined,
    }),
    sequaliReports: fc.option(fc.constant({}), { nil: undefined }),
  })
  .map(stripUndefined);

// FastqStateChange status enum
const fastqStatusArb = fc.constantFrom(
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
  'FASTQ_SET_UPDATED'
);

// FastqSetStateChange status enum
const fastqSetStatusArb = fc.constantFrom(
  'FASTQ_SET_CREATED',
  'FASTQ_SET_DELETED',
  'FASTQ_LINKED',
  'FASTQ_UNLINKED',
  'FASTQ_SET_IS_CURRENT',
  'FASTQ_SET_IS_NOT_CURRENT',
  'FASTQ_SET_ADDITIONAL_FASTQS_ALLOWED',
  'FASTQ_SET_ADDITIONAL_FASTQS_DISALLOWED',
  'FASTQ_SET_MERGED',
  'SOMALIER_UPDATED'
);

// FastqMultiqcJobStateChange status enum
const multiqcStatusArb = fc.constantFrom('PENDING', 'RUNNING', 'FAILED', 'ABORTED', 'SUCCEEDED');

// --- Helper to strip undefined values from objects ---
function stripUndefined(obj: Record<string, unknown>): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(obj)) {
    if (value !== undefined) {
      if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
        result[key] = stripUndefined(value as Record<string, unknown>);
      } else if (Array.isArray(value)) {
        result[key] = value.map((item) =>
          item !== null && typeof item === 'object'
            ? stripUndefined(item as Record<string, unknown>)
            : item
        );
      } else {
        result[key] = value;
      }
    }
  }
  return result;
}

// --- Valid payload generators ---

// FastqStateChange valid payload generator
const fastqStateChangePayloadArb = fc
  .record({
    id: fqrIdArb,
    status: fastqStatusArb,
    library: libraryArb,
    index: nonEmptyStringArb,
    lane: fc.integer({ min: 1, max: 100 }),
    instrumentRunId: nonEmptyStringArb,
    fastqSetId: fc.option(fqsIdArb, { nil: undefined }),
    platform: fc.option(nonEmptyStringArb, { nil: undefined }),
    center: fc.option(nonEmptyStringArb, { nil: undefined }),
    date: fc.option(dateArb, { nil: undefined }),
    readSet: fc.option(fastqPairStorageObjectArb, { nil: undefined }),
    qc: fc.option(qcInformationArb, { nil: undefined }),
    ntsm: fc.option(fileStorageObjectArb, { nil: undefined }),
    readCount: fc.option(fc.nat(), { nil: undefined }),
    baseCountEst: fc.option(fc.nat(), { nil: undefined }),
    isValid: fc.option(fc.boolean(), { nil: undefined }),
  })
  .map(stripUndefined);

// FastqResponse object for FastqSetStateChange fastqSet array items
const fastqResponseArb = fc
  .record({
    id: fqrIdArb,
    index: nonEmptyStringArb,
    lane: fc.integer({ min: 1, max: 100 }),
    instrumentRunId: nonEmptyStringArb,
    library: libraryArb,
    fastqSetId: fc.option(fqsIdArb, { nil: undefined }),
    platform: fc.option(nonEmptyStringArb, { nil: undefined }),
    center: fc.option(nonEmptyStringArb, { nil: undefined }),
    date: fc.option(dateArb, { nil: undefined }),
    readSet: fc.option(fc.constant({}), { nil: undefined }),
    qc: fc.option(fc.constant({}), { nil: undefined }),
    ntsm: fc.option(fc.constant({}), { nil: undefined }),
    readCount: fc.option(fc.nat(), { nil: undefined }),
    baseCountEst: fc.option(fc.nat(), { nil: undefined }),
    isValid: fc.option(fc.boolean(), { nil: undefined }),
  })
  .map(stripUndefined);

// Somalier file storage object
const somalierArb = fc
  .record({
    ingestId: nonEmptyStringArb,
    s3Uri: fc.option(nonEmptyStringArb, { nil: undefined }),
    storageClass: fc.option(nonEmptyStringArb, { nil: undefined }),
    sha256: fc.option(nonEmptyStringArb, { nil: undefined }),
  })
  .map(stripUndefined);

// FastqSetStateChange valid payload generator
const fastqSetStateChangePayloadArb = fc
  .record({
    id: fqsIdArb,
    status: fastqSetStatusArb,
    library: libraryArb,
    fastqSet: fc.array(fastqResponseArb, { minLength: 1, maxLength: 5 }),
    allowAdditionalFastq: fc.option(fc.boolean(), { nil: undefined }),
    isCurrentFastqSet: fc.option(fc.boolean(), { nil: undefined }),
    somalier: fc.option(somalierArb, { nil: undefined }),
  })
  .map(stripUndefined);

// FastqMultiqcJobStateChange valid payload generator
const fastqMultiqcJobStateChangePayloadArb = fc
  .record({
    id: mqjIdArb,
    status: multiqcStatusArb,
    fastqIdList: fc.array(fqrIdArb, { minLength: 1, maxLength: 10 }),
    stepsExecutionArn: fc.option(nonEmptyStringArb, { nil: undefined }),
    multiqcHtml: fc.option(fileStorageObjectArb, { nil: undefined }),
    multiqcParquet: fc.option(fileStorageObjectArb, { nil: undefined }),
  })
  .map(stripUndefined);

// --- Tests ---

describe('Feature: event-schemas, Property 1: Valid payload acceptance', () => {
  /**
   * Validates: Requirements 7.1, 7.2, 7.3, 7.7, 7.8
   *
   * For any event schema and for any payload constructed with all required fields
   * having valid types and patterns, plus any subset of optional fields with correct
   * types, JSON Schema validation SHALL produce zero errors.
   */

  test('FastqStateChange schema accepts all valid payloads', () => {
    const validate = ajv.compile(schemas['fastqStateChange']);

    fc.assert(
      fc.property(fastqStateChangePayloadArb, (payload) => {
        const valid = validate(payload);
        if (!valid) {
          throw new Error(
            `Validation failed for payload: ${JSON.stringify(payload, null, 2)}\nErrors: ${JSON.stringify(validate.errors, null, 2)}`
          );
        }
        return valid === true;
      }),
      { numRuns: 100 }
    );
  });

  test('FastqSetStateChange schema accepts all valid payloads', () => {
    const validate = ajv.compile(schemas['fastqSetStateChange']);

    fc.assert(
      fc.property(fastqSetStateChangePayloadArb, (payload) => {
        const valid = validate(payload);
        if (!valid) {
          throw new Error(
            `Validation failed for payload: ${JSON.stringify(payload, null, 2)}\nErrors: ${JSON.stringify(validate.errors, null, 2)}`
          );
        }
        return valid === true;
      }),
      { numRuns: 100 }
    );
  });

  test('FastqMultiqcJobStateChange schema accepts all valid payloads', () => {
    const validate = ajv.compile(schemas['fastqMultiqcJobStateChange']);

    fc.assert(
      fc.property(fastqMultiqcJobStateChangePayloadArb, (payload) => {
        const valid = validate(payload);
        if (!valid) {
          throw new Error(
            `Validation failed for payload: ${JSON.stringify(payload, null, 2)}\nErrors: ${JSON.stringify(validate.errors, null, 2)}`
          );
        }
        return valid === true;
      }),
      { numRuns: 100 }
    );
  });
});
