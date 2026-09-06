import React from 'react';
import { History, ChevronRight, CheckCircle2, ArrowRight } from 'lucide-react';
import { MOCK_HISTORY_RUNS } from '../data/mockData';
import { RunData } from '../types';

interface HistoryViewProps {
  onSelectRun: (run: RunData) => void;
}

export const HistoryView: React.FC<HistoryViewProps> = ({ onSelectRun }) => {
  return (
    <div id="history-view" className="flex flex-col w-full pb-16">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 mb-6 border-b border-[#554336]/30">
        <div>
          <h1 className="text-[22px] font-medium text-[#e5e1e4]">Autonomous Run History</h1>
          <p className="text-[13px] text-[#dbc2b0]/70 mt-0.5">
            Audit log of autonomous load boundary searches, SLA validations, and reports
          </p>
        </div>
        <span className="font-label-code text-[11px] text-[#dbc2b0]/60">
          Showing {MOCK_HISTORY_RUNS.length} verified runs
        </span>
      </div>

      {/* History Runs List */}
      <div className="border border-[#554336]/30 rounded-[0.25rem] divide-y divide-[#554336]/20 bg-[#1c1b1d] overflow-hidden">
        {MOCK_HISTORY_RUNS.map((run) => (
          <div
            key={run.id}
            onClick={() => onSelectRun(run)}
            className="p-4 hover:bg-[#201f22] transition-colors cursor-pointer group flex flex-col sm:flex-row sm:items-center justify-between gap-3"
          >
            <div className="flex items-start gap-3 min-w-0">
              <div className="w-6 h-6 rounded-full bg-[#ffb77d]/10 flex items-center justify-center text-[#ffb77d] shrink-0 mt-0.5">
                <CheckCircle2 className="w-4 h-4" />
              </div>
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[15px] font-medium text-[#e5e1e4] group-hover:text-[#ffb77d] transition-colors truncate">
                    {run.name}
                  </span>
                  <span className="font-label-code text-[11px] text-[#dbc2b0]/50 bg-[#2a2a2c] px-1.5 py-0.2 rounded-[0.125rem]">
                    {run.id}
                  </span>
                </div>
                <p className="text-[13px] text-[#dbc2b0]/80 truncate mt-0.5 max-w-xl">
                  {run.query}
                </p>
              </div>
            </div>

            <div className="flex items-center justify-between sm:justify-end gap-5 shrink-0">
              <div className="flex flex-col items-start sm:items-end font-label-code text-[11px]">
                <span className="text-[#ffb77d] font-medium">
                  {run.sustainableCapacity} VUs @ {run.observedLatency}ms p95
                </span>
                <span className="text-[#dbc2b0]/50 mt-0.5">
                  {run.startTime} · {run.duration}
                </span>
              </div>
              <ChevronRight className="w-4 h-4 text-[#dbc2b0]/40 group-hover:text-[#ffb77d] transition-colors" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
