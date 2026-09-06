import React, { useState } from 'react';
import { RunData } from '../types';
import {
  Timer,
  BookOpen,
  CheckCircle2,
  Table,
  Code2,
  GitFork,
  RotateCw,
  Share2,
  Check,
  Download,
} from 'lucide-react';

interface RunReportProps {
  runData: RunData;
  onOpenRawMetrics: () => void;
  onOpenK6Script: () => void;
  onOpenTrace: () => void;
  onReRun: () => void;
  onExport: () => void;
}

export const RunReport: React.FC<RunReportProps> = ({
  runData,
  onOpenRawMetrics,
  onOpenK6Script,
  onOpenTrace,
  onReRun,
  onExport,
}) => {
  const [activeVuInspection, setActiveVuInspection] = useState<number>(350);
  const [copiedNotification, setCopiedNotification] = useState(false);

  const handleShare = () => {
    onExport();
    setCopiedNotification(true);
    setTimeout(() => setCopiedNotification(false), 2500);
  };

  return (
    <div id="run-report-document" className="flex flex-col w-full pb-20">
      {/* Report Header Section */}
      <header className="flex flex-col gap-2 pb-6 border-b border-[#554336]/30">
        <div className="flex flex-wrap items-center gap-2 font-label-caps text-[11px] text-[#dbc2b0]">
          <span className="tracking-widest uppercase">Report Document</span>
          <span className="text-[#554336]/40">/</span>
          <span className="font-label-code text-[12px] text-[#e5e1e4] px-1.5 py-0.5 bg-[#2a2a2c] rounded-[0.125rem]">
            {runData.id}
          </span>
          <span className="text-[#554336]/40">/</span>
          <span className="flex items-center gap-1 text-[#dbc2b0]">
            <Timer className="w-3.5 h-3.5 text-[#dbc2b0]" />
            <span>{runData.duration}</span>
          </span>
          <span className="text-[#554336]/40">/</span>
          <span className="px-1.5 py-0.5 bg-[#ee9800]/20 text-[#ffb95f] font-semibold uppercase tracking-wider rounded-[0.125rem]">
            Completed
          </span>
        </div>

        <div className="mt-1 flex flex-col gap-0.5">
          <div className="flex flex-wrap items-baseline gap-3">
            <h1 className="text-[24px] leading-8 font-medium text-[#ffb77d] tracking-tight uppercase">
              Pass — Boundary Found
            </h1>
            <span className="font-label-code text-[11px] text-[#dbc2b0]/70 border border-[#554336]/30 px-1.5 py-0.5 rounded-[0.125rem]">
              REV. 04
            </span>
          </div>
          <p className="text-[16px] text-[#e5e1e4]/90 max-w-[42rem]">
            Sustainable capacity:{' '}
            <span className="text-[#e5e1e4] font-medium">
              {runData.sustainableCapacity} VUs
            </span>{' '}
            at p95 ≤ {runData.targetSla}ms
          </p>
        </div>
      </header>

      {/* Side-by-Side Verification Panel & Capacity Boundary */}
      <section className="mt-6 bg-[#201f22] border border-[#554336]/30 rounded-[0.25rem] overflow-hidden shadow-sm">
        {/* Comparison Block */}
        <div className="grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-[#554336]/30 border-b border-[#554336]/30">
          {/* Threshold Target */}
          <div className="p-5 flex flex-col justify-between bg-[#1c1b1d]/40">
            <div className="flex items-center justify-between text-[#dbc2b0]">
              <span className="font-label-caps text-[11px] tracking-widest uppercase text-[#dbc2b0]/80">
                Threshold SLA
              </span>
              <span className="font-label-code text-[11px] text-[#dbc2b0]/60 font-medium">
                CEILING
              </span>
            </div>
            <div className="mt-3 flex items-baseline gap-1">
              <span className="text-[32px] leading-tight font-medium text-[#e5e1e4] tracking-tight tabular-nums">
                {runData.targetSla}
              </span>
              <span className="font-label-code text-[13px] text-[#dbc2b0]">ms</span>
            </div>
            <div className="mt-1 font-label-code text-[11px] text-[#dbc2b0]/70">
              Target maximum acceptable p95 latency
            </div>
          </div>

          {/* Observed Metric */}
          <div className="p-5 flex flex-col justify-between bg-[#201f22]/60">
            <div className="flex items-center justify-between text-[#dbc2b0]">
              <span className="font-label-caps text-[11px] tracking-widest uppercase text-[#ffb77d] font-medium">
                Observed Latency
              </span>
              <span className="font-label-code text-[11px] text-[#ffb77d] flex items-center gap-1 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-[#ffb77d] inline-block"></span>
                NOMINAL
              </span>
            </div>
            <div className="mt-3 flex items-baseline gap-1">
              <span className="text-[32px] leading-tight font-medium text-[#ffb77d] tracking-tight tabular-nums">
                {runData.observedLatency}
              </span>
              <span className="font-label-code text-[13px] text-[#ffb77d]/80">ms</span>
              <span className="ml-3 font-label-code text-[11px] text-[#dbc2b0] bg-[#2a2a2c] px-1.5 py-0.5 rounded-[0.125rem] font-medium">
                {runData.latencyMargin}ms margin
              </span>
            </div>
            <div className="mt-1 font-label-code text-[11px] text-[#dbc2b0]/80">
              Measured p95 under peak steady load ({runData.sustainableCapacity} VUs)
            </div>
          </div>
        </div>

        {/* Precision Linear Boundary Map (Ruler & Slider) */}
        <div className="p-5 bg-[#0e0e10]/50 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="font-label-caps text-[11px] text-[#dbc2b0] tracking-wider uppercase">
              Parameter Search Space · Virtual Users (VUs)
            </span>
            <span className="font-label-code text-[11px] text-[#dbc2b0]/80">
              Resolution: 25 VUs / step
            </span>
          </div>

          {/* Precise horizontal gauge */}
          <div className="relative pt-6 pb-2">
            {/* Range track base */}
            <div className="h-2 w-full bg-[#353437] rounded-[0.125rem] overflow-hidden flex">
              {/* Pass zone (300 to 350 = 50% of range 300..400) */}
              <div className="w-1/2 h-full bg-[#ffb77d]/25 border-r border-[#ffb77d]"></div>
              {/* Degradation risk zone (350 to 400) */}
              <div className="w-1/2 h-full bg-[#353437] relative">
                <div className="absolute inset-0 bg-[#ffb4ab]/10"></div>
              </div>
            </div>

            {/* Converged pin marker at exactly 50% (350 VUs) */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 flex flex-col items-center select-none">
              <span className="font-label-code text-[10px] text-[#4d2600] bg-[#ffb77d] px-1.5 py-0.2 rounded-[0.125rem] tracking-tight font-medium shadow-sm">
                350 VUs · CONVERGED
              </span>
              <div className="w-[1px] h-3 bg-[#ffb77d]"></div>
            </div>

            {/* Ruler Ticks */}
            <div className="relative w-full flex justify-between mt-2 font-label-code text-[11px] text-[#dbc2b0]/70 select-none">
              <div className="flex flex-col items-start">
                <span className="h-1.5 w-[1px] bg-[#554336]/60 mb-1"></span>
                <span>300</span>
              </div>
              <div className="flex flex-col items-center -ml-2">
                <span className="h-1 w-[1px] bg-[#554336]/40 mb-1"></span>
                <span className="text-[#dbc2b0]/50">325</span>
              </div>
              <div className="flex flex-col items-center">
                <span className="h-2 w-[1px] bg-[#ffb77d] mb-1"></span>
                <span className="text-[#ffb77d] font-medium">350</span>
              </div>
              <div className="flex flex-col items-center -mr-2">
                <span className="h-1 w-[1px] bg-[#554336]/40 mb-1"></span>
                <span className="text-[#dbc2b0]/50">375</span>
              </div>
              <div className="flex flex-col items-end">
                <span className="h-1.5 w-[1px] bg-[#554336]/60 mb-1"></span>
                <span className="text-[#ffb4ab]/70">400</span>
              </div>
            </div>
          </div>

          {/* Footer explanation within card */}
          <div className="flex flex-wrap items-center justify-between pt-1 border-t border-[#554336]/20 font-label-code text-[11px] text-[#dbc2b0]/70 gap-2">
            <div className="flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-[0.125rem] bg-[#ffb77d]/40 border border-[#ffb77d]"></span>
              <span>Verified Operating Envelope (300–350 VUs)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-[0.125rem] bg-[#ffb4ab]/30 border border-[#ffb4ab]/50"></span>
              <span>SLA Invalidation Region (&gt;365 VUs)</span>
            </div>
          </div>
        </div>
      </section>

      {/* Autonomous Decisions Taken Section */}
      <section className="mt-8 flex flex-col gap-3">
        <div className="flex items-center justify-between pb-1 border-b border-[#554336]/20">
          <div className="flex items-center gap-2">
            <h2 className="text-[18px] text-[#e5e1e4] font-medium">
              Autonomous decisions taken
            </h2>
            <span className="font-label-code text-[11px] text-[#dbc2b0] bg-[#201f22] px-1.5 py-0.5 rounded-[0.125rem]">
              {runData.decisions.length} steps executed
            </span>
          </div>
          <span className="font-label-code text-[11px] text-[#dbc2b0]/60">
            Policy: binary-search-v1
          </span>
        </div>

        {/* Step Sequence */}
        <ol className="flex flex-col border border-[#554336]/30 rounded-[0.125rem] divide-y divide-[#554336]/20 bg-[#1c1b1d]/40">
          {runData.decisions.map((dec) => (
            <li
              key={dec.number}
              className={`flex items-start gap-3 p-3 transition-colors ${
                dec.highlighted
                  ? 'bg-[#ffb77d]/5 hover:bg-[#ffb77d]/10'
                  : 'hover:bg-[#201f22]/40'
              }`}
            >
              <span
                className={`font-label-code text-[11px] px-1.5 py-0.5 rounded-[0.125rem] shrink-0 font-medium ${
                  dec.highlighted
                    ? 'text-[#ffb77d] bg-[#ffb77d]/20'
                    : 'text-[#dbc2b0]/70 bg-[#2a2a2c]'
                }`}
              >
                {dec.number}
              </span>
              <div className="flex flex-col min-w-0">
                <span
                  className={`text-[14px] text-[#e5e1e4] ${
                    dec.highlighted ? 'font-medium' : 'font-normal'
                  }`}
                >
                  {dec.title}
                </span>
                <span
                  className={`font-label-code text-[11px] mt-0.5 ${
                    dec.highlighted ? 'text-[#ffb77d]/80' : 'text-[#dbc2b0]/60'
                  }`}
                >
                  {dec.detail}
                </span>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* Plain-English Written Explanation (Analyst's Note) */}
      <article className="mt-8 p-6 bg-[#1c1b1d] border border-[#554336]/30 rounded-[0.125rem] relative shadow-sm">
        <div className="flex items-center justify-between pb-2 border-b border-[#554336]/20 mb-3">
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-[#ffb77d]" />
            <h3 className="text-[18px] text-[#e5e1e4] font-medium">
              Analyst verdict & observations
            </h3>
          </div>
          <span className="font-label-caps text-[11px] text-[#dbc2b0]/60 uppercase">
            Engine Summary
          </span>
        </div>

        {/* Editorial Prose */}
        <div className="space-y-3">
          <p className="font-display-editorial text-[20px] leading-[30px] text-[#e5e1e4]/90 italic">
            "{runData.analystQuote}"
          </p>
          <p className="text-[16px] text-[#dbc2b0] leading-relaxed">
            {runData.analystProse}
          </p>
        </div>

        {/* Sign-off Metadata */}
        <div className="mt-5 pt-3 border-t border-[#554336]/20 flex flex-wrap items-center justify-between font-label-code text-[11px] text-[#dbc2b0]/70 gap-y-2">
          <div className="flex items-center gap-3">
            <span>
              Evaluator: <strong className="text-[#e5e1e4] font-normal">{runData.evaluator}</strong>
            </span>
            <span>·</span>
            <span>
              Target:{' '}
              <strong className="text-[#e5e1e4] font-normal">{runData.evaluatorTarget}</strong>
            </span>
          </div>
          <div className="flex items-center gap-1 text-[#ffb77d]">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Cryptographically Attested Run</span>
          </div>
        </div>
      </article>

      {/* Action Row */}
      <footer className="mt-8 pt-4 border-t border-[#554336]/30 flex flex-wrap items-center justify-between gap-3 mb-6">
        <div className="flex flex-wrap items-center gap-2">
          <button
            id="btn-view-raw-metrics"
            onClick={onOpenRawMetrics}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-[#554336]/40 hover:border-[#554336] hover:bg-[#201f22] text-[#dbc2b0] hover:text-[#e5e1e4] rounded-[0.125rem] transition-colors font-label-code text-[12px] cursor-pointer"
          >
            <Table className="w-3.5 h-3.5" />
            <span>View raw metrics</span>
          </button>

          <button
            id="btn-view-k6-script"
            onClick={onOpenK6Script}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-[#554336]/40 hover:border-[#554336] hover:bg-[#201f22] text-[#dbc2b0] hover:text-[#e5e1e4] rounded-[0.125rem] transition-colors font-label-code text-[12px] cursor-pointer"
          >
            <Code2 className="w-3.5 h-3.5" />
            <span>View k6 script</span>
          </button>

          <button
            id="btn-view-trace"
            onClick={onOpenTrace}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-[#554336]/40 hover:border-[#554336] hover:bg-[#201f22] text-[#dbc2b0] hover:text-[#e5e1e4] rounded-[0.125rem] transition-colors font-label-code text-[12px] cursor-pointer"
          >
            <GitFork className="w-3.5 h-3.5" />
            <span>View execution trace</span>
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            id="btn-rerun"
            onClick={onReRun}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-[#554336]/40 hover:border-[#ffb77d] hover:text-[#ffb77d] hover:bg-[#ffb77d]/5 text-[#dbc2b0] rounded-[0.125rem] transition-colors font-label-code text-[12px] cursor-pointer"
          >
            <RotateCw className="w-3.5 h-3.5" />
            <span>Re-run</span>
          </button>

          <button
            id="btn-export"
            onClick={handleShare}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-[#554336]/40 hover:border-[#554336] hover:bg-[#201f22] text-[#e5e1e4] rounded-[0.125rem] transition-colors font-label-code text-[12px] cursor-pointer"
          >
            {copiedNotification ? (
              <>
                <Check className="w-3.5 h-3.5 text-[#ffb77d]" />
                <span className="text-[#ffb77d]">Exported</span>
              </>
            ) : (
              <>
                <Share2 className="w-3.5 h-3.5" />
                <span>Export</span>
              </>
            )}
          </button>
        </div>
      </footer>
    </div>
  );
};
