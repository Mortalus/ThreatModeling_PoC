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
