import React, { useState, useRef, DragEvent } from 'react';
import { Upload, FileText, X, CheckCircle, AlertCircle, File, FileCode, FileImage } from 'lucide-react';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  acceptedFormats?: string[];
  maxSizeMB?: number;
}

const FileUploadComponent: React.FC<FileUploadProps> = ({
  onFileSelect,
  acceptedFormats = ['.pdf', '.docx', '.txt'],
  maxSizeMB = 10
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'pdf': return <FileText size={48} color="#ef4444" />;
      case 'docx': case 'doc': return <FileCode size={48} color="#3b82f6" />;
      case 'txt': return <File size={48} color="#22c55e" />;
      default: return <FileImage size={48} color="#a855f7" />;
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
  };

  const validateFile = (file: File): boolean => {
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
    
    if (!acceptedFormats.includes(fileExt)) {
      setErrorMessage(`Invalid file type. Accepted formats: ${acceptedFormats.join(', ')}`);
      setUploadStatus('error');
      return false;
    }
    
    if (file.size > maxSizeMB * 1024 * 1024) {
      setErrorMessage(`File too large. Maximum size: ${maxSizeMB}MB`);
      setUploadStatus('error');
      return false;
    }
    
    return true;
  };

  const handleFileSelect = (file: File) => {
    if (validateFile(file)) {
      setSelectedFile(file);
      setUploadStatus('success');
      setErrorMessage('');
      onFileSelect(file);
    }
  };

  const handleDragEnter = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const clearFile = () => {
    setSelectedFile(null);
    setUploadStatus('idle');
    setErrorMessage('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(36, 23, 87, 0.3) 0%, rgba(59, 130, 246, 0.1) 100%)',
      backdropFilter: 'blur(20px)',
      borderRadius: '24px',
      border: '1px solid rgba(168, 85, 247, 0.2)',
      boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.37)',
      padding: '2rem',
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Background decoration */}
      <div style={{
        position: 'absolute',
        top: '-150px',
        left: '-150px',
        width: '400px',
        height: '400px',
        background: 'radial-gradient(circle, rgba(168, 85, 247, 0.1) 0%, transparent 70%)',
        borderRadius: '50%',
        filter: 'blur(60px)'
      }} />

      <div style={{ position: 'relative', zIndex: 1 }}>
        <h2 style={{
          margin: '0 0 2rem 0',
          fontSize: '2rem',
          fontWeight: 700,
          textAlign: 'center',
          background: 'linear-gradient(135deg, #a855f7 0%, #3b82f6 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text'
        }}>
          Upload Security Document
        </h2>

        {!selectedFile ? (
          <div
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: `2px dashed ${isDragging ? '#3b82f6' : 'rgba(168, 85, 247, 0.3)'}`,
              borderRadius: '16px',
              padding: '3rem 2rem',
              textAlign: 'center',
              background: isDragging ? 'rgba(59, 130, 246, 0.1)' : 'rgba(36, 23, 87, 0.4)',
              transition: 'all 0.3s ease',
              cursor: 'pointer',
              position: 'relative',
              overflow: 'hidden',
              transform: isDragging ? 'scale(1.02)' : 'scale(1)'
            }}
          >
            <div style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              width: isDragging ? '100%' : '0',
              height: isDragging ? '100%' : '0',
              background: 'radial-gradient(circle, rgba(59, 130, 246, 0.2) 0%, transparent 70%)',
              transition: 'all 0.3s ease',
              transform: 'translate(-50%, -50%)'
            }} />

            <Upload 
              size={64} 
              style={{ 
                color: isDragging ? '#3b82f6' : '#a855f7',
                marginBottom: '1rem',
                animation: isDragging ? 'bounce 1s infinite' : 'none'
              }} 
            />
            
            <h3 style={{
              margin: '0 0 1rem 0',
              color: '#f8f9ff',
              fontSize: '1.5rem',
              fontWeight: 600
            }}>
              {isDragging ? 'Drop your file here' : 'Drag & Drop or Click to Upload'}
            </h3>
            
            <p style={{
              margin: '0 0 1rem 0',
              color: '#a5b4fc',
              fontSize: '0.875rem'
            }}>
              Upload your security requirements document
            </p>
            
            <div style={{
              display: 'flex',
              justifyContent: 'center',
              gap: '1rem',
              flexWrap: 'wrap'
            }}>
              <span style={{
                background: 'rgba(168, 85, 247, 0.2)',
                color: '#d8b4fe',
                padding: '0.25rem 0.75rem',
                borderRadius: '9999px',
                fontSize: '0.75rem',
                border: '1px solid rgba(168, 85, 247, 0.3)'
              }}>
                Formats: {acceptedFormats.join(', ')}
              </span>
              <span style={{
                background: 'rgba(59, 130, 246, 0.2)',
                color: '#93c5fd',
                padding: '0.25rem 0.75rem',
                borderRadius: '9999px',
                fontSize: '0.75rem',
                border: '1px solid rgba(59, 130, 246, 0.3)'
              }}>
                Max Size: {maxSizeMB}MB
              </span>
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept={acceptedFormats.join(',')}
              onChange={handleFileInputChange}
              style={{ display: 'none' }}
            />
          </div>
        ) : (
          <div style={{
            background: 'rgba(36, 23, 87, 0.6)',
            borderRadius: '16px',
            padding: '2rem',
            border: '1px solid rgba(168, 85, 247, 0.3)',
            position: 'relative'
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '1.5rem'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                {getFileIcon(selectedFile.name)}
                <div>
                  <h4 style={{
                    margin: '0 0 0.25rem 0',
                    color: '#f8f9ff',
                    fontSize: '1.125rem',
                    fontWeight: 600
                  }}>
                    {selectedFile.name}
                  </h4>
                  <p style={{
                    margin: 0,
                    color: '#a5b4fc',
                    fontSize: '0.875rem'
                  }}>
                    {formatFileSize(selectedFile.size)}
                  </p>
                </div>
              </div>
              
              <button
                onClick={clearFile}
                style={{
                  background: 'rgba(239, 68, 68, 0.2)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: '8px',
                  padding: '0.5rem',
                  cursor: 'pointer',
                  color: '#fca5a5',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'all 0.25s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(239, 68, 68, 0.3)';
                  e.currentTarget.style.transform = 'scale(1.1)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)';
                  e.currentTarget.style.transform = 'scale(1)';
                }}
              >
                <X size={20} />
              </button>
            </div>

            {uploadStatus === 'success' && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                padding: '1rem',
                background: 'rgba(34, 197, 94, 0.1)',
                border: '1px solid rgba(34, 197, 94, 0.3)',
                borderRadius: '12px',
                animation: 'slideIn 0.3s ease'
              }}>
                <CheckCircle size={24} color="#22c55e" />
                <div>
                  <p style={{
                    margin: 0,
                    color: '#86efac',
                    fontWeight: 600
                  }}>
                    File uploaded successfully!
                  </p>
                  <p style={{
                    margin: '0.25rem 0 0 0',
                    color: '#86efac',
                    fontSize: '0.875rem',
                    opacity: 0.8
                  }}>
                    Ready for threat analysis
                  </p>
                </div>
              </div>
            )}

            <button
              style={{
                width: '100%',
                marginTop: '1.5rem',
                padding: '1rem',
                background: 'linear-gradient(135deg, #a855f7 0%, #3b82f6 100%)',
                border: 'none',
                borderRadius: '12px',
                color: 'white',
                fontSize: '1rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.75rem',
                boxShadow: '0 4px 15px rgba(168, 85, 247, 0.4)',
                transition: 'all 0.25s ease',
                position: 'relative',
                overflow: 'hidden'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 6px 20px rgba(168, 85, 247, 0.5)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 4px 15px rgba(168, 85, 247, 0.4)';
              }}
            >
              <div style={{
                position: 'absolute',
                top: 0,
                left: '-100%',
                width: '100%',
                height: '100%',
                background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent)',
                transition: 'left 0.5s'
              }} />
              <Upload size={20} />
              Start Threat Analysis
            </button>
          </div>
        )}

        {uploadStatus === 'error' && (
          <div style={{
            marginTop: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '1rem',
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '12px',
            animation: 'shake 0.5s ease'
          }}>
            <AlertCircle size={24} color="#ef4444" />
            <p style={{
              margin: 0,
              color: '#fca5a5'
            }}>
              {errorMessage}
            </p>
          </div>
        )}
      </div>

      <style>{`
        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }
        
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateX(-20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
        
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-10px); }
          75% { transform: translateX(10px); }
        }
      `}</style>
    </div>
  );
};

export default FileUploadComponent;