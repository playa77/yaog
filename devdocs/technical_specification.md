# YaOG UI/UX Improvements — Technical Specification v1.0.0

Date: 2024-03-21
Author: DeepSeek (architect role)
Status: Draft
Depends on: Design Document v1.0.0

## 1. Project Structure

```
yaog/
├── electron/
│   ├── main.cjs                    # No changes required
│   ├── preload.cjs                 # No changes required
│   └── afterPack.cjs               # No changes required
├── src/
│   ├── App.tsx                     # Major rewrite: TabManager, TabContext
│   ├── components/
│   │   ├── TabBar.tsx              # NEW: Tab strip UI
│   │   ├── TabContent.tsx          # NEW: Wraps ChatView + ConversationHeader
│   │   ├── ConversationHeader.tsx  # NEW: Persistent conversation title
│   │   ├── ChatView.tsx            # Minor: Remove empty state RPG elements
│   │   ├── Sidebar.tsx             # Modified: History opens new tab, inline rename confirm
│   │   ├── SettingsSheet.tsx       # Modified: Prompt textarea scrollable
│   │   ├── Toolbar.tsx             # Modified: "New Chat" opens new tab
│   │   ├── MessageBubble.tsx       # No changes
│   │   ├── InputBar.tsx            # No changes
│   │   └── Tooltip.tsx             # No changes
│   ├── contexts/
│   │   └── TabContext.tsx          # NEW: Tab state management
│   ├── types.ts                    # Extended: TabState, TabContextType
│   ├── globals.css                 # Modified: Tab styles, conversation header
│   ├── main.tsx                    # No changes
│   └── lib/
│       └── utils.ts                # No changes
├── build/
│   └── afterPack.cjs               # No changes
└── (config files unchanged)
```

## 2. Dependencies

No new dependencies required. Existing dependencies sufficient:
- **React 19**: State management for tabs
- **TypeScript**: Type safety for new interfaces
- **lucide-react**: Icons for tab close, etc.
- **clsx + tailwind-merge**: Conditional styling

## 3. Configuration

No new configuration keys. Existing settings remain:
- `api_timeout`, `chat_font_size`, `chat_font_family`, `ui_font_size`, `ui_font_family`, `mono_font_family`, `mono_font_size`, `confirm_close`

## 4. Module Specifications

### 4.1 src/contexts/TabContext.tsx
**Purpose**: Manages tab state and synchronization with backend.

**File**: `src/contexts/TabContext.tsx`

**Public Interface**:
```typescript
interface TabState {
  id: string;                    // 'tab-1', 'tab-2', etc.
  conversationId: number | null; // null for new unsaved chats
  title: string;                 // Display title (truncated for tab)
  fullTitle: string;            // Full title for tooltip
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
  // Derived from conversationId
  isNew: boolean;               // conversationId === null
  isDirty: boolean;             // Has unsaved changes (simplified: always false after sync)
}

interface TabContextType {
  tabs: TabState[];
  activeTabId: string;
  activeTab: TabState;
  
  // Actions
  openTab: (options?: { conversationId?: number; title?: string }) => string;
  closeTab: (tabId: string) => void;
  switchTab: (tabId: string) => Promise<void>;
  updateTab: (tabId: string, updates: Partial<TabState>) => void;
  reorderTabs: (fromIndex: number, toIndex: number) => void;
  
  // Backend sync
  saveTabToBackend: (tabId: string) => Promise<void>;
  loadConversationIntoNewTab: (conversationId: number) => Promise<string>;
  
  // Helpers
  findTabByConversationId: (conversationId: number) => string | null;
  getTabIndex: (tabId: string) => number;
}
```

**Internal Behavior**:
- `openTab()`: Generates unique tab ID (`tab-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`). If `conversationId` provided, sets title from conversation list; otherwise "New Chat".
- `switchTab()`: Calls `saveTabToBackend()` for current tab, then switches, then loads new tab state if `conversationId` not null.
- `saveTabToBackend()`: If tab has `conversationId`, ensures backend has latest messages via appropriate IPC calls. For new chats, creates conversation on first message send.
- `loadConversationIntoNewTab()`: IPC `convLoad` → creates tab with loaded state.
- Tab state persisted in React context only; no localStorage needed.

**Error Handling**:
- `switchTab` fails if target tab doesn't exist → falls back to first tab.
- `saveTabToBackend` fails → shows error in tab, preserves frontend state for retry.

**Dependencies**: `window.api`, React context.

### 4.2 src/components/TabBar.tsx
**Purpose**: Tab strip UI below toolbar.

**File**: `src/components/TabBar.tsx`

**Public Interface**:
```typescript
interface TabBarProps {
  // Injected via TabContext
}
```

**Internal Behavior**:
- Horizontal scrollable container for tabs.
- Each tab shows: icon (💬 for new, 📝 for saved), truncated title (12 chars max), close button (×).
- Active tab highlighted with bottom border.
- Tab click → `switchTab()`.
- Close button click → `closeTab()`; if closing active tab, switches to adjacent tab.
- Drag handle for reorder (optional phase 2).
- Overflow menu for many tabs.

**Styling**:
```css
.tab-bar-container {
  height: 36px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  overflow-x: auto;
}

.tab {
  height: 100%;
  min-width: 120px;
  max-width: 200px;
  padding: 0 12px 0 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-right: 1px solid var(--border);
  cursor: pointer;
  user-select: none;
}

.tab.active {
  background: var(--bg-elevated);
  border-bottom: 2px solid var(--accent);
}

.tab-close {
  margin-left: auto;
  opacity: 0.5;
}

.tab-close:hover {
  opacity: 1;
  color: var(--danger);
}
```

**Dependencies**: `TabContext`, `Tooltip`.

### 4.3 src/components/ConversationHeader.tsx
**Purpose**: Persistent conversation title above chat messages.

**File**: `src/components/ConversationHeader.tsx`

**Public Interface**:
```typescript
interface ConversationHeaderProps {
  title: string;
  fullTitle: string;
  conversationId: number | null;
  isNew: boolean;
}
```

**Internal Behavior**:
- Always visible, fixed position or sticky within chat area.
- Shows full conversation title (not truncated).
- For new chats: shows "New Chat" with subtle indicator.
- Non-interactive (except maybe click to rename? No, rename only in sidebar).
- Fades slightly when scrolling.

**Styling**:
```css
.conversation-header {
  padding: 16px 24px 12px;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 10;
}

.conversation-title {
  font-family: var(--font-ui);
  font-size: calc(var(--size-ui) * 1.385); /* ~18px @ 13 */
  font-weight: 600;
  color: var(--text-bright);
}

.conversation-subtitle {
  font-family: var(--font-ui);
  font-size: calc(var(--size-ui) * 0.923); /* ~12px @ 13 */
  color: var(--text-muted);
  margin-top: 2px;
}
```

**Dependencies**: None.

### 4.4 src/components/TabContent.tsx
**Purpose**: Container for ConversationHeader + ChatView + InputBar per tab.

**File**: `src/components/TabContent.tsx`

**Public Interface**:
```typescript
interface TabContentProps {
  tabId: string;
  isActive: boolean;
}
```

**Internal Behavior**:
- Renders only if `isActive` (others hidden).
- Contains `ConversationHeader`, `ChatView`, `InputBar`.
- Passes tab-specific state to children.
- Handles tab-specific event handlers (send, edit, regenerate, etc.) that update tab context.

**Dependencies**: `TabContext`, `ConversationHeader`, `ChatView`, `InputBar`.

### 4.5 src/App.tsx (Modified)
**Purpose**: Root component with tab management.

**Changes**:
- Wrap entire app in `TabProvider`.
- Replace direct `ChatView` with `TabBar` + `TabContent` map.
- Move conversation-specific state into tab context.
- Modify `loadConversation` to use `loadConversationIntoNewTab`.
- Modify `newChat` to use `openTab`.
- Update all chat actions (send, edit, regenerate, delete) to operate on active tab.

**Key modifications**:
```typescript
// Before:
const [messages, setMessages] = useState<DisplayMessage[]>([]);
const [currentConvId, setCurrentConvId] = useState<number | null>(null);

// After:
const { activeTab, updateTab, saveTabToBackend } = useTabContext();
// messages → activeTab.messages
// currentConvId → activeTab.conversationId
```

**RPG removal**:
- Replace "Ready for adventure" → "Ready to chat"
- Replace "Choose your model, set a system prompt for your world, and begin." → "Choose your model, set a system prompt, and begin."
- Replace ⚔️ emoji → 💬

### 4.6 src/components/Sidebar.tsx (Modified)
**Purpose**: History sidebar with new tab behavior.

**Changes**:
- Remove `setSidebarOpen(false)` from `onSelect`.
- Modify `onSelect` to call `loadConversationIntoNewTab`.
- Add inline rename confirmation:
  - Click pencil → edit mode (current)
  - Edit mode shows: text input + [Save] [Cancel] buttons
  - Save button calls `onRename` and exits edit mode
  - Cancel reverts
- Keep delete confirmation unchanged.

**New interface**:
```typescript
interface SidebarProps {
  // ... existing props
  onOpenInNewTab: (id: number) => void; // replaces onSelect
}
```

### 4.7 src/components/SettingsSheet.tsx (Modified)
**Purpose**: Settings with scrollable prompt textarea.

**Changes**:
- In `PromptsTab` component, modify textarea:
  - Remove `resize-y` class
  - Add `overflow-y: auto`
  - Set `max-height: 300px`
  - Keep existing rows={6}

**CSS**:
```css
.prompt-textarea {
  resize: none;
  overflow-y: auto;
  max-height: 300px;
}
```

### 4.8 src/components/Toolbar.tsx (Modified)
**Purpose**: Toolbar with tab-aware new chat.

**Changes**:
- `onNewChat` calls `openTab()` instead of direct `newChat()`.
- Token count shows active tab's token count.
- Model/temperature selectors control active tab's state.

### 4.9 src/components/ChatView.tsx (Modified)
**Purpose**: Chat display with RPG elements removed.

**Changes**:
- Update empty state text and emoji as specified.
- No structural changes.

### 4.10 src/types.ts (Extended)
**New types**:
```typescript
// Add to existing types
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
  openTab: (options?: { conversationId?: number; title?: string }) => string;
  closeTab: (tabId: string) => void;
  switchTab: (tabId: string) => Promise<void>;
  updateTab: (tabId: string, updates: Partial<TabState>) => void;
  reorderTabs: (fromIndex: number, toIndex: number) => void;
  saveTabToBackend: (tabId: string) => Promise<void>;
  loadConversationIntoNewTab: (conversationId: number) => Promise<string>;
  findTabByConversationId: (conversationId: number) => string | null;
  getTabIndex: (tabId: string) => number;
}
```

## 5. Data Layer

### 5.1 Database Schema
No changes to SQLite schema:
```sql
-- Existing tables remain
CREATE TABLE conversations (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, created_at TEXT);
CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id INTEGER, role TEXT, content TEXT, model_used TEXT, temperature_used REAL, timestamp TEXT);
CREATE TABLE system_prompts (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, prompt_text TEXT);
```

### 5.2 Data Migration
No data migration required. Existing conversations load into first tab on app start.

### 5.3 IPC Usage Pattern
```typescript
// Per-tab synchronization
async function syncTabToBackend(tab: TabState): Promise<void> {
  if (tab.conversationId === null) {
    // New chat: nothing to sync until first message
    return;
  }
  
  // Ensure backend has this conversation loaded
  if (backendCurrentConvId !== tab.conversationId) {
    await window.api.convLoad(tab.conversationId);
  }
  
  // Note: Messages are already saved via chatSend/chatEdit/etc.
  // This is just ensuring backend context matches
}
```

## 6. Testing Strategy

### 6.1 Test Framework
- Existing: None specified
- Recommendation: Jest + React Testing Library for new components

### 6.2 Critical Test Cases
1. **Tab opening/closing**
   - Open new tab → appears in tab bar
   - Close active tab → switches to adjacent tab
   - Close last tab → empty state shown

2. **State preservation**
   - Switch tabs → model/temperature/prompt preserved
   - Close and reopen app → tabs restored (first tab only)

3. **Backend sync**
   - Send message in tab A → switch to tab B → message persists in database
   - Rename in sidebar → all tabs with that conversation update

4. **History sidebar**
   - Click conversation → opens new tab
   - Sidebar remains open after click
   - Rename shows inline confirmation

5. **RPG removal**
   - No RPG text in UI
   - Emoji replaced

## 7. Error Handling Conventions

### 7.1 Error Hierarchy
- **TabError**: Tab-specific errors (failed load, save)
- **SyncError**: Backend synchronization failures
- **UIError**: Component rendering errors

### 7.2 Error Recovery
- Tab load fails → show error in tab, offer retry
- Backend sync fails → queue retry, show indicator
- Component error → fallback UI, log to console

### 7.3 User-facing Messages
- "Failed to load conversation" → retry button
- "Could not save changes" → manual save option
- "Tab closed unexpectedly" → restore from backend

## 8. Build, Run, and Deploy

### 8.1 Development Commands
```bash
# Install dependencies (if not already)
npm install

# Rebuild native modules for Electron
npm run rebuild

# Run dev server + Electron
npm run dev

# Build for production
npm run build
```

### 8.2 Production Build
```bash
# Creates AppImage and .deb in dist/
npm run build
```

### 8.3 Deployment Notes
- Electron-builder configuration unchanged
- AppImage sandbox wrapper (`afterPack.cjs`) unchanged
- Version remains 7.2.0

---
