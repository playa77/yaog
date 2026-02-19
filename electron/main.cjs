// electron/main.cjs — YaOG v7 Electron Main Process
// Replaces: api_manager.py, database_manager.py, conversation_manager.py,
//           settings_manager.py, worker_manager.py, utils.py

const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const Database = require('better-sqlite3');

// Linux sandbox fix
if (process.platform === 'linux') {
  app.commandLine.appendSwitch('no-sandbox');
}

// ════════════════════════════════════════════════════════════════
// Paths
// ════════════════════════════════════════════════════════════════

const DATA_DIR = path.join(app.getPath('home'), '.yaog');
const DB_PATH = path.join(DATA_DIR, 'yaog.db');
const SETTINGS_PATH = path.join(DATA_DIR, 'settings.json');
const MODELS_PATH = path.join(DATA_DIR, 'models.json');
const ENV_PATH = path.join(DATA_DIR, '.env');

function ensureDataDir() {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });

  // Migrate from old location if it exists
  const oldDir = path.join(app.getPath('home'), '.or-client');
  const oldDb = path.join(oldDir, 'or-client.db');
  if (fs.existsSync(oldDb) && !fs.existsSync(DB_PATH)) {
    try {
      fs.copyFileSync(oldDb, DB_PATH);
      console.log('[MIGRATE] Copied database from .or-client');
    } catch {}
  }

  // Also check for .env and models.json in CWD (legacy locations)
  const cwdEnv = path.join(process.cwd(), '.env');
  if (fs.existsSync(cwdEnv) && !fs.existsSync(ENV_PATH)) {
    try { fs.copyFileSync(cwdEnv, ENV_PATH); } catch {}
  }
  const cwdModels = path.join(process.cwd(), 'models.json');
  if (fs.existsSync(cwdModels) && !fs.existsSync(MODELS_PATH)) {
    try { fs.copyFileSync(cwdModels, MODELS_PATH); } catch {}
  }
}

// ════════════════════════════════════════════════════════════════
// .env Management
// ════════════════════════════════════════════════════════════════

function getApiKey() {
  // Check env var first
  if (process.env.OPENROUTER_API_KEY &&
      process.env.OPENROUTER_API_KEY !== 'YOUR_API_KEY_HERE') {
    return process.env.OPENROUTER_API_KEY;
  }
  // Then .env file
  try {
    if (fs.existsSync(ENV_PATH)) {
      const content = fs.readFileSync(ENV_PATH, 'utf8');
      for (const line of content.split('\n')) {
        if (line.trim().startsWith('OPENROUTER_API_KEY=')) {
          let val = line.trim().split('=').slice(1).join('=').trim();
          if ((val.startsWith('"') && val.endsWith('"')) ||
              (val.startsWith("'") && val.endsWith("'"))) {
            val = val.slice(1, -1);
          }
          if (val && val !== 'YOUR_API_KEY_HERE') return val;
        }
      }
    }
  } catch {}
  return '';
}

function saveApiKey(key) {
  try {
    fs.writeFileSync(ENV_PATH, `OPENROUTER_API_KEY="${key}"\n`);
    process.env.OPENROUTER_API_KEY = key;
    return true;
  } catch { return false; }
}

// ════════════════════════════════════════════════════════════════
// Settings
// ════════════════════════════════════════════════════════════════

const DEFAULT_SETTINGS = {
  api_timeout: 360,
  chat_font_size: 16.5,
  chat_font_family: 'Literata',
  ui_font_size: 13,
  ui_font_family: 'DM Sans',
  mono_font_family: 'JetBrains Mono',
};

function loadSettings() {
  try {
    if (fs.existsSync(SETTINGS_PATH)) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(fs.readFileSync(SETTINGS_PATH, 'utf8')) };
    }
  } catch {}
  return { ...DEFAULT_SETTINGS };
}

function saveSettings(settings) {
  try { fs.writeFileSync(SETTINGS_PATH, JSON.stringify(settings, null, 2)); } catch {}
}

let settings = loadSettings();

// ════════════════════════════════════════════════════════════════
// Models
// ════════════════════════════════════════════════════════════════

const DEFAULT_MODELS = [
  { name: 'Gemini 2.5 Flash Lite', id: 'google/gemini-2.5-flash-lite' },
  { name: 'Deepseek R1 (free)', id: 'deepseek/deepseek-r1-0528:free' },
  { name: 'Kimi K2 (free)', id: 'moonshotai/kimi-k2:free' },
  { name: 'DeepSeek V3 (free)', id: 'deepseek/deepseek-chat-v3-0324:free' },
  { name: 'Qwen3 (free)', id: 'qwen/qwen3-235b-a22b:free' },
];

function loadModels() {
  try {
    if (fs.existsSync(MODELS_PATH)) {
      const data = JSON.parse(fs.readFileSync(MODELS_PATH, 'utf8'));
      return data.models || DEFAULT_MODELS;
    }
  } catch {}
  return [...DEFAULT_MODELS];
}

function saveModels(models) {
  try { fs.writeFileSync(MODELS_PATH, JSON.stringify({ models }, null, 2)); } catch {}
}

let models = loadModels();

// Cached model metadata from OpenRouter API
let modelMetadata = {};

async function fetchModelMetadata() {
  const key = getApiKey();
  if (!key) return;
  try {
    const res = await fetch('https://openrouter.ai/api/v1/models', {
      headers: { 'Authorization': `Bearer ${key}` },
    });
    if (res.ok) {
      const data = await res.json();
      for (const m of (data.data || [])) {
        modelMetadata[m.id] = m;
      }
    }
  } catch (e) {
    console.error('[MODELS] Failed to fetch metadata:', e.message);
  }
}

// ════════════════════════════════════════════════════════════════
// Database
// ════════════════════════════════════════════════════════════════

let db;

function initDatabase() {
  db = new Database(DB_PATH);
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');

  db.exec(`
    CREATE TABLE IF NOT EXISTS conversations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime'))
    );
    CREATE TABLE IF NOT EXISTS messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      conversation_id INTEGER NOT NULL,
      role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
      content TEXT NOT NULL,
      model_used TEXT,
      temperature_used REAL,
      timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
      FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS system_prompts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      prompt_text TEXT NOT NULL
    );
  `);
}

// DB helpers
const dbGetConversations = () =>
  db.prepare('SELECT id, title, created_at FROM conversations ORDER BY created_at DESC').all();

const dbGetConversation = (id) =>
  db.prepare('SELECT id, title FROM conversations WHERE id = ?').get(id);

const dbAddConversation = (title) =>
  db.prepare('INSERT INTO conversations (title) VALUES (?)').run(title).lastInsertRowid;

const dbRenameConversation = (id, title) =>
  db.prepare('UPDATE conversations SET title = ? WHERE id = ?').run(title, id);

const dbDeleteConversation = (id) =>
  db.prepare('DELETE FROM conversations WHERE id = ?').run(id);

const dbGetMessages = (convId) =>
  db.prepare('SELECT id, role, content, model_used, temperature_used FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC').all(convId);

const dbAddMessage = (convId, role, content, model, temp) =>
  db.prepare('INSERT INTO messages (conversation_id, role, content, model_used, temperature_used) VALUES (?, ?, ?, ?, ?)').run(convId, role, content, model, temp).lastInsertRowid;

const dbUpdateMessage = (msgId, content) =>
  db.prepare('UPDATE messages SET content = ? WHERE id = ?').run(content, msgId);

const dbDeleteMessage = (msgId) =>
  db.prepare('DELETE FROM messages WHERE id = ?').run(msgId);

const dbGetPrompts = () =>
  db.prepare('SELECT id, name, prompt_text FROM system_prompts ORDER BY name ASC').all();

const dbAddPrompt = (name, text) =>
  db.prepare('INSERT INTO system_prompts (name, prompt_text) VALUES (?, ?)').run(name, text);

const dbUpdatePrompt = (id, name, text) =>
  db.prepare('UPDATE system_prompts SET name = ?, prompt_text = ? WHERE id = ?').run(name, text, id);

const dbDeletePrompt = (id) =>
  db.prepare('DELETE FROM system_prompts WHERE id = ?').run(id);

// Fix conversation titles that are stuck as "New Chat"
// Scans for the first user message and uses it as the title
function migrateNewChatTitles() {
  const broken = db.prepare(
    "SELECT id FROM conversations WHERE title = 'New Chat' OR title = 'New Chat…'"
  ).all();
  if (broken.length === 0) return;

  const stmt = db.prepare(
    "SELECT content FROM messages WHERE conversation_id = ? AND role = 'user' ORDER BY timestamp ASC LIMIT 1"
  );
  const update = db.prepare('UPDATE conversations SET title = ? WHERE id = ?');

  const tx = db.transaction(() => {
    for (const { id } of broken) {
      const row = stmt.get(id);
      if (row && row.content) {
        // Strip any file attachment markup before using as title
        let text = row.content.replace(/<div class="yaog-file-content"[^>]*>[\s\S]*?<\/div>/g, '').trim();
        if (!text) text = 'Chat';
        const title = text.length > 50 ? text.slice(0, 50) + '…' : text;
        update.run(title, id);
      }
    }
  });
  tx();
  if (broken.length > 0) {
    console.log(`[MIGRATE] Fixed ${broken.length} conversation title(s).`);
  }
}

// ════════════════════════════════════════════════════════════════
// Conversation State (in-memory, mirrors Python ConversationManager)
// ════════════════════════════════════════════════════════════════

let currentConvId = null;
let messages = []; // {id, role, content, model_used, temperature_used}

function convNew() {
  currentConvId = null;
  messages = [];
}

function convLoad(id) {
  currentConvId = id;
  messages = dbGetMessages(id);
}

function convAddMessage(role, content, model, temp) {
  if (!currentConvId) {
    const title = content.length > 40 ? content.slice(0, 40) + '…' : (content || 'New Chat');
    currentConvId = dbAddConversation(title);
  }
  const msgId = dbAddMessage(currentConvId, role, content, model, temp);
  messages.push({ id: msgId, role, content, model_used: model, temperature_used: temp });
  return messages.length - 1;
}

function convInsertSystem(content) {
  if (!currentConvId) currentConvId = dbAddConversation('New Chat');
  const msgId = dbAddMessage(currentConvId, 'system', content, null, null);
  messages.unshift({ id: msgId, role: 'system', content, model_used: null, temperature_used: null });
}

function convUpdateMessage(index, content) {
  if (index >= 0 && index < messages.length) {
    messages[index].content = content;
    if (messages[index].id) dbUpdateMessage(messages[index].id, content);
  }
}

function convPruneAfter(index) {
  const removed = messages.splice(index + 1);
  for (const m of removed) { if (m.id) dbDeleteMessage(m.id); }
}

function convPruneFrom(index) {
  const removed = messages.splice(index);
  for (const m of removed) { if (m.id) dbDeleteMessage(m.id); }
}

function convMessagesForApi() {
  return messages.map(m => ({ role: m.role, content: m.content }));
}

// ════════════════════════════════════════════════════════════════
// Streaming (replaces worker_manager.py + api_manager.py)
// ════════════════════════════════════════════════════════════════

let abortController = null;

async function streamResponse(win, modelId, temperature, extra) {
  const key = getApiKey();
  if (!key) { win.webContents.send('stream:error', 'API key not configured'); return; }

  abortController = new AbortController();

  const payload = {
    model: modelId,
    messages: convMessagesForApi(),
    temperature,
    stream: true,
    ...extra,
  };

  try {
    const res = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${key}`,
        'Content-Type': 'application/json',
        'X-Title': 'YaOG',
      },
      body: JSON.stringify(payload),
      signal: abortController.signal,
    });

    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      if (res.status === 429) {
        win.webContents.send('stream:error', 'Rate limit (429). Try again shortly.');
      } else {
        win.webContents.send('stream:error', `API error ${res.status}: ${errText.slice(0, 200)}`);
      }
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullContent = '';
    let firstToken = false;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const data = line.slice(6).trim();
        if (data === '[DONE]') break;

        try {
          const chunk = JSON.parse(data);
          const content = chunk.choices?.[0]?.delta?.content;
          if (content) {
            if (!firstToken) {
              firstToken = true;
              win.webContents.send('stream:start', messages.length, modelId);
            }
            fullContent += content;
            win.webContents.send('stream:token', content);
          }
        } catch {}
      }
    }

    // Save to conversation
    convAddMessage('assistant', fullContent, modelId, temperature);

    win.webContents.send('stream:done', fullContent);

  } catch (err) {
    if (err.name === 'AbortError') {
      win.webContents.send('stream:done', '');
    } else {
      win.webContents.send('stream:error', err.message);
    }
  } finally {
    abortController = null;
  }
}

// ════════════════════════════════════════════════════════════════
// File reading (for attachments)
// ════════════════════════════════════════════════════════════════

function readFileContent(filePath) {
  try {
    return fs.readFileSync(filePath, 'utf8');
  } catch {
    try {
      return fs.readFileSync(filePath, 'latin1');
    } catch {
      return '[Could not read file]';
    }
  }
}

// ════════════════════════════════════════════════════════════════
// IPC Handlers
// ════════════════════════════════════════════════════════════════

function registerIPC(win) {

  // ── Conversations ──
  ipcMain.handle('conv:list', () => dbGetConversations());

  ipcMain.handle('conv:new', () => { convNew(); return true; });

  ipcMain.handle('conv:load', (_, id) => {
    convLoad(id);
    return messages.filter(m => m.role !== 'system');
  });

  ipcMain.handle('conv:delete', (_, id) => {
    dbDeleteConversation(id);
    if (currentConvId === id) convNew();
    return true;
  });

  ipcMain.handle('conv:rename', (_, id, title) => {
    dbRenameConversation(id, title);
    return true;
  });

  ipcMain.handle('conv:export', (_, id) => {
    const convs = dbGetConversations();
    const conv = convs.find(c => c.id === id);
    const msgs = dbGetMessages(id);
    return JSON.stringify({ type: 'or-client-chat', title: conv?.title || 'Export', messages: msgs }, null, 2);
  });

  ipcMain.handle('conv:import', async (_, jsonStr) => {
    const data = JSON.parse(jsonStr);
    if (data.type !== 'or-client-chat') throw new Error('Invalid format');
    const cid = dbAddConversation((data.title || 'Imported') + ' (Imported)');
    for (const m of (data.messages || [])) {
      dbAddMessage(cid, m.role, m.content, m.model_used || null, m.temperature_used || 0.7);
    }
    return true;
  });

  // ── Chat ──
  ipcMain.handle('chat:send', async (_, text, modelId, temp, sysPrompt, opts) => {
    // Handle system prompt
    const hasSystem = messages.length > 0 && messages[0].role === 'system';
    if (hasSystem && sysPrompt) {
      convUpdateMessage(0, sysPrompt);
    } else if (hasSystem && !sysPrompt) {
      const sysMsg = messages[0];
      messages.splice(0, 1);
      if (sysMsg.id) dbDeleteMessage(sysMsg.id);
    } else if (!hasSystem && sysPrompt) {
      convInsertSystem(sysPrompt);
    }

    convAddMessage('user', text, null, temp);

    // Fix title — if system prompt created the conversation first, the title is "New Chat"
    if (currentConvId) {
      const conv = dbGetConversation(currentConvId);
      if (conv && conv.title === 'New Chat') {
        let titleText = text.replace(/<div class="yaog-file-content"[^>]*>[\s\S]*?<\/div>/g, '').trim();
        if (!titleText) titleText = 'Chat';
        const properTitle = titleText.length > 50 ? titleText.slice(0, 50) + '…' : titleText;
        dbRenameConversation(currentConvId, properTitle);
      }
    }

    // Handle model suffixes
    let effectiveModel = modelId;
    if (opts?.webSearch && !effectiveModel.endsWith(':online')) effectiveModel += ':online';
    if (!opts?.webSearch && effectiveModel.endsWith(':online')) effectiveModel = effectiveModel.replace(':online', '');

    const extra = {};
    if (opts?.reasoning) extra.include_reasoning = true;

    await streamResponse(win, effectiveModel, temp, extra);
    return { conversations: dbGetConversations(), tokenCount: estimateTokens() };
  });

  ipcMain.handle('chat:stop', () => {
    if (abortController) abortController.abort();
    return true;
  });

  ipcMain.handle('chat:edit', async (_, index, newContent, modelId, temp, opts) => {
    convUpdateMessage(index, newContent);
    convPruneAfter(index);

    let effectiveModel = modelId;
    if (opts?.webSearch && !effectiveModel.endsWith(':online')) effectiveModel += ':online';
    if (!opts?.webSearch && effectiveModel.endsWith(':online')) effectiveModel = effectiveModel.replace(':online', '');

    const extra = {};
    if (opts?.reasoning) extra.include_reasoning = true;

    await streamResponse(win, effectiveModel, temp, extra);
    return { conversations: dbGetConversations(), tokenCount: estimateTokens() };
  });

  ipcMain.handle('chat:regenerate', async (_, index, modelId, temp, opts) => {
    if (messages[index]?.role === 'assistant') convPruneFrom(index);
    else convPruneAfter(index);

    let effectiveModel = modelId;
    if (opts?.webSearch && !effectiveModel.endsWith(':online')) effectiveModel += ':online';
    if (!opts?.webSearch && effectiveModel.endsWith(':online')) effectiveModel = effectiveModel.replace(':online', '');

    const extra = {};
    if (opts?.reasoning) extra.include_reasoning = true;

    await streamResponse(win, effectiveModel, temp, extra);
    return { conversations: dbGetConversations(), tokenCount: estimateTokens() };
  });

  ipcMain.handle('chat:deleteMsg', (_, index) => {
    convPruneFrom(index);
    return { messages: messages.filter(m => m.role !== 'system'), tokenCount: estimateTokens() };
  });

  ipcMain.handle('chat:getMessages', () =>
    messages.filter(m => m.role !== 'system')
  );

  // ── Token counting (rough estimate) ──
  function estimateTokens() {
    let count = 0;
    for (const m of messages) {
      count += 4; // overhead per message
      count += Math.ceil((m.content || '').length / 4);
      count += Math.ceil((m.role || '').length / 4);
    }
    return count + 2;
  }

  ipcMain.handle('chat:tokenCount', () => estimateTokens());

  // ── Models ──
  ipcMain.handle('models:list', () => models);
  ipcMain.handle('models:add', (_, name, id) => {
    if (models.some(m => m.id === id)) return models;
    models.push({ name, id });
    saveModels(models);
    return models;
  });
  ipcMain.handle('models:update', (_, idx, name, id) => {
    if (idx >= 0 && idx < models.length) { models[idx] = { name, id }; saveModels(models); }
    return models;
  });
  ipcMain.handle('models:delete', (_, idx) => {
    if (idx >= 0 && idx < models.length) { models.splice(idx, 1); saveModels(models); }
    return models;
  });
  ipcMain.handle('models:move', (_, idx, dir) => {
    const target = dir === 'up' ? idx - 1 : idx + 1;
    if (target >= 0 && target < models.length) {
      [models[idx], models[target]] = [models[target], models[idx]];
      saveModels(models);
    }
    return models;
  });
  ipcMain.handle('models:metadata', () => modelMetadata);

  // ── System Prompts ──
  ipcMain.handle('prompts:list', () => dbGetPrompts());
  ipcMain.handle('prompts:save', (_, id, name, text) => {
    if (id) dbUpdatePrompt(id, name, text);
    else dbAddPrompt(name, text);
    return dbGetPrompts();
  });
  ipcMain.handle('prompts:delete', (_, id) => { dbDeletePrompt(id); return dbGetPrompts(); });

  // ── Settings ──
  ipcMain.handle('settings:get', () => ({
    ...settings,
    apiKeySet: !!getApiKey(),
  }));
  ipcMain.handle('settings:set', (_, key, value) => {
    settings[key] = value;
    saveSettings(settings);
    return true;
  });
  ipcMain.handle('settings:getApiKey', () => {
    const key = getApiKey();
    return key ? key.slice(0, 8) + '…' + key.slice(-4) : '';
  });
  ipcMain.handle('settings:saveApiKey', (_, key) => saveApiKey(key));

  // ── File dialogs ──
  ipcMain.handle('dialog:openFiles', async () => {
    const result = await dialog.showOpenDialog(win, {
      properties: ['openFile', 'multiSelections'],
      filters: [
        { name: 'Supported', extensions: ['txt','md','json','csv','xml','html','py','js','ts','c','cpp','java','go','rs','sql','log','yml','yaml'] },
        { name: 'All Files', extensions: ['*'] },
      ],
    });
    if (result.canceled) return [];
    return result.filePaths.map(fp => ({
      path: fp,
      name: path.basename(fp),
      content: readFileContent(fp),
    }));
  });

  ipcMain.handle('dialog:saveFile', async (_, defaultName, content) => {
    const result = await dialog.showSaveDialog(win, {
      defaultPath: defaultName,
      filters: [{ name: 'JSON', extensions: ['json'] }],
    });
    if (!result.canceled && result.filePath) {
      fs.writeFileSync(result.filePath, content);
      return true;
    }
    return false;
  });

  ipcMain.handle('dialog:importFile', async () => {
    const result = await dialog.showOpenDialog(win, {
      properties: ['openFile'],
      filters: [{ name: 'JSON', extensions: ['json'] }],
    });
    if (result.canceled || !result.filePaths.length) return null;
    return fs.readFileSync(result.filePaths[0], 'utf8');
  });
}

// ════════════════════════════════════════════════════════════════
// Window & App Lifecycle
// ════════════════════════════════════════════════════════════════

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 800,
    minWidth: 640,
    minHeight: 500,
    backgroundColor: '#0F1117',
    titleBarStyle: 'default',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Dev or production
  if (process.argv.includes('--dev') || !app.isPackaged) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  }

  registerIPC(mainWindow);

  // Fetch model metadata in background
  fetchModelMetadata();
}

app.whenReady().then(() => {
  ensureDataDir();
  initDatabase();
  migrateNewChatTitles();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (db) db.close();
  app.quit();
});
