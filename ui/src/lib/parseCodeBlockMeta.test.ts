/**
 * Unit tests for parseCodeBlockMeta() — SC-5 parser logic.
 *
 * Run with: cd ui && npx tsx src/lib/parseCodeBlockMeta.test.ts
 * No Vitest needed — plain TypeScript test runner pattern.
 */

import { parseCodeBlockMeta } from './parseCodeBlockMeta';

function assert(condition: boolean, msg: string) {
  if (!condition) throw new Error(`FAIL: ${msg}`);
  console.log(`  PASS: ${msg}`);
}

let passed = 0;
let failed = 0;

function test(_name: string, fn: () => void) {
  try {
    fn();
    passed++;
  } catch (e) {
    console.error(`  ${(e as Error).message}`);
    failed++;
  }
}

console.log('parseCodeBlockMeta tests:\n');

// Test 1: Valid pipe-delimited format
test('parses valid format', () => {
  const r1 = parseCodeBlockMeta('Code Block: fn | File: src/a.py | Language: Python | Type: function');
  assert(r1 !== null, 'parses valid format');
  assert(r1!.name === 'fn', 'extracts name');
  assert(r1!.file === 'src/a.py', 'extracts file');
  assert(r1!.language === 'Python', 'extracts language');
  assert(r1!.type === 'function', 'extracts type');
  assert(r1!.remainder === '', 'remainder is empty string when no newline');
});

// Test 2: Plain summary returns null
test('returns null for plain text', () => {
  assert(parseCodeBlockMeta('Normal summary text') === null, 'returns null for plain text');
});

// Test 3: Empty string returns null
test('returns null for empty string', () => {
  assert(parseCodeBlockMeta('') === null, 'returns null for empty string');
});

// Test 4: With narrative remainder
test('extracts remainder after newline', () => {
  const r4 = parseCodeBlockMeta(
    'Code Block: fn | File: src/a.py | Language: Python | Type: function\nSome narrative text'
  );
  assert(r4 !== null, 'parses format with remainder');
  assert(r4!.remainder === 'Some narrative text', 'extracts remainder correctly');
});

// Test 5: Incomplete format (< 4 pipe segments) returns null
test('returns null for incomplete format', () => {
  assert(parseCodeBlockMeta('Code Block: fn | incomplete') === null, 'returns null for incomplete format (< 4 segments)');
});

// Test 6: Class type
test('parses class type', () => {
  const r6 = parseCodeBlockMeta(
    'Code Block: MyClass | File: src/models.py | Language: Python | Type: class'
  );
  assert(r6 !== null, 'parses class entity');
  assert(r6!.type === 'class', 'extracts type=class');
  assert(r6!.name === 'MyClass', 'extracts class name');
});

// Test 7: TypeScript language
test('parses TypeScript language', () => {
  const r7 = parseCodeBlockMeta(
    'Code Block: parseCodeBlockMeta | File: ui/src/lib/parseCodeBlockMeta.ts | Language: TypeScript | Type: function'
  );
  assert(r7 !== null, 'parses TypeScript code block');
  assert(r7!.language === 'TypeScript', 'extracts TypeScript language');
  assert(r7!.file === 'ui/src/lib/parseCodeBlockMeta.ts', 'extracts full file path');
});

// Test 8: Multi-line remainder preserved
test('preserves multi-line remainder', () => {
  const r8 = parseCodeBlockMeta(
    'Code Block: process | File: src/worker.py | Language: Python | Type: function\nLine one\nLine two'
  );
  assert(r8 !== null, 'parses with multi-line remainder');
  assert(r8!.remainder === 'Line one\nLine two', 'preserves full multi-line remainder');
});

// Summary
console.log(`\n${passed + failed} tests: ${passed} passed, ${failed} failed`);
if (failed > 0) {
  throw new Error(`${failed} test(s) failed`);
} else {
  console.log('\nAll parseCodeBlockMeta tests passed!');
}
