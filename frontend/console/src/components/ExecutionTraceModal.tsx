import React from 'react';
import { X, GitFork, Clock, Database, Key, ShieldCheck } from 'lucide-react';
import { MOCK_EXECUTION_TRACE } from '../data/mockData';

interface ExecutionTraceModalProps {
  isOpen: boolean;
  onClose: () => void;
  runId: string;
}

export const ExecutionTraceModal: React.FC<ExecutionTraceModalProps> = ({
  isOpen,
  onClose,
  runId,
}) => {
  if (!isOpen) return null;

  const totalDurationMs = 418;

  return (
    <div
      id="trace-modal-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4 animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        id="trace-modal"
        className="w-full max-w-3xl bg-[#18181b] border border-[#3f3f46] rounded-[0.25rem] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 bg-[#201f22] border-b border-[#353437]">
          <div className="flex items-center gap-2">
            <GitFork className="w-4 h-4 text-[#ffb77d]" />
            <h3 className="text-[15px] font-medium text-[#e5e1e4]">
              Distributed Trace Span Waterfall
            </h3>
            <span className="font-label-code text-[11px] text-[#dbc2b0]/60 ml-2">
              Trace ID: 7f3b89a12c40
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-[#dbc2b0]/60 hover:text-[#e5e1e4] p-1 rounded-[0.125rem] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Trace Waterfall */}
        <div className="p-5 overflow-y-auto space-y-4">
          <div className="flex items-center justify-between font-label-code text-[11px] text-[#dbc2b0]/70 pb-2 border-b border-[#353437]">
            <span>Operation & Span Hierarchy</span>
            <span>Offset & Duration ({totalDurationMs}ms total)</span>
          </div>

          <div className="space-y-2">
            {MOCK_EXECUTION_TRACE.map((span) => {
              const leftPercent = (span.offsetMs / totalDurationMs) * 100;
              const widthPercent = Math.max(
                (span.durationMs / totalDurationMs) * 100,
                3
              );

              return (
                <div
                  key={span.id}
                  className="p-3 bg-[#201f22] border border-[#353437] rounded-[0.125rem] flex flex-col gap-2 hover:border-[#ffb77d]/40 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-label-code text-[11px] px-1.5 py-0.5 rounded-[0.125rem] bg-[#2a2a2c] text-[#ffb77d] font-medium">
                        {span.service}
                      </span>
                      <span className="text-[13px] text-[#e5e1e4] font-medium">
                        {span.operation}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 font-label-code text-[11px]">
                      <span className="text-[#ffb77d] font-medium">{span.duration}</span>
                      <span className="text-[#dbc2b0]/60">({span.status})</span>
                    </div>
                  </div>

                  {/* Waterfall visual bar */}
                  <div className="w-full h-2 bg-[#18181b] rounded-[0.125rem] relative overflow-hidden">
                    <div
                      className="absolute h-full bg-[#ffb77d] rounded-[0.125rem]"
                      style={{
                        left: `${leftPercent}%`,
                        width: `${widthPercent}%`,
                      }}
                    ></div>
                  </div>

                  {/* Tags */}
                  <div className="flex flex-wrap gap-2 text-[10px] font-label-code text-[#dbc2b0]/60 pt-0.5">
                    {Object.entries(span.tags).map(([k, v]) => (
                      <span
                        key={k}
                        className="bg-[#1c1b1d] px-1.5 py-0.5 rounded-[0.125rem] border border-[#353437]"
                      >
                        {k}: <span className="text-[#e5e1e4]">{String(v)}</span>
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 bg-[#201f22] border-t border-[#353437] flex items-center justify-between">
          <span className="font-label-code text-[11px] text-[#dbc2b0]/60">
            Sampling: 100% deterministic on SLA violations and cache replays
          </span>
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
