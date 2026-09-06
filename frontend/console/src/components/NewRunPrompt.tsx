import React, { useState, useEffect } from 'react';
import { Plus, ArrowRight, Brain, Check, FileCode, Sliders, ShieldCheck } from 'lucide-react';

interface NewRunPromptProps {
  onRunTest: (query: string, target: string, env: string, deepReasoning: boolean) => void;
  defaultPrompt?: string;
  isDispatching?: boolean;
}

export const NewRunPrompt: React.FC<NewRunPromptProps> = ({
  onRunTest,
  defaultPrompt = '',
  isDispatching = false,
}) => {
  const [promptText, setPromptText] = useState(defaultPrompt);
  const [deepReasoning, setDeepReasoning] = useState(true);
  const [targetEndpoint, setTargetEndpoint] = useState('api.v2.internal');
  const [isEditingTarget, setIsEditingTarget] = useState(false);
  const [selectedEnv, setSelectedEnv] = useState<'STAGING' | 'CANARY' | 'PROD'>('STAGING');
  const [attachMenuOpen, setAttachMenuOpen] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<string[]>(['openapi-spec-v2.json']);
  const [greeting, setGreeting] = useState('Evening');

  useEffect(() => {
    const hour = new Date().getHours();
    if (hour < 12) setGreeting('Morning');
    else if (hour < 18) setGreeting('Afternoon');
    else setGreeting('Evening');
  }, []);

  const handleRun = () => {
    if (!promptText.trim()) {
      setPromptText(
        'Test fuzzy authentication flows across staging api.v2 endpoints with concurrency limit 50 and observe idempotency keys'
      );
      return;
    }
    onRunTest(promptText.trim(), targetEndpoint, selectedEnv, deepReasoning);
  };

  const fillPrompt = (text: string) => {
    setPromptText(text);
  };

  const toggleAttachment = (name: string) => {
    if (attachedFiles.includes(name)) {
      setAttachedFiles(attachedFiles.filter((f) => f !== name));
    } else {
      setAttachedFiles([...attachedFiles, name]);
    }
  };

  return (
    <div
      id="new-run-screen"
      className="min-h-[calc(100vh-11rem)] flex flex-col justify-center items-center py-12 relative select-none"
    >
      {/* Subtle Background Glow */}
      <div className="absolute inset-0 pointer-events-none flex items-center justify-center opacity-40">
        <div className="w-[32rem] h-[32rem] rounded-full bg-[#1c1b1d] blur-[120px] -translate-y-6"></div>
      </div>

      <div className="w-full relative z-10 flex flex-col items-center">
        {/* Header Eyebrow & Editorial Title */}
        <div className="text-center mb-8 space-y-1">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-[0.125rem] bg-[#201f22] text-[#dbc2b0]/70 font-label-caps text-[11px] mb-2 border border-[#554336]/30">
            <span className="w-1.5 h-1.5 rounded-full bg-[#d97707]"></span>
            <span>AUTONOMOUS AGENT ACTIVE</span>
            <span className="text-[#dbc2b0]/40">/</span>
            <button
              onClick={() => {
                const nextEnv = selectedEnv === 'STAGING' ? 'CANARY' : selectedEnv === 'CANARY' ? 'PROD' : 'STAGING';
                setSelectedEnv(nextEnv);
              }}
              className="font-label-code text-[11px] hover:text-[#ffb77d] transition-colors cursor-pointer"
              title="Click to toggle execution environment"
            >
              ENV:{selectedEnv}
            </button>
          </div>

          <h1 className="font-display-editorial text-[40px] leading-[48px] text-[#e5e1e4] italic font-normal tracking-tight">
            {greeting} — what should we test?
          </h1>
        </div>

        {/* Prompt Card */}
        <div className="w-full max-w-[44rem] px-4 sm:px-0">
          <div
            id="prompt-card"
            className="group relative rounded-xl bg-[#1c1b1d] transition-all duration-200 shadow-sm hover:shadow-md focus-within:bg-[#201f22] border border-[#554336]/30 focus-within:border-[#ffb77d]/40"
          >
            <div className="p-5 flex flex-col gap-3">
              <div className="flex items-start gap-3">
                {/* Plus / Attach Button */}
                <div className="relative">
                  <button
                    id="attach-context-btn"
                    onClick={() => setAttachMenuOpen(!attachMenuOpen)}
                    type="button"
                    className={`mt-1 flex items-center justify-center w-7 h-7 rounded-[0.125rem] bg-[#201f22] hover:bg-[#2a2a2c] transition-colors shrink-0 cursor-pointer ${
                      attachMenuOpen ? 'text-[#ffb77d] border border-[#ffb77d]/40' : 'text-[#dbc2b0] hover:text-[#e5e1e4]'
                    }`}
                    title="Attach context, schema, or endpoint"
                  >
                    <Plus className="w-4 h-4" />
                  </button>

                  {/* Attachment Popover */}
                  {attachMenuOpen && (
                    <div
                      id="attachment-popover"
                      className="absolute top-9 left-0 w-64 bg-[#18181b] border border-[#353437] rounded-[0.25rem] shadow-2xl p-2 z-50 text-xs flex flex-col gap-1.5"
                    >
                      <div className="px-2 py-1 text-[10px] font-label-caps text-[#dbc2b0]/50 tracking-wider uppercase border-b border-[#353437]">
                        Attach Context & Schemas
                      </div>
                      {[
                        { name: 'openapi-spec-v2.json', label: 'OpenAPI 3.1 Endpoint Schema', icon: FileCode },
                        { name: 'jwt-auth-keyset.jwks', label: 'Asymmetric Token Keyset', icon: ShieldCheck },
                        { name: 'rate-limit-policy.yaml', label: 'Rate Limiting Rules', icon: Sliders },
                      ].map((item) => (
                        <button
                          key={item.name}
                          type="button"
                          onClick={() => toggleAttachment(item.name)}
                          className={`flex items-center justify-between p-2 rounded-[0.125rem] transition-colors text-left ${
                            attachedFiles.includes(item.name)
                              ? 'bg-[#201f22] text-[#ffb77d]'
                              : 'text-[#e5e1e4] hover:bg-[#201f22]'
                          }`}
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <item.icon className="w-3.5 h-3.5 shrink-0 text-[#dbc2b0]" />
                            <div className="flex flex-col min-w-0">
                              <span className="font-label-code text-[11px] truncate">{item.name}</span>
                              <span className="text-[10px] text-[#dbc2b0]/50 truncate">{item.label}</span>
                            </div>
                          </div>
                          {attachedFiles.includes(item.name) && (
                            <Check className="w-3.5 h-3.5 text-[#ffb77d] shrink-0" />
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Textarea */}
                <div className="flex-1 min-w-0">
                  <textarea
                    id="prompt-input"
                    rows={3}
                    value={promptText}
                    onChange={(e) => setPromptText(e.target.value)}
                    onKeyDown={(e) => {
                      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                        e.preventDefault();
                        handleRun();
                      }
                    }}
                    placeholder="Describe what you need to test"
                    className="w-full bg-transparent resize-none border-none outline-none text-[16px] text-[#e5e1e4] placeholder:text-[#dbc2b0]/40 leading-relaxed overflow-y-auto"
                  />

                  {/* Display active attached badges if any */}
                  {attachedFiles.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {attachedFiles.map((file) => (
                        <span
                          key={file}
                          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-[0.125rem] bg-[#201f22] border border-[#554336]/40 text-[10px] font-label-code text-[#dbc2b0]"
                        >
                          <FileCode className="w-2.5 h-2.5 text-[#ffb77d]" />
                          {file}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Bottom Control Bar inside card */}
              <div className="pt-2 flex flex-wrap items-center justify-between border-t border-[#554336]/20 gap-2">
                <div className="flex items-center gap-3">
                  {/* Deep Reasoning Toggle */}
                  <button
                    id="deep-reasoning-toggle"
                    type="button"
                    onClick={() => setDeepReasoning(!deepReasoning)}
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-[0.125rem] font-label-caps text-[11px] transition-colors cursor-pointer ${
                      deepReasoning
                        ? 'bg-[#201f22] text-[#e5e1e4] border border-[#554336]/40'
                        : 'bg-[#18181b] text-[#dbc2b0]/50 border border-transparent'
                    }`}
                    title="Toggle autonomous recursive test reasoning"
                  >
                    <Brain className={`w-3.5 h-3.5 ${deepReasoning ? 'text-[#ffb77d]' : 'text-[#dbc2b0]/50'}`} />
                    <span>Deep Reasoning</span>
                  </button>

                  {/* Target Endpoint Input / Display */}
                  <div className="hidden sm:flex items-center gap-1.5 text-[#dbc2b0]/50 font-label-code text-[13px]">
                    <span>Target:</span>
                    {isEditingTarget ? (
                      <input
                        type="text"
                        value={targetEndpoint}
                        autoFocus
                        onBlur={() => setIsEditingTarget(false)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') setIsEditingTarget(false);
                        }}
                        onChange={(e) => setTargetEndpoint(e.target.value)}
                        className="bg-[#201f22] text-[#ffb77d] px-1.5 py-0.5 rounded-[0.125rem] border border-[#ffb77d]/40 outline-none font-label-code text-[12px]"
                      />
                    ) : (
                      <button
                        type="button"
                        onClick={() => setIsEditingTarget(true)}
                        className="text-[#dbc2b0] hover:text-[#ffb77d] hover:underline cursor-pointer"
                        title="Click to edit target API endpoint"
                      >
                        {targetEndpoint}
                      </button>
                    )}
                  </div>
                </div>

                {/* Submit button & shortcut */}
                <div className="flex items-center gap-3">
                  <span className="hidden sm:inline-block font-label-code text-[11px] text-[#dbc2b0]/40 tracking-wider">
                    ⌘ ↵ to run
                  </span>

                  <button
                    id="run-trigger"
                    type="button"
                    disabled={isDispatching}
                    onClick={handleRun}
                    className="inline-flex items-center gap-2 px-3.5 py-2 rounded-[0.125rem] bg-[#d97707] text-[#4d2600] font-medium text-[14px] hover:bg-[#ffb77d] transition-all cursor-pointer select-none active:scale-[0.98] shadow-sm disabled:opacity-75"
                  >
                    {isDispatching ? (
                      <>
                        <span className="w-3.5 h-3.5 border-2 border-[#4d2600] border-t-transparent rounded-full animate-spin"></span>
                        <span>Dispatching agent...</span>
                      </>
                    ) : (
                      <>
                        <span>Run autonomous test</span>
                        <ArrowRight className="w-4 h-4 text-[#4d2600]" />
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Preset Prompts / Suggestion Chips */}
          <div className="mt-5 flex flex-wrap items-center justify-between px-1 text-[#dbc2b0]/50 font-label-code text-[11px] gap-2">
            <div className="flex flex-wrap items-center gap-4">
              <button
                type="button"
                className="hover:text-[#ffb77d] cursor-pointer transition-colors"
                onClick={() =>
                  fillPrompt(
                    'Run fuzzy auth permutations across /v2/sessions with malformed JWT signatures'
                  )
                }
              >
                /fuzzy-auth
              </button>

              <button
                type="button"
                className="hover:text-[#ffb77d] cursor-pointer transition-colors"
                onClick={() =>
                  fillPrompt(
                    'Simulate concurrent load spikes on checkout webhook endpoints up to 10k rps'
                  )
                }
              >
                /load-spike
              </button>

              <button
                type="button"
                className="hover:text-[#ffb77d] cursor-pointer transition-colors"
                onClick={() =>
                  fillPrompt(
                    'Verify state rollbacks and idempotency keys on payment settlement failures'
                  )
                }
              >
                /idempotency
              </button>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#ffb95f]"></span>
              <span>Standby</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
