import React from 'react';

export const ThreatDataViewer: React.FC<any> = ({ data }) => {
  return (
    <div className="threat-data-viewer">
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
};
