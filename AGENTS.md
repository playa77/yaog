# Agent Instructions for YaOG

## Critical Developer Commands
- **Initial Setup**: `npm install && npm run rebuild`
- **Rebuild Native Modules**: `npm run rebuild` (Required for `better-sqlite3` whenever `node_modules` change)
- **Development**: `npm run dev` (Starts Vite HMR and Electron with `--no-sandbox`)
- **Build**: `npm run build` (Builds renderer, then packages with `electron-builder`)

## Architecture & Entrypoints
- **Electron Main**: `electron/main.cjs` (Handles SQLite, OpenRouter API streaming, file processing, and IPC)
- **Electron Preload**: `electron/preload.cjs` (Exposes typed IPC via `window.api`)
- **React Renderer**: `src/App.tsx` (Current root component and state manager)
- **Database**: Local SQLite using `better-sqlite3` in `~/.yaog/yaog.db`
- **Environment**: OpenRouter API key and other secrets are in `~/.yaog/.env`

## High-Signal Context
- **React 19**: Project uses React 19. Ensure components are compatible.
- **Native Modules**: `better-sqlite3` is a native module. If you see "Module not found" or architecture mismatches, run `npm run rebuild`.
- **Tab-based UI**: The application uses a tab-based UI managed via `TabContext.tsx`. State is synced between tabs and the backend on switch.
- **OpenRouter API**: All model communication goes through OpenRouter API in the Main process.
- **IPC Pattern**: Use `window.api` (renderer) to invoke handlers in `main.cjs` (backend). DB work stays in Main.
- **File Processing**: PDF text extraction (`pdf-parse`) and archive handling happen in `main.cjs`.
- **Linux Sandbox**: Electron is launched with `--no-sandbox` to avoid Linux compatibility issues.

## Testing
- No automated tests currently exist in the repository.

## Important Constraints
- **Data Migration**: Automatically copies legacy database from `~/.or-client/` if found on first launch.
- **Font System**: Custom font scaling is defined in `src/globals.css`.
