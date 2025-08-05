import React from 'react';

export const GenericDataViewer: React.FC<any> = ({ data }) => {
  return (
    <div className="generic-data-viewer">
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
};
