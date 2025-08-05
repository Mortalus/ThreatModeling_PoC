import React from 'react';

export const DFDDataViewer: React.FC<any> = ({ data }) => {
  return (
    <div className="dfd-data-viewer">
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
};
