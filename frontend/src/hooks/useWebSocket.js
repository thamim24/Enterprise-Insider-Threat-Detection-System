/**
 * WebSocket Hook - Real-Time Updates
 * 
 * Connects to backend WebSocket for live dashboard updates.
 * Automatically reconnects on disconnect.
 * 
 * Usage:
 *   const { messages, sendMessage, isConnected } = useWebSocket();
 */
import { useState, useEffect, useRef, useCallback } from 'react';

const WS_URL = 'ws://localhost:8000/ws/admin';
const RECONNECT_DELAY = 3000; // 3 seconds
const MAX_RECONNECT_ATTEMPTS = 10;

export const useWebSocket = (onMessage = null) => {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [connectionError, setConnectionError] = useState(null);
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const shouldReconnectRef = useRef(true);
  const reconnectAttemptsRef = useRef(0);
  const onMessageRef = useRef(onMessage);

  // Keep onMessage ref updated
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const connect = useCallback(() => {
    // Clear any existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    try {
      // Get token from localStorage
      const token = localStorage.getItem('access_token');
      
      if (!token) {
        console.error('No authentication token found');
        setConnectionError('Authentication required');
        return;
      }

      console.log('📡 Connecting to WebSocket...');

      // Create WebSocket connection with token
      const ws = new WebSocket(`${WS_URL}?token=${token}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('✅ WebSocket connected');
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttemptsRef.current = 0;

        // Send connection confirmation
        ws.send(JSON.stringify({
          type: 'subscribe',
          channels: ['all']
        }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('📨 WebSocket message:', data);

          // Add to messages array
          setMessages(prev => [...prev, data]);

          // Call custom message handler if provided
          if (onMessageRef.current) {
            onMessageRef.current(data);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        setConnectionError('Connection error');
      };

      ws.onclose = (event) => {
        console.log('🔌 WebSocket closed:', event.code, event.reason);
        setIsConnected(false);
        wsRef.current = null;

        // Attempt reconnection if not manually closed and within retry limit
        if (shouldReconnectRef.current && reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current += 1;
          console.log(`🔄 Reconnecting in ${RECONNECT_DELAY}ms... (attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, RECONNECT_DELAY);
        } else if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
          console.error('❌ Max reconnection attempts reached');
          setConnectionError('Failed to connect after multiple attempts');
        }
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionError(error.message);
    }
  }, []); // Empty dependencies - stable reference

  const disconnect = useCallback(() => {
    console.log('🛑 Disconnecting WebSocket...');
    shouldReconnectRef.current = false;
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsConnected(false);
  }, []);

  const sendMessage = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    console.warn('WebSocket not connected, cannot send message');
    return false;
  }, []);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    shouldReconnectRef.current = true;
    reconnectAttemptsRef.current = 0;
    connect();

    // Cleanup on unmount
    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []); // Only run once on mount

  // Ping/pong for keep-alive (every 30 seconds)
  useEffect(() => {
    if (!isConnected) return;

    const pingInterval = setInterval(() => {
      sendMessage({
        type: 'ping',
        timestamp: new Date().toISOString()
      });
    }, 30000);

    return () => clearInterval(pingInterval);
  }, [isConnected, sendMessage]);

  return {
    isConnected,
    messages,
    sendMessage,
    connectionError,
    reconnectAttempts: reconnectAttemptsRef.current,
    clearMessages: () => setMessages([])
  };
};


/**
 * Hook for handling specific message types
 */
export const useWebSocketMessages = (messageType) => {
  const [filteredMessages, setFilteredMessages] = useState([]);

  const handleMessage = useCallback((message) => {
    if (message.type === messageType) {
      setFilteredMessages(prev => [...prev, message]);
    }
  }, [messageType]);

  const { isConnected, connectionError } = useWebSocket(handleMessage);

  return {
    messages: filteredMessages,
    isConnected,
    connectionError,
    clearMessages: () => setFilteredMessages([])
  };
};

export default useWebSocket;
