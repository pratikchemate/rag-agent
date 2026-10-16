export interface CodeBlock {
  type: 'code';
  language: string;
  code: string;
}

export interface HeaderBlock {
  type: 'header';
  level: number;
  text: string;
}

export interface ListBlock {
  type: 'list';
  ordered: boolean;
  items: string[];
}

export interface ParagraphBlock {
  type: 'paragraph';
  text: string;
}

export type ContentBlock = CodeBlock | HeaderBlock | ListBlock | ParagraphBlock;

export interface InlineToken {
  type: 'text' | 'bold' | 'code' | 'citation';
  content: string;
  label?: string; // For citation (e.g. "S1")
}

/**
 * Parses inline formatting: **bold**, `code`, and [S1] citation tokens.
 */
export function parseInlineTokens(text: string): InlineToken[] {
  if (!text) return [];

  // Regex matches:
  // 1: Citation [S1]
  // 2: Bold **text**
  // 3: Inline code `code`
  const inlineRegex = /(\[S\d+\])|(\*\*[^*]+\*\*)|(`[^`]+`)/g;

  const tokens: InlineToken[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = inlineRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      tokens.push({
        type: 'text',
        content: text.slice(lastIndex, match.index),
      });
    }

    const fullMatch = match[0];
    if (match[1]) {
      // Citation [S1]
      const label = fullMatch.slice(1, -1);
      tokens.push({
        type: 'citation',
        content: fullMatch,
        label,
      });
    } else if (match[2]) {
      // Bold **content**
      tokens.push({
        type: 'bold',
        content: fullMatch.slice(2, -2),
      });
    } else if (match[3]) {
      // Inline code `content`
      tokens.push({
        type: 'code',
        content: fullMatch.slice(1, -1),
      });
    }

    lastIndex = inlineRegex.lastIndex;
  }

  if (lastIndex < text.length) {
    tokens.push({
      type: 'text',
      content: text.slice(lastIndex),
    });
  }

  return tokens;
}

/**
 * Parses markdown text into block-level elements (code, headers, lists, paragraphs).
 */
export function parseMarkdownBlocks(rawText: string): ContentBlock[] {
  if (!rawText) return [];

  const blocks: ContentBlock[] = [];
  const lines = rawText.split(/\r?\n/);

  let inCodeBlock = false;
  let codeLanguage = '';
  let codeBuffer: string[] = [];

  let currentListItems: string[] = [];
  let currentListOrdered = false;

  const flushList = () => {
    if (currentListItems.length > 0) {
      blocks.push({
        type: 'list',
        ordered: currentListOrdered,
        items: [...currentListItems],
      });
      currentListItems = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Fenced code block start/end
    if (trimmed.startsWith('```')) {
      flushList();
      if (inCodeBlock) {
        // Ending code block
        blocks.push({
          type: 'code',
          language: codeLanguage,
          code: codeBuffer.join('\n'),
        });
        inCodeBlock = false;
        codeLanguage = '';
        codeBuffer = [];
      } else {
        // Starting code block
        inCodeBlock = true;
        codeLanguage = trimmed.slice(3).trim();
        codeBuffer = [];
      }
      continue;
    }

    if (inCodeBlock) {
      codeBuffer.push(line);
      continue;
    }

    // Empty lines flush lists
    if (!trimmed) {
      flushList();
      continue;
    }

    // Headers (#, ##, ###)
    const headerMatch = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (headerMatch) {
      flushList();
      blocks.push({
        type: 'header',
        level: headerMatch[1].length,
        text: headerMatch[2],
      });
      continue;
    }

    // Bullet list items (-, *, •)
    const bulletMatch = trimmed.match(/^[-*•]\s+(.+)$/);
    if (bulletMatch) {
      if (currentListItems.length > 0 && currentListOrdered) {
        flushList();
      }
      currentListOrdered = false;
      currentListItems.push(bulletMatch[1]);
      continue;
    }

    // Numbered list items (1., 2., etc.)
    const orderedMatch = trimmed.match(/^\d+\.\s+(.+)$/);
    if (orderedMatch) {
      if (currentListItems.length > 0 && !currentListOrdered) {
        flushList();
      }
      currentListOrdered = true;
      currentListItems.push(orderedMatch[1]);
      continue;
    }

    // Otherwise, normal paragraph line
    flushList();
    blocks.push({
      type: 'paragraph',
      text: line,
    });
  }

  // Flush any remaining code or list blocks
  if (inCodeBlock) {
    blocks.push({
      type: 'code',
      language: codeLanguage,
      code: codeBuffer.join('\n'),
    });
  }
  flushList();

  return blocks;
}
