import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { Citation } from '../../types';
import {
  ContentBlock,
  InlineToken,
  parseInlineTokens,
  parseMarkdownBlocks,
} from './markdownParser';

interface MessageContentProps {
  text: string;
  citations?: Citation[];
  onOpenCitation: (citation: Citation) => void;
}

export const MessageContent: React.FC<MessageContentProps> = ({
  text,
  citations,
  onOpenCitation,
}) => {
  const [copiedCodeIndex, setCopiedCodeIndex] = useState<number | null>(null);

  const handleCopyCode = (code: string, index: number) => {
    navigator.clipboard.writeText(code);
    setCopiedCodeIndex(index);
    setTimeout(() => setCopiedCodeIndex(null), 2000);
  };

  const renderInline = (tokens: InlineToken[], keyPrefix: string) => {
    return tokens.map((token, idx) => {
      const key = `${keyPrefix}-${idx}`;

      if (token.type === 'citation') {
        const citation = citations?.find((c) => c.label === token.label);
        return (
          <button
            key={key}
            type="button"
            onClick={() => citation && onOpenCitation(citation)}
            disabled={!citation}
            title={
              citation
                ? `Source: ${citation.filename}${
                    citation.page_number ? ` (Page ${citation.page_number})` : ''
                  }\n\n"${citation.excerpt.slice(0, 160)}..."`
                : 'Unverified source'
            }
            className="inline-flex items-center gap-0.5 mx-0.5 px-1.5 py-0.5 rounded-md text-[11px] font-bold font-mono bg-indigo-50 hover:bg-indigo-100 text-indigo-700 hover:text-indigo-900 border border-indigo-200/80 hover:border-indigo-300 transition-all cursor-pointer shadow-2xs group align-baseline"
          >
            <span>{token.label}</span>
          </button>
        );
      }

      if (token.type === 'bold') {
        return (
          <strong key={key} className="font-semibold text-slate-900">
            {token.content}
          </strong>
        );
      }

      if (token.type === 'code') {
        return (
          <code
            key={key}
            className="px-1.5 py-0.5 rounded-md bg-slate-100 border border-slate-200 text-indigo-700 font-mono text-[12px]"
          >
            {token.content}
          </code>
        );
      }

      return <span key={key}>{token.content}</span>;
    });
  };

  const blocks: ContentBlock[] = parseMarkdownBlocks(text);

  return (
    <div className="space-y-3 text-[13.5px] leading-relaxed text-slate-800">
      {blocks.map((block, idx) => {
        if (block.type === 'header') {
          const inlineTokens = parseInlineTokens(block.text);
          if (block.level === 1) {
            return (
              <h3 key={idx} className="text-base font-bold text-slate-900 pt-2 pb-1 border-b border-slate-100">
                {renderInline(inlineTokens, `h1-${idx}`)}
              </h3>
            );
          }
          if (block.level === 2) {
            return (
              <h4 key={idx} className="text-sm font-bold text-slate-900 pt-1">
                {renderInline(inlineTokens, `h2-${idx}`)}
              </h4>
            );
          }
          return (
            <h5 key={idx} className="text-[13px] font-semibold text-slate-900 uppercase tracking-wide text-indigo-900 pt-1">
              {renderInline(inlineTokens, `h3-${idx}`)}
            </h5>
          );
        }

        if (block.type === 'list') {
          return (
            <ul key={idx} className="space-y-1.5 my-2 pl-2">
              {block.items.map((item, itemIdx) => {
                const inlineTokens = parseInlineTokens(item);
                return (
                  <li key={itemIdx} className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-2 flex-shrink-0" />
                    <span className="flex-1">{renderInline(inlineTokens, `li-${idx}-${itemIdx}`)}</span>
                  </li>
                );
              })}
            </ul>
          );
        }

        if (block.type === 'code') {
          return (
            <div key={idx} className="relative rounded-xl overflow-hidden bg-slate-900 border border-slate-800 text-slate-100 my-3 group">
              <div className="flex items-center justify-between px-3.5 py-1.5 bg-slate-800/80 border-b border-slate-700/60 text-[11px] font-mono text-slate-400">
                <span>{block.language || 'code'}</span>
                <button
                  type="button"
                  onClick={() => handleCopyCode(block.code, idx)}
                  className="flex items-center gap-1 hover:text-white transition-colors"
                  title="Copy code"
                >
                  {copiedCodeIndex === idx ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="text-emerald-400">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>
              <pre className="p-3.5 overflow-x-auto text-[12px] font-mono leading-normal">
                <code>{block.code}</code>
              </pre>
            </div>
          );
        }

        // Paragraph
        const inlineTokens = parseInlineTokens(block.text);
        return (
          <p key={idx} className="leading-relaxed">
            {renderInline(inlineTokens, `p-${idx}`)}
          </p>
        );
      })}
    </div>
  );
};
