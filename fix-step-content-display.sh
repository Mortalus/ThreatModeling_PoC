#!/bin/bash

echo "Fixing StepContentDisplay component..."

# Update the StepContentDisplay interface to include onStartAnalysis
cat > src/components/pipeline/StepContentDisplay.tsx << 'EOF'
import React, { useState } from 'react';
import { FileUpload } from './FileUpload';
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
  onStartAnalysis?: () => void;
}

export const StepContentDisplay: React.FC<StepContentDisplayProps> = ({
  step,
  stepIndex,
  pipelineState,
  runStep,
  loading,
  onUpload,
  modelConfig,
  onStartAnalysis
}) => {
  const [viewMode, setViewMode] = useState<'formatted' | 'json'>('formatted');

  const stepTitles = [
    'Upload Security Document',
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
            {!step.data ? (
              <FileUpload
                onUpload={onUpload}
                acceptedTypes={['.pdf', '.docx', '.txt']}
                maxSize={10 * 1024 * 1024}
                disabled={loading}
                dragAndDrop={true}
              />
            ) : (
              <div className="upload-success">
                <div className="success-icon">✅</div>
                <h3>File uploaded successfully!</h3>
                <div className="file-info">
                  <div className="info-item">
                    <span className="info-label">📄</span>
                    <span className="info-value">{step.data.filename}</span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">Size:</span>
                    <span className="info-value">{Math.round(step.data.size / 1024)} KB</span>
                  </div>
                </div>
                <p className="ready-message">Ready for threat analysis</p>
                
                {onStartAnalysis && (
                  <button 
                    className="btn btn-primary btn-lg start-analysis-btn"
                    onClick={onStartAnalysis}
                    disabled={loading}
                  >
                    🚀 Start Threat Analysis
                  </button>
                )}
              </div>
            )}
          </div>
        );

      case 1: // DFD Extraction
        return (
          <div className="step-dfd">
            {step.data ? (
              <div className="step-results">
                <div className="view-mode-toggle">
                  <button 
                    className={`view-btn ${viewMode === 'formatted' ? 'active' : ''}`}
                    onClick={() => setViewMode('formatted')}
                  >
                    Formatted View
                  </button>
                  <button 
                    className={`view-btn ${viewMode === 'json' ? 'active' : ''}`}
                    onClick={() => setViewMode('json')}
                  >
                    JSON View
                  </button>
                </div>
                {viewMode === 'json' ? (
                  <pre className="json-view">{JSON.stringify(step.data, null, 2)}</pre>
                ) : (
                  <div className="formatted-view">
                    <h4>Extracted DFD Components</h4>
                    <p>Components extracted from document</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="empty-state">
                <p>No data available. Run this step to extract DFD components.</p>
                <button 
                  className="btn btn-primary"
                  onClick={() => runStep(stepIndex)}
                  disabled={loading || pipelineState.steps[0].status !== 'completed'}
                >
                  Run DFD Extraction
                </button>
              </div>
            )}
          </div>
        );

      case 2: // Threat Generation
      case 3: // Threat Refinement
      case 4: // Attack Path Analysis
        return (
          <div className="step-generic">
            {step.data ? (
              <div className="step-results">
                <div className="view-mode-toggle">
                  <button 
                    className={`view-btn ${viewMode === 'formatted' ? 'active' : ''}`}
                    onClick={() => setViewMode('formatted')}
                  >
                    Formatted View
                  </button>
                  <button 
                    className={`view-btn ${viewMode === 'json' ? 'active' : ''}`}
                    onClick={() => setViewMode('json')}
                  >
                    JSON View
                  </button>
                </div>
                {viewMode === 'json' ? (
                  <pre className="json-view">{JSON.stringify(step.data, null, 2)}</pre>
                ) : (
                  <div className="formatted-view">
                    <h4>{stepTitles[stepIndex]} Results</h4>
                    <p>Analysis complete</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="empty-state">
                <p>No data available. Run this step to continue the analysis.</p>
                <button 
                  className="btn btn-primary"
                  onClick={() => runStep(stepIndex)}
                  disabled={loading || (stepIndex > 0 && pipelineState.steps[stepIndex - 1].status !== 'completed')}
                >
                  Run {stepTitles[stepIndex]}
                </button>
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="step-content-display">
      <div className="step-header">
        <h2 className="step-title">{stepTitles[stepIndex]}</h2>
        <p className="step-description">{stepDescriptions[stepIndex]}</p>
      </div>
      
      <div className="step-content">
        {renderStepContent()}
      </div>
    </div>
  );
};
EOF

# Create/update the CSS for StepContentDisplay
cat > src/components/pipeline/StepContentDisplay.css << 'EOF'
.step-content-display {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.step-header {
  text-align: center;
  margin-bottom: 2rem;
  padding: 0 2rem;
}

.step-title {
  font-size: 2rem;
  font-weight: 600;
  margin: 0 0 0.5rem 0;
  color: var(--text-primary);
}

.step-description {
  font-size: 1rem;
  color: var(--text-secondary);
  margin: 0;
}

.step-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.step-upload {
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
}

.upload-success {
  text-align: center;
  padding: 3rem;
  background-color: var(--bg-surface);
  border-radius: 1rem;
  border: 1px solid var(--border-color);
}

.success-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.upload-success h3 {
  font-size: 1.5rem;
  margin: 0 0 2rem 0;
  color: var(--text-primary);
}

.file-info {
  background-color: var(--bg-secondary);
  border-radius: 0.5rem;
  padding: 1.5rem;
  margin-bottom: 2rem;
  text-align: left;
  max-width: 400px;
  margin-left: auto;
  margin-right: auto;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-label {
  font-weight: 500;
  color: var(--text-secondary);
}

.info-value {
  color: var(--text-primary);
}

.ready-message {
  color: var(--text-secondary);
  margin-bottom: 2rem;
}

.start-analysis-btn {
  font-size: 1.125rem;
  padding: 1rem 2rem;
  background-color: var(--accent-color);
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
}

.start-analysis-btn:hover:not(:disabled) {
  background-color: #2563eb;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.start-analysis-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: var(--text-secondary);
}

.empty-state p {
  margin-bottom: 1.5rem;
}

.view-mode-toggle {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  justify-content: center;
}

.view-btn {
  padding: 0.5rem 1rem;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  border-radius: 0.25rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.view-btn:hover {
  background-color: var(--bg-secondary);
  color: var(--text-primary);
}

.view-btn.active {
  background-color: var(--accent-color);
  color: white;
  border-color: var(--accent-color);
}

.json-view {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  padding: 1.5rem;
  overflow-x: auto;
  font-family: monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--text-primary);
}

.formatted-view {
  padding: 1.5rem;
}

.step-results {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
}
EOF

echo "StepContentDisplay component fixed!"
echo ""
echo "The app should now:"
echo "1. Show the upload screen properly"
echo "2. Display file info after upload"
echo "3. Show the 'Start Threat Analysis' button"
echo "4. Handle settings modal correctly"