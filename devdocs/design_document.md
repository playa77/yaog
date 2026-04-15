# YaOG UI/UX Improvements — Design Document v1.0.0

Date: 2024-03-21
Author: DeepSeek (architect role)
Status: Draft

## 1. Overview

This document describes a set of UI/UX improvements for YaOG (Yet another OpenRouter GUI), an Electron-based chat client. The changes transform the application from an RPG-themed single-conversation interface to a neutral, multi-tab chat interface resembling mainstream web applications. The core functionality remains unchanged—streaming conversations with OpenRouter models, file attachments, system prompts, and local SQLite persistence—while improving usability with browser-like tabs, persistent conversation visibility, and refined interaction patterns.

## 2. Goals and Non-Goals

### Goals
1. **Remove RPG branding from UI elements** while preserving all functionality
2. **Implement browser-like tabs** for multiple concurrent conversations with full state preservation per tab
3. **Always show conversation names**: on tabs (truncated) and as persistent headers in chat view
4. **Keep history sidebar open** when loading conversations (opens in new tab)
5. **Add inline confirmation** for conversation renaming in sidebar
6. **Replace resize handle with scrollbar** for prompt textarea in settings
7. **Maintain backward compatibility**: existing users see their current conversation in first tab with RPG text replaced

### Non-Goals
1. **Backend architecture overhaul**: SQLite schema and IPC API remain unchanged
2. **Prompt content modification**: Default prompt names and text remain (only UI references changed)
3. **Mobile/tablet adaptation**: Changes target desktop Electron experience only
4. **Offline functionality changes**: Existing file processing, PDF extraction, archive handling unchanged
5. **Model or API enhancements**: OpenRouter integration unchanged

## 3. System Architecture

### Current Architecture
- **Single-conversation model**: Backend (`electron/main.cjs`) tracks one `currentConvId` and `messages` array
- **Frontend state**: React components manage conversation list, current messages, UI state
- **IPC bridge**: Preload script exposes typed API for database operations, streaming, file dialogs

### Modified Architecture
- **Frontend tab state**: New `TabManager` component and context manage multiple conversation states
- **Per-tab isolation**: Each tab maintains independent:
  - Conversation ID (or null for new chats)
  - Message list (frontend `DisplayMessage[]`)
  - Selected model, temperature, system prompt, web search toggle
  - Streaming state
- **Backend synchronization**: On tab switch or close, active tab's state flushed to backend via existing IPC calls
- **History sidebar independence**: Sidebar state (`open/closed`) decoupled from tab operations

### Component Changes
```
App.tsx → TabManager (new)
          ├── TabBar (new)
          ├── TabContent (modified ChatView + Header)
          └── SharedToolbar (existing, model/temperature global)
Sidebar.tsx → Modified: clicks open new tab, rename confirmation
SettingsSheet.tsx → Modified: prompt textarea scrollable
```

### Data Flow
1. **Tab activation** → Save previous tab state to backend (if dirty) → Load new tab state from backend
2. **New tab from history** → IPC `convLoad` → Create tab with loaded state
3. **Tab close** → Ensure backend has latest state (already persisted) → Remove frontend state
4. **Rename in sidebar** → Inline confirmation → IPC `convRename` → Update all tabs with that conversation ID

## 4. Data Model

### Frontend State Additions
```typescript
interface TabState {
  id: string; // UUID or incremental number
  conversationId: number | null; // null for new unsaved chats
  title: string; // "New Chat" or conversation title
  messages: DisplayMessage[];
  selectedModel: string;
  temperature: number;
  selectedPrompt: string | null;
  useWebSearch: boolean;
  isStreaming: boolean;
  streamContent: string;
  // ... other per-conversation UI state
}

interface AppState {
  tabs: TabState[];
  activeTabId: string;
  // ... existing state (conversations[], models[], etc.)
}
```

### Backend Compatibility
- **No database schema changes**: `conversations` and `messages` tables unchanged
- **IPC API unchanged**: Existing `convLoad`, `chatSend`, `convRename` etc. work per-conversation
- **Single-conversation backend**: Backend continues to manage one conversation at a time; frontend serializes access

## 5. API / Interface Design

### New Frontend APIs (React Context)
```typescript
interface TabContextType {
  tabs: TabState[];
  activeTab: TabState;
  openTab: (conversationId?: number) => string; // returns new tab ID
  closeTab: (tabId: string) => void;
  switchTab: (tabId: string) => void;
  updateTabState: (tabId: string, updates: Partial<TabState>) => void;
  saveActiveTab: () => Promise<void>; // flush to backend
}
```

### Modified IPC Usage Pattern
```typescript
// Before tab switch:
await saveActiveTab(); // Calls chatSend/convRename/etc. if needed

// After tab switch:
const loaded = await window.api.convLoad(newConversationId);
updateTabState(activeTabId, { ...loaded, conversationId: newConversationId });
```

### Sidebar → Tab Communication
```typescript
// History item click → opens new tab
const handleHistoryClick = async (convId: number) => {
  const tabId = openTab(convId); // Creates tab, loads via IPC
  switchTab(tabId);
  // Sidebar remains open (no setSidebarOpen(false))
};
```

## 6. Security Model

No changes to security model:
- API key remains in `~/.yaog/.env`
- File processing pipeline unchanged
- Electron context isolation unchanged
- Clipboard access unchanged

## 7. Infrastructure and Deployment

### Development Impact
- **New dependencies**: None required
- **Build process**: Unchanged (Vite → Electron-builder)
- **Performance**: Additional memory for multiple loaded conversations; consider >10 tabs

### Deployment
- **Electron version**: Unchanged (v33.2.0)
- **Native modules**: `better-sqlite3`, `pdf-parse` unchanged
- **Distribution**: AppImage/.deb packaging unchanged

## 8. Key Design Decisions

1. **Frontend Tab State over Backend Refactor**
   - **Alternatives**: Refactor backend to support multiple concurrent conversations
   - **Decision**: Frontend state with backend sync
   - **Rationale**: Minimal backend changes, faster implementation, maintains stability of file processing/streaming

2. **Browser-like Tab Semantics**
   - **Alternatives**: MDI (multiple document interface), split views, workspace concept
   - **Decision**: Browser tabs metaphor
   - **Rationale**: Familiar user mental model, predictable behavior, scales to many conversations

3. **Persistent Conversation Header**
   - **Alternatives**: Tab-only display, floating header, message-bubble style
   - **Decision**: Persistent non-scrolling header above chat
   - **Rationale**: Clear context, matches "big four" UI patterns, accessible

4. **Inline Rename Confirmation**
   - **Alternatives**: Modal dialog, auto-save with undo, separate rename panel
   - **Decision**: Inline confirmation (like delete confirmation)
   - **Rationale**: Consistent with existing UI patterns, lightweight, discoverable

5. **History Opens New Tab**
   - **Alternatives**: Replace current tab, user preference, shift-click modifier
   - **Decision**: Always new tab
   - **Rationale**: Preserves current work, matches browser "open link in new tab" expectation

## 9. Open Questions

1. **Tab Limit**: Should we impose a maximum number of tabs? (Decision: No limit initially, monitor memory)
2. **Tab Drag/Drop Implementation**: Use HTML5 Drag API or simpler reorder buttons? (Decision: Implement basic reorder with buttons first)
3. **Empty State with No Tabs**: Show welcome screen or blank area? (Decision: Welcome screen with "New Chat" action)
4. **Tab State Dirty Detection**: How to detect if tab needs saving before switch? (Decision: Save on every switch for simplicity)

---
 
