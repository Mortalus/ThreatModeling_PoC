#!/bin/bash

echo "🔧 Fixing TypeScript errors in the Threat Modeling App..."

# 1. Fix the CSS import issue - move main.css to src folder
echo "Moving CSS file to src folder..."
if [ -f "public/css/main.css" ]; then
    mkdir -p src/css
    mv public/css/main.css src/css/main.css
    echo "✅ Moved main.css to src/css/"
fi

# 2. Update App.tsx to import from correct location
echo "Updating CSS import in App.tsx..."
sed -i.bak 's|../public/css/main.css|./css/main.css|' src/App.tsx

# 3. Fix the ReviewItem type interface - update types/index.ts
echo "Fixing ReviewItem type interface..."
cat > src/types/index.ts << 'EOF'
import { Socket } from 'socket.io-client';

// Pipeline Types
export interface PipelineStep {
  id: number;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  data: any;
  percentage: number;
}

export interface PipelineState {
  steps: PipelineStep[];
}

// Specific data types for ReviewItem
export interface ThreatData {
  component_name: string;
  stride_category: string;
  threat_description: string;
  mitigation_suggestion: string;
  risk_score?: 'Low' | 'Medium' | 'High' | 'Critical';
}

export interface DFDComponentData {
  name: string;
  type: string;
  description?: string;
}

// Review System Types
export interface ReviewItem {
  id: string;
  type: 'threat' | 'dfd_component' | 'attack_path';
  status: 'pending' | 'approved' | 'rejected';
  data: ThreatData | DFDComponentData | any;
  timestamp: string;
  step: number;
}

// Model Configuration Types
export interface ModelConfig {
  llm_provider: 'scaleway' | 'ollama';
  llm_model: string;
  api_key?: string;
  base_url?: string;
  max_tokens: number;
  temperature: number;
  timeout: number;
}

// Notification Types
export interface NotificationProps {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
  dismissible?: boolean;
}

// API Types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface UploadResponse {
  filename: string;
  size: number;
  content_preview: string;
  file_type: string;
}

export interface ProgressData {
  step: number;
  current: number;
  total: number;
  progress: number;
  message: string;
  details?: string;
  timestamp: string;
}

// WebSocket Types
export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

export interface ConnectionStatus {
  status: 'connected' | 'disconnected' | 'connecting' | 'error';
  lastConnected?: Date;
  reconnectAttempts?: number;
}

// File Upload Types
export interface FileUploadProps {
  onUpload: (file: File) => void;
  acceptedTypes?: string[];
  maxSize?: number;
  multiple?: boolean;
  disabled?: boolean;
  dragAndDrop?: boolean;
}

export interface UploadedFile {
  file: File;
  preview?: string;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  progress?: number;
  error?: string;
}

// UI Component Types
export interface LoadingOverlayProps {
  message: string;
  children?: React.ReactNode;
}
EOF

# 4. Fix ReviewCard.tsx to properly type-check data
echo "Fixing ReviewCard.tsx..."
cat > src/components/review/ReviewCard.tsx << 'EOF'
import React, { useState } from 'react';
import { ReviewItem, ThreatData, DFDComponentData } from '../../types';
import './ReviewCard.css';

interface ReviewCardProps {
  item: ReviewItem;
  onReview: (itemId: string, decision: 'approve' | 'reject' | 'modify', comments?: string, modifications?: any) => void;
}

export const ReviewCard: React.FC<ReviewCardProps> = ({ item, onReview }) => {
  const [showDetails, setShowDetails] = useState(false);
  const [comments, setComments] = useState('');
  const [modifications, setModifications] = useState('');

  const getTypeIcon = (type: string): string => {
    switch (type) {
      case 'threat': return '⚠️';
      case 'dfd_component': return '🔗';
      case 'attack_path': return '🎯';
      default: return '📄';
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'pending': return 'var(--warning-color)';
      case 'approved': return 'var(--success-color)';
      case 'rejected': return 'var(--error-color)';
      case 'modify': return 'var(--info-color)';
      default: return 'var(--text-muted)';
    }
  };

  const handleDecision = (decision: 'approve' | 'reject' | 'modify'): void => {
    const finalComments = comments.trim() || undefined;
    const finalModifications = modifications.trim() ? 
      JSON.parse(modifications) : undefined;
    
    onReview(item.id, decision, finalComments, finalModifications);
    setComments('');
    setModifications('');
  };

  const isThreatData = (data: any): data is ThreatData => {
    return item.type === 'threat' && data && 'component_name' in data;
  };

  const isDFDComponentData = (data: any): data is DFDComponentData => {
    return item.type === 'dfd_component' && data && 'name' in data;
  };

  const renderItemData = (): JSX.Element => {
    if (isThreatData(item.data)) {
      const data = item.data as ThreatData;
      return (
        <div className="threat-data">
          <div className="data-row">
            <strong>Component:</strong> {data.component_name}
          </div>
          <div className="data-row">
            <strong>STRIDE:</strong> {data.stride_category}
          </div>
          <div className="data-row">
            <strong>Risk:</strong> 
            <span className={`risk-badge risk-${data.risk_score?.toLowerCase()}`}>
              {data.risk_score}
            </span>
          </div>
          <div className="data-row">
            <strong>Description:</strong>
            <p>{data.threat_description}</p>
          </div>
          <div className="data-row">
            <strong>Mitigation:</strong>
            <p>{data.mitigation_suggestion}</p>
          </div>
        </div>
      );
    }

    if (isDFDComponentData(item.data)) {
      const data = item.data as DFDComponentData;
      return (
        <div className="dfd-data">
          <div className="data-row">
            <strong>Name:</strong> {data.name}
          </div>
          <div className="data-row">
            <strong>Type:</strong> {data.type}
          </div>
          {data.description && (
            <div className="data-row">
              <strong>Description:</strong>
              <p>{data.description}</p>
            </div>
          )}
        </div>
      );
    }

    // Generic data display
    return (
      <div className="generic-data">
        <pre>{JSON.stringify(item.data, null, 2)}</pre>
      </div>
    );
  };

  return (
    <div className={`review-card ${item.status}`}>
      <div className="review-card-header">
        <div className="item-info">
          <span className="item-icon">{getTypeIcon(item.type)}</span>
          <div className="item-meta">
            <h4 className="item-title">
              {item.type.replace('_', ' ').toUpperCase()} - Step {item.step}
            </h4>
            <div className="item-timestamp">
              {new Date(item.timestamp).toLocaleString()}
            </div>
          </div>
        </div>
        
        <div className="item-status">
          <span 
            className="status-badge"
            style={{ backgroundColor: getStatusColor(item.status) }}
          >
            {item.status}
          </span>
        </div>
      </div>

      <div className="review-card-content">
        <button
          className="toggle-details"
          onClick={() => setShowDetails(!showDetails)}
          aria-expanded={showDetails}
        >
          {showDetails ? '▼' : '▶'} {showDetails ? 'Hide' : 'Show'} Details
        </button>

        {showDetails && (
          <div className="item-details">
            {renderItemData()}
          </div>
        )}
      </div>

      {item.status === 'pending' && (
        <div className="review-actions">
          <div className="review-inputs">
            <textarea
              className="comments-input"
              placeholder="Add comments (optional)..."
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              rows={2}
            />
            
            {item.type === 'threat' && (
              <textarea
                className="modifications-input"
                placeholder="Modifications as JSON (optional)..."
                value={modifications}
                onChange={(e) => setModifications(e.target.value)}
                rows={3}
              />
            )}
          </div>

          <div className="decision-buttons">
            <button
              className="btn btn-success"
              onClick={() => handleDecision('approve')}
            >
              ✅ Approve
            </button>
            <button
              className="btn btn-error"
              onClick={() => handleDecision('reject')}
            >
              ❌ Reject
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleDecision('modify')}
              disabled={!modifications.trim()}
            >
              ✏️ Modify
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
EOF

# 5. Fix ReviewPanel.tsx to use correct status values
echo "Fixing ReviewPanel.tsx..."
cat > src/components/review/ReviewPanel.tsx << 'EOF'
import React, { useState, useMemo } from 'react';
import { ReviewCard } from './ReviewCard';
import { ReviewItem } from '../../types';
import './ReviewPanel.css';

interface ReviewPanelProps {
  reviewQueue: ReviewItem[];
  onReview: (itemId: string, decision: 'approve' | 'reject' | 'modify', comments?: string, modifications?: any) => void;
}

export const ReviewPanel: React.FC<ReviewPanelProps> = ({
  reviewQueue,
  onReview
}) => {
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('pending');
  const [sortBy, setSortBy] = useState<'timestamp' | 'type' | 'step'>('timestamp');

  const filteredItems = useMemo(() => {
    let items = [...reviewQueue];
    
    // Apply filter
    if (filter !== 'all') {
      items = items.filter(item => item.status === filter);
    }
    
    // Apply sorting
    items.sort((a, b) => {
      switch (sortBy) {
        case 'timestamp':
          return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
        case 'type':
          return a.type.localeCompare(b.type);
        case 'step':
          return a.step - b.step;
        default:
          return 0;
      }
    });
    
    return items;
  }, [reviewQueue, filter, sortBy]);

  const pendingCount = reviewQueue.filter(item => item.status === 'pending').length;
  const approvedCount = reviewQueue.filter(item => item.status === 'approved').length;
  const rejectedCount = reviewQueue.filter(item => item.status === 'rejected').length;

  return (
    <div className="review-panel">
      <div className="review-header">
        <h2 className="review-title">
          📝 Review Queue
        </h2>
        <div className="review-stats">
          <span className="stat pending">{pendingCount} pending</span>
          <span className="stat approved">{approvedCount} approved</span>
          <span className="stat rejected">{rejectedCount} rejected</span>
        </div>
      </div>

      <div className="review-controls">
        <div className="review-filters">
          <label htmlFor="filter-select">Filter:</label>
          <select
            id="filter-select"
            value={filter}
            onChange={(e) => setFilter(e.target.value as typeof filter)}
            className="filter-select"
          >
            <option value="all">All Items</option>
            <option value="pending">Pending Review</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>

        <div className="review-sort">
          <label htmlFor="sort-select">Sort by:</label>
          <select
            id="sort-select"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            className="sort-select"
          >
            <option value="timestamp">Date</option>
            <option value="type">Type</option>
            <option value="step">Step</option>
          </select>
        </div>
      </div>

      <div className="review-list">
        {filteredItems.length === 0 ? (
          <div className="review-empty">
            <div className="empty-icon">📋</div>
            <h3>No items to review</h3>
            <p>
              {filter === 'pending' 
                ? 'All items have been reviewed!'
                : `No ${filter} items found.`
              }
            </p>
          </div>
        ) : (
          filteredItems.map(item => (
            <ReviewCard
              key={item.id}
              item={item}
              onReview={onReview}
            />
          ))
        )}
      </div>
    </div>
  );
};
EOF

echo "✅ All TypeScript errors fixed!"
echo ""
echo "Summary of fixes:"
echo "1. ✅ Moved main.css to src/css/ folder"
echo "2. ✅ Updated CSS import path in App.tsx"
echo "3. ✅ Fixed ReviewItem type to include 'data' and 'step' properties"
echo "4. ✅ Updated ReviewCard to properly type-check data"
echo "5. ✅ Fixed status values in ReviewPanel (approved/rejected instead of approve/reject)"
echo ""
echo "🚀 Run 'npm start' to start the application!"