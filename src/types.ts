// src/types.ts

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
}

export interface Message {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  model_used: string | null;
  temperature_used: number | null;
}

export interface Model {
  name: string;
  id: string;
}

export interface SystemPrompt {
  id: number;
  name: string;
  prompt_text: string;
  when_to_use: string;
}

export interface ChatOpts {
  webSearch?: boolean;
}

export interface LoadedConversationState {
  modelId: string | null;
  systemPrompt: string | null;
  temperature: number | null;
  webSearch: boolean;
}

export interface LoadedConversation {
  messages: Message[];
  state: LoadedConversationState;
}

export interface FileAttachment {
  path: string;
  name: string;
  content: string;
}

export interface DisplayMessage {
  idx: number;      // actual backend array index (stable across edits)
  role: 'user' | 'assistant' | 'system';
  html: string;
  raw: string;      // user-typed text only (file content stripped)
  fullRaw: string;  // FULL raw content including file blocks
  model: string;
}

export interface TabState {
  id: string;
  conversationId: number | null;
  title: string;
  fullTitle: string;
  messages: DisplayMessage[];
  selectedModel: string;
  temperature: number;
  selectedPrompt: string | null;
  useWebSearch: boolean;
  isStreaming: boolean;
  streamContent: string;
  streamModel: string;
  error: string | null;
  pendingInput: string;
  stagedFiles: FileAttachment[];
  isNew: boolean;
  isDirty: boolean;
}

export interface TabContextType {
  tabs: TabState[];
  activeTabId: string;
  activeTab: TabState;
  openTab: (options?: { conversationId?: number; title?: string }) => Promise<string>;
  closeTab: (tabId: string) => Promise<void>;
  switchTab: (tabId: string) => Promise<void>;
  updateTab: (tabId: string, updates: Partial<TabState>) => void;
  reorderTabs: (fromIndex: number, toIndex: number) => void;
  saveTabToBackend: (tabId: string) => Promise<void>;
  loadConversationIntoNewTab: (conversationId: number) => Promise<string>;
  loadConversationIntoTab: (conversationId: number, tabId: string) => Promise<string>;
  findTabByConversationId: (conversationId: number) => string | null;
  getTabIndex: (tabId: string) => number;
  updateTabsForConversation: (conversationId: number, title: string) => void;
}

export interface AppSettings {
  api_timeout: number;
  chat_font_size: number;
  chat_font_family: string;
  ui_font_size: number;
  ui_font_family: string;
  mono_font_family: string;
  mono_font_size: number;
  confirm_close: boolean;
  apiKeySet: boolean;
}

// Electron preload API
declare global {
  interface Window {
    api: {
      convList: () => Promise<Conversation[]>;
      convNew: () => Promise<boolean>;
      convLoad: (id: number) => Promise<LoadedConversation>;
      convDelete: (id: number) => Promise<boolean>;
      convRename: (id: number, title: string) => Promise<boolean>;
      convExport: (id: number) => Promise<string>;
      convImport: (json: string) => Promise<boolean>;
      tabSwitch: (tabId: string | null) => Promise<boolean>;
      tabClose: (tabId: string) => Promise<boolean>;

      chatSend: (tabId: string, text: string, modelId: string, temp: number, sysPrompt: string | null, opts: ChatOpts) => Promise<{ conversations: Conversation[]; tokenCount: number }>;
      chatStop: (tabId: string) => Promise<boolean>;
      chatEdit: (tabId: string, index: number, content: string, modelId: string, temp: number, opts: ChatOpts) => Promise<{ conversations: Conversation[]; tokenCount: number }>;
      chatRegenerate: (tabId: string, index: number, modelId: string, temp: number, opts: ChatOpts) => Promise<{ conversations: Conversation[]; tokenCount: number }>;
      chatDeleteMsg: (tabId: string, index: number) => Promise<{ messages: Message[]; tokenCount: number }>;
      chatGetMessages: (tabId: string) => Promise<Message[]>;
      chatGetFullMessages: (tabId: string) => Promise<Message[]>;
      chatTokenCount: (tabId: string) => Promise<number>;
      chatTokenCountFull: (tabId: string, text: string) => Promise<number>;

      modelsList: () => Promise<Model[]>;
      modelsAdd: (name: string, id: string) => Promise<Model[]>;
      modelsUpdate: (idx: number, name: string, id: string) => Promise<Model[]>;
      modelsDelete: (idx: number) => Promise<Model[]>;
      modelsMove: (idx: number, dir: 'up' | 'down') => Promise<Model[]>;
      modelsMetadata: (modelId?: string | null) => Promise<Record<string, any>>;

      promptsList: () => Promise<SystemPrompt[]>;
      promptsSave: (id: number | null, name: string, text: string, whenToUse?: string) => Promise<SystemPrompt[]>;
      promptsDelete: (id: number) => Promise<SystemPrompt[]>;

      settingsGet: () => Promise<AppSettings>;
      settingsSet: (key: string, value: any) => Promise<boolean>;
      settingsGetApiKey: () => Promise<string>;
      settingsSaveApiKey: (key: string) => Promise<boolean>;

      clipboardWrite: (text: string) => Promise<boolean>;

      dialogOpenFiles: () => Promise<FileAttachment[]>;
      dialogSaveFile: (name: string, content: string) => Promise<boolean>;
      dialogImportFile: () => Promise<string | null>;

      onStreamStart: (cb: (tabId: string, index: number, model: string) => void) => void;
      onStreamToken: (cb: (tabId: string, text: string) => void) => void;
      onStreamDone: (cb: (tabId: string, content: string) => void) => void;
      onStreamError: (cb: (tabId: string, msg: string) => void) => void;
    };
  }
}
