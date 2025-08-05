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
