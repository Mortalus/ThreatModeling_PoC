import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Shield, AlertTriangle, Zap, Activity, FileText, Network, Settings, CheckCircle, Clock, XCircle } from 'lucide-react';

interface PipelineStep {
  name: string;
  status: 'idle' | 'running' | 'completed' | 'error';
  percentage: number;
  icon: React.ReactNode;
  description: string;
}

const Sidebar: React.FC = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected'>('connected');

  const pipelineSteps: PipelineStep[] = [
    {
      name: 'Document Upload',
      status: 'completed',
      percentage: 100,
      icon: <FileText size={24} />,
      description: 'Upload security requirements'
    },
    {
      name: 'DFD Extraction',
      status: 'completed',
      percentage: 100,
      icon: <Network size={24} />,
      description: 'Extract data flow diagrams'
    },
    {
      name: 'Threat Generation',
      status: 'running',
      percentage: 65,
      icon: <AlertTriangle size={24} />,
      description: 'Generate security threats'
    },
    {
      name: 'Threat Refinement',
      status: 'idle',
      percentage: 0,
      icon: <Zap size={24} />,
      description: 'Enhance threat quality'
    },
    {
      name: 'Attack Path Analysis',
      status: 'idle',
      percentage: 0,
      icon: <Activity size={24} />,
      description: 'Analyze attack chains'
    }
  ];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle size={16} className="text-green-400" />;
      case 'running': return <Clock size={16} className="text-purple-400 animate-spin" />;
      case 'error': return <XCircle size={16} className="text-red-400" />;
      default: return <div className="w-4 h-4 rounded-full border-2 border-gray-500" />;
    }
  };

  useEffect(() => {
    // Simulate real-time updates
    const interval = setInterval(() => {
      setConnectionStatus(prev => prev === 'connected' ? 'connected' : 'disconnected');
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className={`sidebar ${isCollapsed ? 'collapsed' : ''}`} style={{
      width: isCollapsed ? '60px' : '280px',
      transition: 'width 0.3s ease',
      background: 'linear-gradient(180deg, #110b2b 0%, #1a1140 100%)',
      borderRight: '1px solid rgba(255, 255, 255, 0.1)',
      height: '100vh',
      position: 'fixed',
      left: 0,
      top: 0,
      display: 'flex',
      flexDirection: 'column',
      zIndex: 100
    }}>
      {/* Header */}
      <div className="sidebar-header" style={{
        padding: '2rem 1.5rem',
        borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        background: 'rgba(168, 85, 247, 0.05)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <Shield size={32} style={{ color: '#a855f7', flexShrink: 0 }} />
          {!isCollapsed && (
            <div>
              <h1 style={{
                margin: 0,
                fontSize: '1.5rem',
                fontWeight: 700,
                background: 'linear-gradient(135deg, #a855f7 0%, #3b82f6 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text'
              }}>ThreatShield</h1>
              <p style={{ margin: 0, fontSize: '0.75rem', color: '#a5b4fc' }}>AI Security Pipeline</p>
            </div>
          )}
        </div>
      </div>

      {/* Pipeline Steps */}
      <div style={{ flex: 1, padding: '1rem 0', overflowY: 'auto' }}>
        <div style={{ padding: '0 0.5rem' }}>
          {!isCollapsed && (
            <h3 style={{ 
              fontSize: '0.75rem', 
              color: '#6366f1', 
              textTransform: 'uppercase', 
              letterSpacing: '0.1em',
              margin: '0 1rem 1rem'
            }}>Pipeline Progress</h3>
          )}
          
          {pipelineSteps.map((step, index) => (
            <div
              key={index}
              className={`pipeline-step ${step.status} ${activeStep === index ? 'active' : ''}`}
              onClick={() => setActiveStep(index)}
              style={{
                margin: '0.5rem',
                borderRadius: '12px',
                overflow: 'hidden',
                transition: 'all 0.25s ease',
                background: activeStep === index 
                  ? 'linear-gradient(135deg, #a855f7 0%, #3b82f6 100%)' 
                  : 'rgba(255, 255, 255, 0.02)',
                border: '1px solid transparent',
                borderColor: activeStep === index ? 'transparent' : step.status === 'running' ? '#a855f7' : 'transparent',
                borderLeftWidth: '3px',
                borderLeftColor: step.status === 'completed' ? '#22c55e' : step.status === 'running' ? '#a855f7' : 'transparent',
                cursor: 'pointer',
                position: 'relative',
                boxShadow: activeStep === index ? '0 4px 20px rgba(168, 85, 247, 0.4)' : 'none'
              }}
              onMouseEnter={(e) => {
                if (activeStep !== index) {
                  e.currentTarget.style.background = 'rgba(168, 85, 247, 0.1)';
                  e.currentTarget.style.borderColor = 'rgba(168, 85, 247, 0.3)';
                  e.currentTarget.style.transform = 'translateX(4px)';
                }
              }}
              onMouseLeave={(e) => {
                if (activeStep !== index) {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)';
                  e.currentTarget.style.borderColor = 'transparent';
                  e.currentTarget.style.transform = 'translateX(0)';
                }
              }}
            >
              <button style={{
                width: '100%',
                padding: '1rem',
                border: 'none',
                background: 'transparent',
                color: activeStep === index ? '#ffffff' : '#f8f9ff',
                textAlign: 'left',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '1rem'
              }}>
                <span style={{ fontSize: '1.5rem', filter: 'saturate(1.5)' }}>{step.icon}</span>
                {!isCollapsed && (
                  <div style={{ flex: 1 }}>
                    <span style={{ fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>
                      {step.name}
                    </span>
                    <div style={{ fontSize: '0.75rem', color: activeStep === index ? 'rgba(255,255,255,0.8)' : '#a5b4fc', display: 'flex', gap: '1rem', alignItems: 'center' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        {getStatusIcon(step.status)}
                        {step.status}
                      </span>
                      {step.status === 'running' && (
                        <span>{step.percentage}%</span>
                      )}
                    </div>
                  </div>
                )}
              </button>
              {step.status === 'running' && (
                <div style={{
                  position: 'absolute',
                  bottom: 0,
                  left: 0,
                  right: 0,
                  height: '3px',
                  background: 'rgba(255, 255, 255, 0.1)',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    width: `${step.percentage}%`,
                    height: '100%',
                    background: 'linear-gradient(90deg, #a855f7, #3b82f6)',
                    transition: 'width 0.3s ease',
                    position: 'relative',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)',
                      animation: 'shimmer 2s infinite'
                    }} />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Bottom Controls */}
      <div style={{ padding: '1rem', borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
        {!isCollapsed && (
          <>
            <button className="btn btn-secondary" style={{
              width: '100%',
              marginBottom: '0.5rem',
              background: 'rgba(36, 23, 87, 0.7)',
              border: '1px solid rgba(168, 85, 247, 0.2)',
              color: '#f8f9ff',
              padding: '0.75rem',
              borderRadius: '12px',
              fontSize: '0.875rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              transition: 'all 0.25s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(168, 85, 247, 0.2)';
              e.currentTarget.style.borderColor = '#a855f7';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(36, 23, 87, 0.7)';
              e.currentTarget.style.borderColor = 'rgba(168, 85, 247, 0.2)';
              e.currentTarget.style.transform = 'translateY(0)';
            }}>
              <Settings size={16} />
              Settings
            </button>
            
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.5rem',
              background: 'rgba(255, 255, 255, 0.02)',
              borderRadius: '8px',
              fontSize: '0.75rem',
              color: connectionStatus === 'connected' ? '#22c55e' : '#ef4444'
            }}>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: connectionStatus === 'connected' ? '#22c55e' : '#ef4444',
                animation: connectionStatus === 'connected' ? 'pulse 2s infinite' : 'none'
              }} />
              <span>{connectionStatus === 'connected' ? 'Connected' : 'Disconnected'}</span>
            </div>
          </>
        )}
      </div>

      {/* Collapse Toggle */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        style={{
          position: 'absolute',
          top: '50%',
          right: '-12px',
          transform: 'translateY(-50%)',
          width: '24px',
          height: '48px',
          background: 'linear-gradient(135deg, #a855f7 0%, #3b82f6 100%)',
          border: 'none',
          borderRadius: '0 12px 12px 0',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          boxShadow: '4px 0 12px rgba(0, 0, 0, 0.2)',
          transition: 'all 0.25s ease'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'translateY(-50%) translateX(2px)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'translateY(-50%)';
        }}
      >
        {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>

      <style>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        
        @keyframes pulse {
          0% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.4); }
          70% { box-shadow: 0 0 0 10px rgba(34, 197, 94, 0); }
          100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
        }
        
        .animate-spin {
          animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default Sidebar;