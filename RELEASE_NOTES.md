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

## Critical Fixes

### Attachment content no longer leaks into chat

v7.0.0 had a regression from v5 where the raw contents of attached documents were rendered directly inside chat message bubbles. A 500-line Python file would appear inline as part of the user's message. This was caused by the display layer running the full stored message — including hidden file-content blocks — through the markdown renderer on every backend refresh.

**Fix:** A `stripFileContent()` pipeline now separates the API payload (which still includes full document text for the model) from the display layer (which shows only the user's typed message plus compact 📎 filename badges). A CSS safety net (`display: none !important`) on `.yaog-file-content` blocks catches any edge case.

### AppImage sandbox crash resolved

The built AppImage would crash immediately with `FATAL:setuid_sandbox_host.cc` because Chromium's SUID sandbox check runs before any Node flags are parsed — making `app.commandLine.appendSwitch('no-sandbox')` useless.

**Fix:** An `afterPack` electron-builder hook (`build/afterPack.cjs`) renames the real Electron binary to `yaog.bin` and replaces it with a bash wrapper that passes `--no-sandbox` on the command line before Chromium starts. The hook is robust: it tries `productFilename`, `executableName`, and `name`, then falls back to ELF magic-byte scanning.

---

## New Features

### PDF support

PDFs are now first-class citizens. The file dialog lists them by default (no more "All Files" hunting), and the processing pipeline uses a three-strategy cascade:

1. **`pdftotext -layout`** (poppler-utils) — best quality, preserves layout
2. **`pdf-parse`** (Node library, bundled) — always available, no system deps
3. **Raw string extraction** — last-resort fallback for damaged or exotic PDFs

For best results, install poppler-utils: `sudo apt install poppler-utils`.

### Archive processing pipeline

Attachments are no longer naively read as UTF-8 and dumped. A proper ingestion pipeline handles:

- **ZIP** / JAR / EPUB — list contents, extract text files with size limits
- **tar** / tar.gz / tar.bz2 / tar.xz — same treatment
- **RAR** — via `unrar` (graceful error message if not installed)
- **7z** — listing via `7z` command
- **gzip** (single file) — Node zlib decompression
- **JSON** — pretty-printed via `JSON.stringify(..., null, 2)`
- **Binary detection** — null-byte scan on first 8 KB, clean rejection message

Per-file limit: 512 KB. Per-archive total: 2 MB.

### Context menu (right-click)

Electron's native context menu was completely absent. Right-clicking anywhere now shows the appropriate menu: Cut/Copy/Paste/Undo/Redo/Select All in editable fields, Copy/Select All on selected text.

### Close confirmation

Closing the window now prompts "Close the application?" with a native dialog. Togglable in Settings → General.

### Granular copy system

**Per message** (dropdown arrow next to the copy button):

- **Copy as Text** — markdown formatting stripped, plain text
- **Copy as Markdown** — raw source preserved
- **Copy with Attachments** — full content including hidden document payloads (only shown when attachments are present)

**Per conversation** (clipboard icon in toolbar):

- **Copy Conversation (Text)** — all messages with `[You]`/`[Model]` labels, markdown stripped
- **Copy Conversation (Markdown)** — labels + raw markdown preserved
- **Copy Full Context** — everything including system prompt and all hidden attachment blocks

All copy operations use Electron's native clipboard API for reliability.

### Actually scalable font settings

v7.0.0's font size sliders were decorative — every component used hardcoded Tailwind classes (`text-xs`, `text-sm`, `text-[11px]`) that ignored the CSS variables. Moving the slider changed nothing.

**Fix:** A complete `fs-ui-*` class system (3xs through 4xl) replaces all hardcoded sizes. Every class derives from `calc(var(--size-ui) * factor)`, so the entire interface scales when the slider moves. The monospace font now has its own size slider too — all three font categories (chat, interface, code) have independent font family and size controls.

---

## Version History

| Version | Date | Summary |
|---------|------|---------|
| 7.1.6 | 2026-03-19 | Versioning consistency pass only |
| 7.1.5 | 2026-03-19 | Removed reasoning controls and related parameter plumbing |
| 7.1.1 | 2025-02-20 | PDF support, archive pipeline, context menu, copy system, close confirm, font scaling fix, sandbox fix |
| 7.0.0 | — | Initial Electron rewrite from Python/Qt (v5) |
