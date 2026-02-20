// electron/main.cjs — YaOG v7 Electron Main Process
const { app, BrowserWindow, ipcMain, dialog, Menu, clipboard } = require('electron');
const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');
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
  const oldDir = path.join(app.getPath('home'), '.or-client');
  const oldDb = path.join(oldDir, 'or-client.db');
  if (fs.existsSync(oldDb) && !fs.existsSync(DB_PATH)) {
    try { fs.copyFileSync(oldDb, DB_PATH); console.log('[MIGRATE] Copied database from .or-client'); } catch {}
  }
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
  if (process.env.OPENROUTER_API_KEY && process.env.OPENROUTER_API_KEY !== 'YOUR_API_KEY_HERE') {
    return process.env.OPENROUTER_API_KEY;
  }
  try {
    if (fs.existsSync(ENV_PATH)) {
      const content = fs.readFileSync(ENV_PATH, 'utf8');
      for (const line of content.split('\n')) {
        if (line.trim().startsWith('OPENROUTER_API_KEY=')) {
          let val = line.trim().split('=').slice(1).join('=').trim();
          if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
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
  try { fs.writeFileSync(ENV_PATH, `OPENROUTER_API_KEY="${key}"\n`); process.env.OPENROUTER_API_KEY = key; return true; } catch { return false; }
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
  mono_font_size: 14,
  confirm_close: true,
};

function loadSettings() {
  try {
    if (fs.existsSync(SETTINGS_PATH)) return { ...DEFAULT_SETTINGS, ...JSON.parse(fs.readFileSync(SETTINGS_PATH, 'utf8')) };
  } catch {}
  return { ...DEFAULT_SETTINGS };
}
function saveSettings(s) { try { fs.writeFileSync(SETTINGS_PATH, JSON.stringify(s, null, 2)); } catch {} }
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
function loadModels() { try { if (fs.existsSync(MODELS_PATH)) { const d = JSON.parse(fs.readFileSync(MODELS_PATH, 'utf8')); return d.models || DEFAULT_MODELS; } } catch {} return [...DEFAULT_MODELS]; }
function saveModels(m) { try { fs.writeFileSync(MODELS_PATH, JSON.stringify({ models: m }, null, 2)); } catch {} }
let models = loadModels();
let modelMetadata = {};
async function fetchModelMetadata() {
  const key = getApiKey(); if (!key) return;
  try { const res = await fetch('https://openrouter.ai/api/v1/models', { headers: { 'Authorization': `Bearer ${key}` } }); if (res.ok) { const data = await res.json(); for (const m of (data.data || [])) modelMetadata[m.id] = m; } } catch (e) { console.error('[MODELS] Failed to fetch metadata:', e.message); }
}

// ════════════════════════════════════════════════════════════════
// Database
// ════════════════════════════════════════════════════════════════

let db;
function initDatabase() {
  db = new Database(DB_PATH); db.pragma('journal_mode = WAL'); db.pragma('foreign_keys = ON');
  db.exec(`CREATE TABLE IF NOT EXISTS conversations (id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f','now','localtime')));CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT,conversation_id INTEGER NOT NULL,role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),content TEXT NOT NULL,model_used TEXT,temperature_used REAL,timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f','now','localtime')),FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE);CREATE TABLE IF NOT EXISTS system_prompts (id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL UNIQUE,prompt_text TEXT NOT NULL);`);
}
const dbGetConversations = () => db.prepare('SELECT id, title, created_at FROM conversations ORDER BY created_at DESC').all();
const dbGetConversation = (id) => db.prepare('SELECT id, title FROM conversations WHERE id = ?').get(id);
const dbAddConversation = (title) => db.prepare('INSERT INTO conversations (title) VALUES (?)').run(title).lastInsertRowid;
const dbRenameConversation = (id, title) => db.prepare('UPDATE conversations SET title = ? WHERE id = ?').run(title, id);
const dbDeleteConversation = (id) => db.prepare('DELETE FROM conversations WHERE id = ?').run(id);
const dbGetMessages = (convId) => db.prepare('SELECT id, role, content, model_used, temperature_used FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC').all(convId);
const dbAddMessage = (convId, role, content, model, temp) => db.prepare('INSERT INTO messages (conversation_id, role, content, model_used, temperature_used) VALUES (?, ?, ?, ?, ?)').run(convId, role, content, model, temp).lastInsertRowid;
const dbUpdateMessage = (msgId, content) => db.prepare('UPDATE messages SET content = ? WHERE id = ?').run(content, msgId);
const dbDeleteMessage = (msgId) => db.prepare('DELETE FROM messages WHERE id = ?').run(msgId);
const dbGetPrompts = () => db.prepare('SELECT id, name, prompt_text FROM system_prompts ORDER BY name ASC').all();
const dbAddPrompt = (name, text) => db.prepare('INSERT INTO system_prompts (name, prompt_text) VALUES (?, ?)').run(name, text);
const dbUpdatePrompt = (id, name, text) => db.prepare('UPDATE system_prompts SET name = ?, prompt_text = ? WHERE id = ?').run(name, text, id);
const dbDeletePrompt = (id) => db.prepare('DELETE FROM system_prompts WHERE id = ?').run(id);

function migrateNewChatTitles() {
  const broken = db.prepare("SELECT id FROM conversations WHERE title = 'New Chat' OR title = 'New Chat…'").all();
  if (broken.length === 0) return;
  const stmt = db.prepare("SELECT content FROM messages WHERE conversation_id = ? AND role = 'user' ORDER BY timestamp ASC LIMIT 1");
  const update = db.prepare('UPDATE conversations SET title = ? WHERE id = ?');
  const tx = db.transaction(() => {
    for (const { id } of broken) {
      const row = stmt.get(id);
      if (row && row.content) {
        let text = row.content.replace(/<div class="yaog-file-content"[^>]*>[\s\S]*?<\/div>/g, '').trim();
        if (!text) text = 'Chat';
        update.run(text.length > 50 ? text.slice(0, 50) + '…' : text, id);
      }
    }
  });
  tx();
  if (broken.length > 0) console.log(`[MIGRATE] Fixed ${broken.length} conversation title(s).`);
}

// ════════════════════════════════════════════════════════════════
// Conversation State
// ════════════════════════════════════════════════════════════════

let currentConvId = null;
let messages = [];

function convNew() { currentConvId = null; messages = []; }
function convLoad(id) { currentConvId = id; messages = dbGetMessages(id); }
function convAddMessage(role, content, model, temp) {
  if (!currentConvId) {
    let t = content.replace(/<div class="yaog-file-content"[^>]*>[\s\S]*?<\/div>/g, '').trim();
    if (!t) t = 'New Chat';
    currentConvId = dbAddConversation(t.length > 40 ? t.slice(0, 40) + '…' : t);
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
  if (index >= 0 && index < messages.length) { messages[index].content = content; if (messages[index].id) dbUpdateMessage(messages[index].id, content); }
}
function convPruneAfter(index) { const r = messages.splice(index + 1); for (const m of r) if (m.id) dbDeleteMessage(m.id); }
function convPruneFrom(index) { const r = messages.splice(index); for (const m of r) if (m.id) dbDeleteMessage(m.id); }
function convMessagesForApi() { return messages.map(m => ({ role: m.role, content: m.content })); }

// ════════════════════════════════════════════════════════════════
// Streaming
// ════════════════════════════════════════════════════════════════

let abortController = null;
async function streamResponse(win, modelId, temperature, extra) {
  const key = getApiKey();
  if (!key) { win.webContents.send('stream:error', 'API key not configured'); return; }
  abortController = new AbortController();
  const payload = { model: modelId, messages: convMessagesForApi(), temperature, stream: true, ...extra };
  try {
    const res = await fetch('https://openrouter.ai/api/v1/chat/completions', { method: 'POST', headers: { 'Authorization': `Bearer ${key}`, 'Content-Type': 'application/json', 'X-Title': 'YaOG' }, body: JSON.stringify(payload), signal: abortController.signal });
    if (!res.ok) { const errText = await res.text().catch(() => ''); win.webContents.send('stream:error', res.status === 429 ? 'Rate limit (429). Try again shortly.' : `API error ${res.status}: ${errText.slice(0, 200)}`); return; }
    const reader = res.body.getReader(); const decoder = new TextDecoder(); let buffer = ''; let fullContent = ''; let firstToken = false;
    while (true) {
      const { done, value } = await reader.read(); if (done) break;
      buffer += decoder.decode(value, { stream: true }); const lines = buffer.split('\n'); buffer = lines.pop() || '';
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue; const data = line.slice(6).trim(); if (data === '[DONE]') break;
        try { const chunk = JSON.parse(data); const content = chunk.choices?.[0]?.delta?.content; if (content) { if (!firstToken) { firstToken = true; win.webContents.send('stream:start', messages.length, modelId); } fullContent += content; win.webContents.send('stream:token', content); } } catch {}
      }
    }
    convAddMessage('assistant', fullContent, modelId, temperature);
    win.webContents.send('stream:done', fullContent);
  } catch (err) {
    if (err.name === 'AbortError') win.webContents.send('stream:done', '');
    else win.webContents.send('stream:error', err.message);
  } finally { abortController = null; }
}

// ════════════════════════════════════════════════════════════════
// FILE PROCESSING PIPELINE
// ════════════════════════════════════════════════════════════════
//
// The "deep stomach": transform raw file bytes into clean,
// structured text suitable for an LLM.  This is separate from
// all rendering / display concerns.
//

const MAX_FILE_SIZE = 2 * 1024 * 1024;        // 2 MB per file / extracted archive
const MAX_SINGLE_ENTRY = 512 * 1024;           // 512 KB per single file inside archive

const TEXT_EXTENSIONS = new Set([
  'txt','md','markdown','rst','log','cfg','ini','conf','properties',
  'json','json5','jsonl','ndjson',
  'xml','xsl','xslt','xsd','dtd','svg',
  'yaml','yml','toml',
  'csv','tsv',
  'html','htm','xhtml','css','scss','less','sass',
  'js','jsx','mjs','cjs','ts','tsx','mts','cts',
  'py','pyw','pyi','rb','php','java','kt','kts','scala','groovy','clj','cljs',
  'c','h','cpp','hpp','cc','cxx','cs','m','mm',
  'go','rs','swift','dart','lua','r','jl','ex','exs','erl','hrl',
  'sql','sh','bash','zsh','fish','bat','cmd','ps1','psm1',
  'dockerfile','makefile','cmake','rakefile','justfile',
  'gitignore','gitattributes','env','editorconfig','prettierrc','eslintrc',
  'tex','bib','sty','cls',
  'vue','svelte','astro',
  'proto','graphql','gql',
]);

function getExtChain(filePath) {
  const base = path.basename(filePath).toLowerCase();
  const parts = base.split('.');
  if (parts.length >= 3) {
    const last2 = parts.slice(-2).join('.');
    if (['tar.gz','tar.bz2','tar.xz','tar.zst'].includes(last2)) return last2;
  }
  return parts.length > 1 ? parts.pop() : '';
}

function isTextExt(ext) { return TEXT_EXTENSIONS.has(ext.toLowerCase()); }

function isLikelyBinary(buf) {
  // Check first 8KB for null bytes — strong binary indicator
  const check = buf.slice(0, 8192);
  for (let i = 0; i < check.length; i++) { if (check[i] === 0) return true; }
  return false;
}

function readAsText(filePath) {
  try {
    const buf = fs.readFileSync(filePath);
    if (buf.length > MAX_FILE_SIZE) return `[File too large: ${(buf.length / 1024 / 1024).toFixed(1)} MB — limit is ${MAX_FILE_SIZE / 1024 / 1024} MB]`;
    if (isLikelyBinary(buf)) return `[Binary file — ${buf.length} bytes, not shown]`;
    return buf.toString('utf8');
  } catch {
    try { return fs.readFileSync(filePath, 'latin1'); } catch { return '[Could not read file]'; }
  }
}

/**
 * Check if a command exists on PATH.
 */
function commandExists(cmd) {
  try { execSync(`which ${cmd}`, { stdio: 'pipe' }); return true; } catch { return false; }
}

/**
 * Pretty-format JSON content.
 */
function processJson(raw, name) {
  try {
    const parsed = JSON.parse(raw);
    return JSON.stringify(parsed, null, 2);
  } catch {
    return raw; // Return as-is if not valid JSON
  }
}

/**
 * Process a ZIP archive — list contents, extract text files.
 */
function processZip(filePath, name) {
  if (!commandExists('unzip')) return `[Archive: ${name} — 'unzip' not installed, cannot extract]`;
  const parts = [`[Archive: ${name}]`];
  try {
    // List contents
    const listing = execSync(`unzip -l "${filePath}"`, { encoding: 'utf8', maxBuffer: 1024 * 1024, timeout: 10000 });
    const files = [];
    for (const line of listing.split('\n')) {
      const m = line.match(/^\s*(\d+)\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+(.+)$/);
      if (m) files.push({ size: parseInt(m[1]), name: m[2].trim() });
    }
    parts.push(`Contents (${files.length} files):`);
    for (const f of files) parts.push(`  ${f.name} (${f.size} bytes)`);
    parts.push('');

    // Extract text files
    let totalExtracted = 0;
    for (const f of files) {
      if (totalExtracted >= MAX_FILE_SIZE) { parts.push('[Extraction limit reached, remaining files skipped]'); break; }
      if (f.size === 0 || f.name.endsWith('/')) continue; // directory
      if (f.size > MAX_SINGLE_ENTRY) { parts.push(`--- SKIPPED: ${f.name} (${(f.size / 1024).toFixed(0)} KB, too large) ---`); continue; }
      const ext = path.extname(f.name).slice(1).toLowerCase();
      if (!isTextExt(ext) && ext !== '') { parts.push(`--- SKIPPED: ${f.name} (binary/unsupported type) ---`); continue; }
      try {
        const content = execSync(`unzip -p "${filePath}" "${f.name}"`, { encoding: 'utf8', maxBuffer: MAX_SINGLE_ENTRY + 1024, timeout: 10000 });
        if (isLikelyBinary(Buffer.from(content.slice(0, 8192)))) { parts.push(`--- SKIPPED: ${f.name} (binary content) ---`); continue; }
        parts.push(`--- START OF FILE: ${f.name} ---`);
        parts.push(content);
        parts.push(`--- END OF FILE: ${f.name} ---`);
        parts.push('');
        totalExtracted += content.length;
      } catch { parts.push(`--- FAILED TO EXTRACT: ${f.name} ---`); }
    }
  } catch (e) { parts.push(`[Error processing archive: ${e.message}]`); }
  return parts.join('\n');
}

/**
 * Process tar / tar.gz / tar.bz2 / tar.xz archive.
 */
function processTar(filePath, name) {
  if (!commandExists('tar')) return `[Archive: ${name} — 'tar' not installed]`;
  const parts = [`[Archive: ${name}]`];
  try {
    const listing = execSync(`tar -tf "${filePath}"`, { encoding: 'utf8', maxBuffer: 1024 * 1024, timeout: 15000 });
    const entries = listing.trim().split('\n').filter(Boolean);
    parts.push(`Contents (${entries.length} entries):`);
    for (const e of entries) parts.push(`  ${e}`);
    parts.push('');

    let totalExtracted = 0;
    for (const entry of entries) {
      if (totalExtracted >= MAX_FILE_SIZE) { parts.push('[Extraction limit reached]'); break; }
      if (entry.endsWith('/')) continue;
      const ext = path.extname(entry).slice(1).toLowerCase();
      if (!isTextExt(ext) && ext !== '') continue;
      try {
        const content = execSync(`tar -xf "${filePath}" --to-stdout "${entry}"`, { encoding: 'utf8', maxBuffer: MAX_SINGLE_ENTRY + 1024, timeout: 10000 });
        if (isLikelyBinary(Buffer.from(content.slice(0, 8192)))) continue;
        parts.push(`--- START OF FILE: ${entry} ---`);
        parts.push(content);
        parts.push(`--- END OF FILE: ${entry} ---`);
        parts.push('');
        totalExtracted += content.length;
      } catch {}
    }
  } catch (e) { parts.push(`[Error processing archive: ${e.message}]`); }
  return parts.join('\n');
}

/**
 * Process RAR archive.
 */
function processRar(filePath, name) {
  if (!commandExists('unrar')) return `[Archive: ${name} — 'unrar' not installed. Install with: sudo apt install unrar]`;
  const parts = [`[Archive: ${name}]`];
  try {
    const listing = execSync(`unrar l "${filePath}"`, { encoding: 'utf8', maxBuffer: 1024 * 1024, timeout: 10000 });
    parts.push(listing);
    parts.push('');

    // Extract text files to stdout
    const fileList = execSync(`unrar lb "${filePath}"`, { encoding: 'utf8', maxBuffer: 1024 * 1024, timeout: 10000 });
    const entries = fileList.trim().split('\n').filter(Boolean);
    let totalExtracted = 0;
    for (const entry of entries) {
      if (totalExtracted >= MAX_FILE_SIZE) { parts.push('[Extraction limit reached]'); break; }
      if (entry.endsWith('/') || entry.endsWith('\\')) continue;
      const ext = path.extname(entry).slice(1).toLowerCase();
      if (!isTextExt(ext) && ext !== '') continue;
      try {
        const content = execSync(`unrar p -inul "${filePath}" "${entry}"`, { encoding: 'utf8', maxBuffer: MAX_SINGLE_ENTRY + 1024, timeout: 10000 });
        if (isLikelyBinary(Buffer.from(content.slice(0, 8192)))) continue;
        parts.push(`--- START OF FILE: ${entry} ---`);
        parts.push(content);
        parts.push(`--- END OF FILE: ${entry} ---`);
        parts.push('');
        totalExtracted += content.length;
      } catch {}
    }
  } catch (e) { parts.push(`[Error processing RAR: ${e.message}]`); }
  return parts.join('\n');
}

/**
 * Process 7z archive.
 */
function process7z(filePath, name) {
  if (!commandExists('7z')) return `[Archive: ${name} — '7z' not installed. Install with: sudo apt install p7zip-full]`;
  const parts = [`[Archive: ${name}]`];
  try {
    const listing = execSync(`7z l "${filePath}"`, { encoding: 'utf8', maxBuffer: 1024 * 1024, timeout: 10000 });
    parts.push(listing);
  } catch (e) { parts.push(`[Error listing 7z: ${e.message}]`); }
  return parts.join('\n');
}

/**
 * Process PDF files.
 * Strategy: try pdftotext (poppler-utils) first for best quality,
 * fall back to pdf-parse (pure Node, always available).
 */
function processPdf(filePath, name) {
  const fileSize = fs.statSync(filePath).size;
  if (fileSize > MAX_FILE_SIZE * 2) {
    return `[PDF too large: ${(fileSize / 1024 / 1024).toFixed(1)} MB — limit is ${(MAX_FILE_SIZE * 2) / 1024 / 1024} MB]`;
  }

  // Strategy 1: pdftotext (poppler-utils) — best layout fidelity
  if (commandExists('pdftotext')) {
    try {
      const text = execSync(`pdftotext -layout "${filePath}" -`, {
        encoding: 'utf8',
        maxBuffer: MAX_FILE_SIZE + 1024 * 64,
        timeout: 30000,
      }).trim();
      if (text.length > 0) {
        return `[PDF: ${name}, ${Math.ceil(fileSize / 1024)} KB]\n\n${text.slice(0, MAX_FILE_SIZE)}`;
      }
    } catch (e) {
      console.warn(`[PDF] pdftotext failed for ${name}:`, e.message);
    }
    // pdftotext might fail for scanned/image PDFs — fall through to pdf-parse
  }

  // Strategy 2: pdf-parse (pure Node — always works if installed)
  try {
    // pdf-parse is async but we need sync here; use execSync with a helper
    const helperCode = `
      const pdfParse = require('pdf-parse');
      const fs = require('fs');
      const buf = fs.readFileSync(${JSON.stringify(filePath)});
      pdfParse(buf).then(data => {
        process.stdout.write(JSON.stringify({
          pages: data.numpages,
          text: data.text
        }));
      }).catch(err => {
        process.stdout.write(JSON.stringify({ error: err.message }));
      });
    `;
    const result = execSync(`node -e ${JSON.stringify(helperCode)}`, {
      encoding: 'utf8',
      maxBuffer: MAX_FILE_SIZE + 1024 * 64,
      timeout: 30000,
      cwd: path.join(__dirname, '..'),  // so it finds node_modules
    }).trim();

    if (result) {
      try {
        const parsed = JSON.parse(result);
        if (parsed.error) {
          return `[PDF: ${name} — extraction error: ${parsed.error}]`;
        }
        if (parsed.text && parsed.text.trim().length > 0) {
          const pageInfo = parsed.pages ? `, ${parsed.pages} pages` : '';
          return `[PDF: ${name}, ${Math.ceil(fileSize / 1024)} KB${pageInfo}]\n\n${parsed.text.trim().slice(0, MAX_FILE_SIZE)}`;
        }
        return `[PDF: ${name} — no extractable text (possibly scanned/image-only PDF)]`;
      } catch {
        return `[PDF: ${name} — could not parse extraction result]`;
      }
    }
  } catch (e) {
    console.warn(`[PDF] pdf-parse failed for ${name}:`, e.message);
  }

  // Strategy 3: last resort — try strings-like extraction
  try {
    const buf = fs.readFileSync(filePath);
    // Extract printable ASCII runs of 8+ chars — crude but better than nothing
    const strings = [];
    let current = '';
    for (let i = 0; i < Math.min(buf.length, MAX_FILE_SIZE); i++) {
      const b = buf[i];
      if (b >= 32 && b < 127) {
        current += String.fromCharCode(b);
      } else {
        if (current.length >= 8) strings.push(current);
        current = '';
      }
    }
    if (current.length >= 8) strings.push(current);
    const extracted = strings.join(' ').trim();
    if (extracted.length > 100) {
      return `[PDF: ${name} — raw text extraction (limited quality), ${Math.ceil(fileSize / 1024)} KB]\n\n${extracted.slice(0, MAX_FILE_SIZE)}`;
    }
  } catch {}

  return `[PDF: ${name} — could not extract text. Install poppler-utils for best PDF support: sudo apt install poppler-utils]`;
}

/**
 * Master file processor — the "deep stomach".
 * Takes a file path, returns structured text content suitable for an LLM.
 */
function processFile(filePath) {
  const name = path.basename(filePath);
  const ext = getExtChain(filePath);

  // PDFs — first-class support
  if (ext === 'pdf') return processPdf(filePath, name);

  // Archives
  if (ext === 'zip' || ext === 'jar' || ext === 'war' || ext === 'epub') return processZip(filePath, name);
  if (ext === 'tar' || ext === 'tar.gz' || ext === 'tgz' || ext === 'tar.bz2' || ext === 'tar.xz' || ext === 'tar.zst') return processTar(filePath, name);
  if (ext === 'rar') return processRar(filePath, name);
  if (ext === '7z') return process7z(filePath, name);
  if (ext === 'gz' && !ext.startsWith('tar')) {
    // Single gzip file — decompress and read
    try {
      const { gunzipSync } = require('zlib');
      const buf = fs.readFileSync(filePath);
      const decompressed = gunzipSync(buf);
      if (isLikelyBinary(decompressed)) return `[Binary gzip file — ${decompressed.length} bytes]`;
      return decompressed.toString('utf8').slice(0, MAX_FILE_SIZE);
    } catch { return `[Could not decompress ${name}]`; }
  }

  // Structured data — read and reformat
  const raw = readAsText(filePath);
  if (raw.startsWith('[')) return raw; // error message from readAsText

  if (ext === 'json' || ext === 'json5' || ext === 'jsonl' || ext === 'ndjson') {
    if (ext === 'jsonl' || ext === 'ndjson') return raw; // line-delimited, don't reformat
    return processJson(raw, name);
  }

  // XML — validate it's well-formed, return as-is
  if (ext === 'xml' || ext === 'xsl' || ext === 'xslt' || ext === 'xsd' || ext === 'svg') {
    return raw; // XML is already structured text
  }

  // CSV / TSV — return as-is (structured enough for the model)
  if (ext === 'csv' || ext === 'tsv') return raw;

  // Everything else — text or binary detection already handled in readAsText
  return raw;
}

// ════════════════════════════════════════════════════════════════
// IPC Handlers
// ════════════════════════════════════════════════════════════════

function registerIPC(win) {

  // ── Conversations ──
  ipcMain.handle('conv:list', () => dbGetConversations());
  ipcMain.handle('conv:new', () => { convNew(); return true; });
  ipcMain.handle('conv:load', (_, id) => { convLoad(id); return messages.filter(m => m.role !== 'system'); });
  ipcMain.handle('conv:delete', (_, id) => { dbDeleteConversation(id); if (currentConvId === id) convNew(); return true; });
  ipcMain.handle('conv:rename', (_, id, title) => { dbRenameConversation(id, title); return true; });
  ipcMain.handle('conv:export', (_, id) => {
    const convs = dbGetConversations(); const conv = convs.find(c => c.id === id);
    const msgs = dbGetMessages(id);
    return JSON.stringify({ type: 'or-client-chat', title: conv?.title || 'Export', messages: msgs }, null, 2);
  });
  ipcMain.handle('conv:import', async (_, jsonStr) => {
    const data = JSON.parse(jsonStr);
    if (data.type !== 'or-client-chat') throw new Error('Invalid format');
    const cid = dbAddConversation((data.title || 'Imported') + ' (Imported)');
    for (const m of (data.messages || [])) dbAddMessage(cid, m.role, m.content, m.model_used || null, m.temperature_used || 0.7);
    return true;
  });

  // ── Chat ──
  ipcMain.handle('chat:send', async (_, text, modelId, temp, sysPrompt, opts) => {
    const hasSystem = messages.length > 0 && messages[0].role === 'system';
    if (hasSystem && sysPrompt) convUpdateMessage(0, sysPrompt);
    else if (hasSystem && !sysPrompt) { const s = messages[0]; messages.splice(0, 1); if (s.id) dbDeleteMessage(s.id); }
    else if (!hasSystem && sysPrompt) convInsertSystem(sysPrompt);

    convAddMessage('user', text, null, temp);

    if (currentConvId) {
      const conv = dbGetConversation(currentConvId);
      if (conv && conv.title === 'New Chat') {
        let titleText = text.replace(/<div class="yaog-file-content"[^>]*>[\s\S]*?<\/div>/g, '').trim();
        if (!titleText) titleText = 'Chat';
        dbRenameConversation(currentConvId, titleText.length > 50 ? titleText.slice(0, 50) + '…' : titleText);
      }
    }

    let effectiveModel = modelId;
    if (opts?.webSearch && !effectiveModel.endsWith(':online')) effectiveModel += ':online';
    if (!opts?.webSearch && effectiveModel.endsWith(':online')) effectiveModel = effectiveModel.replace(':online', '');
    const extra = {}; if (opts?.reasoning) extra.include_reasoning = true;

    await streamResponse(win, effectiveModel, temp, extra);
    return { conversations: dbGetConversations(), tokenCount: estimateTokens() };
  });

  ipcMain.handle('chat:stop', () => { if (abortController) abortController.abort(); return true; });

  ipcMain.handle('chat:edit', async (_, index, newContent, modelId, temp, opts) => {
    convUpdateMessage(index, newContent); convPruneAfter(index);
    let effectiveModel = modelId;
    if (opts?.webSearch && !effectiveModel.endsWith(':online')) effectiveModel += ':online';
    if (!opts?.webSearch && effectiveModel.endsWith(':online')) effectiveModel = effectiveModel.replace(':online', '');
    const extra = {}; if (opts?.reasoning) extra.include_reasoning = true;
    await streamResponse(win, effectiveModel, temp, extra);
    return { conversations: dbGetConversations(), tokenCount: estimateTokens() };
  });

  ipcMain.handle('chat:regenerate', async (_, index, modelId, temp, opts) => {
    if (messages[index]?.role === 'assistant') convPruneFrom(index); else convPruneAfter(index);
    let effectiveModel = modelId;
    if (opts?.webSearch && !effectiveModel.endsWith(':online')) effectiveModel += ':online';
    if (!opts?.webSearch && effectiveModel.endsWith(':online')) effectiveModel = effectiveModel.replace(':online', '');
    const extra = {}; if (opts?.reasoning) extra.include_reasoning = true;
    await streamResponse(win, effectiveModel, temp, extra);
    return { conversations: dbGetConversations(), tokenCount: estimateTokens() };
  });

  ipcMain.handle('chat:deleteMsg', (_, index) => {
    convPruneFrom(index);
    return { messages: messages.filter(m => m.role !== 'system'), tokenCount: estimateTokens() };
  });

  ipcMain.handle('chat:getMessages', () => messages.filter(m => m.role !== 'system'));

  // Return ALL messages including file-content blocks (for full context copy)
  ipcMain.handle('chat:getFullMessages', () => [...messages]);

  // ── Token counting ──
  function estimateTokens() { let c = 0; for (const m of messages) { c += 4 + Math.ceil((m.content || '').length / 4) + Math.ceil((m.role || '').length / 4); } return c + 2; }
  ipcMain.handle('chat:tokenCount', () => estimateTokens());

  // ── Models ──
  ipcMain.handle('models:list', () => models);
  ipcMain.handle('models:add', (_, name, id) => { if (models.some(m => m.id === id)) return models; models.push({ name, id }); saveModels(models); return models; });
  ipcMain.handle('models:update', (_, idx, name, id) => { if (idx >= 0 && idx < models.length) { models[idx] = { name, id }; saveModels(models); } return models; });
  ipcMain.handle('models:delete', (_, idx) => { if (idx >= 0 && idx < models.length) { models.splice(idx, 1); saveModels(models); } return models; });
  ipcMain.handle('models:move', (_, idx, dir) => { const t = dir === 'up' ? idx - 1 : idx + 1; if (t >= 0 && t < models.length) { [models[idx], models[t]] = [models[t], models[idx]]; saveModels(models); } return models; });
  ipcMain.handle('models:metadata', () => modelMetadata);

  // ── System Prompts ──
  ipcMain.handle('prompts:list', () => dbGetPrompts());
  ipcMain.handle('prompts:save', (_, id, name, text) => { if (id) dbUpdatePrompt(id, name, text); else dbAddPrompt(name, text); return dbGetPrompts(); });
  ipcMain.handle('prompts:delete', (_, id) => { dbDeletePrompt(id); return dbGetPrompts(); });

  // ── Settings ──
  ipcMain.handle('settings:get', () => ({ ...settings, apiKeySet: !!getApiKey() }));
  ipcMain.handle('settings:set', (_, key, value) => { settings[key] = value; saveSettings(settings); return true; });
  ipcMain.handle('settings:getApiKey', () => { const k = getApiKey(); return k ? k.slice(0, 8) + '…' + k.slice(-4) : ''; });
  ipcMain.handle('settings:saveApiKey', (_, key) => saveApiKey(key));

  // ── Clipboard (for context menu & programmatic copy) ──
  ipcMain.handle('clipboard:write', (_, text) => { clipboard.writeText(text); return true; });

  // ── File dialogs ──
  ipcMain.handle('dialog:openFiles', async () => {
    const result = await dialog.showOpenDialog(win, {
      properties: ['openFile', 'multiSelections'],
      filters: [
        { name: 'Documents & Code', extensions: ['pdf','txt','md','json','csv','xml','html','py','js','ts','c','cpp','java','go','rs','sql','log','yml','yaml','toml','sh','rb','php','css','scss','jsx','tsx','vue','svelte'] },
        { name: 'PDF Documents', extensions: ['pdf'] },
        { name: 'Archives', extensions: ['zip','tar','gz','tgz','rar','7z','bz2','xz'] },
        { name: 'All Files', extensions: ['*'] },
      ],
    });
    if (result.canceled) return [];
    return result.filePaths.map(fp => ({
      path: fp,
      name: path.basename(fp),
      content: processFile(fp),
    }));
  });

  ipcMain.handle('dialog:saveFile', async (_, defaultName, content) => {
    const result = await dialog.showSaveDialog(win, { defaultPath: defaultName, filters: [{ name: 'JSON', extensions: ['json'] }] });
    if (!result.canceled && result.filePath) { fs.writeFileSync(result.filePath, content); return true; }
    return false;
  });

  ipcMain.handle('dialog:importFile', async () => {
    const result = await dialog.showOpenDialog(win, { properties: ['openFile'], filters: [{ name: 'JSON', extensions: ['json'] }] });
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
    width: 1100, height: 800, minWidth: 640, minHeight: 500,
    backgroundColor: '#0F1117', titleBarStyle: 'default',
    webPreferences: { preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, nodeIntegration: false },
  });

  // ── Close confirmation ──
  mainWindow.on('close', (e) => {
    if (settings.confirm_close !== false) {
      const choice = dialog.showMessageBoxSync(mainWindow, {
        type: 'question',
        buttons: ['Close', 'Cancel'],
        defaultId: 1,
        cancelId: 1,
        title: 'Close YaOG',
        message: 'Close the application?',
        detail: 'Your conversation history is saved automatically.',
      });
      if (choice === 1) e.preventDefault();
    }
  });

  // ── Native context menu (Cut / Copy / Paste / Select All) ──
  mainWindow.webContents.on('context-menu', (_event, params) => {
    const template = [];

    // If text is selected, offer copy
    if (params.selectionText) {
      template.push({ label: 'Copy', role: 'copy' });
      template.push({ type: 'separator' });
    }

    // If in an editable field
    if (params.isEditable) {
      template.push({ label: 'Undo', role: 'undo', enabled: params.editFlags.canUndo });
      template.push({ label: 'Redo', role: 'redo', enabled: params.editFlags.canRedo });
      template.push({ type: 'separator' });
      template.push({ label: 'Cut', role: 'cut', enabled: params.editFlags.canCut });
      template.push({ label: 'Copy', role: 'copy', enabled: params.editFlags.canCopy });
      template.push({ label: 'Paste', role: 'paste', enabled: params.editFlags.canPaste });
      template.push({ type: 'separator' });
      template.push({ label: 'Select All', role: 'selectAll', enabled: params.editFlags.canSelectAll });
    } else if (!params.selectionText) {
      // Not editable, no selection — just offer select all
      template.push({ label: 'Select All', role: 'selectAll' });
    } else {
      // Not editable, has selection
      template.push({ label: 'Select All', role: 'selectAll' });
    }

    if (template.length > 0) {
      Menu.buildFromTemplate(template).popup();
    }
  });

  if (process.argv.includes('--dev') || !app.isPackaged) mainWindow.loadURL('http://localhost:5173');
  else mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));

  registerIPC(mainWindow);
  fetchModelMetadata();
}

app.whenReady().then(() => {
  ensureDataDir(); initDatabase(); migrateNewChatTitles(); createWindow();
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});

app.on('window-all-closed', () => { if (db) db.close(); app.quit(); });
