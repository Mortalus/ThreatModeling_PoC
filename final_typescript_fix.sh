#!/bin/bash

echo "🔧 Fixing final TypeScript error (null vs undefined)..."

# Fix the ProgressDisplay component to accept null
cat > src/components/common/ProgressDisplay.tsx << 'EOF'
import React from 'react';
import { PipelineStep } from '../../types';
import './ProgressDisplay.css';

interface ProgressDisplayProps {
  step?: PipelineStep | null;
}

export const ProgressDisplay: React.FC<ProgressDisplayProps> = ({ step }) => {
  if (!step || step.status !== 'running') {
    return null;
  }

  return (
    <div className="progress-display">
      <div className="progress-header">
        <h4 className="progress-title">
          Processing: {step.name}
        </h4>
        <span className="progress-percentage">
          {step.percentage}%
        </span>
      </div>
      
      <div className="progress-bar-container">
        <div 
          className="progress-bar-fill"
          style={{ width: `${step.percentage}%` }}
        />
      </div>
      
      {step.data?.message && (
        <div className="progress-message">
          {step.data.message}
        </div>
      )}
    </div>
  );
};
EOF

# Also fix the LoadingOverlay component to accept null
cat > src/components/common/LoadingOverlay.tsx << 'EOF'
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
EOF

# Create the CSS for ProgressDisplay if it doesn't exist
cat > src/components/common/ProgressDisplay.css << 'EOF'
.progress-display {
  position: fixed;
  bottom: 20px;
  right: 20px;
  background-color: var(--bg-surface, #1e293b);
  border: 1px solid var(--border-color, #334155);
  border-radius: 12px;
  padding: 1rem;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  min-width: 300px;
  z-index: 1080;
  animation: slideInUp 0.3s ease-out;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.progress-title {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary, #f8fafc);
}

.progress-percentage {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--accent-color, #3b82f6);
}

.progress-bar-container {
  width: 100%;
  height: 8px;
  background-color: var(--bg-tertiary, #334155);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 0.75rem;
}

.progress-bar-fill {
  height: 100%;
  background-color: var(--accent-color, #3b82f6);
  transition: width 0.3s ease;
  border-radius: 4px;
}

.progress-message {
  font-size: 0.75rem;
  color: var(--text-muted, #94a3b8);
  margin-top: 0.5rem;
}

@keyframes slideInUp {
  from {
    transform: translateY(100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}
EOF

# Create LoadingOverlay CSS if it doesn't exist
cat > src/components/common/LoadingOverlay.css << 'EOF'
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(10, 14, 26, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1050;
  backdrop-filter: blur(4px);
}

.loading-content {
  background-color: var(--bg-surface, #1e293b);
  padding: 2rem;
  border-radius: 12px;
  border: 1px solid var(--border-color, #334155);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  text-align: center;
  max-width: 400px;
  width: 90%;
}

.loading-spinner {
  display: inline-block;
  position: relative;
  width: 64px;
  height: 64px;
  margin-bottom: 1rem;
}

.spinner-ring {
  box-sizing: border-box;
  display: block;
  position: absolute;
  width: 51px;
  height: 51px;
  margin: 6px;
  border: 6px solid var(--accent-color, #3b82f6);
  border-radius: 50%;
  animation: spinner-ring 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
  border-color: var(--accent-color, #3b82f6) transparent transparent transparent;
}

.spinner-ring:nth-child(1) { animation-delay: -0.45s; }
.spinner-ring:nth-child(2) { animation-delay: -0.3s; }
.spinner-ring:nth-child(3) { animation-delay: -0.15s; }

@keyframes spinner-ring {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.loading-message {
  font-size: 1.125rem;
  font-weight: 500;
  color: var(--text-primary, #f8fafc);
  margin-bottom: 1rem;
}

.loading-additional-content {
  color: var(--text-secondary, #cbd5e1);
  font-size: 0.875rem;
}

.loading-details {
  margin-top: 1rem;
}

.current-step-info {
  margin-bottom: 0.5rem;
  color: var(--text-secondary, #cbd5e1);
}

.loading-progress {
  margin: 0.75rem 0;
  height: 4px;
  background-color: var(--bg-tertiary, #334155);
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background-color: var(--accent-color, #3b82f6);
  transition: width 0.3s ease;
  border-radius: 2px;
}

.loading-hint {
  margin-top: 0.75rem;
  color: var(--text-muted, #94a3b8);
}
EOF

echo "✅ Fixed ProgressDisplay to accept null"
echo "✅ Updated LoadingOverlay component"
echo "✅ Created CSS files for components"
echo ""
echo "🚀 TypeScript error should be resolved now!"
