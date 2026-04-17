# YaOG v7.3.0 — Release Notes

**Released:** 2026-04-17
**Previous:** v7.2.0

---

## Highlights

### Persistent Memories (New)

YaOG now supports persistent, user-defined memories that can be applied across conversations.

- Added a dedicated **Memories** section in Settings.
- You can toggle memories on/off with **Use memories**.
- You can save long-form preference/context notes (up to **28,000 characters**).
- Memories are designed for durable defaults such as writing preferences, communication style, and recurring constraints.

### Backend Memory Context Injection

When enabled, memories are prepended to model requests as system context with explicit guardrails:

- Current chat instructions still override stored memory when they conflict.
- Memories are treated as contextual defaults, not rigid rules.
- The model is instructed not to reveal memory contents unless asked.

### UX Clarity Improvements

- Added a **Memories active** status badge in the composer area.
- Added save feedback in the Memories settings panel.
- Added clear privacy messaging in settings indicating memories are local to the app.

### Settings + Type System Updates

- Extended app settings with `use_memories` and `memories_text`.
- Added memory sanitization and hard character cap enforcement in backend settings writes.
- Wired renderer initialization to reflect memory activation state at startup.

---

# YaOG v7.2.0 — Release Notes

**Released:** 2026-04-16
**Previous:** v7.1.6

---

## Major Improvements

### UI Stability & Layout Integrity

A complete overhaul of the layout engine ensures the UI remains fully visible and responsive at all times.

- **Strict Viewport Constraints**: Added `h-screen` and `overflow-hidden` to the root container to prevent the "out of bounds" bug where the toolbar or tabs could be pushed off-screen.
- **Improved Side Panel**: The history menu has been converted from an absolute overlay to a proper flex-resizing side panel. Expanding history now correctly reflows the chat window rather than covering it.
- **Flicker-Free Synchronization**: Implemented debounced state syncing between individual tabs and the global context, resolving high-frequency re-render loops (the "high voltage" flickering).
- **Tab Lifecycle**: Fixed a double-initialization bug that caused two empty tabs to open on startup.

### Professional Rebranding & Content Refinement

Removed all remaining RPG-themed placeholders and defaults to establish a neutral, professional identity.

- **Neutral System Prompts**: Rewrote "The Dude" to **"The Assistant"** and "The Buddy" to **"The Partner"** with updated professional instructions.
- **Inter UI Font**: Switched the default interface font to **Inter** for better readability and a modern aesthetic.
- **Refined Placeholders**: Replaced RPG-themed font previews and system prompt examples with technical and general-purpose text.

### Build & Distribution

- **Dedicated Build Script**: Introduced `build.js` for safe native module rebuilding and cross-platform packaging.
- **Linux Compatibility**: Integrated a permanent `--no-sandbox` binary wrapper via `afterPack.cjs` to ensure flawless execution on Linux distributions.
- **API Metadata**: All outgoing OpenRouter requests now include proper `X-Title` and `HTTP-Referer` headers for better service integration.

---

# YaOG v7.1.6 — Release Notes

**Released:** 2026-03-19
**Previous:** v7.1.5

---

## Changes

### Versioning discipline pass

This release is strictly a versioning consistency update:

- aligned app/package version to **7.1.6**
- aligned documentation header versioning to **v7.1.6**
- normalized release-note ordering so the latest release is clearly first

No functional or behavioral changes were made in this release.

---

# YaOG v7.1.5 — Release Notes

**Released:** 2026-03-19
**Previous:** v7.1.4

---

## Changes

### Removed reasoning controls and parameter plumbing

Reasoning level management has been removed from the app. The Reasoning slider is gone from the toolbar, renderer-side reasoning state and metadata interpretation are removed, and chat requests no longer attempt to send `include_reasoning` / `reasoning_effort` style OpenRouter parameters.

YaOG now fully delegates reasoning behavior to OpenRouter/model defaults while preserving all existing chat, web search, and model selection behavior.

---

# YaOG v7.1.1 — Release Notes

**Released:** 2025-02-20
**Previous:** v7.0.0

---

## Version History

| Version | Date | Summary |
|---------|------|---------|
| 7.3.0 | 2026-04-17 | Persistent memories across chats, backend memory injection, UI memory status and settings integration |
| 7.2.0 | 2026-04-16 | UI stability, multi-tab fixes, professional content rewrite, build script |
| 7.1.6 | 2026-03-19 | Versioning consistency pass only |
| 7.1.5 | 2026-03-19 | Removed reasoning controls and related parameter plumbing |
| 7.1.1 | 2025-02-20 | PDF support, archive pipeline, context menu, copy system, close confirm, font scaling fix, sandbox fix |
| 7.0.0 | — | Initial Electron rewrite from Python/Qt (v5) |
