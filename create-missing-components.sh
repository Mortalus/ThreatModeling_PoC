#!/bin/bash

echo "Creating missing viewer components..."

# Create FileUpload component if it doesn't exist
cat > src/components/pipeline/FileUpload.tsx << 'EOF'
import React, { useState, useRef, DragEvent } from 'react';
import './FileUpload.css';

interface FileUploadProps {
  onUpload: (file: File) => void;
  acceptedTypes?: string[];
  maxSize?: number;
  multiple?: boolean;
  disabled?: boolean;
  dragAndDrop?: boolean;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onUpload,
  acceptedTypes = ['.pdf', '.docx', '.txt'],
  maxSize = 10 * 1024 * 1024, // 10MB
  disabled = false,
  dragAndDrop = true
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    const extension = '.' + file.name.split('.').pop()?.toLowerCase();
    
    if (acceptedTypes.length > 0 && !acceptedTypes.includes(extension)) {
      return `File type not supported. Please use: ${acceptedTypes.join(', ')}`;
    }
    
    if (maxSize && file.size > maxSize) {
      return `File too large. Maximum size: ${Math.round(maxSize / 1024 / 1024)}MB`;
    }
    
    return null;
  };

  const handleFile = (file: File) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }
    
    setError(null);
    onUpload(file);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (disabled) return;
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!disabled && dragAndDrop) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleClick = () => {
    if (!disabled && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  return (
    <div 
      className={`file-upload ${isDragging ? 'dragging' : ''} ${disabled ? 'disabled' : ''}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={handleClick}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept={acceptedTypes.join(',')}
        onChange={handleFileSelect}
        disabled={disabled}
        style={{ display: 'none' }}
      />
      
      <div className="upload-icon">📄</div>
      <h3 className="upload-title">
        {dragAndDrop ? 'Drop your file here' : 'Upload a file'}
      </h3>
      <p className="upload-subtitle">
        or <span className="upload-link">browse</span> to choose a file
      </p>
      <p className="upload-hint">
        Supported formats: {acceptedTypes.join(', ')} (max {Math.round(maxSize / 1024 / 1024)}MB)
      </p>
      
      {error && (
        <div className="upload-error">
          ⚠️ {error}
        </div>
      )}
    </div>
  );
};
EOF

# Create FileUpload CSS
cat > src/components/pipeline/FileUpload.css << 'EOF'
.file-upload {
  border: 2px dashed var(--border-color);
  border-radius: 1rem;
  padding: 3rem 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background-color: var(--bg-surface);
}

.file-upload:hover:not(.disabled) {
  border-color: var(--accent-color);
  background-color: rgba(59, 130, 246, 0.05);
}

.file-upload.dragging {
  border-color: var(--accent-color);
  background-color: rgba(59, 130, 246, 0.1);
  transform: scale(1.02);
}

.file-upload.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.upload-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.upload-title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0 0 0.5rem 0;
  color: var(--text-primary);
}

.upload-subtitle {
  color: var(--text-secondary);
  margin: 0 0 1rem 0;
}

.upload-link {
  color: var(--accent-color);
  text-decoration: underline;
}

.upload-hint {
  font-size: 0.875rem;
  color: var(--text-muted);
  margin: 0;
}

.upload-error {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background-color: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--error-color);
  border-radius: 0.5rem;
  color: var(--error-color);
  font-size: 0.875rem;
}
EOF

# Create stub components for missing viewers
mkdir -p src/components/pipeline

# ThreatDataViewer stub
cat > src/components/pipeline/ThreatDataViewer.tsx << 'EOF'
import React from 'react';

export const ThreatDataViewer: React.FC<any> = ({ data }) => {
  return (
    <div className="threat-data-viewer">
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
};
EOF

# DFDDataViewer stub
cat > src/components/pipeline/DFDDataViewer.tsx << 'EOF'
import React from 'react';

export const DFDDataViewer: React.FC<any> = ({ data }) => {
  return (
    <div className="dfd-data-viewer">
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
};
EOF

# AttackPathViewer stub
cat > src/components/pipeline/AttackPathViewer.tsx << 'EOF'
import React from 'react';

export const AttackPathViewer: React.FC<any> = ({ data }) => {
  return (
    <div className="attack-path-viewer">
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
};
EOF

# GenericDataViewer stub
cat > src/components/pipeline/GenericDataViewer.tsx << 'EOF'
import React from 'react';

export const GenericDataViewer: React.FC<any> = ({ data }) => {
  return (
    <div className="generic-data-viewer">
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
};
EOF

echo "All missing components created!"
echo ""
echo "Run these scripts in order:"
echo "1. bash fix-step-content-display.sh"
echo "2. bash create-missing-components.sh"
echo ""
echo "Then run 'npm start' and the app should work properly!"