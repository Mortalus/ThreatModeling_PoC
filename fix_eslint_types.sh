#!/bin/bash

echo "🔧 Fixing ESLint config and missing types..."

# 1. Fix ESLint configuration - remove the problematic config
echo "Fixing ESLint configuration..."

# Check if there's a package.json with eslint config inside src/
if [ -f "src/package.json" ]; then
    echo "Removing problematic src/package.json..."
    rm src/package.json
fi

# Update the main package.json to remove problematic ESLint config
cat > package.json << 'EOF'
{
  "name": "threat-model-app",
  "version": "1.0.0",
  "description": "AI-Powered Threat Modeling Pipeline - React Application",
  "private": true,
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "socket.io-client": "^4.7.4",
    "chart.js": "^4.4.0",
    "react-chartjs-2": "^5.2.0",
    "d3": "^7.8.5",
    "mermaid": "^10.6.1",
    "date-fns": "^2.30.0",
    "lodash": "^4.17.21",
    "classnames": "^2.3.2"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@types/node": "^18.19.0",
    "@types/d3": "^7.4.3",
    "@types/lodash": "^4.14.202",
    "typescript": "^4.9.5",
    "react-scripts": "5.0.1",
    "web-vitals": "^3.5.0"
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  },
  "proxy": "http://localhost:5000"
}
EOF

# 2. Create complete types file with all missing types
echo "Creating complete types file..."

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

// Review System Types
export interface ReviewItem {
  id: string;
  type: 'threat' | 'dfd_component' | 'attack_path';
  status: 'pending' | 'approve' | 'reject' | 'modify';
  data: any;
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

// Data Viewer Types
export interface DataViewerProps {
  data: any;
  title?: string;
  viewMode?: 'formatted' | 'json';
  onViewModeChange?: (mode: 'formatted' | 'json') => void;
}

// Threat Modeling Types
export interface Threat {
  id: string;
  component_name: string;
  stride_category: string;
  threat_description: string;
  mitigation_suggestion: string;
  impact: 'Low' | 'Medium' | 'High' | 'Critical';
  likelihood: 'Low' | 'Medium' | 'High' | 'Critical';
  risk_score: 'Low' | 'Medium' | 'High' | 'Critical';
  references: string[];
  mitre_attack?: string[];
  cve_references?: string[];
}

export interface DFDComponent {
  id: string;
  name: string;
  type: 'External Entity' | 'Process' | 'Data Store' | 'Data Flow';
  description?: string;
  trust_boundary?: boolean;
  attributes?: Record<string, any>;
}

export interface AttackPath {
  id: string;
  name: string;
  description: string;
  steps: AttackStep[];
  likelihood: 'Low' | 'Medium' | 'High' | 'Critical';
  impact: 'Low' | 'Medium' | 'High' | 'Critical';
  mitigation_strategies: string[];
}

export interface AttackStep {
  step_number: number;
  technique: string;
  description: string;
  mitre_attack_id?: string;
  prerequisites: string[];
  detection_methods: string[];
}
EOF

# 3. Remove the problematic useWebSockets.ts file if it exists
if [ -f "src/hooks/useWebSockets.ts" ]; then
    echo "Removing problematic useWebSockets.ts..."
    rm src/hooks/useWebSockets.ts
fi

# 4. Update the existing useWebSocket.ts to not import missing types
cat > src/hooks/useWebSocket.ts << 'EOF'
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
EOF

# 5. Fix the FileUpload component to not use the UploadedFile type internally
cat > src/components/pipeline/FileUpload.tsx << 'EOF'
import React, { useCallback, useState, useRef } from 'react';
import { FileUploadProps } from '../../types';
import './FileUpload.css';

export const FileUpload: React.FC<FileUploadProps> = ({
  onUpload,
  acceptedTypes = ['.pdf', '.docx', '.txt'],
  maxSize = 10 * 1024 * 1024, // 10MB
  multiple = false,
  disabled = false,
  dragAndDrop = true
}) => {
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback((files: FileList | null) => {
    if (!files || files.length === 0) return;

    const fileArray = Array.from(files);
    
    // Validate files
    for (const file of fileArray) {
      if (maxSize && file.size > maxSize) {
        console.error(`File ${file.name} is too large`);
        continue;
      }
      
      if (acceptedTypes.length > 0) {
        const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
        if (!acceptedTypes.includes(fileExt)) {
          console.error(`File type ${fileExt} not accepted`);
          continue;
        }
      }
      
      // Upload file
      onUpload(file);
    }
  }, [onUpload, acceptedTypes, maxSize]);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (disabled) return;
    
    const files = e.dataTransfer.files;
    handleFiles(files);
  }, [handleFiles, disabled]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files);
  }, [handleFiles]);

  const openFileDialog = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  return (
    <div className="file-upload-container">
      <div 
        className={`file-upload-area ${dragActive ? 'drag-active' : ''} ${disabled ? 'disabled' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={openFileDialog}
        role="button"
        tabIndex={0}
        aria-label="Upload files"
      >
        <div className="file-upload-content">
          <div className="file-upload-icon">📁</div>
          <div className="file-upload-text">
            <strong>Click to upload</strong> or drag and drop files here
          </div>
          <div className="file-upload-hint">
            Supported formats: {acceptedTypes.join(', ')}
            {maxSize && ` • Max size: ${Math.round(maxSize / 1024 / 1024)}MB`}
          </div>
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        multiple={multiple}
        accept={acceptedTypes.join(',')}
        onChange={handleInputChange}
        style={{ display: 'none' }}
        disabled={disabled}
      />
    </div>
  );
};
EOF

# 6. Create a simple tsconfig.json that works
cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "es5",
    "lib": [
      "dom",
      "dom.iterable",
      "es6"
    ],
    "allowJs": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "noFallthroughCasesInSwitch": true,
    "module": "esnext",
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": [
    "src"
  ]
}
EOF

echo "✅ Fixed ESLint configuration"
echo "✅ Created complete types file with all missing types"
echo "✅ Fixed component imports"
echo "✅ Simplified tsconfig.json"
echo ""
echo "🚀 Try npm start again!"
