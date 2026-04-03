/**
 * Standalone parser for pipe-delimited code block metadata embedded in entity summaries.
 *
 * Format: "Code Block: <name> | File: <path> | Language: <lang> | Type: <type>"
 * Per D-09: format-driven (summary prefix), not entity-type-driven (tags).
 *
 * Extracted from EntityPanel.tsx for independent testability (SC-5).
 */

export interface CodeBlockMeta {
  name: string;
  file: string;
  language: string;
  type: string;
  remainder: string;  // summary text after the structured prefix
}

/**
 * Parse pipe-delimited code block metadata from an entity summary string.
 *
 * Returns null for:
 * - Strings that don't start with "Code Block:"
 * - Strings with fewer than 4 pipe-delimited segments
 * - Strings missing required name or file fields
 */
export function parseCodeBlockMeta(summary: string): CodeBlockMeta | null {
  if (!summary.startsWith('Code Block:')) return null;

  // Split only the first line (structured prefix may be followed by narrative)
  const firstLine = summary.split('\n')[0];
  const parts = firstLine.split(' | ');
  if (parts.length < 4) return null;

  const name = parts[0].replace('Code Block:', '').trim();
  const file = parts.find(p => p.startsWith('File:'))?.replace('File:', '').trim() ?? '';
  const language = parts.find(p => p.startsWith('Language:'))?.replace('Language:', '').trim() ?? '';
  const type = parts.find(p => p.startsWith('Type:'))?.replace('Type:', '').trim() ?? '';

  if (!name || !file) return null;

  // Everything after the first line is the narrative remainder
  const remainder = summary.slice(firstLine.length).trim();

  return { name, file, language, type, remainder };
}
