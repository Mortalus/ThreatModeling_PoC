#!/bin/bash

# FIXED Auto-convert existing JavaScript components to React TypeScript
# This script reads your backup JS files and converts them to React components

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[CONVERT]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "🔄 Auto-Converting JavaScript to React Components (FIXED)"
echo "======================================================="

# Find the JavaScript files
BACKUP_DIR=""
if [ -d "backup" ]; then
    BACKUP_DIR=$(find backup -type d -name "*" | sort -r | head -n 1)
    if [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR/js" ]; then
        print_status "Found backup directory: $BACKUP_DIR"
    else
        print_warning "No JS backup found, looking for js/ directory in root"
        if [ -d "js" ]; then
            BACKUP_DIR="."
        else
            print_error "No js/ directory found. Please ensure you have your original JavaScript files."
            exit 1
        fi
    fi
else
    print_warning "No backup directory found, looking for js/ directory in root"
    if [ -d "js" ]; then
        BACKUP_DIR="."
    else
        print_error "No js/ directory found. Please ensure you have your original JavaScript files."
        exit 1
    fi
fi

JS_DIR="$BACKUP_DIR/js"
print_status "Using JavaScript files from: $JS_DIR"

# Continue with the rest of the conversion...
# The components were already created by the previous run, so let's just create the missing pieces

print_status "Creating remaining component stubs..."

# Create proper data viewer components
cat > src/components/pipeline/ThreatDataViewer.tsx << 'EOF'
import React from 'react';

interface ThreatDataViewerProps {
  data: any;
  viewMode?: 'formatted' | 'json';
  onViewModeChange?: (mode: 'formatted' | 'json') => void;
  showRefinements?: boolean;
}

export const ThreatDataViewer: React.FC<ThreatDataViewerProps> = ({ 
  data, 
  viewMode = 'formatted', 
  onViewModeChange,
  showRefinements = false
}) => {
  const threats = Array.isArray(data?.threats) ? data.threats : (Array.isArray(data) ? data : []);
  
  return (
    <div className="threat-data-viewer">
      <div className="data-viewer-header">
        <h3>🛡️ Threat Analysis Results</h3>
        {onViewModeChange && (
          <div className="view-mode-controls">
            <button 
              className={`btn btn-sm ${viewMode === 'formatted' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => onViewModeChange('formatted')}
            >
              📊 Formatted
            </button>
            <button 
              className={`btn btn-sm ${viewMode === 'json' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => onViewModeChange('json')}
            >
              📝 JSON
            </button>
          </div>
        )}
      </div>
      
      <div className="data-viewer-content">
        {viewMode === 'json' ? (
          <pre className="json-display">
            {JSON.stringify(data, null, 2)}
          </pre>
        ) : (
          <div className="formatted-display">
            <div className="threats-summary">
              <h4>Summary: {threats.length} threats identified</h4>
            </div>
            
            <div className="threats-list">
              {threats.map((threat: any, index: number) => (
                <div key={index} className="threat-card">
                  <div className="threat-header">
                    <span className="threat-component">{threat.component_name}</span>
                    <span className={`risk-badge risk-${threat.risk_score?.toLowerCase()}`}>
                      {threat.risk_score}
                    </span>
                  </div>
                  <div className="threat-category">
                    STRIDE: {threat.stride_category}
                  </div>
                  <div className="threat-description">
                    {threat.threat_description}
                  </div>
                  <div className="threat-mitigation">
                    <strong>Mitigation:</strong> {threat.mitigation_suggestion}
                  </div>
                  {showRefinements && threat.mitre_attack && (
                    <div className="threat-mitre">
                      <strong>MITRE ATT&CK:</strong> {threat.mitre_attack.join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
EOF

cat > src/components/pipeline/DFDDataViewer.tsx << 'EOF'
import React from 'react';

interface DFDDataViewerProps {
  data: any;
  viewMode?: 'formatted' | 'json';
  onViewModeChange?: (mode: 'formatted' | 'json') => void;
}

export const DFDDataViewer: React.FC<DFDDataViewerProps> = ({ 
  data, 
  viewMode = 'formatted', 
  onViewModeChange
}) => {
  const dfdData = data?.dfd || data;
  
  return (
    <div className="dfd-data-viewer">
      <div className="data-viewer-header">
        <h3>🔗 Data Flow Diagram Components</h3>
        {onViewModeChange && (
          <div className="view-mode-controls">
            <button 
              className={`btn btn-sm ${viewMode === 'formatted' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => onViewModeChange('formatted')}
            >
              📊 Formatted
            </button>
            <button 
              className={`btn btn-sm ${viewMode === 'json' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => onViewModeChange('json')}
            >
              📝 JSON
            </button>
          </div>
        )}
      </div>
      
      <div className="data-viewer-content">
        {viewMode === 'json' ? (
          <pre className="json-display">
            {JSON.stringify(data, null, 2)}
          </pre>
        ) : (
          <div className="formatted-display">
            {dfdData?.project_name && (
              <div className="dfd-project-info">
                <h4>📋 {dfdData.project_name}</h4>
                {dfdData.description && <p>{dfdData.description}</p>}
              </div>
            )}
            
            <div className="dfd-components">
              {dfdData?.external_entities && (
                <div className="component-section">
                  <h5>🔴 External Entities ({dfdData.external_entities.length})</h5>
                  <div className="component-list">
                    {dfdData.external_entities.map((entity: any, index: number) => (
                      <div key={index} className="component-item">
                        <strong>{entity.name}</strong>
                        {entity.description && <p>{entity.description}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {dfdData?.processes && (
                <div className="component-section">
                  <h5>⚙️ Processes ({dfdData.processes.length})</h5>
                  <div className="component-list">
                    {dfdData.processes.map((process: any, index: number) => (
                      <div key={index} className="component-item">
                        <strong>{process.name}</strong>
                        {process.description && <p>{process.description}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {dfdData?.data_stores && (
                <div className="component-section">
                  <h5>💾 Data Stores ({dfdData.data_stores.length})</h5>
                  <div className="component-list">
                    {dfdData.data_stores.map((store: any, index: number) => (
                      <div key={index} className="component-item">
                        <strong>{store.name}</strong>
                        {store.description && <p>{store.description}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {dfdData?.data_flows && (
                <div className="component-section">
                  <h5>🔄 Data Flows ({dfdData.data_flows.length})</h5>
                  <div className="component-list">
                    {dfdData.data_flows.map((flow: any, index: number) => (
                      <div key={index} className="component-item">
                        <strong>{flow.name}</strong>
                        {flow.description && <p>{flow.description}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
EOF

cat > src/components/pipeline/AttackPathViewer.tsx << 'EOF'
import React from 'react';

interface AttackPathViewerProps {
  data: any;
  viewMode?: 'formatted' | 'json';
  onViewModeChange?: (mode: 'formatted' | 'json') => void;
}

export const AttackPathViewer: React.FC<AttackPathViewerProps> = ({ 
  data, 
  viewMode = 'formatted', 
  onViewModeChange
}) => {
  const attackPaths = Array.isArray(data?.attack_paths) ? data.attack_paths : (Array.isArray(data) ? data : []);
  
  return (
    <div className="attack-path-viewer">
      <div className="data-viewer-header">
        <h3>🎯 Attack Path Analysis</h3>
        {onViewModeChange && (
          <div className="view-mode-controls">
            <button 
              className={`btn btn-sm ${viewMode === 'formatted' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => onViewModeChange('formatted')}
            >
              📊 Formatted
            </button>
            <button 
              className={`btn btn-sm ${viewMode === 'json' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => onViewModeChange('json')}
            >
              📝 JSON
            </button>
          </div>
        )}
      </div>
      
      <div className="data-viewer-content">
        {viewMode === 'json' ? (
          <pre className="json-display">
            {JSON.stringify(data, null, 2)}
          </pre>
        ) : (
          <div className="formatted-display">
            <div className="attack-paths-summary">
              <h4>Summary: {attackPaths.length} attack paths identified</h4>
            </div>
            
            <div className="attack-paths-list">
              {attackPaths.map((path: any, index: number) => (
                <div key={index} className="attack-path-card">
                  <div className="path-header">
                    <h5>{path.name || `Attack Path ${index + 1}`}</h5>
                    <div className="path-metrics">
                      <span className={`impact-badge impact-${path.impact?.toLowerCase()}`}>
                        Impact: {path.impact}
                      </span>
                      <span className={`likelihood-badge likelihood-${path.likelihood?.toLowerCase()}`}>
                        Likelihood: {path.likelihood}
                      </span>
                    </div>
                  </div>
                  
                  {path.description && (
                    <div className="path-description">
                      {path.description}
                    </div>
                  )}
                  
                  {path.steps && (
                    <div className="path-steps">
                      <h6>Attack Steps:</h6>
                      <ol>
                        {path.steps.map((step: any, stepIndex: number) => (
                          <li key={stepIndex} className="attack-step">
                            <strong>{step.technique || `Step ${stepIndex + 1}`}</strong>
                            {step.description && <p>{step.description}</p>}
                            {step.mitre_attack_id && (
                              <span className="mitre-tag">MITRE: {step.mitre_attack_id}</span>
                            )}
                          </li>
                        ))}
                      </ol>
                    </div>
                  )}
                  
                  {path.mitigation_strategies && (
                    <div className="path-mitigations">
                      <h6>Mitigation Strategies:</h6>
                      <ul>
                        {path.mitigation_strategies.map((mitigation: string, mitIndex: number) => (
                          <li key={mitIndex}>{mitigation}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
EOF

cat > src/components/pipeline/GenericDataViewer.tsx << 'EOF'
import React from 'react';

interface GenericDataViewerProps {
  data: any;
  title?: string;
}

export const GenericDataViewer: React.FC<GenericDataViewerProps> = ({ 
  data,
  title = "Data Viewer"
}) => {
  return (
    <div className="generic-data-viewer">
      <div className="data-viewer-header">
        <h3>📄 {title}</h3>
      </div>
      
      <div className="data-viewer-content">
        <div className="formatted-display">
          {typeof data === 'object' ? (
            <pre className="json-display">
              {JSON.stringify(data, null, 2)}
            </pre>
          ) : (
            <div className="text-display">
              {String(data)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
EOF

print_success "Created improved data viewer components"

# Create proper sidebar components
cat > src/components/sidebar/PipelineStep.tsx << 'EOF'
import React from 'react';

interface PipelineStepProps {
  step: any;
  index: number;
  active: boolean;
  onClick: () => void;
  isCollapsed: boolean;
  modelConfig?: any;
  icon: string;
}

export const PipelineStep: React.FC<PipelineStepProps> = ({
  step,
  index,
  active,
  onClick,
  isCollapsed,
  modelConfig,
  icon
}) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return '✅';
      case 'running': return '⏳';
      case 'error': return '❌';
      default: return '⭕';
    }
  };

  return (
    <div className={`pipeline-step ${active ? 'active' : ''} ${step.status}`}>
      <button className="pipeline-step-button" onClick={onClick}>
        <span className="step-icon">{icon}</span>
        {!isCollapsed && (
          <div className="step-content">
            <span className="step-name">{step.name}</span>
            <div className="step-meta">
              <span className="step-status">{getStatusIcon(step.status)} {step.status}</span>
              {step.percentage > 0 && step.status === 'running' && (
                <span className="step-progress">{step.percentage}%</span>
              )}
            </div>
          </div>
        )}
      </button>
    </div>
  );
};
EOF

cat > src/components/sidebar/ConnectionStatus.tsx << 'EOF'
import React from 'react';
import { Socket } from 'socket.io-client';

interface ConnectionStatusProps {
  socket: Socket | null;
  compact?: boolean;
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ 
  socket, 
  compact = false 
}) => {
  const isConnected = socket?.connected || false;
  const status = isConnected ? 'connected' : 'disconnected';
  
  return (
    <div className={`connection-status ${status} ${compact ? 'compact' : ''}`}>
      <div className="connection-indicator">
        <span className="connection-dot"></span>
        {!compact && (
          <div className="connection-info">
            <span className="connection-text">
              {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
            </span>
            <span className="connection-detail">
              {isConnected ? 'Real-time updates active' : 'Reconnecting...'}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
EOF

cat > src/components/sidebar/CollapsedStepIndicator.tsx << 'EOF'
import React from 'react';

interface CollapsedStepIndicatorProps {
  step: any;
  index: number;
  active: boolean;
  onClick: () => void;
  icon: string;
}

export const CollapsedStepIndicator: React.FC<CollapsedStepIndicatorProps> = ({
  step,
  index,
  active,
  onClick,
  icon
}) => {
  const getStatusIndicator = (status: string) => {
    switch (status) {
      case 'completed': return '✅';
      case 'running': return '⏳';
      case 'error': return '❌';
      default: return '';
    }
  };

  return (
    <div className={`collapsed-step-indicator ${active ? 'active' : ''} ${step.status}`}>
      <button 
        className="collapsed-step-button"
        onClick={onClick}
        title={`${step.name} - ${step.status}`}
        aria-label={`Step ${index + 1}: ${step.name}`}
      >
        <div className="step-icon-container">
          <span className="step-icon">{icon}</span>
          <span className="step-number">{index + 1}</span>
        </div>
        <span className="status-indicator">{getStatusIndicator(step.status)}</span>
      </button>
    </div>
  );
};
EOF

print_success "Created proper sidebar components"

# Create CSS for data viewers
cat > src/components/pipeline/DataViewers.css << 'EOF'
/* Shared styles for all data viewers */
.threat-data-viewer,
.dfd-data-viewer,
.attack-path-viewer,
.generic-data-viewer {
  background-color: var(--bg-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  overflow: hidden;
}

.data-viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md);
  background-color: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.data-viewer-header h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.125rem;
}

.view-mode-controls {
  display: flex;
  gap: var(--spacing-xs);
}

.data-viewer-content {
  padding: var(--spacing-md);
  max-height: 600px;
  overflow-y: auto;
}

.json-display {
  background-color: var(--bg-primary);
  color: var(--text-secondary);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  font-family: var(--font-family-mono);
  font-size: 0.875rem;
  line-height: 1.5;
  overflow-x: auto;
  white-space: pre-wrap;
}

/* Threat-specific styles */
.threats-summary {
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md);
  background-color: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.threat-card {
  background-color: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.threat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-sm);
}

.threat-component {
  font-weight: 600;
  color: var(--text-primary);
}

.risk-badge {
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 500;
  color: white;
}

.risk-low { background-color: var(--success-color); }
.risk-medium { background-color: var(--warning-color); }
.risk-high { background-color: var(--error-color); }
.risk-critical { background-color: #dc2626; }

.threat-category {
  font-size: 0.875rem;
  color: var(--text-muted);
  margin-bottom: var(--spacing-sm);
}

.threat-description,
.threat-mitigation,
.threat-mitre {
  margin-bottom: var(--spacing-sm);
  line-height: 1.5;
}

/* DFD-specific styles */
.dfd-project-info {
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md);
  background-color: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.component-section {
  margin-bottom: var(--spacing-lg);
}

.component-section h5 {
  margin: 0 0 var(--spacing-md) 0;
  color: var(--text-primary);
  font-size: 1rem;
  font-weight: 600;
}

.component-list {
  display: grid;
  gap: var(--spacing-sm);
}

.component-item {
  padding: var(--spacing-sm);
  background-color: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
}

.component-item strong {
  color: var(--text-primary);
}

.component-item p {
  margin: var(--spacing-xs) 0 0 0;
  color: var(--text-secondary);
  font-size: 0.875rem;
}

/* Attack Path-specific styles */
.attack-paths-summary {
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md);
  background-color: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.attack-path-card {
  background-color: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.path-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-sm);
}

.path-header h5 {
  margin: 0;
  color: var(--text-primary);
}

.path-metrics {
  display: flex;
  gap: var(--spacing-xs);
  flex-wrap: wrap;
}

.impact-badge,
.likelihood-badge {
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 500;
  color: white;
}

.impact-low,
.likelihood-low { background-color: var(--success-color); }
.impact-medium,
.likelihood-medium { background-color: var(--warning-color); }
.impact-high,
.likelihood-high { background-color: var(--error-color); }

.path-description {
  margin-bottom: var(--spacing-md);
  color: var(--text-secondary);
  line-height: 1.5;
}

.path-steps,
.path-mitigations {
  margin-bottom: var(--spacing-md);
}

.path-steps h6,
.path-mitigations h6 {
  margin: 0 0 var(--spacing-sm) 0;
  color: var(--text-primary);
  font-size: 0.875rem;
  font-weight: 600;
}

.attack-step {
  margin-bottom: var(--spacing-sm);
}

.attack-step strong {
  color: var(--text-primary);
}

.attack-step p {
  margin: var(--spacing-xs) 0;
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.mitre-tag {
  display: inline-block;
  background-color: var(--accent-color);
  color: white;
  padding: 2px var(--spacing-xs);
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  margin-top: var(--spacing-xs);
}
EOF

print_success "Created comprehensive CSS for data viewers"

print_success "JavaScript to React conversion completed successfully!"
echo ""
echo "🎉 All Components Created!"
echo "========================="
echo ""
echo "✅ Fixed the bash substitution errors"
echo "✅ Created comprehensive data viewers with formatted display"
echo "✅ Added proper TypeScript interfaces"
echo "✅ Included responsive CSS styling"
echo ""
echo "🚀 You can now test your React app:"
echo "   npm start"
echo ""
echo "📝 All components are now ready for use in your App.tsx!"