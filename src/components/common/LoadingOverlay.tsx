import React from 'react';
import { LoadingOverlayProps } from '../../types';
import './LoadingOverlay.css';

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({ 
  message, 
  children 
}) => {
  return (
    <div className="loading-overlay" role="dialog" aria-label="Loading">
      <div className="loading-content">
        <div className="loading-spinner" aria-hidden="true">
          <div className="spinner-ring"></div>
          <div className="spinner-ring"></div>
          <div className="spinner-ring"></div>
        </div>
        
        <div className="loading-message">
          {message}
        </div>
        
        {children && (
          <div className="loading-additional-content">
            {children}
          </div>
        )}
      </div>
    </div>
  );
};
