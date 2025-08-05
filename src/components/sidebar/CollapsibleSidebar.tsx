import React from 'react';
import { PipelineStep } from '../../types';
import './CollapsibleSidebar.css';

interface CollapsibleSidebarProps {
  steps: PipelineStep[];
  currentStep: number;
  onStepClick: (stepIndex: number) => void;
  collapsed: boolean;
  onToggle: () => void;
  onSettingsClick: () => void;
}

export const CollapsibleSidebar: React.FC<CollapsibleSidebarProps> = ({
  steps,
  currentStep,
  onStepClick,
  collapsed,
  onToggle,
  onSettingsClick
}) => {
  const getStepIcon = (stepIndex: number): string => {
    const icons = ['📄', '🔍', '⚠️', '🔧', '🎯'];
    return icons[stepIndex] || '📋';
  };

  const getStepStatusClass = (step: PipelineStep): string => {
    switch (step.status) {
      case 'completed': return 'completed';
      case 'running': return 'running';
      case 'error': return 'error';
      default: return '';
    }
  };

  return (
    <div className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        {!collapsed && (
          <>
            <h1>ThreatShield</h1>
            <p>AI Security Pipeline</p>
          </>
        )}
      </div>

      <button className="sidebar-toggle" onClick={onToggle}>
        {collapsed ? '→' : '←'}
      </button>

      <div className="pipeline-steps">
        <h3 className={collapsed ? 'collapsed-title' : ''}>
          {collapsed ? 'P' : 'PIPELINE PROGRESS'}
        </h3>
        
        {steps.map((step, index) => (
          <div
            key={step.id}
            className={`step-item ${index === currentStep ? 'active' : ''} ${getStepStatusClass(step)}`}
            onClick={() => onStepClick(index)}
          >
            <span className="step-icon">{getStepIcon(index)}</span>
            {!collapsed && (
              <div className="step-content">
                <div className="step-name">{step.name}</div>
                <div className="step-status">
                  {step.status === 'running' ? `${step.percentage}%` : step.status}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="sidebar-footer">
        <button className="settings-btn" onClick={onSettingsClick}>
          ⚙️ {!collapsed && 'Settings'}
        </button>
      </div>
    </div>
  );
};
