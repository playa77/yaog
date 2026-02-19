# YaOG v7 — Yet another OpenRouter GUI

Immersive AI chat client built for solo & group RPG. Dark ebook-reader aesthetic, modern web stack.

## Stack

- **Electron** — Desktop shell (Ubuntu → Android next)
- **React 19 + TypeScript** — UI
- **Vite** — Build / HMR
- **Tailwind CSS** — Styling
- **better-sqlite3** — Local database
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
electron/
  main.cjs       → Backend: window, SQLite, API streaming, IPC
  preload.cjs     → Context bridge (typed API for renderer)
src/
  App.tsx         → State management, layout, stream handling
  components/
    Toolbar.tsx   → Model picker, temperature, nav
    Sidebar.tsx   → Slide-out history drawer
    ChatView.tsx  → Message list + streaming
    MessageBubble.tsx → Individual message with actions
    InputBar.tsx  → Text input, attachments, send/stop
    SettingsSheet.tsx → Settings, API key, models, prompts
  globals.css     → Tailwind + prose styles + hljs theme
  types.ts        → TypeScript types + window.api declaration
```

## Features

- [x] Streaming responses from any OpenRouter model
- [x] System prompts (create, save, load, edit, delete)
- [x] Markdown rendering with syntax highlighting
- [x] Conversation history (create, load, rename, delete)
- [x] Message edit, regenerate, delete with branching
- [x] File attachments (text, code, logs)
- [x] Chat import/export (JSON)
- [x] Token count estimate
- [x] Temperature control
- [x] Web search (:online) toggle
- [x] Reasoning (CoT) toggle
- [x] Dark immersive theme

## Migrating from v5

Your old database at `~/.or-client/or-client.db` is auto-detected and copied to `~/.yaog/yaog.db` on first launch. Your conversations are preserved.

## Building for Distribution

```bash
npm run build
```

Produces AppImage and .deb in `release/`.

## License

MIT
