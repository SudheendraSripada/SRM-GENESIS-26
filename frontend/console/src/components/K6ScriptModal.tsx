import React, { useState } from 'react';
import { X, Copy, Check, Download, Code2 } from 'lucide-react';
import { MOCK_K6_SCRIPT } from '../data/mockData';

interface K6ScriptModalProps {
  isOpen: boolean;
  onClose: () => void;
  runId: string;
}

export const K6ScriptModal: React.FC<K6ScriptModalProps> = ({
  isOpen,
  onClose,
  runId,
}) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(MOCK_K6_SCRIPT);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([MOCK_K6_SCRIPT], { type: 'text/javascript' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${runId}_synthetics.k6.js`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      id="k6-script-modal-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4 animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        id="k6-script-modal"
        className="w-full max-w-3xl bg-[#18181b] border border-[#3f3f46] rounded-[0.25rem] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 bg-[#201f22] border-b border-[#353437]">
          <div className="flex items-center gap-2">
            <Code2 className="w-4 h-4 text-[#ffb77d]" />
            <h3 className="text-[15px] font-medium text-[#e5e1e4]">
              Synthesized Load & Invariance Script (k6)
            </h3>
            <span className="font-label-code text-[11px] text-[#dbc2b0]/60 ml-2">
              k6 / JavaScript ES6
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-[#dbc2b0]/60 hover:text-[#e5e1e4] p-1 rounded-[0.125rem] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Script Content */}
        <div className="p-4 bg-[#0e0e10] overflow-y-auto flex-1 font-label-code text-[12px] leading-relaxed select-text">
          <pre className="text-[#dbc2b0]">
            <code>{MOCK_K6_SCRIPT}</code>
          </pre>
        </div>

        {/* Footer Actions */}
        <div className="px-5 py-3 bg-[#201f22] border-t border-[#353437] flex items-center justify-between">
          <span className="font-label-code text-[11px] text-[#dbc2b0]/60">
            Autonomous target: api.v2.internal / threshold: p(95)&lt;500ms
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownload}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#2a2a2c] hover:bg-[#353437] text-[#e5e1e4] rounded-[0.125rem] text-[12px] font-label-code transition-colors cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download .js</span>
            </button>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#d97707] hover:bg-[#ffb77d] text-[#4d2600] font-medium rounded-[0.125rem] text-[12px] font-label-code transition-colors cursor-pointer"
            >
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy script'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
