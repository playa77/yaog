import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';
import type { TabState, TabContextType, Conversation, LoadedConversation } from '../types';

const TabContext = createContext<TabContextType | undefined>(undefined);

export const useTabContext = () => {
  const context = useContext(TabContext);
  if (!context) {
    throw new Error('useTabContext must be used within a TabProvider');
  }
  return context;
};

const createDefaultTab = (id: string, conversationId: number | null = null, title: string = 'New Chat'): TabState => ({
  id,
  conversationId,
  title,
  fullTitle: title,
  messages: [],
  selectedModel: '',
  temperature: 1.0,
  selectedPrompt: null,
  useWebSearch: false,
  isStreaming: false,
  streamContent: '',
  streamModel: '',
  error: null,
  pendingInput: '',
  stagedFiles: [],
  isNew: conversationId === null,
  isDirty: false,
});

export const TabProvider: React.FC<{ children: React.ReactNode, conversations: Conversation[] }> = ({ children, conversations }) => {
  const [tabs, setTabs] = useState<TabState[]>([]);
  const [activeTabId, setActiveTabId] = useState<string>('');

  const activeTab = useMemo(() => {
    return tabs.find(t => t.id === activeTabId) || tabs[0];
  }, [tabs, activeTabId]);

  const saveTabToBackend = useCallback(async (tabId: string) => {
    const tab = tabs.find(t => t.id === tabId);
    if (tab && tab.conversationId !== null) {
      await window.api.tabSwitch(tabId);
    }
  }, [tabs]);

  const openTab = useCallback(async (options?: { conversationId?: number; title?: string }) => {
    const id = `tab-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
    const newTab = createDefaultTab(id, options?.conversationId, options?.title);
    setTabs(prev => [...prev, newTab]);
    await window.api.tabSwitch(id); setActiveTabId(id);
    return id;
  }, []);

  const closeTab = useCallback(async (tabId: string) => {
    await window.api.tabClose(tabId);
    
    let nextTabId: string | null = null;
    setTabs(prev => {
      const index = prev.findIndex(t => t.id === tabId);
      if (index === -1) return prev;
      const newTabs = prev.filter(t => t.id !== tabId);
      if (tabId === activeTabId && newTabs.length > 0) {
        nextTabId = newTabs[Math.min(index, newTabs.length - 1)].id;
      }
      return newTabs;
    });

    if (nextTabId) {
      await window.api.tabSwitch(nextTabId);
      setActiveTabId(nextTabId);
    } else if (tabId === activeTabId) {
      setActiveTabId('');
    }
  }, [activeTabId]);

  const switchTab = useCallback(async (tabId: string) => {
    if (activeTabId) {
      await saveTabToBackend(activeTabId);
    }
    await window.api.tabSwitch(tabId); setActiveTabId(tabId);
  }, [activeTabId, saveTabToBackend]);

  const updateTab = useCallback((tabId: string, updates: Partial<TabState>) => {
    setTabs(prev => prev.map(t => t.id === tabId ? { ...t, ...updates } : t));
  }, []);

  const reorderTabs = useCallback((fromIndex: number, toIndex: number) => {
    setTabs(prev => {
      const result = Array.from(prev);
      const [removed] = result.splice(fromIndex, 1);
      result.splice(toIndex, 0, removed);
      return result;
    });
  }, []);

  const loadConversationIntoNewTab = useCallback(async (conversationId: number) => {
    // Check if already open
    const existingTabId = tabs.find(t => t.conversationId === conversationId)?.id;
    if (existingTabId) {
      await switchTab(existingTabId);
      return existingTabId;
    }

    const conversation = conversations.find(c => c.id === conversationId);
    const title = conversation?.title || `Conversation ${conversationId}`;
    
    const id = `tab-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
    const newTab: TabState = {
      ...createDefaultTab(id, conversationId, title),
      messages: [], // Will be rendered in App.tsx for now
      selectedModel: '',
      temperature: 1.0,
      selectedPrompt: null,
      useWebSearch: false,
    };

    setTabs(prev => [...prev, newTab]);
    await window.api.tabSwitch(id); setActiveTabId(id);
    const loaded: LoadedConversation = await window.api.convLoad(conversationId);
    updateTab(id, {
      selectedModel: loaded.state.modelId || '',
      temperature: loaded.state.temperature ?? 1.0,
      selectedPrompt: loaded.state.systemPrompt,
      useWebSearch: loaded.state.webSearch,
    });
    return id;
  }, [tabs, conversations, switchTab, updateTab]);

  const findTabByConversationId = useCallback((conversationId: number) => {
    const tab = tabs.find(t => t.conversationId === conversationId);
    return tab ? tab.id : null;
  }, [tabs]);

  const getTabIndex = useCallback((tabId: string) => {
    return tabs.findIndex(t => t.id === tabId);
  }, [tabs]);

  const updateTabsForConversation = useCallback((conversationId: number, title: string) => {
    setTabs(prev => prev.map(t => t.conversationId === conversationId ? { ...t, title, fullTitle: title } : t));
  }, []);

  const loadConversationIntoTab = useCallback(async (conversationId: number, tabId: string) => {
    const conversation = conversations.find(c => c.id === conversationId);
    const title = conversation?.title || `Conversation ${conversationId}`;
    await window.api.tabSwitch(tabId); setActiveTabId(tabId);
    const loaded: LoadedConversation = await window.api.convLoad(conversationId);
    
    const updates: Partial<TabState> = {
      conversationId,
      title,
      fullTitle: title,
      messages: [], // Rendered in App.tsx
      selectedModel: loaded.state.modelId || '',
      temperature: loaded.state.temperature ?? 1.0,
      selectedPrompt: loaded.state.systemPrompt,
      useWebSearch: loaded.state.webSearch,
      isNew: false,
    };

    updateTab(tabId, updates);
    return tabId;
  }, [conversations, updateTab]);

  const value = useMemo(() => ({
    tabs,
    activeTabId,
    activeTab,
    openTab,
    closeTab,
    switchTab,
    updateTab,
    reorderTabs,
    saveTabToBackend,
    loadConversationIntoNewTab,
    loadConversationIntoTab,
    findTabByConversationId,
    getTabIndex,
    updateTabsForConversation,
  }), [
    tabs, 
    activeTabId, 
    activeTab, 
    openTab, 
    closeTab, 
    switchTab, 
    updateTab, 
    reorderTabs, 
    saveTabToBackend, 
    loadConversationIntoNewTab, 
    loadConversationIntoTab,
    findTabByConversationId, 
    getTabIndex,
    updateTabsForConversation,
  ]);

  return (
    <TabContext.Provider value={value}>
      {children}
    </TabContext.Provider>
  );
};
