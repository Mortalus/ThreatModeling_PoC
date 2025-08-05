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
