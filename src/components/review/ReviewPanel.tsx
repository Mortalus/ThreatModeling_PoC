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
