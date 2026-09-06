import React from 'react';
import { X, Server, Cpu, HardDrive, ShieldCheck, Activity, Users } from 'lucide-react';

interface WorkspaceModalProps {
  isOpen: boolean;
  onClose: () => void;
  cluster: string;
}

export const WorkspaceModal: React.FC<WorkspaceModalProps> = ({
  isOpen,
  onClose,
  cluster,
}) => {
  if (!isOpen) return null;

  return (
    <div
      id="workspace-modal-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4 animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        id="workspace-modal"
        className="w-full max-w-xl bg-[#18181b] border border-[#3f3f46] rounded-[0.25rem] shadow-2xl overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 bg-[#201f22] border-b border-[#353437]">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-[#ffb77d]" />
            <h3 className="text-[15px] font-medium text-[#e5e1e4]">
              Workspace & Cluster Status
            </h3>
            <span className="font-label-code text-[11px] text-[#dbc2b0]/60 ml-2">
              mono-workspace / primary-node
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-[#dbc2b0]/60 hover:text-[#e5e1e4] p-1 rounded-[0.125rem] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4">
          <div className="p-4 bg-[#201f22] border border-[#353437] rounded-[0.125rem]">
            <div className="flex items-center justify-between mb-3">
              <span className="font-label-caps text-[10px] text-[#dbc2b0]/70 uppercase tracking-wider">
                Primary Cluster Ingress
              </span>
              <span className="font-label-code text-[11px] text-[#ffb77d] flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#ffb77d] animate-pulse"></span>
                HEALTHY
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 font-label-code text-xs">
              <div>
                <span className="text-[#dbc2b0]/50 block text-[10px]">Active Cluster</span>
                <span className="text-[#e5e1e4] font-medium">{cluster}</span>
              </div>
              <div>
                <span className="text-[#dbc2b0]/50 block text-[10px]">Active Synthetic Runners</span>
                <span className="text-[#ffb77d] font-medium">8 / 16 Pods</span>
              </div>
              <div>
                <span className="text-[#dbc2b0]/50 block text-[10px]">K8s Namespace</span>
                <span className="text-[#e5e1e4]">agent-synthetics-v2</span>
              </div>
            </div>
          </div>

          <div className="p-4 bg-[#201f22] border border-[#353437] rounded-[0.125rem]">
            <span className="font-label-caps text-[10px] text-[#dbc2b0]/70 uppercase tracking-wider block mb-3">
              Node Infrastructure Telemetry
            </span>
            <div className="space-y-2.5 font-label-code text-xs">
              <div className="flex justify-between items-center">
                <span className="flex items-center gap-2 text-[#dbc2b0]">
                  <Cpu className="w-3.5 h-3.5 text-[#ffb77d]" />
                  <span>CPU Allocation</span>
                </span>
                <span className="text-[#e5e1e4]">34.2% (12 Cores)</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="flex items-center gap-2 text-[#dbc2b0]">
                  <HardDrive className="w-3.5 h-3.5 text-[#ffb77d]" />
                  <span>Memory Allocation</span>
                </span>
                <span className="text-[#e5e1e4]">18.4 GB / 64 GB</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="flex items-center gap-2 text-[#dbc2b0]">
                  <ShieldCheck className="w-3.5 h-3.5 text-[#ffb77d]" />
                  <span>Security Sandbox</span>
                </span>
                <span className="text-[#ffb77d]">eBPF Enforced</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 bg-[#201f22] border-t border-[#353437] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-[#2a2a2c] hover:bg-[#353437] text-[#e5e1e4] rounded-[0.125rem] text-[12px] font-label-code transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
