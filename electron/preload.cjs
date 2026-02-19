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

  // Chat
  chatSend:       (text, modelId, temp, sysPrompt, opts) => ipcRenderer.invoke('chat:send', text, modelId, temp, sysPrompt, opts),
  chatStop:       ()                                      => ipcRenderer.invoke('chat:stop'),
  chatEdit:       (index, content, modelId, temp, opts)   => ipcRenderer.invoke('chat:edit', index, content, modelId, temp, opts),
  chatRegenerate: (index, modelId, temp, opts)            => ipcRenderer.invoke('chat:regenerate', index, modelId, temp, opts),
  chatDeleteMsg:  (index)                                 => ipcRenderer.invoke('chat:deleteMsg', index),
  chatGetMessages: ()                                     => ipcRenderer.invoke('chat:getMessages'),
  chatTokenCount: ()                                      => ipcRenderer.invoke('chat:tokenCount'),

  // Models
  modelsList:    ()                    => ipcRenderer.invoke('models:list'),
  modelsAdd:     (name, id)            => ipcRenderer.invoke('models:add', name, id),
  modelsUpdate:  (idx, name, id)       => ipcRenderer.invoke('models:update', idx, name, id),
  modelsDelete:  (idx)                 => ipcRenderer.invoke('models:delete', idx),
  modelsMove:    (idx, dir)            => ipcRenderer.invoke('models:move', idx, dir),
  modelsMetadata: ()                   => ipcRenderer.invoke('models:metadata'),

  // System Prompts
  promptsList:   ()                    => ipcRenderer.invoke('prompts:list'),
  promptsSave:   (id, name, text)      => ipcRenderer.invoke('prompts:save', id, name, text),
  promptsDelete: (id)                  => ipcRenderer.invoke('prompts:delete', id),

  // Settings
  settingsGet:      ()                 => ipcRenderer.invoke('settings:get'),
  settingsSet:      (key, val)         => ipcRenderer.invoke('settings:set', key, val),
  settingsGetApiKey: ()                => ipcRenderer.invoke('settings:getApiKey'),
  settingsSaveApiKey: (key)            => ipcRenderer.invoke('settings:saveApiKey', key),

  // Dialogs
  dialogOpenFiles: ()                  => ipcRenderer.invoke('dialog:openFiles'),
  dialogSaveFile:  (name, content)     => ipcRenderer.invoke('dialog:saveFile', name, content),
  dialogImportFile: ()                 => ipcRenderer.invoke('dialog:importFile'),

  // Stream events (main → renderer)
  onStreamStart: (cb) => { ipcRenderer.on('stream:start', (_, idx, model) => cb(idx, model)); },
  onStreamToken: (cb) => { ipcRenderer.on('stream:token', (_, text) => cb(text)); },
  onStreamDone:  (cb) => { ipcRenderer.on('stream:done',  (_, content) => cb(content)); },
  onStreamError: (cb) => { ipcRenderer.on('stream:error', (_, msg) => cb(msg)); },
});
