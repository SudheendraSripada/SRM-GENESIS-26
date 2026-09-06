import React, { useState } from 'react';
import { Search, User, Check } from 'lucide-react';

interface HeaderProps {
  onOpenSearch: () => void;
  cluster: string;
  onClusterChange: (cluster: string) => void;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenSearch,
  cluster,
  onClusterChange,
}) => {
  const [clusterMenuOpen, setClusterMenuOpen] = useState(false);

  const clusters = [
    { id: 'prod-eu-west-1', label: 'cluster: prod-eu-west-1', status: 'ready', region: 'Frankfurt' },
    { id: 'prod-us-east-1', label: 'cluster: prod-us-east-1', status: 'ready', region: 'N. Virginia' },
    { id: 'staging-asia-south-1', label: 'cluster: staging-asia-south-1', status: 'ready', region: 'Mumbai' },
  ];

  return (
    <header
      id="app-header"
      className="fixed top-0 left-[260px] right-0 h-14 bg-[#0e0e10] border-b border-[#554336]/20 z-40 flex items-center justify-between px-6"
    >
      {/* Cluster Status with drop-down */}
      <div className="relative flex items-center gap-3">
        <button
          id="cluster-selector-button"
          onClick={() => setClusterMenuOpen(!clusterMenuOpen)}
          className="flex items-center gap-2 hover:bg-[#1c1b1d] px-2 py-1 rounded-[0.125rem] transition-colors text-left cursor-pointer"
        >
          <span className="font-label-code text-[13px] text-[#dbc2b0]/70">
            cluster: {cluster}
          </span>
          <span className="text-[#554336]/60">/</span>
          <span className="font-label-code text-[11px] text-[#ffb77d] flex items-center gap-1.5 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-[#ffb77d] inline-block animate-pulse"></span>
            ready
          </span>
        </button>

        {clusterMenuOpen && (
          <div
            id="cluster-dropdown-menu"
            className="absolute top-11 left-0 w-64 bg-[#18181b] border border-[#353437] rounded-[0.25rem] shadow-xl py-1 z-50 text-xs"
          >
            <div className="px-3 py-1.5 font-label-caps text-[10px] text-[#dbc2b0]/50 tracking-wider uppercase border-b border-[#353437]">
              Switch Ingress Cluster
            </div>
            {clusters.map((c) => (
              <button
                key={c.id}
                onClick={() => {
                  onClusterChange(c.id);
                  setClusterMenuOpen(false);
                }}
                className={`w-full flex items-center justify-between px-3 py-2 text-left hover:bg-[#201f22] transition-colors ${
                  cluster === c.id ? 'text-[#ffb77d] font-medium' : 'text-[#e5e1e4]'
                }`}
              >
                <div className="flex flex-col">
                  <span className="font-label-code text-[12px]">{c.id}</span>
                  <span className="text-[10px] text-[#dbc2b0]/60">{c.region}</span>
                </div>
                {cluster === c.id && <Check className="w-3.5 h-3.5 text-[#ffb77d]" />}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Search and Profile */}
      <div className="flex items-center gap-3">
        <button
          id="header-search-btn"
          onClick={onOpenSearch}
          className="flex items-center gap-2 text-[#dbc2b0]/70 font-label-code text-[12px] border border-[#554336]/30 px-3 py-1 rounded-[0.125rem] hover:border-[#ffb77d]/50 hover:text-[#e5e1e4] transition-all cursor-pointer"
        >
          <Search className="w-3.5 h-3.5" />
          <span>Search</span>
          <span className="text-[10px] text-[#dbc2b0]/50 ml-1 font-semibold">⌘K</span>
        </button>

        <div
          id="user-avatar"
          className="w-8 h-8 rounded-full bg-[#ffb77d] flex items-center justify-center shrink-0 shadow-sm cursor-pointer hover:ring-2 hover:ring-[#ffb77d]/40 transition-all"
          title="Logged in as mohitsrinivas20007@gmail.com"
        >
          <User className="w-4 h-4 text-[#4d2600]" />
        </div>
      </div>
    </header>
  );
};

