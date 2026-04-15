# YaOG UI/UX Improvements — Roadmap v1.0.0

Date: 2024-03-21
Author: DeepSeek (architect role)
Status: Draft
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
**Depends on**: Nothing

#### WP-1.1: Extend TypeScript types for tab state
- **Scope**: Modify `src/types.ts` to add `TabState` and `TabContextType` interfaces as defined in Technical Specification.
- **Depends on**: Nothing
- **Acceptance Criteria**:
  - [ ] AC-1: `src/types.ts` contains exact `TabState` interface with all fields from Technical Specification 4.10
  - [ ] AC-2: `src/types.ts` contains exact `TabContextType` interface with all methods from Technical Specification 4.10
  - [ ] AC-3: TypeScript compilation passes: `npx tsc --noEmit` shows 0 errors
- **Estimated complexity**: Trivial
- **Notes**: Copy interfaces directly from Tech Spec.

#### WP-1.2: Create TabContext provider
- **Scope**: Create `src/contexts/TabContext.tsx` with React context implementing `TabContextType`.
- **Depends on**: WP-1.1
- **Acceptance Criteria**:
  - [ ] AC-1: File `src/contexts/TabContext.tsx` exists with exported `TabProvider` component
  - [ ] AC-2: `TabProvider` manages `tabs` array and `activeTabId` in React state
  - [ ] AC-3: `openTab()` creates new tab with unique ID and default state
  - [ ] AC-4: `closeTab()` removes tab from array; if closing active tab, switches to adjacent tab
  - [ ] AC-5: `switchTab()` sets `activeTabId` without backend sync (placeholder)
  - [ ] AC-6: `updateTab()` updates specific tab's state via setter
  - [ ] AC-7: Context exports `useTabContext()` hook
- **Estimated complexity**: Moderate
- **Notes**: Backend sync in WP-2.3. For now, just state management.

#### WP-1.3: Integrate TabProvider into App
- **Scope**: Modify `src/App.tsx` to wrap content in `TabProvider`, initialize with one tab containing current conversation.
- **Depends on**: WP-1.2
- **Acceptance Criteria**:
  - [ ] AC-1: `src/App.tsx` imports `TabProvider` and wraps main content
  - [ ] AC-2: On app start, creates one tab with existing conversation state (or "New Chat" if none)
  - [ ] AC-3: Existing functionality unchanged (messages display, input works)
  - [ ] AC-4: App compiles and runs without errors
- **Estimated complexity**: Moderate
- **Notes**: Tab UI not visible yet; state exists but not displayed.

### Milestone 2: Tab UI and Basic Operations
**Outcome**: Visible tab bar with open/close/switch functionality. Backend synchronization on tab switch.
**Depends on**: Milestone 1

#### WP-2.1: Create TabBar component
- **Scope**: Create `src/components/TabBar.tsx` with tab strip UI.
- **Depends on**: WP-1.3
- **Acceptance Criteria**:
  - [ ] AC-1: File `src/components/TabBar.tsx` exists
  - [ ] AC-2: Renders horizontal list of tabs from `TabContext`
  - [ ] AC-3: Each tab shows: icon (💬 for new, 📝 for saved), truncated title (12 chars max with `…`), close button (×)
  - [ ] AC-4: Active tab highlighted with bottom border `border-b-2 border-accent`
  - [ ] AC-5: Click tab calls `switchTab()`
  - [ ] AC-6: Click close button calls `closeTab()`
  - [ ] AC-7: CSS matches design: height 36px, background `bg-surface`, border bottom
- **Estimated complexity**: Moderate
- **Notes**: Use existing Tailwind colors. No drag reorder yet.

#### WP-2.2: Create ConversationHeader component
- **Scope**: Create `src/components/ConversationHeader.tsx` for persistent title above chat.
- **Depends on**: WP-1.3
- **Acceptance Criteria**:
  - [ ] AC-1: File `src/components/ConversationHeader.tsx` exists
  - [ ] AC-2: Receives `title`, `fullTitle`, `conversationId`, `isNew` as props
  - [ ] AC-3: Renders title in `font-ui` at `fs-ui-xl` size
  - [ ] AC-4: For new chats: shows "New Chat" with subtle `(unsaved)` indicator
  - [ ] AC-5: Position sticky at top of chat area
  - [ ] AC-6: Background `bg`, border bottom `border-border`
  - [ ] AC-7: Does not use message bubble styling
- **Estimated complexity**: Trivial
- **Notes**: Simple display component only.

#### WP-2.3: Create TabContent component and integrate
- **Scope**: Create `src/components/TabContent.tsx` that wraps ConversationHeader + ChatView + InputBar.
- **Depends on**: WP-2.1, WP-2.2
- **Acceptance Criteria**:
  - [ ] AC-1: File `src/components/TabContent.tsx` exists
  - [ ] AC-2: Receives `tabId` and `isActive` props
  - [ ] AC-3: Renders `ConversationHeader` with tab's title
  - [ ] AC-4: Renders `ChatView` with tab's messages and streaming state
  - [ ] AC-5: Renders `InputBar` with tab's pendingInput and stagedFiles
  - [ ] AC-6: Only renders when `isActive` (others hidden via `display: none`)
  - [ ] AC-7: Event handlers (send, edit, etc.) update tab state via `updateTab()`
- **Estimated complexity**: Moderate
- **Notes**: This replaces direct ChatView/InputBar in App.tsx.

#### WP-2.4: Implement backend synchronization
- **Scope**: Modify `TabContext` to sync tab state with backend on switch.
- **Depends on**: WP-2.3
- **Acceptance Criteria**:
  - [ ] AC-1: `switchTab()` calls `saveTabToBackend()` for current tab before switching
  - [ ] AC-2: `saveTabToBackend()`: if tab has `conversationId`, calls `window.api.convLoad()` to ensure backend context
  - [ ] AC-3: `saveTabToBackend()`: for new chats (null conversationId), does nothing
  - [ ] AC-4: `loadConversationIntoNewTab()`: calls `window.api.convLoad()`, creates tab with loaded state
  - [ ] AC-5: Tab switch preserves all state (model, temp, prompt, web search)
- **Estimated complexity**: Significant
- **Notes**: This is the core synchronization logic.

#### WP-2.5: Update App.tsx layout
- **Scope**: Modify `src/App.tsx` to render TabBar and map over tabs for TabContent.
- **Depends on**: WP-2.4
- **Acceptance Criteria**:
  - [ ] AC-1: `src/App.tsx` renders `TabBar` below `Toolbar`
  - [ ] AC-2: Maps over `tabs` to render `TabContent` for each
  - [ ] AC-3: Removes direct `ChatView` and `InputBar` rendering
  - [ ] AC-4: Moves chat-specific state (messages, streaming, etc.) into tab context usage
  - [ ] AC-5: App runs with tabs visible and functional
- **Estimated complexity**: Moderate
- **Notes**: Major restructuring of App.tsx.

### Milestone 3: History and New Chat Integration
**Outcome**: Sidebar opens conversations in new tabs. Toolbar "New Chat" opens new tab.
**Depends on**: Milestone 2

#### WP-3.1: Modify Sidebar for new tab behavior
- **Scope**: Update `src/components/Sidebar.tsx` to open conversations in new tabs.
- **Depends on**: WP-2.5
- **Acceptance Criteria**:
  - [ ] AC-1: `onSelect` prop renamed to `onOpenInNewTab`
  - [ ] AC-2: Clicking conversation calls `loadConversationIntoNewTab()` from context
  - [ ] AC-3: Does NOT call `setSidebarOpen(false)` (sidebar stays open)
  - [ ] AC-4: New tab becomes active after loading
  - [ ] AC-5: Existing delete functionality unchanged
- **Estimated complexity**: Trivial
- **Notes**: Simple prop/function change.

#### WP-3.2: Modify Toolbar "New Chat" button
- **Scope**: Update `src/components/Toolbar.tsx` to open new tab instead of replacing current.
- **Depends on**: WP-3.1
- **Acceptance Criteria**:
  - [ ] AC-1: `onNewChat` handler calls `openTab()` from context
  - [ ] AC-2: New tab becomes active
  - [ ] AC-3: New tab has "New Chat" title, null conversationId
  - [ ] AC-4: Existing toolbar functionality (model select, temp, copy) works on active tab
- **Estimated complexity**: Trivial
- **Notes**: Token count should reflect active tab.

#### WP-3.3: Update all chat actions to use tab context
- **Scope**: Modify `src/App.tsx` chat actions (send, edit, regenerate, delete) to operate on active tab.
- **Depends on**: WP-3.2
- **Acceptance Criteria**:
  - [ ] AC-1: `sendMessage()` updates active tab's messages and streaming state
  - [ ] AC-2: `editMessage()` updates active tab's messages
  - [ ] AC-3: `regenerateMessage()` updates active tab's messages
  - [ ] AC-4: `deleteMessage()` updates active tab's messages
  - [ ] AC-5: All actions call `saveTabToBackend()` after completion
  - [ ] AC-6: Token count updates per active tab
- **Estimated complexity**: Moderate
- **Notes**: This completes the tab-aware chat functionality.

### Milestone 4: Conversation Rename Improvements
**Outcome**: Inline rename confirmation in sidebar. Conversation names update across all tabs.
**Depends on**: Milestone 3

#### WP-4.1: Implement inline rename confirmation in Sidebar
- **Scope**: Modify `src/components/Sidebar.tsx` rename flow to show Save/Cancel buttons.
- **Depends on**: WP-3.3
- **Acceptance Criteria**:
  - [ ] AC-1: Click pencil enters edit mode: replaces text with input field
  - [ ] AC-2: Edit mode shows: text input + [Save] [Cancel] buttons inline
  - [ ] AC-3: Save button calls `onRename` with new title, exits edit mode
  - [ ] AC-4: Cancel button reverts to original title, exits edit mode
  - [ ] AC-5: Enter key saves, Escape key cancels
  - [ ] AC-6: UI matches delete confirmation styling (same row, buttons)
- **Estimated complexity**: Moderate
- **Notes**: Similar pattern to delete confirmation but for save.

#### WP-4.2: Update tab titles when conversation renamed
- **Scope**: Modify `TabContext` to update all tabs with same conversationId when rename occurs.
- **Depends on**: WP-4.1
- **Acceptance Criteria**:
  - [ ] AC-1: `TabContext` has method `updateTabsForConversation(conversationId, newTitle)`
  - [ ] AC-2: Method updates `title` and `fullTitle` for all tabs with matching `conversationId`
  - [ ] AC-3: Sidebar rename calls this method after successful IPC rename
  - [ ] AC-4: Tab bar and conversation header update immediately
- **Estimated complexity**: Trivial
- **Notes**: Simple state update across tabs.

### Milestone 5: RPG Branding Removal
**Outcome**: All RPG-themed UI text and emoji replaced with neutral alternatives.
**Depends on**: Milestone 4

#### WP-5.1: Replace RPG text in ChatView
- **Scope**: Update `src/components/ChatView.tsx` empty state text and emoji.
- **Depends on**: WP-4.2
- **Acceptance Criteria**:
  - [ ] AC-1: "Ready for adventure" changed to "Ready to chat"
  - [ ] AC-2: "Choose your model, set a system prompt for your world, and begin." changed to "Choose your model, set a system prompt, and begin."
  - [ ] AC-3: ⚔️ emoji changed to 💬
  - [ ] AC-4: Empty state styling unchanged (layout, spacing, colors)
- **Estimated complexity**: Trivial
- **Notes**: Simple text replacement.

#### WP-5.2: Update README description
- **Scope**: Update `README.md` to remove RPG references from description.
- **Depends on**: WP-5.1
- **Acceptance Criteria**:
  - [ ] AC-1: "Immersive AI chat client built for solo & group RPG" changed to "Immersive AI chat client"
  - [ ] AC-2: Any other RPG references in README removed or neutralized
  - [ ] AC-3: Features list unchanged (still includes all technical features)
- **Estimated complexity**: Trivial
- **Notes**: Documentation only, doesn't affect runtime.

### Milestone 6: Prompt Field Scrolling Fix
**Outcome**: Prompt textarea in settings has vertical scrollbar instead of resize handle.
**Depends on**: Milestone 5

#### WP-6.1: Modify SettingsSheet prompt textarea
- **Scope**: Update `src/components/SettingsSheet.tsx` prompt textarea styling.
- **Depends on**: WP-5.2
- **Acceptance Criteria**:
  - [ ] AC-1: Prompt textarea has `resize: none` CSS property
  - [ ] AC-2: Prompt textarea has `overflow-y: auto`
  - [ ] AC-3: Prompt textarea has `max-height: 300px`
  - [ ] AC-4: Vertical scrollbar appears when content exceeds visible area
  - [ ] AC-5: Existing rows={6} attribute remains
  - [ ] AC-6: All other settings functionality unchanged
- **Estimated complexity**: Trivial
- **Notes**: CSS-only change.

### Milestone 7: Polish and Edge Cases
**Outcome**: Handle edge cases, improve UX, final testing.
**Depends on**: Milestone 6

#### WP-7.1: Handle empty state with no tabs
- **Scope**: When all tabs closed, show welcome screen with "New Chat" action.
- **Depends on**: WP-6.1
- **Acceptance Criteria**:
  - [ ] AC-1: Closing last tab results in empty tab bar
  - [ ] AC-2: Main area shows welcome screen (same as ChatView empty state)
  - [ ] AC-3: Welcome screen has prominent "New Chat" button
  - [ ] AC-4: Clicking "New Chat" button opens new tab
  - [ ] AC-5: Toolbar "New Chat" button also works in this state
- **Estimated complexity**: Moderate
- **Notes**: Similar to browser when all tabs closed.

#### WP-7.2: Add tab tooltips with full titles
- **Scope**: Add Tooltip component to tabs showing full conversation title.
- **Depends on**: WP-7.1
- **Acceptance Criteria**:
  - [ ] AC-1: Each tab in TabBar wrapped in `Tooltip` component
  - [ ] AC-2: Tooltip shows `fullTitle` (untruncated)
  - [ ] AC-3: Tooltip position "top"
  - [ ] AC-4: Hover delay matches existing tooltips (400ms)
- **Estimated complexity**: Trivial
- **Notes**: Use existing Tooltip component.

#### WP-7.3: Final integration testing
- **Scope**: Test complete workflow across all changes.
- **Depends on**: WP-7.2
- **Acceptance Criteria**:
  - [ ] AC-1: Open multiple conversations from history → each opens in new tab
  - [ ] AC-2: Switch between tabs → state preserved
  - [ ] AC-3: Rename conversation in sidebar → updates all tabs immediately
  - [ ] AC-4: Close and reopen app → first tab restored with state
  - [ ] AC-5: No RPG text visible anywhere in UI
  - [ ] AC-6: Prompt textarea scrolls, doesn't resize
  - [ ] AC-7: All existing functionality (attachments, streaming, copy, settings) works
- **Estimated complexity**: Significant
- **Notes**: Manual testing of complete user journey.

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
