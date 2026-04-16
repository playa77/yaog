import React from 'react';
import { MessageSquare, FileText, X } from 'lucide-react';
import { useTabContext } from '../contexts/TabContext';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import Tooltip from './Tooltip';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const TabBar: React.FC = () => {
  const { tabs, activeTabId, switchTab, closeTab } = useTabContext();

  const truncateTitle = (title: string) => {
    if (title.length <= 12) return title;
    return title.substring(0, 11) + '…';
  };

  if (tabs.length === 0) return null;

  return (
    <div className="h-9 bg-bg-surface border-b border-border flex items-center overflow-x-auto no-scrollbar shrink-0">
      {tabs.map((tab) => {
        const isActive = tab.id === activeTabId;
        const Icon = tab.conversationId === null ? MessageSquare : FileText;

        return (
          <Tooltip key={tab.id} text={tab.fullTitle}>
            <div
              onClick={() => switchTab(tab.id)}
              className={cn(
                "h-full min-w-[120px] max-w-[200px] px-3 flex items-center gap-2 border-r border-border cursor-pointer select-none transition-colors group relative",
                isActive ? "bg-bg-elevated" : "hover:bg-bg-hover"
              )}
            >
              <Icon 
                size={14} 
                className={cn(isActive ? "text-accent" : "text-text-muted group-hover:text-text")} 
              />
              
              <span className={cn(
                "fs-ui-xs truncate flex-1",
                isActive ? "text-text-bright font-medium" : "text-text-muted group-hover:text-text"
              )}>
                {truncateTitle(tab.title)}
              </span>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  closeTab(tab.id);
                }}
                className="ml-auto p-0.5 rounded-sm opacity-0 group-hover:opacity-50 hover:!opacity-100 hover:bg-bg-elevated text-text-muted hover:text-danger transition-all"
                aria-label="Close tab"
              >
                <X size={12} />
              </button>

              {isActive && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent" />
              )}
            </div>
          </Tooltip>
        );
      })}
    </div>
  );
};

export default TabBar;
