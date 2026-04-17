import React from 'react';
import ConversationHeader from './ConversationHeader';
import ChatView from './ChatView';
import InputBar from './InputBar';
import type { TabState, DisplayMessage, FileAttachment } from '../types';

interface TabContentProps {
  tab: TabState;
  isActive: boolean;
  // Temporary: passing actions and state from App.tsx until state is fully migrated to context
  useMarkdown: boolean;
  apiKeySet: boolean;
  memoriesActive: boolean;
  onSendMessage: (text: string) => void;
  onStopGeneration: () => void;
  onEditMessage: (index: number, content: string) => void;
  onRegenerateMessage: (index: number) => void;
  onDeleteMessage: (index: number) => void;
  onAttachFiles: () => void;
  onRemoveStagedFile: (name: string) => void;
  onInputChange: (text: string) => void;
  onDismissError: () => void;
  onOpenSettings: (tab: string) => void;
}

const TabContent: React.FC<TabContentProps> = ({
  tab,
  isActive,
  useMarkdown,
  apiKeySet,
  memoriesActive,
  onSendMessage,
  onStopGeneration,
  onEditMessage,
  onRegenerateMessage,
  onDeleteMessage,
  onAttachFiles,
  onRemoveStagedFile,
  onInputChange,
  onDismissError,
  onOpenSettings,
}) => {
  return (
    <div className={`flex-1 flex flex-col min-h-0 ${isActive ? 'flex' : 'hidden'}`}>
      <ConversationHeader
        title={tab.title}
        fullTitle={tab.fullTitle}
        conversationId={tab.conversationId}
        isNew={tab.isNew}
      />
      
      <div className="flex-1 relative overflow-hidden">
        <ChatView
          messages={tab.messages}
          isStreaming={tab.isStreaming}
          streamContent={tab.streamContent}
          streamModel={tab.streamModel}
          useMarkdown={useMarkdown}
          onEdit={onEditMessage}
          onRegenerate={onRegenerateMessage}
          onDelete={onDeleteMessage}
          error={tab.error}
          onDismissError={onDismissError}
        />
      </div>

      <InputBar
        onSend={onSendMessage}
        onStop={onStopGeneration}
        isStreaming={tab.isStreaming}
        onAttach={onAttachFiles}
        stagedFiles={tab.stagedFiles}
        onRemoveFile={onRemoveStagedFile}
        apiKeySet={apiKeySet}
        memoriesActive={memoriesActive}
        onOpenSettings={() => onOpenSettings('api')}
        onInputChange={onInputChange}
      />
    </div>
  );
};

export default TabContent;
