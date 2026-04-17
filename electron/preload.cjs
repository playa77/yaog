// electron/preload.cjs — Context Bridge
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  // Conversations
  convList:    ()              => ipcRenderer.invoke('conv:list'),
  convNew:     ()              => ipcRenderer.invoke('conv:new'),
  convLoad:    (id)            => ipcRenderer.invoke('conv:load', id),
  convDelete:  (id)            => ipcRenderer.invoke('conv:delete', id),
  convRename:  (id, title)     => ipcRenderer.invoke('conv:rename', id, title),
  convExport:  (id)            => ipcRenderer.invoke('conv:export', id),
  convImport:  (json)          => ipcRenderer.invoke('conv:import', json),
  tabSwitch:  (tabId)         => ipcRenderer.invoke("tab:switch", tabId),
  tabClose:   (tabId)         => ipcRenderer.invoke("tab:close", tabId),

  // Chat
  chatSend:         (tabId, text, modelId, temp, sysPrompt, opts) => ipcRenderer.invoke('chat:send', tabId, text, modelId, temp, sysPrompt, opts),
  chatStop:         (tabId)                                      => ipcRenderer.invoke('chat:stop', tabId),
  chatEdit:         (tabId, index, content, modelId, temp, opts)   => ipcRenderer.invoke('chat:edit', tabId, index, content, modelId, temp, opts),
  chatRegenerate:   (tabId, index, modelId, temp, opts)            => ipcRenderer.invoke('chat:regenerate', tabId, index, modelId, temp, opts),
  chatDeleteMsg:    (tabId, index)                                 => ipcRenderer.invoke('chat:deleteMsg', tabId, index),
  chatGetMessages:  (tabId)                                      => ipcRenderer.invoke('chat:getMessages', tabId),
  chatGetFullMessages: (tabId)                                   => ipcRenderer.invoke('chat:getFullMessages', tabId),
  chatTokenCount:   (tabId)                                      => ipcRenderer.invoke('chat:tokenCount', tabId),
  chatTokenCountFull: (tabId, text)                          => ipcRenderer.invoke('chat:tokenCountFull', tabId, text),

  // Models
  modelsList:    ()                    => ipcRenderer.invoke('models:list'),
  modelsAdd:     (name, id)            => ipcRenderer.invoke('models:add', name, id),
  modelsUpdate:  (idx, name, id)       => ipcRenderer.invoke('models:update', idx, name, id),
  modelsDelete:  (idx)                 => ipcRenderer.invoke('models:delete', idx),
  modelsMove:    (idx, dir)            => ipcRenderer.invoke('models:move', idx, dir),
  modelsMetadata: (modelId = null)     => ipcRenderer.invoke('models:metadata', modelId),

  // System Prompts
  promptsList:   ()                    => ipcRenderer.invoke('prompts:list'),
  promptsSave:   (id, name, text, whenToUse) => ipcRenderer.invoke('prompts:save', id, name, text, whenToUse),
  promptsDelete: (id)                  => ipcRenderer.invoke('prompts:delete', id),

  // Settings
  settingsGet:       ()                => ipcRenderer.invoke('settings:get'),
  settingsSet:       (key, val)        => ipcRenderer.invoke('settings:set', key, val),
  settingsGetApiKey: ()                => ipcRenderer.invoke('settings:getApiKey'),
  settingsSaveApiKey: (key)            => ipcRenderer.invoke('settings:saveApiKey', key),

  // Clipboard (main process — works reliably in Electron)
  clipboardWrite:    (text)            => ipcRenderer.invoke('clipboard:write', text),

  // Dialogs
  dialogOpenFiles:  ()                 => ipcRenderer.invoke('dialog:openFiles'),
  dialogSaveFile:   (name, content)    => ipcRenderer.invoke('dialog:saveFile', name, content),
  dialogImportFile: ()                 => ipcRenderer.invoke('dialog:importFile'),

  // Stream events (main → renderer)
  onStreamStart: (cb) => { ipcRenderer.on('stream:start', (_, tabId, idx, model) => cb(tabId, idx, model)); },
  onStreamToken: (cb) => { ipcRenderer.on('stream:token', (_, tabId, text) => cb(tabId, text)); },
  onStreamDone:  (cb) => { ipcRenderer.on('stream:done',  (_, tabId, content) => cb(tabId, content)); },
  onStreamError: (cb) => { ipcRenderer.on('stream:error', (_, tabId, msg) => cb(tabId, msg)); },
});
