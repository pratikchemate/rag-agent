import { describe, it, expect } from 'vitest';
import { parseInlineTokens, parseMarkdownBlocks } from './markdownParser';

describe('markdownParser', () => {
  describe('parseInlineTokens', () => {
    it('parses plain text without formatting', () => {
      const tokens = parseInlineTokens('Simple plain text string');
      expect(tokens).toEqual([
        { type: 'text', content: 'Simple plain text string' },
      ]);
    });

    it('parses citations correctly', () => {
      const tokens = parseInlineTokens('According to the policy [S1], retries are capped [S2].');
      expect(tokens).toEqual([
        { type: 'text', content: 'According to the policy ' },
        { type: 'citation', content: '[S1]', label: 'S1' },
        { type: 'text', content: ', retries are capped ' },
        { type: 'citation', content: '[S2]', label: 'S2' },
        { type: 'text', content: '.' },
      ]);
    });

    it('parses bold text and inline code', () => {
      const tokens = parseInlineTokens('Use **POST /chat** with `Authorization` header [S1].');
      expect(tokens).toEqual([
        { type: 'text', content: 'Use ' },
        { type: 'bold', content: 'POST /chat' },
        { type: 'text', content: ' with ' },
        { type: 'code', content: 'Authorization' },
        { type: 'text', content: ' header ' },
        { type: 'citation', content: '[S1]', label: 'S1' },
        { type: 'text', content: '.' },
      ]);
    });
  });

  describe('parseMarkdownBlocks', () => {
    it('parses headers, lists, code blocks, and paragraphs', () => {
      const markdown = `### LSTM Architecture [S1]
LSTM networks use three gates:
- Forget Gate [S1]
- Input Gate [S2]
- Output Gate [S3]

\`\`\`python
def forward(x):
    return x
\`\`\`
Conclusion sentence.`;

      const blocks = parseMarkdownBlocks(markdown);
      expect(blocks).toHaveLength(5);

      expect(blocks[0]).toEqual({
        type: 'header',
        level: 3,
        text: 'LSTM Architecture [S1]',
      });

      expect(blocks[1]).toEqual({
        type: 'paragraph',
        text: 'LSTM networks use three gates:',
      });

      expect(blocks[2]).toEqual({
        type: 'list',
        ordered: false,
        items: ['Forget Gate [S1]', 'Input Gate [S2]', 'Output Gate [S3]'],
      });

      expect(blocks[3]).toEqual({
        type: 'code',
        language: 'python',
        code: 'def forward(x):\n    return x',
      });

      expect(blocks[4]).toEqual({
        type: 'paragraph',
        text: 'Conclusion sentence.',
      });
    });
  });
});
