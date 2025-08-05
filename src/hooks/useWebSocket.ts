import { useEffect, useState, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';

interface UseWebSocketReturn {
  socket: Socket | null;
  connectionStatus: 'connected' | 'disconnected' | 'connecting';
  isConnected: boolean;
  sendMessage: (type: string, data: any) => void;
}

export const useWebSocket = (): UseWebSocketReturn => {
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'connecting'>('disconnected');
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:5000';
    
    setConnectionStatus('connecting');
    const socket = io(wsUrl);
    socketRef.current = socket;

    socket.on('connect', () => {
      setConnectionStatus('connected');
    });

    socket.on('disconnect', () => {
      setConnectionStatus('disconnected');
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  const sendMessage = useCallback((type: string, data: any) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit(type, data);
    }
  }, []);

  return {
    socket: socketRef.current,
    connectionStatus,
    isConnected: connectionStatus === 'connected',
    sendMessage
  };
};
