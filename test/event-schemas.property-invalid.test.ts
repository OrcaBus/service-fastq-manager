/**
 * Property-Based Tests: Invalid Payload Rejection
 *
 * Feature: event-schemas, Property 2: Invalid payload rejection
 *
 * Validates: Requirements 1.8, 7.4, 7.5, 7.6
 *
 * For any event schema and for any payload that violates at least one schema constraint
 * (missing required field, wrong type, invalid pattern, invalid enum value, or extra
 * properties where additionalProperties is false), JSON Schema validation SHALL produce
 * at least one error.
 */

import * as fc from 'fast-check';
import * as fs from 'fs';
import * as path from 'path';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';

// Load schemas
const schemasDir = path.join(__dirname, '..', 'app', 'event-schemas');

const fastqStateChangeSchema = JSON.parse(
  fs.readFileSync(path.join(schemasDir, 'fastq-state-change', '2025.06.04', 'schema.json'), 'utf-8')
);

const fastqSetStateChangeSchema = JSON.parse(
  fs.readFileSync(
    path.join(schemasDir, 'fastq-set-state-change', '2025.06.04', 'schema.json'),
    'utf-8'
  )
);

const fastqMultiqcJobStateChangeSchema = JSON.parse(
  fs.readFileSync(
    path.join(schemasDir, 'fastq-multiqc-job-state-change', '2025.06.04', 'schema.json'),
    'utf-8'
  )
);

// Set up Ajv (validateSchema: false to skip $schema 2020-12 meta-schema check)
const ajv = new Ajv({ strict: false, allErrors: true, validateSchema: false });
addFormats(ajv);

const validateFastqStateChange = ajv.compile(fastqStateChangeSchema);
const validateFastqSetStateChange = ajv.compile(fastqSetStateChangeSchema);
const validateFastqMultiqcJobStateChange = ajv.compile(fastqMultiqcJobStateChangeSchema);

// --- Valid base payloads ---
function validFastqStateChangePayload(): Record<string, unknown> {
  return {
    id: 'fqr.AAAAAAAAAAAAAAAAAAAAAAAAAA',
    status: 'FASTQ_CREATED',
    library: {
      orcabusId: 'lib.AAAAAAAAAAAAAAAAAAAAAAAAAA',
      libraryId: 'L000001',
    },
    index: 'ATCGATCG',
    lane: 1,
    instrumentRunId: 'run001',
  };
}

function validFastqSetStateChangePayload(): Record<string, unknown> {
  return {
    id: 'fqs.AAAAAAAAAAAAAAAAAAAAAAAAAA',
    status: 'FASTQ_SET_CREATED',
    library: {
      orcabusId: 'lib.AAAAAAAAAAAAAAAAAAAAAAAAAA',
      libraryId: 'L000001',
    },
    fastqSet: [
      {
        id: 'fqr.AAAAAAAAAAAAAAAAAAAAAAAAAA',
        index: 'ATCGATCG',
        lane: 1,
        instrumentRunId: 'run001',
        library: {
          orcabusId: 'lib.AAAAAAAAAAAAAAAAAAAAAAAAAA',
          libraryId: 'L000001',
        },
      },
    ],
  };
}

function validFastqMultiqcJobStateChangePayload(): Record<string, unknown> {
  return {
    id: 'mqj.AAAAAAAAAAAAAAAAAAAAAAAAAA',
    status: 'PENDING',
    fastqIdList: ['fqr.AAAAAAAAAAAAAAAAAAAAAAAAAA'],
  };
}

// --- Mutation types ---
type MutationType =
  | 'removeRequired'
  | 'wrongType'
  | 'invalidPattern'
  | 'invalidEnum'
  | 'extraProperty';

// --- Mutation strategies for FastqStateChange ---
function mutateFastqStateChange(mutation: MutationType, seed: number): Record<string, unknown> {
  const payload = validFastqStateChangePayload();
  const requiredFields = ['id', 'status', 'library', 'index', 'lane', 'instrumentRunId'];

  switch (mutation) {
    case 'removeRequired': {
      const fieldIndex = seed % requiredFields.length;
      delete payload[requiredFields[fieldIndex]];
      break;
    }
    case 'wrongType': {
      // Replace a string field with a number, or integer with a string
      const typeTargets: Array<[string, unknown]> = [
        ['id', 12345],
        ['status', true],
        ['index', 99],
        ['lane', 'not-a-number'],
        ['instrumentRunId', false],
        ['library', 'not-an-object'],
      ];
      const target = typeTargets[seed % typeTargets.length];
      payload[target[0]] = target[1];
      break;
    }
    case 'invalidPattern': {
      // Use an id that doesn't match the required pattern
      const invalidIds = [
        'invalid-id',
        'fqr.lowercase',
        'fqs.AAAAAAAAAAAAAAAAAAAAAAAAAA', // wrong prefix
        'fqr.SHORT',
        'fqr.aaaaaaaaaaaaaaaaaaaaaaaaaa', // lowercase
      ];
      payload['id'] = invalidIds[seed % invalidIds.length];
      break;
    }
    case 'invalidEnum': {
      payload['status'] = 'INVALID_STATUS_VALUE';
      break;
    }
    case 'extraProperty': {
      payload['additionalProperty'] = 'value';
      break;
    }
  }
  return payload;
}

// --- Mutation strategies for FastqSetStateChange ---
function mutateFastqSetStateChange(mutation: MutationType, seed: number): Record<string, unknown> {
  const payload = validFastqSetStateChangePayload();
  const requiredFields = ['id', 'status', 'library', 'fastqSet'];

  switch (mutation) {
    case 'removeRequired': {
      const fieldIndex = seed % requiredFields.length;
      delete payload[requiredFields[fieldIndex]];
      break;
    }
    case 'wrongType': {
      const typeTargets: Array<[string, unknown]> = [
        ['id', 12345],
        ['status', 42],
        ['library', 'not-an-object'],
        ['fastqSet', 'not-an-array'],
      ];
      const target = typeTargets[seed % typeTargets.length];
      payload[target[0]] = target[1];
      break;
    }
    case 'invalidPattern': {
      const invalidIds = [
        'invalid-id',
        'fqs.lowercase',
        'fqr.AAAAAAAAAAAAAAAAAAAAAAAAAA', // wrong prefix
        'fqs.SHORT',
        'fqs.aaaaaaaaaaaaaaaaaaaaaaaaaa', // lowercase
      ];
      payload['id'] = invalidIds[seed % invalidIds.length];
      break;
    }
    case 'invalidEnum': {
      payload['status'] = 'INVALID_STATUS_VALUE';
      break;
    }
    case 'extraProperty': {
      payload['additionalProperty'] = 'value';
      break;
    }
  }
  return payload;
}

// --- Mutation strategies for FastqMultiqcJobStateChange ---
function mutateFastqMultiqcJobStateChange(
  mutation: MutationType,
  seed: number
): Record<string, unknown> {
  const payload = validFastqMultiqcJobStateChangePayload();
  const requiredFields = ['id', 'status', 'fastqIdList'];

  switch (mutation) {
    case 'removeRequired': {
      const fieldIndex = seed % requiredFields.length;
      delete payload[requiredFields[fieldIndex]];
      break;
    }
    case 'wrongType': {
      const typeTargets: Array<[string, unknown]> = [
        ['id', 12345],
        ['status', false],
        ['fastqIdList', 'not-an-array'],
      ];
      const target = typeTargets[seed % typeTargets.length];
      payload[target[0]] = target[1];
      break;
    }
    case 'invalidPattern': {
      const invalidIds = [
        'invalid-id',
        'mqj.lowercase',
        'fqr.AAAAAAAAAAAAAAAAAAAAAAAAAA', // wrong prefix
        'mqj.SHORT',
        'mqj.aaaaaaaaaaaaaaaaaaaaaaaaaa', // lowercase
      ];
      payload['id'] = invalidIds[seed % invalidIds.length];
      break;
    }
    case 'invalidEnum': {
      payload['status'] = 'INVALID_STATUS_VALUE';
      break;
    }
    case 'extraProperty': {
      payload['additionalProperty'] = 'value';
      break;
    }
  }
  return payload;
}

// --- Arbitraries ---
const mutationArb = fc.oneof(
  fc.constant('removeRequired' as MutationType),
  fc.constant('wrongType' as MutationType),
  fc.constant('invalidPattern' as MutationType),
  fc.constant('invalidEnum' as MutationType),
  fc.constant('extraProperty' as MutationType)
);

const seedArb = fc.nat({ max: 1000 });

describe('Feature: event-schemas, Property 2: Invalid payload rejection', () => {
  /**
   * **Validates: Requirements 1.8, 7.4, 7.5, 7.6**
   *
   * For any event schema and for any payload that violates at least one schema constraint,
   * JSON Schema validation SHALL produce at least one error.
   */

  test('FastqStateChange: any mutated payload produces at least one validation error', () => {
    fc.assert(
      fc.property(mutationArb, seedArb, (mutation, seed) => {
        const payload = mutateFastqStateChange(mutation, seed);
        const valid = validateFastqStateChange(payload);
        expect(valid).toBe(false);
        expect(validateFastqStateChange.errors).not.toBeNull();
        expect(validateFastqStateChange.errors!.length).toBeGreaterThanOrEqual(1);
      }),
      { numRuns: 100 }
    );
  });

  test('FastqSetStateChange: any mutated payload produces at least one validation error', () => {
    fc.assert(
      fc.property(mutationArb, seedArb, (mutation, seed) => {
        const payload = mutateFastqSetStateChange(mutation, seed);
        const valid = validateFastqSetStateChange(payload);
        expect(valid).toBe(false);
        expect(validateFastqSetStateChange.errors).not.toBeNull();
        expect(validateFastqSetStateChange.errors!.length).toBeGreaterThanOrEqual(1);
      }),
      { numRuns: 100 }
    );
  });

  test('FastqMultiqcJobStateChange: any mutated payload produces at least one validation error', () => {
    fc.assert(
      fc.property(mutationArb, seedArb, (mutation, seed) => {
        const payload = mutateFastqMultiqcJobStateChange(mutation, seed);
        const valid = validateFastqMultiqcJobStateChange(payload);
        expect(valid).toBe(false);
        expect(validateFastqMultiqcJobStateChange.errors).not.toBeNull();
        expect(validateFastqMultiqcJobStateChange.errors!.length).toBeGreaterThanOrEqual(1);
      }),
      { numRuns: 100 }
    );
  });
});
