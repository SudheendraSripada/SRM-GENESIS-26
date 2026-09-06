import React, { useState, useEffect } from 'react';
import { Search, Play, FileText, Settings, Server, ArrowRight, X } from 'lucide-react';
import { ScreenId } from '../types';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigateScreen: (screen: ScreenId) => void;
  onSelectPrompt: (prompt: string) => void;
  onSelectCluster: (cluster: string) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onNavigateScreen,
  onSelectPrompt,
  onSelectCluster,
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const actions = [
    {
      id: 'act-1',
      category: 'Navigation',
      label: 'New Run: Describe what you need to test',
      shortcut: '⌘N',
      action: () => {
        onNavigateScreen('prompt');
        onClose();
      },
    },
    {
      id: 'act-2',
      category: 'Screen Jump',
      label: 'Jump to Step 1: Analysing (Screen 2)',
      shortcut: '2',
      action: () => {
        onNavigateScreen('analysing');
        onClose();
      },
    },
    {
      id: 'act-3',
      category: 'Screen Jump',
      label: 'Jump to Step 3: Validating checklist (Screen 3)',
      shortcut: '3',
      action: () => {
        onNavigateScreen('validating');
        onClose();
      },
    },
    {
      id: 'act-4',
      category: 'Screen Jump',
      label: 'Jump to Step 5: Testing telemetry & terminal (Screen 4)',
      shortcut: '4',
      action: () => {
        onNavigateScreen('testing');
        onClose();
      },
    },
    {
      id: 'act-5',
      category: 'Screen Jump',
      label: 'Jump to Report: Pass Boundary Found (Screen 5)',
      shortcut: '5',
      action: () => {
        onNavigateScreen('report');
        onClose();
      },
    },
    {
      id: 'act-6',
      category: 'Presets',
      label: 'Run /fuzzy-auth permutations across /v2/sessions',
      shortcut: '↵',
      action: () => {
        onSelectPrompt(
          'Run fuzzy auth permutations across /v2/sessions with malformed JWT signatures'
        );
        onNavigateScreen('prompt');
        onClose();
      },
    },
    {
      id: 'act-7',
      category: 'Presets',
      label: 'Run /load-spike checkout webhook endpoints up to 10k rps',
      shortcut: '↵',
      action: () => {
        onSelectPrompt(
          'Simulate concurrent load spikes on checkout webhook endpoints up to 10k rps'
        );
        onNavigateScreen('prompt');
        onClose();
      },
    },
    {
      id: 'act-8',
      category: 'Cluster',
      label: 'Switch to prod-eu-west-1 (Frankfurt)',
      shortcut: 'EU',
      action: () => {
        onSelectCluster('prod-eu-west-1');
        onClose();
      },
    },
    {
      id: 'act-9',
      category: 'Cluster',
      label: 'Switch to prod-us-east-1 (N. Virginia)',
      shortcut: 'US',
      action: () => {
        onSelectCluster('prod-us-east-1');
        onClose();
      },
    },
  ];

  const filtered = actions.filter((a) =>
    a.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div
      id="command-palette-backdrop"
      className="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-black/70 backdrop-blur-xs p-4 animate-in fade-in duration-100"
      onClick={onClose}
    >
      <div
        id="command-palette"
        className="w-full max-w-xl bg-[#18181b] border border-[#3f3f46] rounded-[0.25rem] shadow-2xl overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-[#353437] bg-[#201f22]">
          <Search className="w-4 h-4 text-[#ffb77d] shrink-0" />
          <input
            type="text"
            autoFocus
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Type a command or search screens, runs, presets..."
            className="w-full bg-transparent border-none outline-none text-[14px] text-[#e5e1e4] placeholder:text-[#dbc2b0]/40"
          />
          <span className="font-label-code text-[11px] text-[#dbc2b0]/50 bg-[#2a2a2c] px-1.5 py-0.5 rounded-[0.125rem]">
            ESC
          </span>
        </div>

        {/* Results list */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-1">
          {filtered.length === 0 ? (
            <div className="py-8 text-center text-[#dbc2b0]/50 text-xs font-label-code">
              No matching commands found.
            </div>
          ) : (
            filtered.map((item) => (
              <button
                key={item.id}
                onClick={item.action}
                className="w-full flex items-center justify-between px-3 py-2 rounded-[0.125rem] hover:bg-[#201f22] text-left transition-colors group cursor-pointer"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="font-label-caps text-[9px] text-[#dbc2b0]/50 bg-[#201f22] px-1 py-0.5 rounded-[0.125rem] tracking-wider uppercase shrink-0">
                    {item.category}
                  </span>
                  <span className="text-[13px] text-[#e5e1e4] group-hover:text-[#ffb77d] transition-colors truncate">
                    {item.label}
                  </span>
                </div>
                <span className="font-label-code text-[11px] text-[#dbc2b0]/40 group-hover:text-[#ffb77d] shrink-0 ml-2">
                  {item.shortcut}
                </span>
              </button>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 bg-[#201f22] border-t border-[#353437] flex items-center justify-between text-[11px] font-label-code text-[#dbc2b0]/50">
          <span>Navigate with ⌘K / Arrow Keys</span>
          <span>CONSOLE v0.9</span>
        </div>
      </div>
    </div>
  );
};
