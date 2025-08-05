import React, { useState } from 'react';
import { Upload, Cloud, Check, AlertCircle, Eye, FileCode, TrendingUp, Shield, ExternalLink } from 'lucide-react';

interface ThreatData {
  threat_id: string;
  component: string;
  threat_type: string;
  description: string;
  impact: string;
  likelihood: string;
  risk_score: number;
  mitigation: string;
  mitre_attack?: string[];
}

interface StepData {
  threats?: ThreatData[];
  dfd?: any;
  attackPaths?: any[];
}

interface PipelineStepDisplayProps {
  stepName: string;
  stepData?: StepData;
  stepStatus: 'idle' | 'running' | 'completed' | 'error';
  stepDescription: string;
}

const PipelineStepDisplay: React.FC<PipelineStepDisplayProps> = ({
  stepName,
  stepData,
  stepStatus,
  stepDescription
}) => {
  const [viewMode, setViewMode] = useState<'formatted' | 'json'>('formatted');
  const [expandedThreats, setExpandedThreats] = useState<Set<string>>(new Set());

  const toggleThreatExpansion = (threatId: string) => {
    const newExpanded = new Set(expandedThreats);
    if (newExpanded.has(threatId)) {
      newExpanded.delete(threatId);
    } else {
      newExpanded.add(threatId);
    }
    setExpandedThreats(newExpanded);
  };

  const getRiskBadgeStyle = (score: number) => {
    if (score >= 8) return { bg: 'rgba(239, 68, 68, 0.2)', color: '#fca5a5', border: 'rgba(239, 68, 68, 0.3)' };
    if (score >= 6) return { bg: 'rgba(249, 115, 22, 0.2)', color: '#fdba74', border: 'rgba(249, 115, 22, 0.3)' };
    if (score >= 4) return { bg: 'rgba(245, 158, 11, 0.2)', color: '#fcd34d', border: 'rgba(245, 158, 11, 0.3)' };
    return { bg: 'rgba(34, 197, 94, 0.2)', color: '#86efac', border: 'rgba(34, 197, 94, 0.3)' };
  };

  const renderThreatCard = (threat: ThreatData) => {
    const isExpanded = expandedThreats.has(threat.threat_id);
    const riskStyle = getRiskBadgeStyle(threat.risk_score);

    return (
      <div
        key={threat.threat_id}
        className="threat-card"
        style={{
          background: 'rgba(36, 23, 87, 0.7)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(168, 85, 247, 0.2)',
          borderRadius: '12px',
          padding: '1.5rem',
          marginBottom: '1rem',
          transition: 'all 0.25s ease',
          position: 'relative',
          overflow: 'hidden',
          cursor: 'pointer'
        }}
        onClick={() => toggleThreatExpansion(threat.threat_id)}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'translateX(4px)';
          e.currentTarget.style.borderColor = '#a855f7';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'translateX(0)';
          e.currentTarget.style.borderColor = 'rgba(168, 85, 247, 0.2)';
        }}
      >
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '4px',
          height: '100%',
          background: 'linear-gradient(135deg, #a855f7 0%, #3b82f6 100%)',
          opacity: isExpanded ? 1 : 0,
          transition: 'opacity 0.25s ease'
        }} />

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
          <div style={{ flex: 1 }}>
            <h4 style={{ margin: '0 0 0.5rem 0', color: '#f8f9ff', fontWeight: 600, fontSize: '1.125rem' }}>
              {threat.threat_type}
            </h4>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
              <span style={{
                background: riskStyle.bg,
                color: riskStyle.color,
                border: `1px solid ${riskStyle.border}`,
                padding: '0.25rem 0.75rem',
                borderRadius: '9999px',
                fontSize: '0.75rem',
                fontWeight: 600,
                letterSpacing: '0.05em'
              }}>
                RISK: {threat.risk_score}/10
              </span>
              <span style={{ color: '#a5b4fc', fontSize: '0.875rem' }}>
                <Shield size={14} style={{ display: 'inline', marginRight: '0.25rem' }} />
                {threat.component}
              </span>
            </div>
          </div>
        </div>

        <p style={{ margin: '0 0 1rem 0', color: '#e0e7ff', lineHeight: 1.6 }}>
          {threat.description}
        </p>

        {isExpanded && (
          <div style={{
            marginTop: '1rem',
            paddingTop: '1rem',
            borderTop: '1px solid rgba(168, 85, 247, 0.2)',
            animation: 'fadeIn 0.25s ease'
          }}>
            <div style={{ marginBottom: '1rem' }}>
              <h5 style={{ margin: '0 0 0.5rem 0', color: '#a855f7', fontSize: '0.875rem', fontWeight: 600 }}>
                Impact
              </h5>
              <p style={{ margin: 0, color: '#e0e7ff', fontSize: '0.875rem' }}>{threat.impact}</p>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <h5 style={{ margin: '0 0 0.5rem 0', color: '#a855f7', fontSize: '0.875rem', fontWeight: 600 }}>
                Mitigation
              </h5>
              <p style={{ margin: 0, color: '#e0e7ff', fontSize: '0.875rem' }}>{threat.mitigation}</p>
            </div>

            {threat.mitre_attack && threat.mitre_attack.length > 0 && (
              <div>
                <h5 style={{ margin: '0 0 0.5rem 0', color: '#a855f7', fontSize: '0.875rem', fontWeight: 600 }}>
                  MITRE ATT&CK Techniques
                </h5>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {threat.mitre_attack.map((technique, idx) => (
                    <span
                      key={idx}
                      style={{
                        background: 'rgba(59, 130, 246, 0.2)',
                        color: '#93c5fd',
                        border: '1px solid rgba(59, 130, 246, 0.3)',
                        padding: '0.25rem 0.5rem',
                        borderRadius: '6px',
                        fontSize: '0.75rem',
                        fontFamily: 'monospace',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.25rem'
                      }}
                    >
                      {technique}
                      <ExternalLink size={12} />
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <style>{`
          @keyframes fadeIn {
            from {
              opacity: 0;
              transform: translateY(-10px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }
        `}</style>
      </div>
    );
  };

  const renderEmptyState = () => (
    <div style={{
      textAlign: 'center',
      padding: '4rem 2rem',
      color: '#a5b4fc'
    }}>
      <div style={{ fontSize: '3rem', opacity: 0.3, marginBottom: '1rem' }}>
        {stepStatus === 'idle' ? <Cloud size={48} /> : <AlertCircle size={48} />}
      </div>
      <h3 style={{ margin: '0 0 0.5rem 0', color: '#e0e7ff' }}>
        {stepStatus === 'idle' ? 'Ready to Start' : 'No Data Available'}
      </h3>
      <p style={{ margin: 0, fontSize: '0.875rem' }}>
        {stepStatus === 'idle' 
          ? 'Click "Run Step" to begin processing'
          : 'Complete previous steps to see results here'}
      </p>
    </div>
  );

  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(36, 23, 87, 0.3) 0%, rgba(59, 130, 246, 0.1) 100%)',
      backdropFilter: 'blur(20px)',
      borderRadius: '24px',
      border: '1px solid rgba(168, 85, 247, 0.2)',
      boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.37)',
      padding: '2rem',
      minHeight: '400px',
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Background decoration */}
      <div style={{
        position: 'absolute',
        top: '-100px',
        right: '-100px',
        width: '300px',
        height: '300px',
        background: 'radial-gradient(circle, rgba(168, 85, 247, 0.1) 0%, transparent 70%)',
        borderRadius: '50%',
        filter: 'blur(60px)'
      }} />

      {/* Header */}
      <div style={{ marginBottom: '2rem', position: 'relative', zIndex: 1 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{
              margin: '0 0 0.5rem 0',
              fontSize: '2rem',
              fontWeight: 700,
              background: 'linear-gradient(135deg, #a855f7 0%, #3b82f6 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text'
            }}>
              {stepName}
            </h2>
            <p style={{ margin: 0, color: '#a5b4fc', fontSize: '0.875rem' }}>
              {stepDescription}
            </p>
          </div>
          
          {stepData && Object.keys(stepData).length > 0 && (
            <div style={{
              display: 'flex',
              gap: '0.25rem',
              background: 'rgba(0, 0, 0, 0.2)',
              padding: '0.25rem',
              borderRadius: '12px'
            }}>
              <button
                onClick={() => setViewMode('formatted')}
                style={{
                  padding: '0.5rem 1rem',
                  border: 'none',
                  background: viewMode === 'formatted' ? 'rgba(255, 255, 255, 0.2)' : 'transparent',
                  color: viewMode === 'formatted' ? '#f8f9ff' : '#a5b4fc',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '0.75rem',
                  fontWeight: 500,
                  transition: 'all 0.15s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}
              >
                <Eye size={14} />
                Formatted
              </button>
              <button
                onClick={() => setViewMode('json')}
                style={{
                  padding: '0.5rem 1rem',
                  border: 'none',
                  background: viewMode === 'json' ? 'rgba(255, 255, 255, 0.2)' : 'transparent',
                  color: viewMode === 'json' ? '#f8f9ff' : '#a5b4fc',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '0.75rem',
                  fontWeight: 500,
                  transition: 'all 0.15s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}
              >
                <FileCode size={14} />
                JSON
              </button>
            </div>
          )}
        </div>

        {stepStatus === 'running' && (
          <div style={{ marginTop: '1rem' }}>
            <div style={{
              height: '4px',
              background: 'rgba(255, 255, 255, 0.1)',
              borderRadius: '9999px',
              overflow: 'hidden'
            }}>
              <div style={{
                width: '65%',
                height: '100%',
                background: 'linear-gradient(90deg, #a855f7, #3b82f6)',
                borderRadius: '9999px',
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
          </div>
        )}
      </div>

      {/* Content */}
      <div style={{ position: 'relative', zIndex: 1 }}>
        {!stepData || Object.keys(stepData).length === 0 ? (
          renderEmptyState()
        ) : viewMode === 'formatted' && stepData.threats ? (
          <div>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '1.5rem'
            }}>
              <h3 style={{ margin: 0, color: '#e0e7ff', fontSize: '1.125rem' }}>
                Identified Threats ({stepData.threats.length})
              </h3>
              <button style={{
                background: 'rgba(168, 85, 247, 0.2)',
                border: '1px solid rgba(168, 85, 247, 0.3)',
                color: '#a855f7',
                padding: '0.5rem 1rem',
                borderRadius: '8px',
                fontSize: '0.75rem',
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                transition: 'all 0.25s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(168, 85, 247, 0.3)';
                e.currentTarget.style.transform = 'translateY(-1px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(168, 85, 247, 0.2)';
                e.currentTarget.style.transform = 'translateY(0)';
              }}>
                <TrendingUp size={14} />
                Analyze Trends
              </button>
            </div>
            {stepData.threats.map(renderThreatCard)}
          </div>
        ) : (
          <pre style={{
            background: 'rgba(0, 0, 0, 0.3)',
            padding: '1.5rem',
            borderRadius: '12px',
            overflow: 'auto',
            maxHeight: '600px',
            color: '#e0e7ff',
            fontSize: '0.875rem',
            fontFamily: 'monospace',
            border: '1px solid rgba(168, 85, 247, 0.2)'
          }}>
            {JSON.stringify(stepData, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
};

export default PipelineStepDisplay;