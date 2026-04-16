import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface ConversationHeaderProps {
  title: string;
  fullTitle: string;
  conversationId: number | null;
  isNew: boolean;
}

const ConversationHeader: React.FC<ConversationHeaderProps> = ({ title, fullTitle, conversationId, isNew }) => {
  return (
    <div className="shrink-0 z-10 px-6 py-4 pb-3 bg-bg border-b border-border bg-opacity-95 backdrop-blur-sm">
      <h1 className="fs-ui-2xl font-semibold text-text-bright font-sans truncate" title={fullTitle}>
        {fullTitle}
      </h1>
      <div className="flex items-center gap-2 mt-0.5">
        <span className="fs-ui-xs text-text-muted font-sans">
          {isNew ? (
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
              New Chat <span className="opacity-60">(unsaved)</span>
            </span>
          ) : (
            `Conversation #${conversationId}`
          )}
        </span>
      </div>
    </div>
  );
};

export default ConversationHeader;
