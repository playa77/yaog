# YaOG v7.3.0 — Yet another OpenRouter GUI

YaOG is an immersive desktop AI chat client for OpenRouter models, built with Electron + React 19 and designed around fast multi-conversation workflows, local-first data storage, and production-ready message controls.

## What’s New in v7.3.0

- **Persistent Memories**: You can now store durable user preferences/context and apply them to every conversation via **Settings → Memories**.
- **Safe Memory Injection**: Memories are injected as hidden system context in the backend and are not shown in visible chat history.
- **Memory Visibility in Composer**: The input area now shows a clear **“Memories active”** status indicator.
- **Hard Limits + Local Privacy**: Memory content is stored locally in `~/.yaog/settings.json` and capped at **28,000 characters**.

For full details, see [RELEASE_NOTES.md](./RELEASE_NOTES.md).

## Core Capabilities

- **Multi-tab chat workspace** with state synchronization between renderer and backend.
- **Streaming responses** from OpenRouter with stop controls and error handling.
- **Conversation history management** (rename, delete, import/export JSON).
- **Message-level controls**: edit + re-run, regenerate, delete trailing branch.
- **Copy modes** at message and conversation scope (text, markdown, full context including attachment blocks).
- **File attachment ingestion** with text extraction for:
  - PDF
  - ZIP / TAR / TGZ / TAR.BZ2 / TAR.XZ / TAR.ZST
  - RAR / 7Z
  - GZ and common text/code file types
- **Prompt system** with editable reusable system prompts.
- **Custom model registry** (add, edit, reorder, remove model IDs).
- **Web search mode toggle** (applies `:online` model variant behavior).
- **Token estimation** for active tab context + pending input.
- **Font system customization** for chat/UI/code typography.
- **API key management** in app settings (stored in `~/.yaog/.env`).
- **Local SQLite persistence** (`~/.yaog/yaog.db`) with legacy migration from `~/.or-client/`.

## Tech Stack

- **Electron** (desktop shell + secure preload bridge)
- **React 19 + TypeScript** (renderer UI)
- **Vite** (dev server + build)
- **Tailwind CSS** (styling)
- **better-sqlite3** (local persistence)
- **marked + highlight.js** (markdown + syntax highlighting)
- **pdf-parse** + native CLI helpers (`pdftotext`, `unzip`, `tar`, `unrar`, `7z` when available)

## Project Architecture

```text
build.js                 Automated build workflow (native rebuild + electron-builder)
electron/
  main.cjs               Main process: DB, streaming, settings, files, IPC handlers
  preload.cjs            Typed IPC surface exposed as window.api
  afterPack.cjs          Linux no-sandbox wrapper integration for packaged builds
src/
  App.tsx                Root UI state orchestration
  contexts/TabContext.tsx Multi-tab lifecycle + synchronization
  components/
    Toolbar.tsx          Model, temperature, copy, settings, token display
    TabBar.tsx           Open tab navigation
    Sidebar.tsx          History list + import/export + rename/delete
    ChatView.tsx         Rendered message stream
    MessageBubble.tsx    Per-message actions (copy/edit/regenerate/delete)
    InputBar.tsx         Compose area, attachments, send/stop, memories indicator
    SettingsSheet.tsx    General, fonts, API key, memories, models, prompts tabs
```

## Setup

### Prerequisites

- Node.js **18+**
- Build tools for native module compilation (`better-sqlite3`)

Ubuntu/Debian example:

```bash
sudo apt install -y build-essential python3
```

### Install and Run

```bash
npm install
npm run rebuild
npm run dev
```

### Configure OpenRouter API Key

Either set the key in **Settings → API Key**, or pre-seed:

```bash
mkdir -p ~/.yaog
echo 'OPENROUTER_API_KEY="sk-or-v1-..."' > ~/.yaog/.env
```

## Build for Distribution

```bash
npm run build
```

Artifacts are generated in `dist/` (AppImage + `.deb` on Linux). Linux packages include a no-sandbox wrapper for compatibility.

## Data Locations

- **Database**: `~/.yaog/yaog.db`
- **Settings**: `~/.yaog/settings.json`
- **API key env file**: `~/.yaog/.env`
- **Models registry**: `~/.yaog/models.json`
- **Prompt metadata**: `~/.yaog/prompt-meta.json`

## Migration

On first launch, YaOG auto-migrates legacy data when detected:

- `~/.or-client/or-client.db` → `~/.yaog/yaog.db`

## License

MIT
