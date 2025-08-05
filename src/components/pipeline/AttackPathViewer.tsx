import React from 'react';

export const AttackPathViewer: React.FC<any> = ({ data }) => {
  return (
    <div className="attack-path-viewer">
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
};
