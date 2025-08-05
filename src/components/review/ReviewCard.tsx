import React, { useState } from 'react';
import { ReviewItem } from '../../types';
import './ReviewCard.css';

interface ReviewCardProps {
  item: ReviewItem;
  onReview: (itemId: string, decision: 'approve' | 'reject' | 'modify', comments?: string, modifications?: any) => void;
}

export const ReviewCard: React.FC<ReviewCardProps> = ({ item, onReview }) => {
  const [showDetails, setShowDetails] = useState(false);
  const [comments, setComments] = useState('');
  const [modifications, setModifications] = useState('');

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'threat': return '⚠️';
      case 'dfd_component': return '🔗';
      case 'attack_path': return '🎯';
      default: return '📄';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'var(--warning-color)';
      case 'approve': return 'var(--success-color)';
      case 'reject': return 'var(--error-color)';
      case 'modify': return 'var(--info-color)';
      default: return 'var(--text-muted)';
    }
  };

  const handleDecision = (decision: 'approve' | 'reject' | 'modify') => {
    const finalComments = comments.trim() || undefined;
    const finalModifications = modifications.trim() ? JSON.parse(modifications) : undefined;
    
    onReview(item.id, decision, finalComments, finalModifications);
    setComments('');
    setModifications('');
  };

  const renderItemData = () => {
    if (item.type === 'threat' && item.data) {
      return (
        <div className="threat-data">
          <div className="data-row">
            <strong>Component:</strong> {item.data.component_name}
          </div>
          <div className="data-row">
            <strong>STRIDE:</strong> {item.data.stride_category}
          </div>
          <div className="data-row">
            <strong>Risk:</strong> 
            <span className={`risk-badge risk-${item.data.risk_score?.toLowerCase()}`}>
              {item.data.risk_score}
            </span>
          </div>
          <div className="data-row">
            <strong>Description:</strong>
            <p>{item.data.threat_description}</p>
          </div>
          <div className="data-row">
            <strong>Mitigation:</strong>
            <p>{item.data.mitigation_suggestion}</p>
          </div>
        </div>
      );
    }

    if (item.type === 'dfd_component' && item.data) {
      return (
        <div className="dfd-data">
          <div className="data-row">
            <strong>Name:</strong> {item.data.name}
          </div>
          <div className="data-row">
            <strong>Type:</strong> {item.data.type}
          </div>
          {item.data.description && (
            <div className="data-row">
              <strong>Description:</strong>
              <p>{item.data.description}</p>
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
