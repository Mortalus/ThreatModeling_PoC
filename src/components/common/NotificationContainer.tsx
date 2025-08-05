import React from 'react';
import { NotificationProps } from '../../types';
import './NotificationContainer.css';

interface NotificationContainerProps {
  notifications: NotificationProps[];
  onDismiss: (id: string) => void;
}

export const NotificationContainer: React.FC<NotificationContainerProps> = ({
  notifications,
  onDismiss
}) => {
  return (
    <div className="notification-container">
      {notifications.map(notification => (
        <div 
          key={notification.id}
          className={`notification ${notification.type}`}
        >
          <div className="notification-icon">
            {notification.type === 'success' && '✅'}
            {notification.type === 'error' && '❌'}
            {notification.type === 'warning' && '⚠️'}
            {notification.type === 'info' && 'ℹ️'}
          </div>
          <div className="notification-content">
            <p className="notification-message">{notification.message}</p>
          </div>
          {notification.dismissible && (
            <button 
              className="notification-close"
              onClick={() => onDismiss(notification.id)}
            >
              ×
            </button>
          )}
        </div>
      ))}
    </div>
  );
};
