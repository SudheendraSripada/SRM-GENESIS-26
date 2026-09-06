import React from 'react';
import { FolderOpen, ArrowUpRight, Play, CheckCircle2 } from 'lucide-react';
import { MOCK_PROJECTS } from '../data/mockData';

interface ProjectsViewProps {
  onSelectProject: (projectName: string, targetEndpoint: string) => void;
}

export const ProjectsView: React.FC<ProjectsViewProps> = ({ onSelectProject }) => {
  return (
    <div id="projects-view" className="flex flex-col w-full pb-16">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 mb-6 border-b border-[#554336]/30">
        <div>
          <h1 className="text-[22px] font-medium text-[#e5e1e4]">Target Projects & Services</h1>
          <p className="text-[13px] text-[#dbc2b0]/70 mt-0.5">
            Configured target microservices, API schemas, and baseline load limits
          </p>
        </div>
        <span className="font-label-code text-[11px] text-[#ffb77d] border border-[#ffb77d]/30 px-2 py-1 rounded-[0.125rem]">
          {MOCK_PROJECTS.length} Targets Active
        </span>
      </div>

      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {MOCK_PROJECTS.map((proj) => (
          <div
            key={proj.id}
            className="p-5 bg-[#1c1b1d] border border-[#554336]/30 rounded-[0.25rem] hover:border-[#ffb77d]/40 transition-colors flex flex-col justify-between group"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="font-label-code text-[14px] text-[#ffb77d] font-medium">
                  {proj.name}
                </span>
                <span className="font-label-caps text-[10px] text-[#dbc2b0]/60 bg-[#201f22] px-1.5 py-0.5 rounded-[0.125rem] uppercase">
                  {proj.env}
                </span>
              </div>

              <div className="text-[13px] text-[#e5e1e4]/90 mb-3">{proj.service}</div>

              <div className="font-label-code text-[11px] text-[#dbc2b0]/60 mb-4 bg-[#0e0e10] p-2 rounded-[0.125rem] truncate">
                target: {proj.targetEndpoint}
              </div>
            </div>

            <div className="pt-3 border-t border-[#554336]/20 flex items-center justify-between">
              <div className="flex items-center gap-3 font-label-code text-[11px] text-[#dbc2b0]/70">
                <span>{proj.runsCount} runs</span>
                <span>•</span>
                <span className="text-[#ffb77d]">{proj.sustainableVus} VUs capacity</span>
              </div>

              <button
                onClick={() => onSelectProject(proj.name, proj.targetEndpoint)}
                className="flex items-center gap-1 text-[12px] font-label-code text-[#ffb77d] hover:text-[#ffddb8] transition-colors cursor-pointer"
              >
                <span>Run Test</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
