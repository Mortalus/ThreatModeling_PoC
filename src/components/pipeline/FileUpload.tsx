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
