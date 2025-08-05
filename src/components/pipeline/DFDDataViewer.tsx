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
