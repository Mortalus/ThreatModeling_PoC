import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { NotificationProps } from '../types';

// Generate unique IDs
const generateId = (): string => {
  return `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

// Default notification duration by type
const DEFAULT_DURATIONS = {
  success: 4000,
  info: 5000,
  warning: 6000,
  error: 8000
};

interface NotificationContextType {
  notifications: NotificationProps[];
  showNotification: (message: string, type: NotificationProps['type'], duration?: number) => string;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  updateNotification: (id: string, updates: Partial<NotificationProps>) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

interface NotificationProviderProps {
  children: ReactNode;
  maxNotifications?: number;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ 
  children, 
  maxNotifications = 5 
}) => {
  const [notifications, setNotifications] = useState<NotificationProps[]>([]);

  const showNotification = useCallback((
    message: string, 
    type: NotificationProps['type'], 
    duration?: number
  ): string => {
    const id = generateId();
    const notificationDuration = duration ?? DEFAULT_DURATIONS[type];
    
    const newNotification: NotificationProps = {
      id,
      type,
      message,
      duration: notificationDuration,
      dismissible: true
    };

    setNotifications(prev => {
      // Remove oldest notifications if we exceed the limit
      const updated = [...prev, newNotification];
      return updated.length > maxNotifications 
        ? updated.slice(-maxNotifications)
        : updated;
    });

    // Auto-dismiss after duration
    if (notificationDuration > 0) {
      setTimeout(() => {
        removeNotification(id);
      }, notificationDuration);
    }

    return id;
  }, [maxNotifications]);

  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(notification => notification.id !== id));
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  const updateNotification = useCallback((id: string, updates: Partial<NotificationProps>) => {
    setNotifications(prev => 
      prev.map(notification => 
        notification.id === id 
          ? { ...notification, ...updates }
          : notification
      )
    );
  }, []);

  const contextValue: NotificationContextType = {
    notifications,
    showNotification,
    removeNotification,
    clearNotifications,
    updateNotification
  };

  return (
    <NotificationContext.Provider value={contextValue}>
      {children}
    </NotificationContext.Provider>
  );
};

export const useNotifications = (): NotificationContextType => {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};

// Specialized hooks for common notification patterns
export const useToast = () => {
  const { showNotification } = useNotifications();

  const toast = {
    success: (message: string, duration?: number) => showNotification(message, 'success', duration),
    error: (message: string, duration?: number) => showNotification(message, 'error', duration),
    warning: (message: string, duration?: number) => showNotification(message, 'warning', duration),
    info: (message: string, duration?: number) => showNotification(message, 'info', duration)
  };

  return toast;
};

export const useProgressNotification = () => {
  const { showNotification, updateNotification, removeNotification } = useNotifications();

  const showProgress = useCallback((message: string) => {
    return showNotification(message, 'info', 0); // Persistent notification
  }, [showNotification]);

  const updateProgress = useCallback((id: string, message: string) => {
    updateNotification(id, { message });
  }, [updateNotification]);

  const completeProgress = useCallback((id: string, successMessage: string) => {
    updateNotification(id, { 
      message: successMessage, 
      type: 'success',
      duration: 3000
    });
    
    setTimeout(() => removeNotification(id), 3000);
  }, [updateNotification, removeNotification]);

  const failProgress = useCallback((id: string, errorMessage: string) => {
    updateNotification(id, { 
      message: errorMessage, 
      type: 'error',
      duration: 5000
    });
    
    setTimeout(() => removeNotification(id), 5000);
  }, [updateNotification, removeNotification]);

  return {
    showProgress,
    updateProgress,
    completeProgress,
    failProgress
  };
};