import * as fc from 'fast-check';
import { camelCaseToKebabCase } from '../infrastructure/stage/utils';

/**
 * Feature: event-schemas, Property 3: camelCase to kebab-case conversion
 *
 * Validates: Requirements 4.2
 *
 * For any string composed of one or more camelCase words (lowercase start,
 * uppercase word boundaries), the camelCaseToKebabCase function SHALL produce
 * a string that is entirely lowercase, uses hyphens as word separators, and
 * round-trips consistently (idempotence on already-converted strings).
 */
describe('Feature: event-schemas, Property 3: camelCase to kebab-case conversion', () => {
  const lowerChars = 'abcdefghijklmnopqrstuvwxyz';
  const lowerDigitChars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  const upperChars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

  // Generate a lowercase word (1-10 chars)
  const lowerWordGen = fc
    .array(fc.constantFrom(...lowerChars.split('')), { minLength: 1, maxLength: 10 })
    .map((chars) => chars.join(''));

  // Generate an uppercase-started word segment (e.g., "State", "Change", "A")
  const upperWordGen = fc
    .tuple(
      fc.constantFrom(...upperChars.split('')),
      fc
        .array(fc.constantFrom(...lowerDigitChars.split('')), { minLength: 0, maxLength: 10 })
        .map((chars) => chars.join(''))
    )
    .map(([upper, rest]) => upper + rest);

  // Generate camelCase strings: lowercase word followed by zero or more uppercase-started words
  const camelCaseGen = fc
    .tuple(lowerWordGen, fc.array(upperWordGen, { minLength: 0, maxLength: 5 }))
    .map(([first, words]) => first + words.join(''));

  test('result is entirely lowercase (no uppercase letters)', () => {
    fc.assert(
      fc.property(camelCaseGen, (input) => {
        const result = camelCaseToKebabCase(input);
        expect(result).toBe(result.toLowerCase());
      }),
      { numRuns: 100 }
    );
  });

  test('result contains only lowercase letters, digits, and hyphens', () => {
    fc.assert(
      fc.property(camelCaseGen, (input) => {
        const result = camelCaseToKebabCase(input);
        expect(result).toMatch(/^[a-z0-9-]+$/);
      }),
      { numRuns: 100 }
    );
  });

  test('idempotence: applying the function twice produces same result as once', () => {
    fc.assert(
      fc.property(camelCaseGen, (input) => {
        const result = camelCaseToKebabCase(input);
        const resultTwice = camelCaseToKebabCase(result);
        expect(resultTwice).toBe(result);
      }),
      { numRuns: 100 }
    );
  });
});
