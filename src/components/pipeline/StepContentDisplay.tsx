import React, { useState, useMemo } from 'react';
import { FileUpload } from './FileUpload';
import { ThreatDataViewer } from './ThreatDataViewer';
import { DFDDataViewer } from './DFDDataViewer';
import { AttackPathViewer } from './AttackPathViewer';
import { GenericDataViewer } from './GenericDataViewer';
import { PipelineStep, ModelConfig } from '../../types';
import './StepContentDisplay.css';

interface StepContentDisplayProps {
  step: PipelineStep;
  stepIndex: number;
  pipelineState: any;
  runStep: (stepIndex: number) => void;
  loading: boolean;
  onUpload: (file: File) => void;
  modelConfig: ModelConfig | null;
}

export const StepContentDisplay: React.FC<StepContentDisplayProps> = ({
  step,
  stepIndex,
  pipelineState,
  runStep,
  loading,
  onUpload,
  modelConfig
}) => {
  const [viewMode, setViewMode] = useState<'formatted' | 'json'>('formatted');

  const stepTitles = [
    'Document Upload',
    'Data Flow Diagram Extraction', 
    'Threat Identification',
    'Threat Refinement',
    'Attack Path Analysis'
  ];

  const stepDescriptions = [
    'Upload your security requirements document (PDF, DOCX, or TXT format)',
    'AI analyzes the document to extract Data Flow Diagram components',
    'Generate security threats using STRIDE methodology',
    'Enhance threats with MITRE ATT&CK mappings and CVE data',
    'Analyze potential attack paths and exploit chains'
  ];

  const renderStepContent = () => {
    switch (stepIndex) {
      case 0: // Document Upload
        return (
          <div className="step-upload">
            <FileUpload
              onUpload={onUpload}
              acceptedTypes={['.pdf', '.docx', '.txt']}
              maxSize={10 * 1024 * 1024}
              disabled={loading}
              dragAndDrop={true}
            />
            {step.data && (
              <div className="upload-success">
                <h4>✅ File uploaded successfully</h4>
                <div className="file-info">
                  <p><strong>Filename:</strong> {step.data.filename}</p>
                  <p><strong>Size:</strong> {Math.round(step.data.size / 1024)} KB</p>
                  <p><strong>Type:</strong> {step.data.file_type}</p>
                </div>
                {step.data.content_preview && (
                  <div className="content-preview">
                    <h5>Content Preview:</h5>
                    <pre>{step.data.content_preview.substring(0, 500)}...</pre>
                  </div>
                )}
              </div>
            )}
          </div>
        );

      case 1: // DFD Extraction
        return (
          <div className="step-dfd">
            {step.data ? (
              <DFDDataViewer 
                data={step.data} 
                viewMode={viewMode}
                onViewModeChange={setViewMode}
              />
            ) : (
              <div className="step-placeholder">
                <p>Data Flow Diagram components will appear here after extraction.</p>
              </div>
            )}
          </div>
        );

      case 2: // Threat Identification
        return (
          <div className="step-threats">
            {step.data ? (
              <ThreatDataViewer 
                data={step.data}
                viewMode={viewMode}
                onViewModeChange={setViewMode}
              />
            ) : (
              <div className="step-placeholder">
                <p>Identified threats will appear here after analysis.</p>
              </div>
            )}
          </div>
        );

      case 3: // Threat Refinement  
        return (
          <div className="step-refinement">
            {step.data ? (
              <ThreatDataViewer 
                data={step.data}
                viewMode={viewMode}
                onViewModeChange={setViewMode}
                showRefinements={true}
              />
            ) : (
              <div className="step-placeholder">
                <p>Refined threats with MITRE ATT&CK mappings will appear here.</p>
              </div>
            )}
          </div>
        );

      case 4: // Attack Path Analysis
        return (
          <div className="step-attack-paths">
            {step.data ? (
              <AttackPathViewer 
                data={step.data}
                viewMode={viewMode}
                onViewModeChange={setViewMode}
              />
            ) : (
              <div className="step-placeholder">
                <p>Attack path analysis will appear here.</p>
              </div>
            )}
          </div>
        );

      default:
        return (
          <div className="step-generic">
            {step.data ? (
              <GenericDataViewer data={step.data} />
            ) : (
              <div className="step-placeholder">
                <p>Step data will appear here after processing.</p>
              </div>
            )}
          </div>
        );
    }
  };

  const canRunStep = useMemo(() => {
    if (stepIndex === 0) return false; // Upload step doesn't "run"
    if (loading) return false;
    if (stepIndex > 0 && pipelineState.steps[stepIndex - 1].status !== 'completed') {
      return false;
    }
    return true;
  }, [stepIndex, loading, pipelineState.steps]);

  return (
    <div className="step-content-display">
      <div className="step-header">
        <h2 className="step-title">
          {stepTitles[stepIndex] || `Step ${stepIndex + 1}`}
        </h2>
        <p className="step-description">
          {stepDescriptions[stepIndex] || 'Process this pipeline step'}
        </p>
      </div>

      {step.data && stepIndex > 0 && (
        <div className="step-view-controls">
          <div className="view-mode-tabs">
            <button
              className={`tab ${viewMode === 'formatted' ? 'active' : ''}`}
              onClick={() => setViewMode('formatted')}
            >
              📊 Formatted View
            </button>
            <button
              className={`tab ${viewMode === 'json' ? 'active' : ''}`}
              onClick={() => setViewMode('json')}
            >
              📝 Raw JSON
            </button>
          </div>
        </div>
      )}

      <div className="step-content">
        {renderStepContent()}
      </div>

      {stepIndex > 0 && (
        <div className="step-actions">
          <button
            className="btn btn-primary btn-lg"
            onClick={() => runStep(stepIndex)}
            disabled={!canRunStep}
            aria-label={`Run ${stepTitles[stepIndex]}`}
          >
            {loading ? (
              <>⏳ Processing...</>
            ) : (
              <>▶️ Run {stepTitles[stepIndex]}</>
            )}
          </button>
          
          {step.status === 'error' && (
            <button
              className="btn btn-secondary"
              onClick={() => runStep(stepIndex)}
              disabled={loading}
            >
              🔄 Retry
            </button>
          )}
        </div>
      )}

      {step.status === 'error' && step.data?.error && (
        <div className="step-error">
          <h4>❌ Error</h4>
          <p>{step.data.error}</p>
        </div>
      )}
    </div>
  );
};
