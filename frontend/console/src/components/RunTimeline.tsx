import React, { useState, useEffect, useRef } from 'react';
import { ScreenId, StepItem, AssertionLog } from '../types';
import {
  Check,
  ChevronRight,
  ChevronDown,
  Plus,
  Square,
  Play,
  Terminal,
  ArrowUp,
  User,
  Timer,
  Sparkles,
} from 'lucide-react';
import { INITIAL_ASSERTION_LOGS } from '../data/mockData';

interface RunTimelineProps {
  currentScreen: ScreenId;
  runQuery: string;
  targetEndpoint: string;
  env: string;
  runId: string;
  onNavigateToReport: () => void;
  onStopRun: () => void;
  isRunning: boolean;
  onSendMessage: (msg: string) => void;
}

export const RunTimeline: React.FC<RunTimelineProps> = ({
  currentScreen,
  runQuery,
  targetEndpoint,
  env,
  runId,
  onNavigateToReport,
  onStopRun,
  isRunning,
  onSendMessage,
}) => {
  const [interveneInput, setInterveneInput] = useState('');
  const [activeStepExpanded, setActiveStepExpanded] = useState<string>(
    currentScreen === 'analysing'
      ? 'analysing'
      : currentScreen === 'validating'
      ? 'validating'
      : 'testing'
  );

  // Live timer for Testing stage
  const [elapsedSeconds, setElapsedSeconds] = useState(48.2);
  const [latencyValue, setLatencyValue] = useState(438);
  const [rpsValue, setRpsValue] = useState(411);
  const [assertionLogs, setAssertionLogs] = useState<AssertionLog[]>(INITIAL_ASSERTION_LOGS);
  const [streamInterventions, setStreamInterventions] = useState<string[]>([]);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Update expanded step when screen switches
  useEffect(() => {
    if (currentScreen === 'analysing') setActiveStepExpanded('analysing');
    else if (currentScreen === 'validating') setActiveStepExpanded('validating');
    else if (currentScreen === 'testing') setActiveStepExpanded('testing');
  }, [currentScreen]);

  // Live Telemetry simulation while in 'testing' screen
  useEffect(() => {
    if (currentScreen !== 'testing' || !isRunning) return;

    const timerInterval = setInterval(() => {
      setElapsedSeconds((prev) => +(prev + 0.1).toFixed(1));
    }, 100);

    const telemetryInterval = setInterval(() => {
      // Subtle organic jitter within SLA limits
      setLatencyValue((prev) => {
        const delta = Math.floor(Math.random() * 5) - 2;
        const next = prev + delta;
        return next < 420 ? 425 : next > 450 ? 442 : next;
      });
      setRpsValue((prev) => {
        const delta = Math.floor(Math.random() * 7) - 3;
        return prev + delta;
      });
    }, 1200);

    // Dynamic assertion log streamer
    const logInterval = setInterval(() => {
      const now = new Date();
      const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now
        .getMinutes()
        .toString()
        .padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}.${now
        .getMilliseconds()
        .toString()
        .padStart(3, '0')}`;
      const slots = [14, 22, 38, 45, 12, 50];
      const slot = slots[Math.floor(Math.random() * slots.length)];
      const idemp = Math.random().toString(36).substring(2, 8);
      const isReplay = Math.random() > 0.5;

      const newLogText = isReplay
        ? `POST /v2/auth/token concurrency_slot=${slot} idempotency_key=${idemp} (replay) -> 200 OK [CACHED] (24ms)`
        : `POST /v2/auth/token concurrency_slot=${slot} idempotency_key=${idemp} -> 200 OK (${
            340 + Math.floor(Math.random() * 80)
          }ms)`;

      setAssertionLogs((prev) => {
        const nextLogs = [...prev];
        // Remove trailing active cursor from last
        if (nextLogs.length > 0) {
          nextLogs[nextLogs.length - 1] = {
            ...nextLogs[nextLogs.length - 1],
            isActive: false,
          };
        }
        nextLogs.push({
          id: 'log-' + Date.now(),
          timestamp: timeStr,
          text: newLogText,
        });

        // Periodically inject assertion verification pass
        if (Math.random() > 0.6) {
          nextLogs.push({
            id: 'assert-' + Date.now(),
            timestamp: timeStr,
            text: 'ASSERT PASS: Idempotency invariant holds under state variance',
            isAssertPass: true,
          });
        }

        // Add next active cursor line
        nextLogs.push({
          id: 'cursor-' + Date.now(),
          timestamp: timeStr,
          text: `POST /v2/auth/introspect fuzzy_payload=0x7f..${Math.random()
            .toString(16)
            .substring(2, 6)}`,
          isActive: true,
        });

        // Keep last 15 logs for performance
        return nextLogs.slice(-16);
      });

      if (terminalEndRef.current) {
        terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
      }
    }, 2400);

    return () => {
      clearInterval(timerInterval);
      clearInterval(telemetryInterval);
      clearInterval(logInterval);
    };
  }, [currentScreen, isRunning]);

  const handleSendIntervention = (e: React.FormEvent) => {
    e.preventDefault();
    if (!interveneInput.trim()) return;
    const msg = interveneInput.trim();
    setStreamInterventions((prev) => [...prev, msg]);
    onSendMessage(msg);
    setInterveneInput('');
  };

  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(1);
    return `${mins.toString().padStart(2, '0')}:${secs.padStart(4, '0')}s`;
  };

  // Sparkline points for SVG based on latency
  const sparklinePoints = 'M0,18 L15,17 L30,12 L45,19 L60,8 L75,14 L90,6 L100,9';

  return (
    <div className="flex flex-col w-full pb-20">
      {/* Run Header Context Pill - Screen 4 / General live run view */}
      {currentScreen === 'testing' && (
        <div
          id="run-context-header"
          className="flex items-center justify-between pb-4 mb-5 border-b border-[#554336]/20"
        >
          <div className="flex items-center gap-2">
            <span className="font-label-caps text-[11px] text-[#dbc2b0]/80 tracking-widest uppercase">
              Run Context
            </span>
            <span className="text-[#554336]/40">/</span>
            <span className="font-label-code text-[13px] text-[#ffb77d]">{runId}</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#ffb77d] animate-pulse"></span>
            <span className="font-label-caps text-[11px] text-[#ffb77d] uppercase tracking-wider font-medium">
              Live Execution
            </span>
          </div>
        </div>
      )}

      {/* User Prompt Bubble */}
      <section
        id="user-prompt-card"
        className="flex flex-col bg-[#1c1b1d] rounded-[0.25rem] p-4 mb-6 border border-[#554336]/30 shadow-sm"
      >
        <div className="flex items-center justify-between pb-1.5 mb-2 border-b border-[#554336]/15">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-full bg-[#d97707]/20 flex items-center justify-center text-[#ffb77d]">
              <User className="w-3.5 h-3.5" />
            </div>
            <span className="text-[14px] font-medium text-[#e5e1e4]">You</span>
            <span className="text-[#554336]/40 text-xs">•</span>
            <span className="font-label-code text-[12px] text-[#dbc2b0]/70">just now</span>
          </div>

          <span className="font-label-code text-[11px] text-[#dbc2b0]/50">
            {targetEndpoint} · {env.toLowerCase()}
          </span>
        </div>

        <p className="text-[16px] text-[#e5e1e4] leading-relaxed font-normal">{runQuery}</p>

        {/* Display user injected interventions if any */}
        {streamInterventions.length > 0 && (
          <div className="mt-3 pt-2 border-t border-[#554336]/20 flex flex-col gap-1.5">
            <span className="text-[10px] font-label-caps text-[#ffb77d] uppercase tracking-wider">
              Runtime Interventions Injected:
            </span>
            {streamInterventions.map((msg, i) => (
              <div
                key={i}
                className="text-[13px] text-[#ffb77d]/90 bg-[#201f22] px-2.5 py-1 rounded-[0.125rem] border border-[#d97707]/30"
              >
                ↳ {msg}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Execution Timeline Steps Container */}
      <section className="flex flex-col space-y-1 mb-8" id="execution-timeline">
        {/* ================= STEP 1: ANALYSING ================= */}
        {currentScreen === 'analysing' ? (
          /* Active Analysing (Screen 2 style) */
          <div
            id="step-analysing-active"
            className="py-3 px-3.5 bg-[#1c1b1d] rounded-[0.25rem] border border-[#554336]/30 flex items-center justify-between cursor-pointer group hover:bg-[#201f22] transition-colors"
            onClick={() =>
              setActiveStepExpanded(activeStepExpanded === 'analysing' ? '' : 'analysing')
            }
          >
            <div className="flex items-center gap-3">
              <div className="relative flex items-center justify-center w-5 h-5">
                <span className="w-2 h-2 rounded-full bg-[#ffb77d] animate-ping absolute"></span>
                <span className="w-2 h-2 rounded-full bg-[#ffb77d] relative"></span>
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <span className="text-[#e5e1e4] font-medium text-[15px]">Analysing</span>
                  <span className="font-label-caps text-[11px] text-[#ffb77d] px-1.5 py-0.5 rounded-[0.125rem] bg-[#201f22] border border-[#554336]/30 font-medium">
                    ACTIVE
                  </span>
                </div>
                <span className="text-[13px] text-[#dbc2b0]/70 mt-0.5">
                  Mapping endpoint schema & auth headers...
                </span>
              </div>
            </div>
            <ChevronDown className="w-4 h-4 text-[#dbc2b0]/60 group-hover:text-[#e5e1e4]" />
          </div>
        ) : (
          /* Settled Analysing */
          <div
            id="step-analysing-settled"
            className="flex items-center justify-between px-4 py-2 bg-[#1c1b1d] rounded-[0.125rem] border border-[#554336]/15 hover:bg-[#201f22] transition-colors group cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <div className="w-5 h-5 rounded-full bg-[#2a2a2c] flex items-center justify-center text-[#ffb77d] border border-[#ffb77d]/30">
                <Check className="w-3.5 h-3.5" />
              </div>
              <span className="text-[14px] text-[#dbc2b0] group-hover:text-[#e5e1e4] transition-colors font-medium">
                Analysing
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-label-code text-[11px] text-[#dbc2b0]/50">1.2s</span>
              <ChevronRight className="w-4 h-4 text-[#dbc2b0]/40 group-hover:text-[#dbc2b0]" />
            </div>
          </div>
        )}

        {/* ================= STEP 2: BUILDING PLAN ================= */}
        {currentScreen === 'analysing' ? (
          /* Queued Building Plan (Screen 2) */
          <div className="py-3 px-3.5 bg-[#1c1b1d] rounded-[0.125rem] border border-[#554336]/20 flex items-center justify-between cursor-pointer group">
            <div className="flex items-center gap-3">
              <div className="w-5 h-5 flex items-center justify-center">
                <span className="w-1.5 h-1.5 rounded-full border border-[#dbc2b0]/40"></span>
              </div>
              <div className="flex flex-col">
                <span className="text-[#dbc2b0]/70 font-normal text-[14px]">Building Plan</span>
                <span className="font-label-code text-[11px] text-[#dbc2b0]/40 mt-0.5">Queued</span>
              </div>
            </div>
            <ChevronRight className="w-4 h-4 text-[#dbc2b0]/40 group-hover:text-[#dbc2b0]/60" />
          </div>
        ) : (
          /* Settled Building Plan (Screens 3, 4) */
          <div className="flex items-center justify-between px-4 py-2 bg-[#1c1b1d] rounded-[0.125rem] border border-[#554336]/15 hover:bg-[#201f22] transition-colors group cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="w-5 h-5 rounded-full bg-[#2a2a2c] flex items-center justify-center text-[#ffb77d] border border-[#ffb77d]/30">
                <Check className="w-3.5 h-3.5" />
              </div>
              <span className="text-[14px] text-[#dbc2b0] group-hover:text-[#e5e1e4] transition-colors font-medium">
                Building Plan
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-label-code text-[11px] text-[#dbc2b0]/50">3.4s</span>
              <ChevronRight className="w-4 h-4 text-[#dbc2b0]/40 group-hover:text-[#dbc2b0]" />
            </div>
          </div>
        )}

        {/* ================= STEP 3: VALIDATING ================= */}
        {currentScreen === 'validating' ? (
          /* Active Validating (Screen 3 with checklist) */
          <div
            id="step-validating-active"
            className="border border-[#554336]/30 bg-[#1c1b1d] rounded-[0.25rem] overflow-hidden"
          >
            <div className="py-3 px-3.5 flex items-center justify-between cursor-pointer group bg-[#201f22]/60">
              <div className="flex items-center gap-3">
                <div className="relative flex items-center justify-center w-5 h-5">
                  <span className="w-2 h-2 rounded-full bg-[#ffb77d] animate-ping absolute"></span>
                  <span className="w-2 h-2 rounded-full bg-[#ffb77d] relative"></span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[#e5e1e4] font-medium text-[15px]">Validating</span>
                  <span className="font-label-caps text-[11px] text-[#ffb77d] px-1.5 py-0.5 rounded-[0.125rem] bg-[#201f22] border border-[#554336]/30">
                    ACTIVE
                  </span>
                </div>
              </div>
              <ChevronDown className="w-4 h-4 text-[#dbc2b0]/60 group-hover:text-[#e5e1e4]" />
            </div>

            {/* Checklist items */}
            <div className="pl-8 pr-4 pb-4 pt-1 space-y-1.5 bg-[#1c1b1d]">
              <div className="flex items-center gap-3 py-1">
                <div className="w-4 h-4 flex items-center justify-center text-[#ffb77d]">
                  <Check className="w-3.5 h-3.5" />
                </div>
                <span className="text-[13px] text-[#e5e1e4]">Intent schema</span>
              </div>

              <div className="flex items-center gap-3 py-1">
                <div className="w-4 h-4 flex items-center justify-center text-[#ffb77d]">
                  <Check className="w-3.5 h-3.5" />
                </div>
                <span className="text-[13px] text-[#e5e1e4]">Target allowlist</span>
              </div>

              <div className="flex items-center gap-3 py-1">
                <div className="w-4 h-4 flex items-center justify-center">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#ffb77d] animate-ping"></span>
                </div>
                <span className="text-[13px] text-[#e5e1e4] font-medium">Load bounds</span>
                <span className="font-label-code text-[11px] text-[#ffb77d] ml-auto">
                  evaluating...
                </span>
              </div>

              <div className="flex items-center gap-3 py-1 opacity-50">
                <div className="w-4 h-4 flex items-center justify-center">
                  <span className="w-1 h-1 rounded-full bg-[#dbc2b0]/40"></span>
                </div>
                <span className="text-[13px] text-[#dbc2b0]/60">Payload validity</span>
              </div>

              <div className="flex items-center gap-3 py-1 opacity-50">
                <div className="w-4 h-4 flex items-center justify-center">
                  <span className="w-1 h-1 rounded-full bg-[#dbc2b0]/40"></span>
                </div>
                <span className="text-[13px] text-[#dbc2b0]/60">Execution policy</span>
              </div>
            </div>
          </div>
        ) : currentScreen === 'testing' ? (
          /* Settled Validating (Screen 4) */
          <div className="flex items-center justify-between px-4 py-2 bg-[#1c1b1d] rounded-[0.125rem] border border-[#554336]/15 hover:bg-[#201f22] transition-colors group cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="w-5 h-5 rounded-full bg-[#2a2a2c] flex items-center justify-center text-[#ffb77d] border border-[#ffb77d]/30">
                <Check className="w-3.5 h-3.5" />
              </div>
              <span className="text-[14px] text-[#dbc2b0] group-hover:text-[#e5e1e4] transition-colors font-medium">
                Validating
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-label-code text-[11px] text-[#dbc2b0]/50">0.8s</span>
              <ChevronRight className="w-4 h-4 text-[#dbc2b0]/40 group-hover:text-[#dbc2b0]" />
            </div>
          </div>
        ) : (
          /* Pending Validating (Screen 2) */
          <div className="py-2.5 px-4 bg-[#1c1b1d] rounded-[0.125rem] border border-[#554336]/15 flex items-center justify-between cursor-pointer opacity-50 hover:opacity-80 transition-opacity">
            <div className="flex items-center gap-3">
              <div className="w-5 h-5 flex items-center justify-center">
                <span className="w-1 h-1 rounded-full bg-[#dbc2b0]/40"></span>
              </div>
              <span className="text-[#dbc2b0]/60 font-normal text-[13px]">Validating</span>
            </div>
            <ChevronRight className="w-4 h-4 text-[#dbc2b0]/40" />
          </div>
        )}

        {/* ================= STEP 4: BUILDING TEST ================= */}
        {currentScreen === 'testing' ? (
          /* Settled Building Test (Screen 4) */
          <div className="flex items-center justify-between px-4 py-2 bg-[#1c1b1d] rounded-[0.125rem] border border-[#554336]/15 hover:bg-[#201f22] transition-colors group cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="w-5 h-5 rounded-full bg-[#2a2a2c] flex items-center justify-center text-[#ffb77d] border border-[#ffb77d]/30">
                <Check className="w-3.5 h-3.5" />
              </div>
              <span className="text-[14px] text-[#dbc2b0] group-hover:text-[#e5e1e4] transition-colors font-medium">
                Building Test
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-label-code text-[11px] text-[#dbc2b0]/50">2.1s</span>
              <ChevronRight className="w-4 h-4 text-[#dbc2b0]/40 group-hover:text-[#dbc2b0]" />
            </div>
          </div>
        ) : (
          /* Pending Building Test (Screens 2, 3) */
          <div className="py-2.5 px-4 bg-[#1c1b1d] rounded-[0.125rem] border border-[#554336]/15 flex items-center justify-between cursor-pointer opacity-50 hover:opacity-80 transition-opacity">
            <div className="flex items-center gap-3">
              <div className="w-5 h-5 flex items-center justify-center">
                <span className="w-1 h-1 rounded-full bg-[#dbc2b0]/40"></span>
              </div>
              <span className="text-[#dbc2b0]/60 font-normal text-[13px]">Building Test</span>
            </div>
            <ChevronRight className="w-4 h-4 text-[#dbc2b0]/40" />
          </div>
        )}

        {/* ================= STEP 5: TESTING ================= */}
        {currentScreen === 'testing' ? (
          /* Active Testing with Live Telemetry & Assertion Terminal (Screen 4) */
          <div
            id="step-testing-active"
            className="flex flex-col bg-[#201f22] rounded-[0.25rem] border border-[#ffb77d]/40 overflow-hidden shadow-lg"
          >
            {/* Active Row Header */}
            <div className="flex items-center justify-between px-4 py-3 bg-[#2a2a2c]/40 border-b border-[#554336]/20">
              <div className="flex items-center gap-3">
                <div className="relative flex items-center justify-center w-5 h-5">
                  <span className="absolute w-3 h-3 rounded-full bg-[#ffb77d]/20 animate-ping"></span>
                  <span className="w-2 h-2 rounded-full bg-[#ffb77d]"></span>
                </div>
                <span className="text-[18px] text-[#e5e1e4] font-medium leading-none">
                  Testing
                </span>
                <span className="font-label-caps text-[10px] tracking-widest text-[#ffb77d] border border-[#ffb77d]/40 bg-[#ffb77d]/10 px-2 py-0.5 rounded-[0.125rem] font-semibold">
                  ACTIVE
                </span>
              </div>

              <div className="flex items-center gap-3">
                <span
                  id="timer-readout"
                  className="font-label-code text-[12px] text-[#ffb77d] tabular-nums font-medium"
                >
                  {formatTimer(elapsedSeconds)}
                </span>
                <ChevronDown className="w-4 h-4 text-[#e5e1e4]" />
              </div>
            </div>

            {/* Active Metrics Panel Body */}
            <div className="p-5 flex flex-col space-y-4 bg-[#1c1b1d]">
              {/* Telemetry Readout Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {/* Readout 1: Active VUs */}
                <div className="flex flex-col justify-between bg-[#201f22] p-3 rounded-[0.125rem] border border-[#554336]/20">
                  <span className="font-label-caps text-[10px] text-[#dbc2b0]/70 uppercase tracking-wider">
                    Active VUs
                  </span>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="font-label-code text-[26px] leading-tight font-medium text-[#e5e1e4] tabular-nums">
                      300
                    </span>
                    <span className="font-label-code text-[11px] text-[#dbc2b0]/50">
                      / 300
                    </span>
                  </div>
                </div>

                {/* Readout 2: P95 Latency + Inline Trend */}
                <div className="flex flex-col justify-between bg-[#201f22] p-3 rounded-[0.125rem] border border-[#554336]/20">
                  <div className="flex items-center justify-between">
                    <span className="font-label-caps text-[10px] text-[#dbc2b0]/70 uppercase tracking-wider">
                      P95 Latency
                    </span>
                    <span className="font-label-code text-[10px] text-[#ffb77d]">±4ms</span>
                  </div>
                  <div className="mt-1 flex flex-col">
                    <span className="font-label-code text-[26px] leading-tight font-medium text-[#ffb77d] tabular-nums">
                      {latencyValue}ms
                    </span>
                    {/* Sparkline Trend Chart */}
                    <div className="w-full h-5 mt-1 overflow-hidden">
                      <svg
                        className="w-full h-full text-[#ffb77d]"
                        fill="none"
                        preserveAspectRatio="none"
                        viewBox="0 0 100 24"
                      >
                        <path
                          d={sparklinePoints}
                          stroke="currentColor"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="1.5"
                        />
                      </svg>
                    </div>
                  </div>
                </div>

                {/* Readout 3: RPS */}
                <div className="flex flex-col justify-between bg-[#201f22] p-3 rounded-[0.125rem] border border-[#554336]/20">
                  <span className="font-label-caps text-[10px] text-[#dbc2b0]/70 uppercase tracking-wider">
                    RPS
                  </span>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="font-label-code text-[26px] leading-tight font-medium text-[#e5e1e4] tabular-nums">
                      {rpsValue}
                    </span>
                    <span className="font-label-code text-[11px] text-[#ffb77d] flex items-center">
                      <ArrowUp className="w-3 h-3" />
                      req/s
                    </span>
                  </div>
                </div>

                {/* Readout 4: Error Rate */}
                <div className="flex flex-col justify-between bg-[#201f22] p-3 rounded-[0.125rem] border border-[#554336]/20">
                  <span className="font-label-caps text-[10px] text-[#dbc2b0]/70 uppercase tracking-wider">
                    Error Rate
                  </span>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="font-label-code text-[26px] leading-tight font-medium text-[#e5e1e4] tabular-nums">
                      0.3%
                    </span>
                    <span className="font-label-code text-[11px] text-[#dbc2b0]/60">
                      within SLA
                    </span>
                  </div>
                </div>
              </div>

              {/* Terminal Sub-Stream for Active Assertion Output */}
              <div
                id="assertions-terminal"
                className="flex flex-col bg-[#0e0e10] rounded-[0.125rem] border border-[#554336]/30 overflow-hidden"
              >
                <div className="flex items-center justify-between px-3 py-1.5 bg-[#2a2a2c]/30 border-b border-[#554336]/15">
                  <div className="flex items-center gap-1.5 text-[#dbc2b0]/60 font-label-code text-[11px]">
                    <Terminal className="w-3.5 h-3.5" />
                    <span>assertions: fuzz_eval_cluster_0</span>
                  </div>
                  <span className="font-label-code text-[10px] text-[#ffb77d]/80">
                    streaming (buffer: 128kb)
                  </span>
                </div>

                <div className="p-3 font-label-code text-[12px] leading-5 text-[#dbc2b0]/90 space-y-1 select-text max-h-48 overflow-y-auto font-normal">
                  {assertionLogs.map((log) => (
                    <div
                      key={log.id}
                      className={
                        log.isAssertPass
                          ? 'text-[#ffb77d] font-medium'
                          : log.isActive
                          ? 'text-[#dbc2b0]/80 flex items-center gap-2'
                          : 'text-[#dbc2b0]/50'
                      }
                    >
                      <span>
                        [{log.timestamp}] {log.text}
                      </span>
                      {log.isActive && (
                        <span className="w-1.5 h-3 bg-[#ffb77d] inline-block animate-pulse"></span>
                      )}
                    </div>
                  ))}
                  <div ref={terminalEndRef} />
                </div>
              </div>

              {/* Transition to Report Button trigger for interactive experience */}
              <div className="pt-2 flex items-center justify-between">
                <span className="text-[11px] font-label-code text-[#dbc2b0]/60">
                  Binary search convergence nearing ±10 VU ceiling...
                </span>
                <button
                  type="button"
                  onClick={onNavigateToReport}
                  className="px-2.5 py-1 bg-[#2a2a2c] hover:bg-[#353437] text-[#ffb77d] text-[11px] font-label-code rounded-[0.125rem] border border-[#ffb77d]/30 flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <span>Converge & View Report</span>
                  <ChevronRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* Pending Testing (Screens 2, 3) */
          <div className="py-2.5 px-4 bg-[#1c1b1d] rounded-[0.125rem] border border-[#554336]/15 flex items-center justify-between cursor-pointer opacity-50 hover:opacity-80 transition-opacity">
            <div className="flex items-center gap-3">
              <div className="w-5 h-5 flex items-center justify-center">
                <span className="w-1 h-1 rounded-full bg-[#dbc2b0]/40"></span>
              </div>
              <span className="text-[#dbc2b0]/60 font-normal text-[13px]">Testing</span>
            </div>
            <ChevronRight className="w-4 h-4 text-[#dbc2b0]/40" />
          </div>
        )}

        {/* ================= STEP 6: SUMMARIZING ================= */}
        <div className="py-2.5 px-4 bg-[#0e0e10] rounded-[0.125rem] border border-[#554336]/10 flex items-center justify-between cursor-pointer opacity-50 select-none">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 rounded-full border border-[#554336]/40 flex items-center justify-center">
              <span className="w-1 h-1 rounded-full bg-[#554336]/60"></span>
            </div>
            <span className="text-[13px] text-[#dbc2b0]/60">Summarizing</span>
          </div>
          <ChevronRight className="w-4 h-4 text-[#554336]/40" />
        </div>

        {/* ================= STEP 7: BUILDING REPORT ================= */}
        <div className="py-2.5 px-4 bg-[#0e0e10] rounded-[0.125rem] border border-[#554336]/10 flex items-center justify-between cursor-pointer opacity-50 select-none">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 rounded-full border border-[#554336]/40 flex items-center justify-center">
              <span className="w-1 h-1 rounded-full bg-[#554336]/60"></span>
            </div>
            <span className="text-[13px] text-[#dbc2b0]/60">Building Report</span>
          </div>
          <ChevronRight className="w-4 h-4 text-[#554336]/40" />
        </div>
      </section>

      {/* Sticky Bottom Interrupt / Messaging Deck */}
      <div className="fixed bottom-4 left-[260px] right-0 z-30 flex justify-center px-6">
        <form
          onSubmit={handleSendIntervention}
          className="w-full max-w-[48rem] bg-[#1c1b1d] border border-[#554336]/30 rounded-xl px-3.5 py-1.5 flex items-center gap-3 shadow-2xl focus-within:border-[#554336]/50 focus-within:bg-[#201f22] transition-all"
        >
          <button
            type="button"
            className="flex items-center justify-center w-6 h-6 rounded-[0.125rem] text-[#dbc2b0]/70 hover:text-[#e5e1e4] hover:bg-[#201f22] transition-colors cursor-pointer"
            title="Attach context or override payload"
          >
            <Plus className="w-4 h-4" />
          </button>

          <input
            type="text"
            value={interveneInput}
            onChange={(e) => setInterveneInput(e.target.value)}
            placeholder="Send a message or interrupt run..."
            className="flex-1 bg-transparent border-none outline-none text-[13px] text-[#e5e1e4] placeholder:text-[#dbc2b0]/40 py-1"
          />

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onStopRun}
              className="flex items-center gap-1 px-2 py-0.5 rounded-[0.125rem] text-[#dbc2b0]/60 hover:text-[#ffb4ab] hover:bg-[#93000a]/20 text-[11px] font-label-code transition-colors cursor-pointer"
              title="Interrupt or stop run execution"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              <span>{isRunning ? 'Stop' : 'Halted'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
