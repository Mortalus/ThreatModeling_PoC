import React, { useState, useEffect } from 'react';
import { io, Socket } from 'socket.io-client';
import EnhancedSidebar from './components/sidebar/EnhancedSidebar';
import ModernPipelineDisplay from './components/pipeline/ModernPipelineDisplay';
import ModernFileUpload from './components/pipeline/ModernFileUpload';
import './App.css';

// Import the new CSS
import '../public/css/main.css';

interface PipelineStep {
  name: string;
  status: 'idle' | 'running' | 'completed' | 'error';
  percentage: number;
  data?: any;
}

function App() {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [pipelineSteps, setPipelineSteps] = useState<PipelineStep[]>([
    { name: 'Document Upload', status: 'idle', percentage: 0 },
    { name: 'DFD Extraction', status: 'idle', percentage: 0 },
    { name: 'Threat Generation', status: 'idle', percentage: 0 },
    { name: 'Threat Refinement', status: 'idle', percentage: 0 },
    { name: 'Attack Path Analysis', status: 'idle', percentage: 0 }
  ]);

  useEffect(() => {
    // Initialize WebSocket connection
    const socketInstance = io('/', {
      transports: ['websocket', 'polling']
    });

    socketInstance.on('connect', () => {
      console.log('Connected to server');
    });

    socketInstance.on('pipeline_update', (data: any) => {
      // Handle pipeline updates
      if (data.step_index !== undefined && data.status) {
        setPipelineSteps(prev => {
          const updated = [...prev];
          updated[data.step_index] = {
            ...updated[data.step_index],
            status: data.status,
            percentage: data.percentage || 0,
            data: data.data
          };
          return updated;
        });
      }
    });

    setSocket(socketInstance);

    return () => {
      socketInstance.disconnect();
    };
  }, []);

  const handleFileUpload = async (file: File) => {
    // Handle file upload logic
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        // Update first step to completed
        setPipelineSteps(prev => {
          const updated = [...prev];
          updated[0] = { ...updated[0], status: 'completed', percentage: 100 };
          return updated;
        });
      }
    } catch (error) {
      console.error('Upload failed:', error);
    }
  };

  return (
    <div className="app-container" style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-primary)' }}>
      <EnhancedSidebar />
      
      <main className="main-content" style={{ 
        flex: 1, 
        marginLeft: '280px',
        padding: '2rem',
        transition: 'margin-left 0.3s ease'
      }}>
        <div className="content-wrapper" style={{ maxWidth: '1200px', margin: '0 auto' }}>
          {currentStep === 0 ? (
            <ModernFileUpload onFileSelect={handleFileUpload} />
          ) : (
            <ModernPipelineDisplay
              stepName={pipelineSteps[currentStep].name}
              stepData={pipelineSteps[currentStep].data}
              stepStatus={pipelineSteps[currentStep].status}
              stepDescription="Process and analyze security requirements"
            />
          )}
        </div>
      </main>
    </div>
  );
}

export default App;