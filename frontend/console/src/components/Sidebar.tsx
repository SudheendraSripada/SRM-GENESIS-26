import React from 'react';
import { NavTab, ScreenId } from '../types';
import { Terminal, Plus, Play, FolderOpen, History, User, ChevronsUpDown } from 'lucide-react';

interface SidebarProps {
  currentTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  onNewRun: () => void;
  onOpenWorkspace: () => void;
  currentScreen: ScreenId;
  onScreenChange: (screen: ScreenId) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onTabChange,
  onNewRun,
  onOpenWorkspace,
  currentScreen,
  onScreenChange,
}) => {
  return (
    <aside
      id="app-sidebar"
      className="fixed left-0 top-0 h-full w-[260px] bg-[#0e0e10] border-r border-[#554336]/30 z-50 flex flex-col justify-between select-none"
    >
      <div className="flex flex-col">
        {/* Brand Header */}
        <div className="h-14 px-4 flex items-center justify-between border-b border-[#554336]/20">
          <button
            onClick={() => {
              onTabChange('runs');
              onScreenChange('prompt');
            }}
            className="flex items-center gap-2 text-left group focus:outline-none"
          >
            <div className="w-5 h-5 rounded-[0.125rem] bg-[#ffb77d] flex items-center justify-center transition-transform group-hover:scale-105">
              <Terminal className="w-3.5 h-3.5 text-[#4d2600]" />
            </div>
            <span className="font-label-caps text-[11px] text-[#e5e1e4] tracking-wider uppercase font-semibold">
              Console
            </span>
          </button>
          <span className="font-label-code text-[11px] text-[#dbc2b0]/70 border border-[#554336]/30 px-1.5 py-0.5 rounded-[0.125rem]">
            v0.9
          </span>
        </div>

        {/* New Run Button */}
        <div className="p-4">
          <button
            id="new-run-button"
            onClick={onNewRun}
            className="w-full flex items-center justify-between px-3 py-2 bg-[#ffb77d] text-[#4d2600] rounded-[0.125rem] hover:bg-[#ffddb8] active:scale-[0.99] transition-all font-medium cursor-pointer shadow-sm"
          >
            <div className="flex items-center gap-2">
              <Plus className="w-4 h-4 text-[#4d2600]" />
              <span className="text-[14px] font-medium leading-none">New Run</span>
            </div>
            <span className="font-label-code text-[10px] text-[#4d2600]/80 font-semibold">
              ⌘N
            </span>
          </button>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex flex-col px-1 space-y-0.5" id="nav-menu">
          <button
            id="nav-runs"
            onClick={() => onTabChange('runs')}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-[0.125rem] transition-colors text-left ${
              currentTab === 'runs'
                ? 'bg-[#201f22] text-[#e5e1e4] font-medium border-l-2 border-[#d97707]'
                : 'text-[#dbc2b0]/80 hover:bg-[#1c1b1d] hover:text-[#e5e1e4]'
            }`}
          >
            <Play className="w-4 h-4 shrink-0" />
            <span className="text-[14px]">Runs</span>
          </button>

          <button
            id="nav-projects"
            onClick={() => onTabChange('projects')}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-[0.125rem] transition-colors text-left ${
              currentTab === 'projects'
                ? 'bg-[#201f22] text-[#e5e1e4] font-medium border-l-2 border-[#d97707]'
                : 'text-[#dbc2b0]/80 hover:bg-[#1c1b1d] hover:text-[#e5e1e4]'
            }`}
          >
            <FolderOpen className="w-4 h-4 shrink-0" />
            <span className="text-[14px]">Projects</span>
          </button>

          <button
            id="nav-history"
            onClick={() => onTabChange('history')}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-[0.125rem] transition-colors text-left ${
              currentTab === 'history'
                ? 'bg-[#201f22] text-[#e5e1e4] font-medium border-l-2 border-[#d97707]'
                : 'text-[#dbc2b0]/80 hover:bg-[#1c1b1d] hover:text-[#e5e1e4]'
            }`}
          >
            <History className="w-4 h-4 shrink-0" />
            <span className="text-[14px]">History</span>
          </button>
        </nav>
      </div>

      {/* Workspace Footer Card */}
      <div className="p-4 border-t border-[#554336]/20 flex flex-col gap-3">
        <button
          id="workspace-switcher"
          onClick={onOpenWorkspace}
          className="w-full flex items-center justify-between text-left group hover:bg-[#1c1b1d] p-1.5 -m-1.5 rounded-[0.125rem] transition-colors"
        >
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 rounded-full bg-[#ffb77d] flex items-center justify-center shrink-0">
              <User className="w-4 h-4 text-[#4d2600]" />
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-[13px] text-[#e5e1e4] truncate leading-tight font-medium">
                mono-workspace
              </span>
              <span className="font-label-code text-[11px] text-[#dbc2b0]/60 truncate leading-tight">
                primary-node
              </span>
            </div>
          </div>
          <ChevronsUpDown className="w-4 h-4 text-[#dbc2b0]/60 group-hover:text-[#e5e1e4] shrink-0" />
        </button>
      </div>
    </aside>
  );
};
