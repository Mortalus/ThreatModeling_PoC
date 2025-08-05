import React, { useEffect, useRef } from 'react';
import { useNotifications } from '../../context/NotificationContext';
import { NotificationProps } from '../../types';
import './NotificationContainer.css';

interface NotificationItemProps {
  notification: NotificationProps;
  onRemove: (id: string) => void;
}

const NotificationItem: React.FC<NotificationItemProps> = ({ notification, onRemove }) => {
  const progressRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Get notification styling based on type
  const getNotificationIcon = (type: NotificationProps['type']): string => {
    switch (type) {
      case 'success': return '✅';
      case 'error': return '❌';
      case 'warning': return '⚠️';
      case 'info': return 'ℹ️';
      default: return 'ℹ️';
    }
  };

  const getNotificationColor = (type: NotificationProps['type']): string => {
    switch (type) {
      case 'success': return '#10b981';
      case 'error': return '#ef4444';
      case 'warning': return '#f59e0b';
      case 'info': return '#3b82f6';
      default: return '#6b7280';
    }
  };

  // Auto-dismiss progress bar animation
  useEffect(() => {
    if (!notification.duration || notification.duration <= 0) return;

    const progressBar = progressRef.current;
    if (!progressBar) return;

    // Animate progress bar
    progressBar.style.transition = `width ${notification.duration}ms linear`;
    progressBar.style.width = '0%';

    // Set timeout for removal
    timeoutRef.current = setTimeout(() => {
      onRemove(notification.id);
    }, notification.duration);

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [notification.duration, notification.id, onRemove]);

  // Handle manual dismiss
  const handleDismiss = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    
    onRemove(notification.id);
  };

  // Handle keyboard dismiss
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleDismiss(e as any);
    }
  };

  const notificationClass = `notification notification-${notification.type}`;
  const progressColor = getNotificationColor(notification.type);

  return (
    <div
      className={notificationClass}
      role="alert"
      aria-live={notification.type === 'error' ? 'assertive' : 'polite'}
      style={{ '--notification-color': progressColor } as React.CSSProperties}
    >
      <div className="notification-content">
        <div className="notification-icon" aria-hidden="true">
          {getNotificationIcon(notification.type)}
        </div>
        
        <div className="notification-message">
          {notification.message}
        </div>
        
        {notification.dismissible && (
          <button
            className="notification-dismiss"
            onClick={handleDismiss}
            onKeyDown={handleKeyDown}
            aria-label="Dismiss notification"
            title="Dismiss (or click anywhere)"
            type="button"
          >
            ×
          </button>
        )}
      </div>
      
      {notification.duration && notification.duration > 0 && (
        <div className="notification-progress">
          <div
            ref={progressRef}
            className="notification-progress-bar"
            style={{ backgroundColor: progressColor }}
          />
        </div>
      )}
    </div>
  );
};

export const NotificationContainer: React.FC = () => {
  const { notifications, removeNotification } = useNotifications();
  const containerRef = useRef<HTMLDivElement>(null);

  // Handle global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Clear all notifications with Escape key
      if (e.key === 'Escape' && notifications.length > 0) {
        notifications.forEach(notification => {
          removeNotification(notification.id);
        });
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [notifications, removeNotification]);

  // Auto-scroll to show new notifications
  useEffect(() => {
    if (containerRef.current && notifications.length > 0) {
      const container = containerRef.current;
      const lastNotification = container.lastElementChild as HTMLElement;
      
      if (lastNotification) {
        lastNotification.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'nearest' 
        });
      }
    }
  }, [notifications.length]);

  // Announce new notifications to screen readers
  useEffect(() => {
    if (notifications.length === 0) return;
    
    const latestNotification = notifications[notifications.length - 1];
    
    // Create and insert announcement element
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', 'polite');
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = `${latestNotification.type}: ${latestNotification.message}`;
    
    document.body.appendChild(announcement);
    
    // Clean up after announcement
    setTimeout(() => {
      if (document.body.contains(announcement)) {
        document.body.removeChild(announcement);
      }
    }, 1000);
  }, [notifications]);

  if (notifications.length === 0) {
    return null;
  }

  return (
    <div 
      ref={containerRef}
      className="notification-container"
      role="region"
      aria-label="Notifications"
      aria-live="polite"
    >
      {notifications.map((notification) => (
        <NotificationItem
          key={notification.id}
          notification={notification}
          onRemove={removeNotification}
        />
      ))}
      
      {notifications.length > 1 && (
        <div className="notification-summary">
          <small className="text-muted">
            {notifications.length} active notifications • Press Escape to clear all
          </small>
        </div>
      )}
    </div>
  );
};