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
}

export interface ChatOpts {
  webSearch?: boolean;
  reasoning?: boolean;
}

export interface FileAttachment {
  path: string;
  name: string;
  content: string;
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
      convLoad: (id: number) => Promise<Message[]>;
      convDelete: (id: number) => Promise<boolean>;
      convRename: (id: number, title: string) => Promise<boolean>;
      convExport: (id: number) => Promise<string>;
      convImport: (json: string) => Promise<boolean>;

      chatSend: (text: string, modelId: string, temp: number, sysPrompt: string | null, opts: ChatOpts) => Promise<{ conversations: Conversation[]; tokenCount: number }>;
      chatStop: () => Promise<boolean>;
      chatEdit: (index: number, content: string, modelId: string, temp: number, opts: ChatOpts) => Promise<{ conversations: Conversation[]; tokenCount: number }>;
      chatRegenerate: (index: number, modelId: string, temp: number, opts: ChatOpts) => Promise<{ conversations: Conversation[]; tokenCount: number }>;
      chatDeleteMsg: (index: number) => Promise<{ messages: Message[]; tokenCount: number }>;
      chatGetMessages: () => Promise<Message[]>;
      chatGetFullMessages: () => Promise<Message[]>;
      chatTokenCount: () => Promise<number>;

      modelsList: () => Promise<Model[]>;
      modelsAdd: (name: string, id: string) => Promise<Model[]>;
      modelsUpdate: (idx: number, name: string, id: string) => Promise<Model[]>;
      modelsDelete: (idx: number) => Promise<Model[]>;
      modelsMove: (idx: number, dir: 'up' | 'down') => Promise<Model[]>;
      modelsMetadata: () => Promise<Record<string, any>>;

      promptsList: () => Promise<SystemPrompt[]>;
      promptsSave: (id: number | null, name: string, text: string) => Promise<SystemPrompt[]>;
      promptsDelete: (id: number) => Promise<SystemPrompt[]>;

      settingsGet: () => Promise<AppSettings>;
      settingsSet: (key: string, value: any) => Promise<boolean>;
      settingsGetApiKey: () => Promise<string>;
      settingsSaveApiKey: (key: string) => Promise<boolean>;

      clipboardWrite: (text: string) => Promise<boolean>;

      dialogOpenFiles: () => Promise<FileAttachment[]>;
      dialogSaveFile: (name: string, content: string) => Promise<boolean>;
      dialogImportFile: () => Promise<string | null>;

      onStreamStart: (cb: (index: number, model: string) => void) => void;
      onStreamToken: (cb: (text: string) => void) => void;
      onStreamDone: (cb: (content: string) => void) => void;
      onStreamError: (cb: (msg: string) => void) => void;
    };
  }
}
