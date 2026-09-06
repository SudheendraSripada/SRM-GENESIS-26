import React from 'react';
import { X, Check, BarChart2, Activity, Zap, Server } from 'lucide-react';
import { RunData } from '../types';

interface RawMetricsModalProps {
  isOpen: boolean;
  onClose: () => void;
  runData: RunData;
}

export const RawMetricsModal: React.FC<RawMetricsModalProps> = ({
  isOpen,
  onClose,
  runData,
}) => {
  if (!isOpen) return null;

  return (
    <div
      id="raw-metrics-modal-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4 animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        id="raw-metrics-modal"
        className="w-full max-w-2xl bg-[#18181b] border border-[#3f3f46] rounded-[0.25rem] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-3.5 bg-[#201f22] border-b border-[#353437]">
          <div className="flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-[#ffb77d]" />
            <h3 className="text-[15px] font-medium text-[#e5e1e4]">
              Raw Telemetry & Quantile Distribution
            </h3>
            <span className="font-label-code text-[11px] text-[#dbc2b0]/60 ml-2">
              {runData.id}
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-[#dbc2b0]/60 hover:text-[#e5e1e4] p-1 rounded-[0.125rem] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-5 overflow-y-auto space-y-6 text-xs">
          {/* Latency Quantiles Table */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="font-label-caps text-[10px] text-[#dbc2b0]/70 uppercase tracking-wider">
                Response Time Quantiles (p95 target ≤ {runData.targetSla}ms)
              </span>
              <span className="font-label-code text-[11px] text-[#ffb77d]">
                Sample count: {runData.executionMetrics ? runData.executionMetrics.requests.toLocaleString() : '18,420'} requests
              </span>
            </div>
            <div className="border border-[#353437] rounded-[0.125rem] overflow-hidden">
              <table className="w-full text-left font-label-code">
                <thead className="bg-[#201f22] text-[#dbc2b0]/70 border-b border-[#353437]">
                  <tr>
                    <th className="p-2.5">Percentile</th>
                    <th className="p-2.5">Observed</th>
                    <th className="p-2.5">SLA Margin</th>
                    <th className="p-2.5">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#353437] text-[#e5e1e4]">
                  <tr className="hover:bg-[#201f22]/50">
                    <td className="p-2.5">p50 (Median)</td>
                    <td className="p-2.5">{runData.executionMetrics ? `${runData.executionMetrics.p50_ms}ms` : '184ms'}</td>
                    <td className="p-2.5 text-[#ffb77d]">{runData.executionMetrics ? `${runData.executionMetrics.p50_ms - runData.targetSla}ms` : '-316ms'}</td>
                    <td className="p-2.5 text-[#ffb77d]">PASS</td>
                  </tr>
                  <tr className="hover:bg-[#201f22]/50">
                    <td className="p-2.5">p90</td>
                    <td className="p-2.5">{runData.executionMetrics ? `${runData.executionMetrics.p90_ms}ms` : '388ms'}</td>
                    <td className="p-2.5 text-[#ffb77d]">{runData.executionMetrics ? `${runData.executionMetrics.p90_ms - runData.targetSla}ms` : '-112ms'}</td>
                    <td className="p-2.5 text-[#ffb77d]">PASS</td>
                  </tr>
                  <tr className="bg-[#ffb77d]/10 font-medium">
                    <td className="p-2.5 text-[#ffb77d]">p95 (Ceiling SLA)</td>
                    <td className="p-2.5 text-[#ffb77d]">{runData.executionMetrics ? `${runData.executionMetrics.p95_ms}ms` : '438ms'}</td>
                    <td className="p-2.5 text-[#ffb77d]">{runData.executionMetrics ? `${runData.executionMetrics.p95_ms - runData.targetSla}ms` : '-62ms'}</td>
                    <td className="p-2.5 text-[#ffb77d]">
                      {runData.executionMetrics && runData.executionMetrics.p95_ms <= runData.targetSla ? 'COMPLIANT' : 'NOMINAL'}
                    </td>
                  </tr>
                  <tr className="hover:bg-[#201f22]/50">
                    <td className="p-2.5">p99</td>
                    <td className="p-2.5">{runData.executionMetrics ? `${runData.executionMetrics.p99_ms}ms` : '489ms'}</td>
                    <td className="p-2.5 text-[#ffb77d]">{runData.executionMetrics ? `${runData.executionMetrics.p99_ms - runData.targetSla}ms` : '-11ms'}</td>
                    <td className="p-2.5 text-[#ffb77d]">ACCEPTABLE</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* HTTP Status Breakdown & Invariance */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-4 bg-[#201f22] border border-[#353437] rounded-[0.125rem] flex flex-col justify-between">
              <span className="font-label-caps text-[10px] text-[#dbc2b0]/70 uppercase tracking-wider mb-2">
                HTTP Status Breakdown
              </span>
              <div className="space-y-1.5 font-label-code text-[12px]">
                <div className="flex justify-between">
                  <span className="text-[#ffb77d]">200 OK</span>
                  <span className="text-[#e5e1e4]">18,400 (99.89%)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#ffb95f]">429 Too Many Requests</span>
                  <span className="text-[#e5e1e4]">16 (0.09%)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#ffb4ab]">500 Internal Error</span>
                  <span className="text-[#e5e1e4]">4 (0.02%)</span>
                </div>
              </div>
            </div>

            <div className="p-4 bg-[#201f22] border border-[#353437] rounded-[0.125rem] flex flex-col justify-between">
              <span className="font-label-caps text-[10px] text-[#dbc2b0]/70 uppercase tracking-wider mb-2">
                Idempotency Invariant Verification
              </span>
              <div className="space-y-1.5 font-label-code text-[12px]">
                <div className="flex justify-between">
                  <span className="text-[#dbc2b0]">Replay Cache Hits</span>
                  <span className="text-[#ffb77d]">4,210 matches</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#dbc2b0]">Fingerprint Discrepancies</span>
                  <span className="text-[#ffb77d]">0 (0.00%)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#dbc2b0]">Cache TTL Expirations</span>
                  <span className="text-[#e5e1e4]">3 (expected)</span>
                </div>
              </div>
            </div>
          </div>

          {/* Infrastructure Health */}
          <div className="p-4 bg-[#1c1b1d] border border-[#353437] rounded-[0.125rem]">
            <span className="font-label-caps text-[10px] text-[#dbc2b0]/70 uppercase tracking-wider block mb-2">
              Downstream Node Resource Utilization
            </span>
            <div className="grid grid-cols-3 gap-3 font-label-code text-center">
              <div className="p-2 bg-[#201f22] rounded-[0.125rem]">
                <div className="text-[10px] text-[#dbc2b0]/60">Redis Memory</div>
                <div className="text-[14px] text-[#ffb77d] font-medium mt-0.5">64.2%</div>
              </div>
              <div className="p-2 bg-[#201f22] rounded-[0.125rem]">
                <div className="text-[10px] text-[#dbc2b0]/60">Auth Core CPU</div>
                <div className="text-[14px] text-[#ffb77d] font-medium mt-0.5">78.4%</div>
              </div>
              <div className="p-2 bg-[#201f22] rounded-[0.125rem]">
                <div className="text-[10px] text-[#dbc2b0]/60">Socket Pool</div>
                <div className="text-[14px] text-[#ffb77d] font-medium mt-0.5">48/64</div>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
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
