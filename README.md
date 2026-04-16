# YaOG v7.2.0 — Yet another OpenRouter GUI

Immersive AI chat client. Dark ebook-reader aesthetic, modern web stack.

## Stack

- **Electron** — Desktop shell
- **React 19 + TypeScript** — UI
- **Vite** — Build / HMR
- **Tailwind CSS** — Styling
- **better-sqlite3** — Local database
- **pdf-parse** — PDF text extraction
- **OpenRouter API** — All models via openrouter.ai

## Setup

```bash
# Install dependencies
npm install

# Rebuild native module for Electron
npm run rebuild

# Set your API key (or do it in-app via Settings)
mkdir -p ~/.yaog
echo 'OPENROUTER_API_KEY="sk-or-v1-..."' > ~/.yaog/.env

# Run in dev mode
npm run dev
```

> **Note**: You need Node.js 18+ and build tools for better-sqlite3:
> ```bash
> sudo apt install build-essential python3
> ```

## Architecture

```
build.js          → Automated build script (rebuilds native modules + packages)
electron/
  main.cjs        → Backend: window, SQLite, API streaming, IPC, file processing
  preload.cjs     → Context bridge (typed API for renderer)
  afterPack.cjs   → Linux sandbox fix (binary wrapper hook)
src/
  App.tsx          → Root component, state management, global event handling
  contexts/
    TabContext.tsx → Multi-tab state management & synchronization
  components/
    Toolbar.tsx    → Model selection, temperature, settings, copy actions
    TabBar.tsx     → Navigation between open chat sessions
    Sidebar.tsx    → History management (resizing side panel)
    ChatView.tsx   → Scrollable message list with auto-scroll logic
    MessageBubble.tsx → Individual message units with granular copy menu
    InputBar.tsx   → Multi-line text input with file attachment support
    SettingsSheet.tsx → Global configuration (API, Models, Prompts, Fonts)
```

## Features

- [x] **Multi-Tab Interface** — Keep multiple conversations open and sync state between them.
- [x] **Stable Layout** — High-integrity flexbox UI that prevents content overflow.
- [x] **Resizing Sidebar** — History drawer that reflows the main chat area.
- [x] **Professional Prompts** — Curated system instructions for architects, assistants, and partners.
- [x] **Streaming API** — Real-time responses from any OpenRouter model.
- [x] **Markdown Rendering** — Clean typography with syntax highlighting for code.
- [x] **Document Ingestion** — Support for PDF, ZIP, TAR, RAR, and 7Z with text extraction.
- [x] **Granular Copy** — Specialized copy modes (Markdown, Plain Text, Full Context).
- [x] **Font Customization** — Independent family/size controls for Chat, UI (Inter), and Code.
- [x] **Local Database** — All history stored securely in a local SQLite file.

## Migrating from v5

Your old database at `~/.or-client/or-client.db` is auto-detected and copied to `~/.yaog/yaog.db` on first launch.

## Building for Distribution

```bash
npm run build
```

Produces AppImage and .deb in `dist/`. The AppImage includes a `--no-sandbox` wrapper for Linux compatibility.

## License

MIT
