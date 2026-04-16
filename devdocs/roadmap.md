# YaOG UI/UX Improvements — Roadmap v1.0.0

Date: 2024-03-21
Author: DeepSeek (architect role)
Status: Completed
Depends on: Design Document v1.0.0, Technical Specification v1.0.0

## 0. Engineering Standards

Conventions that apply to ALL work packages:

- **Language**: TypeScript 5.7, React 19
- **Linter/Formatter**: ESLint, Prettier (existing config)
- **Test runner**: None specified (manual testing)
- **Commit message format**: Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`)
- **Branch naming**: `feature/tabs`, `fix/rename-confirm`, `refactor/rpg-cleanup`
- **Definition of "done"**:
  1. Code compiles without TypeScript errors
  2. Component renders without console errors
  3. Functionality works as described in acceptance criteria
  4. No regression in existing functionality
  5. UI matches existing design system (colors, spacing, fonts)

## 1. Milestones

### Milestone 1: Core Tab Infrastructure
**Outcome**: Basic tab state management without UI. Conversations load into tabs instead of replacing current view.
**Status**: COMPLETED

#### WP-1.1: Extend TypeScript types for tab state
- **Status**: COMPLETED
- **Acceptance Criteria**:
  - [x] AC-1: `src/types.ts` contains exact `TabState` interface with all fields from Technical Specification 4.10
  - [x] AC-2: `src/types.ts` contains exact `TabContextType` interface with all methods from Technical Specification 4.10
  - [x] AC-3: TypeScript compilation passes

#### WP-1.2: Create TabContext provider
- **Status**: COMPLETED
- **Acceptance Criteria**:
  - [x] AC-1: File `src/contexts/TabContext.tsx` exists with exported `TabProvider` component
  - [x] AC-2: `TabProvider` manages `tabs` array and `activeTabId` in React state
  - [x] AC-3: `openTab()` creates new tab with unique ID and default state
  - [x] AC-4: `closeTab()` removes tab from array; if closing active tab, switches to adjacent tab
  - [x] AC-5: `switchTab()` sets `activeTabId`
  - [x] AC-6: `updateTab()` updates specific tab's state via setter
  - [x] AC-7: Context exports `useTabContext()` hook

#### WP-1.3: Integrate TabProvider into App
- **Status**: COMPLETED
- **Acceptance Criteria**:
  - [x] AC-1: `src/App.tsx` imports `TabProvider` and wraps main content
  - [x] AC-2: On app start, creates one tab with existing conversation state (or "New Chat" if none)
  - [x] AC-3: Existing functionality unchanged (messages display, input works)
  - [x] AC-4: App compiles and runs without errors

### Milestone 2: Tab UI and Basic Operations
**Outcome**: Visible tab bar with open/close/switch functionality. Backend synchronization on tab switch.
**Status**: COMPLETED

#### WP-2.1: Create TabBar component
- **Status**: COMPLETED
- **Acceptance Criteria**:
  - [x] AC-1: File `src/components/TabBar.tsx` exists
  - [x] AC-2: Renders horizontal list of tabs from `TabContext`
  - [x] AC-3: Each tab shows: icon (💬 for new, 📝 for saved), truncated title (12 chars max with `…`), close button (×)
  - [x] AC-4: Active tab highlighted with bottom border `border-b-2 border-accent`
  - [x] AC-5: Click tab calls `switchTab()`
  - [x] AC-6: Click close button calls `closeTab()`
  - [x] AC-7: CSS matches design: height 36px, background `bg-surface`, border bottom

#### WP-2.2: Create ConversationHeader component
- **Status**: COMPLETED
- **Acceptance Criteria**:
  - [x] AC-1: File `src/components/ConversationHeader.tsx` exists
  - [x] AC-2: Receives `title`, `fullTitle`, `conversationId`, `isNew` as props
  - [x] AC-3: Renders title in `font-ui` at `fs-ui-xl` size
  - [x] AC-4: For new chats: shows "New Chat" with subtle `(unsaved)` indicator
  - [x] AC-5: Position sticky at top of chat area
  - [x] AC-6: Background `bg`, border bottom `border-border`
  - [x] AC-7: Does not use message bubble styling

#### WP-2.3: Create TabContent component and integrate
- **Status**: COMPLETED
- **Acceptance Criteria**:
  - [x] AC-1: File `src/components/TabContent.tsx` exists
  - [x] AC-2: Receives `tabId` and `isActive` props
  - [x] AC-3: Renders `ConversationHeader` with tab's title
  - [x] AC-4: Renders `ChatView` with tab's messages and streaming state
  - [x] AC-5: Renders `InputBar` with tab's pendingInput and stagedFiles
  - [x] AC-6: Only renders when `isActive` (others hidden via `display: none`)
  - [x] AC-7: Event handlers (send, edit, etc.) update tab state via `updateTab()`

#### WP-2.4: Implement backend synchronization
- **Status**: COMPLETED
- **Acceptance Criteria**:
  - [x] AC-1: `switchTab()` calls `saveTabToBackend()` for current tab before switching
  - [x] AC-2: `saveTabToBackend()`: if tab has `conversationId`, calls `window.api.convLoad()` to ensure backend context
  - [x] AC-3: `saveTabToBackend()`: for new chats (null conversationId), does nothing
  - [x] AC-4: `loadConversationIntoNewTab()`: calls `window.api.convLoad()`, creates tab with loaded state
  - [x] AC-5: Tab switch preserves all state (model, temp, prompt, web search)

#### WP-2.5: Update App.tsx layout
- **Status**: COMPLETED
- **Acceptance Criteria**:
  - [x] AC-1: `src/App.tsx` renders `TabBar` below `Toolbar`
  - [x] AC-2: Maps over `tabs` to render `TabContent` for each
  - [x] AC-3: Removes direct `ChatView` and `InputBar` rendering
  - [x] AC-4: Moves chat-specific state (messages, streaming, etc.) into tab context usage
  - [x] AC-5: App runs with tabs visible and functional

### Milestone 3: History and New Chat Integration
**Outcome**: Sidebar opens conversations in new tabs. Toolbar "New Chat" opens new tab.
**Status**: COMPLETED

#### WP-3.1: Modify Sidebar for new tab behavior
- **Status**: COMPLETED
- **Acceptance Criteria**:
  - [x] AC-1: `onSelect` prop renamed to `onOpenInNewTab`
  - [x] AC-2: Clicking conversation calls `loadConversationIntoNewTab()` from context
  - [x] AC-3: Does NOT call `setSidebarOpen(false)` (sidebar stays open)
  - [x] AC-4: New tab becomes active after loading
  - [x] AC-5: Existing delete functionality unchanged

#### WP-3.2: Modify Toolbar "New Chat" button
- **Status**: COMPLETED
- **Acceptance Criteria**:
  - [x] AC-1: `onNewChat` handler calls `openTab()` from context
  - [x] AC-2: New tab becomes active
  - [x] AC-3: New tab has "New Chat" title, null conversationId
  - [x] AC-4: Existing toolbar functionality (model select, temp, copy) works on active tab

#### WP-3.3: Update all chat actions to use tab context
- **Status**: COMPLETED
- **Acceptance Criteria**:
  - [x] AC-1: `sendMessage()` updates active tab's messages and streaming state
  - [x] AC-2: `editMessage()` updates active tab's messages
  - [x] AC-3: `regenerateMessage()` updates active tab's messages
  - [x] AC-4: `deleteMessage()` updates active tab's messages
  - [x] AC-5: All actions call `saveTabToBackend()` after completion
  - [x] AC-6: Token count updates per active tab

### Milestone 4: Conversation Rename Improvements
**Outcome**: Inline rename confirmation in sidebar. Conversation names update across all tabs.
**Status**: COMPLETED

#### WP-4.1: Implement inline rename confirmation in Sidebar
- **Status**: COMPLETED
- **Acceptance Criteria**:
  - [x] AC-1: Click pencil enters edit mode: replaces text with input field
  - [x] AC-2: Edit mode shows: text input + [Save] [Cancel] buttons inline
  - [x] AC-3: Save button calls `onRename` with new title, exits edit mode
  - [x] AC-4: Cancel button reverts to original title, exits edit mode
  - [x] AC-5: Enter key saves, Escape key cancels
  - [x] AC-6: UI matches delete confirmation styling (same row, buttons)

#### WP-4.2: Update tab titles when conversation renamed
- **Status**: COMPLETED
- **Acceptance Criteria**:
  - [x] AC-1: `TabContext` has method `updateTabsForConversation(conversationId, newTitle)`
  - [x] AC-2: Method updates `title` and `fullTitle` for all tabs with matching `conversationId`
  - [x] AC-3: Sidebar rename calls this method after successful IPC rename
  - [x] AC-4: Tab bar and conversation header update immediately

### Milestone 5: RPG Branding Removal
**Outcome**: All RPG-themed UI text and emoji replaced with neutral alternatives.
**Status**: COMPLETED

#### WP-5.1: Replace RPG text in ChatView
- **Status**: COMPLETED
- **Acceptance Criteria**:
  - [x] AC-1: "Ready for adventure" changed to "Ready to chat"
  - [x] AC-2: "Choose your model, set a system prompt for your world, and begin." changed to "Choose your model, set a system prompt, and begin."
  - [x] AC-3: ⚔️ emoji changed to 💬
  - [x] AC-4: Empty state styling unchanged (layout, spacing, colors)

#### WP-5.2: Update README description
- **Status**: COMPLETED
- **Acceptance Criteria**:
  - [x] AC-1: "Immersive AI chat client built for solo & group RPG" changed to "Immersive AI chat client"
  - [x] AC-2: Any other RPG references in README removed or neutralized
  - [x] AC-3: Features list unchanged (still includes all technical features)

### Milestone 6: Prompt Field Scrolling Fix
**Outcome**: Prompt textarea in settings has vertical scrollbar instead of resize handle.
**Status**: COMPLETED

#### WP-6.1: Modify SettingsSheet prompt textarea
- **Status**: COMPLETED
- **Acceptance Criteria**:
  - [x] AC-1: Prompt textarea has `resize: none` CSS property
  - [x] AC-2: Prompt textarea has `overflow-y: auto`
  - [x] AC-3: Prompt textarea has `max-height: 300px`
  - [x] AC-4: Vertical scrollbar appears when content exceeds visible area
  - [x] AC-5: Existing rows={6} attribute remains
  - [x] AC-6: All other settings functionality unchanged

### Milestone 7: Polish and Edge Cases
**Outcome**: Handle edge cases, improve UX, final testing.
**Status**: COMPLETED

#### WP-7.1: Handle empty state with no tabs
- **Status**: COMPLETED
- **Acceptance Criteria**:
  - [x] AC-1: Closing last tab results in empty tab bar
  - [x] AC-2: Main area shows welcome screen (same as ChatView empty state)
  - [x] AC-3: Welcome screen has prominent "New Chat" button
  - [x] AC-4: Clicking "New Chat" button opens new tab
  - [x] AC-5: Toolbar "New Chat" button also works in this state

#### WP-7.2: Add tab tooltips with full titles
- **Status**: COMPLETED
- **Acceptance Criteria**:
  - [x] AC-1: Each tab in TabBar wrapped in `Tooltip` component
  - [x] AC-2: Tooltip shows `fullTitle` (untruncated)
  - [x] AC-3: Tooltip position "top"
  - [x] AC-4: Hover delay matches existing tooltips (400ms)

#### WP-7.3: Final integration testing
- **Status**: COMPLETED
- **Acceptance Criteria**:
  - [x] AC-1: Open multiple conversations from history → each opens in new tab
  - [x] AC-2: Switch between tabs → state preserved
  - [x] AC-3: Rename conversation in sidebar → updates all tabs immediately
  - [x] AC-4: Close and reopen app → first tab restored with state
  - [x] AC-5: No RPG text visible anywhere in UI
  - [x] AC-6: Prompt textarea scrolls, doesn't resize
  - [x] AC-7: All existing functionality (attachments, streaming, copy, settings) works

---

## N. Future Work (Post-v1.0)

1. **Tab drag-and-drop reordering**
   - **What**: Implement HTML5 drag API for tab reordering
   - **Why deferred**: Complexity vs. value; buttons sufficient for v1
   - **Trigger**: User request or polish phase

2. **Tab session persistence**
   - **What**: Save tab state to localStorage, restore all tabs on app reopen
   - **Why deferred**: Adds complexity; single tab restore sufficient for v1
   - **Trigger**: User request for workspace feature

3. **Tab overflow menu**
   - **What**: Dropdown menu when many tabs don't fit in bar
   - **Why deferred**: Edge case; horizontal scroll works
   - **Trigger**: User feedback about many tabs

4. **Tab preview on hover**
   - **What**: Show message preview when hovering tab
   - **Why deferred**: Nice-to-have, not essential
   - **Trigger**: Polish phase

5. **Keyboard shortcuts for tab navigation**
   - **What**: Ctrl+Tab, Ctrl+Shift+Tab, Ctrl+W
   - **Why deferred**: Electron may handle some; consistency needed
   - **Trigger**: Power user feedback

---
