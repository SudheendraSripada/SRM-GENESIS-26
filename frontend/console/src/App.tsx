/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useCallback } from 'react';
import { NavTab, ScreenId, RunData } from './types';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { NewRunPrompt } from './components/NewRunPrompt';
import { RunTimeline } from './components/RunTimeline';
import { RunReport } from './components/RunReport';
import { RawMetricsModal } from './components/RawMetricsModal';
import { K6ScriptModal } from './components/K6ScriptModal';
import { ExecutionTraceModal } from './components/ExecutionTraceModal';
import { CommandPalette } from './components/CommandPalette';
import { WorkspaceModal } from './components/WorkspaceModal';
import { ProjectsView } from './components/ProjectsView';
import { HistoryView } from './components/HistoryView';
import {
  DEFAULT_RUN_QUERY,
  INITIAL_STEPS,
  INITIAL_DECISIONS,
  MOCK_HISTORY_RUNS,
} from './data/mockData';

export default function App() {
  const [currentTab, setCurrentTab] = useState<NavTab>('runs');
  const [currentScreen, setCurrentScreen] = useState<ScreenId>('prompt');
  const [cluster, setCluster] = useState('prod-eu-west-1');
  const [isSimulating, setIsSimulating] = useState(false);
  const [isDispatching, setIsDispatching] = useState(false);

  // Active run model
  const [runQuery, setRunQuery] = useState(DEFAULT_RUN_QUERY);
  const [runTarget, setRunTarget] = useState('api.v2.internal');
  const [runEnv, setRunEnv] = useState('staging');
  const [runId, setRunId] = useState('run_088f12a9_auth_fuzz');
  const [isRunning, setIsRunning] = useState(true);

  // Current active run full data
  const [currentRunData, setCurrentRunData] = useState<RunData>(MOCK_HISTORY_RUNS[0]);

  // Modal open states
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isRawMetricsOpen, setIsRawMetricsOpen] = useState(false);
  const [isK6ScriptOpen, setIsK6ScriptOpen] = useState(false);
  const [isTraceOpen, setIsTraceOpen] = useState(false);
  const [isWorkspaceOpen, setIsWorkspaceOpen] = useState(false);

  // Auto-simulation progression
  useEffect(() => {
    if (!isSimulating) return;

    const timeout = setTimeout(() => {
      if (currentScreen === 'prompt') {
        setCurrentScreen('analysing');
      } else if (currentScreen === 'analysing') {
        setCurrentScreen('validating');
      } else if (currentScreen === 'validating') {
        setCurrentScreen('testing');
      } else if (currentScreen === 'testing') {
        setCurrentScreen('report');
        setIsSimulating(false);
      }
    }, 4000);

    return () => clearTimeout(timeout);
  }, [isSimulating, currentScreen]);

  // Global keyboard shortcuts (⌘N, ⌘K, ESC)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Check if user is typing in an input/textarea
      const isInput =
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement;

      if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
        e.preventDefault();
        handleNewRun();
        return;
      }

      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen(true);
        return;
      }

      // Quick numbers 1..5 for direct screen switching when not in text input
      if (!isInput && !e.metaKey && !e.ctrlKey && !e.altKey) {
        if (e.key === '1') {
          setCurrentTab('runs');
          setCurrentScreen('prompt');
        } else if (e.key === '2') {
          setCurrentTab('runs');
          setCurrentScreen('analysing');
        } else if (e.key === '3') {
          setCurrentTab('runs');
          setCurrentScreen('validating');
        } else if (e.key === '4') {
          setCurrentTab('runs');
          setCurrentScreen('testing');
        } else if (e.key === '5') {
          setCurrentTab('runs');
          setCurrentScreen('report');
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleNewRun = () => {
    setCurrentTab('runs');
    setCurrentScreen('prompt');
    setIsSimulating(false);
  };

  const handleRunTest = (
    query: string,
    target: string,
    env: string,
    deepReasoning: boolean
  ) => {
    setIsDispatching(true);
    setRunQuery(query);
    setRunTarget(target);
    setRunEnv(env);
    const newId = `run_${Math.random().toString(16).substring(2, 10)}_auth_fuzz`;
    setRunId(newId);
    setIsRunning(true);

    setTimeout(() => {
      setIsDispatching(false);
      setCurrentTab('runs');
      setCurrentScreen('analysing');
      setIsSimulating(true);
    }, 600);
  };

  const handleStopRun = () => {
    setIsRunning(false);
    setIsSimulating(false);
  };

  const handleSendMessage = (msg: string) => {
    // Injects an intervention
  };

  const handleSelectProject = (projectName: string, targetEndpoint: string) => {
    setRunTarget(targetEndpoint);
    setRunQuery(`Run recursive security boundary tests on ${projectName} endpoints`);
    setCurrentTab('runs');
    setCurrentScreen('prompt');
  };

  const handleSelectHistoricalRun = (run: RunData) => {
    setCurrentRunData(run);
    setRunQuery(run.query);
    setRunTarget(run.target);
    setRunId(run.id);
    setCurrentTab('runs');
    setCurrentScreen('report');
  };

  const handleResetSimulation = () => {
    setIsSimulating(false);
    setCurrentScreen('prompt');
  };

  return (
    <div className="min-h-screen bg-[#0e0e10] text-[#e5e1e4] flex flex-col font-sans">
      {/* Fixed Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onTabChange={(tab) => {
          setCurrentTab(tab);
          if (tab === 'runs' && currentScreen === 'prompt') {
            setCurrentScreen('prompt');
          }
        }}
        onNewRun={handleNewRun}
        onOpenWorkspace={() => setIsWorkspaceOpen(true)}
        currentScreen={currentScreen}
        onScreenChange={(s) => {
          setCurrentTab('runs');
          setCurrentScreen(s);
        }}
      />

      {/* Fixed Top Header */}
      <Header
        onOpenSearch={() => setIsSearchOpen(true)}
        cluster={cluster}
        onClusterChange={setCluster}
      />

      {/* Main Content Area */}
      <main className="ml-[260px] pt-14 min-h-screen flex flex-col bg-[#0e0e10]">
        <div className="w-full max-w-[48rem] mx-auto px-6 py-6 flex-1 flex flex-col">
          {currentTab === 'projects' ? (
            <ProjectsView onSelectProject={handleSelectProject} />
          ) : currentTab === 'history' ? (
            <HistoryView onSelectRun={handleSelectHistoricalRun} />
          ) : (
            /* Runs Tab: switch between the screens */
            <>
              {currentScreen === 'prompt' && (
                <NewRunPrompt
                  onRunTest={handleRunTest}
                  defaultPrompt={runQuery}
                  isDispatching={isDispatching}
                />
              )}

              {(currentScreen === 'analysing' ||
                currentScreen === 'validating' ||
                currentScreen === 'testing') && (
                <RunTimeline
                  currentScreen={currentScreen}
                  runQuery={runQuery}
                  targetEndpoint={runTarget}
                  env={runEnv}
                  runId={runId}
                  onNavigateToReport={() => setCurrentScreen('report')}
                  onStopRun={handleStopRun}
                  isRunning={isRunning}
                  onSendMessage={handleSendMessage}
                />
              )}

              {currentScreen === 'report' && (
                <RunReport
                  runData={{
                    ...currentRunData,
                    id: runId,
                    query: runQuery,
                    target: runTarget,
                  }}
                  onOpenRawMetrics={() => setIsRawMetricsOpen(true)}
                  onOpenK6Script={() => setIsK6ScriptOpen(true)}
                  onOpenTrace={() => setIsTraceOpen(true)}
                  onReRun={handleNewRun}
                  onExport={() => {
                    navigator.clipboard?.writeText?.(
                      `Autonomous Test Attestation: ${runId}\nSustainable Capacity: 350 VUs\nSLA Ceiling: 500ms (Observed: 438ms)\nVerdict: ${currentRunData.analystQuote}`
                    );
                  }}
                />
              )}
            </>
          )}
        </div>
      </main>

      {/* Modals & Dialogs */}
      <CommandPalette
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        onNavigateScreen={(s) => {
          setCurrentTab('runs');
          setCurrentScreen(s);
        }}
        onSelectPrompt={(p) => {
          setRunQuery(p);
        }}
        onSelectCluster={setCluster}
      />

      <RawMetricsModal
        isOpen={isRawMetricsOpen}
        onClose={() => setIsRawMetricsOpen(false)}
        runData={currentRunData}
      />

      <K6ScriptModal
        isOpen={isK6ScriptOpen}
        onClose={() => setIsK6ScriptOpen(false)}
        runId={runId}
      />

      <ExecutionTraceModal
        isOpen={isTraceOpen}
        onClose={() => setIsTraceOpen(false)}
        runId={runId}
      />

      <WorkspaceModal
        isOpen={isWorkspaceOpen}
        onClose={() => setIsWorkspaceOpen(false)}
        cluster={cluster}
      />
    </div>
  );
}
