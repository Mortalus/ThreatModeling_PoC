import React from 'react';
import { Socket } from 'socket.io-client';

interface ConnectionStatusProps {
  socket: Socket | null;
  compact?: boolean;
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ 
  socket, 
  compact = false 
}) => {
  const isConnected = socket?.connected || false;
  const status = isConnected ? 'connected' : 'disconnected';
  
  return (
    <div className={`connection-status ${status} ${compact ? 'compact' : ''}`}>
      <div className="connection-indicator">
        <span className="connection-dot"></span>
        {!compact && (
          <div className="connection-info">
            <span className="connection-text">
              {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
            </span>
            <span className="connection-detail">
              {isConnected ? 'Real-time updates active' : 'Reconnecting...'}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
