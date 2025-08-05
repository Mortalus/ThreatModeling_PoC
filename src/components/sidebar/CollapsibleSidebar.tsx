import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Socket } from 'socket.io-client';
import { PipelineStep as EnhancedPipelineStep } from './PipelineStep';
import { ConnectionStatus } from './ConnectionStatus';
import { CollapsedStepIndicator } from './CollapsedStepIndicator';
import { PipelineState, ModelConfig } from '../../types';
import './CollapsibleSidebar.css';

interface CollapsibleSidebarProps {
  pipelineState: PipelineState;
  currentStep: number;
  setCurrentStep: (step: number) => void;
  loading: boolean;
  pendingReviewCount: number;
  showReviewPanel: boolean;
  setShowReviewPanel: (show: boolean) => void;
  socket: Socket | null;
  modelConfig: ModelConfig | null;
}

// Custom hooks for sidebar functionality
const useSidebarState = () => {
  const [isCollapsed, setIsCollapsed] = useState(() => {
    const saved = localStorage.getItem('sidebar-collapsed');
    return saved ? JSON.parse(saved) : false;
  });

  const toggleSidebar = useCallback(() => {
    setIsCollapsed((prev: boolean) => {
      const newValue = !prev;
      localStorage.setItem('sidebar-collapsed', JSON.stringify(newValue));
      return newValue;
    });
  }, []);

  return { isCollapsed, toggleSidebar };
};

const useResponsiveSidebar = () => {
  const [isMobile, setIsMobile] = useState(false);
  const [isTablet, setIsTablet] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      setIsMobile(width < 768);
      setIsTablet(width >= 768 && width < 1024);
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return { isMobile, isTablet };
};

const useSidebarAnimations = (isCollapsed: boolean) => {
  const [isAnimating, setIsAnimating] = useState(false);
  const animationTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    setIsAnimating(true);
    
    if (animationTimeoutRef.current) {
      clearTimeout(animationTimeoutRef.current);
    }
    
    animationTimeoutRef.current = setTimeout(() => {
      setIsAnimating(false);
    }, 400);

    return () => {
      if (animationTimeoutRef.current) {
        clearTimeout(animationTimeoutRef.current);
      }
    };
  }, [isCollapsed]);

  return { isAnimating };
};

export const CollapsibleSidebar: React.FC<CollapsibleSidebarProps> = ({
  pipelineState,
  currentStep,
  setCurrentStep,
  loading,
  pendingReviewCount,
  showReviewPanel,
  setShowReviewPanel,
  socket,
  modelConfig
}) => {
  const { isCollapsed, toggleSidebar } = useSidebarState();
  const { isMobile, isTablet } = useResponsiveSidebar();
  const { isAnimating } = useSidebarAnimations(isCollapsed);
  const sidebarRef = useRef<HTMLDivElement>(null);

  // Pipeline step icons
  const PIPELINE_ICONS = ['📄', '🔗', '⚠️', '✨', '🎯'];

  // Keyboard shortcut for toggling sidebar
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.ctrlKey && event.key === 'b') {
        event.preventDefault();
        toggleSidebar();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [toggleSidebar]);

  // Auto-collapse on mobile
  useEffect(() => {
    if (isMobile && !isCollapsed) {
      toggleSidebar();
    }
  }, [isMobile, isCollapsed, toggleSidebar]);

  // Handle click outside to collapse on mobile
  useEffect(() => {
    if (!isMobile) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (sidebarRef.current && !sidebarRef.current.contains(event.target as Node)) {
        if (!isCollapsed) {
          toggleSidebar();
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isMobile, isCollapsed, toggleSidebar]);

  // CSS classes
  const sidebarClasses = useMemo(() => {
    const classes = ['sidebar'];
    if (isCollapsed) classes.push('collapsed');
    if (isAnimating) classes.push('animating');
    if (isMobile) classes.push('mobile');
    if (isTablet) classes.push('tablet');
    return classes.join(' ');
  }, [isCollapsed, isAnimating, isMobile, isTablet]);

  const handleStepClick = useCallback((stepIndex: number) => {
    if (!loading) {
      setCurrentStep(stepIndex);
      
      // Auto-collapse on mobile after selection
      if (isMobile && !isCollapsed) {
        setTimeout(() => toggleSidebar(), 300);
      }
    }
  }, [loading, setCurrentStep, isMobile, isCollapsed, toggleSidebar]);

  const handleReviewToggle = useCallback(() => {
    setShowReviewPanel(!showReviewPanel);
  }, [showReviewPanel, setShowReviewPanel]);

  const sidebarContent = isCollapsed ? (
    // Collapsed sidebar content
    <div className="sidebar-collapsed-content">
      <div className="collapsed-steps" role="list">
        {pipelineState.steps.map((step, index) => (
          <CollapsedStepIndicator
            key={step.id}
            step={step}
            index={index}
            active={index === currentStep}
            onClick={() => handleStepClick(index)}
            icon={PIPELINE_ICONS[index]}
          />
        ))}
      </div>
      
      {pendingReviewCount > 0 && (
        <div className="collapsed-review-indicator">
          <button
            className="btn btn-icon btn-primary"
            onClick={handleReviewToggle}
            title={`${pendingReviewCount} items pending review`}
            aria-label={`Review queue with ${pendingReviewCount} pending items`}
          >
            📝
            <span className="review-count-badge" aria-hidden="true">
              {pendingReviewCount}
            </span>
          </button>
        </div>
      )}

      <div className="collapsed-connection-status">
        <ConnectionStatus socket={socket} compact />
      </div>
    </div>
  ) : (
    // Expanded sidebar content
    <>
      <div className="sidebar-header">
        <h1>🛡️ Advanced Threat Modeling</h1>
        <p>AI-Powered Security Analysis</p>
      </div>
      
      <div className="pipeline-steps" role="list">
        {pipelineState.steps.map((step, index) => (
          <EnhancedPipelineStep
            key={step.id}
            step={step}
            index={index}
            active={index === currentStep}
            onClick={() => handleStepClick(index)}
            isCollapsed={false}
            modelConfig={modelConfig}
            icon={PIPELINE_ICONS[index]}
          />
        ))}
      </div>
      
      {pendingReviewCount > 0 && (
        <div className="review-button-container">
          <button
            className="btn btn-primary btn-block"
            onClick={handleReviewToggle}
            aria-label={`Review queue with ${pendingReviewCount} pending items`}
          >
            📝 Review Queue ({pendingReviewCount})
          </button>
        </div>
      )}
      
      <ConnectionStatus socket={socket} />
    </>
  );

  return (
    <div
      ref={sidebarRef}
      className={sidebarClasses}
      role="navigation"
      aria-label="Pipeline Progress Navigation"
      aria-expanded={!isCollapsed}
    >
      {/* Toggle Button */}
      <button
        className="sidebar-toggle"
        onClick={toggleSidebar}
        aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        title={`${isCollapsed ? 'Expand' : 'Collapse'} Progress Panel (Ctrl+B)`}
        type="button"
      >
        <span className="sidebar-toggle-icon" aria-hidden="true">
          {isCollapsed ? '▶' : '◀'}
        </span>
      </button>

      {/* Sidebar Content */}
      <div className="sidebar-content">
        {sidebarContent}
      </div>
    </div>
  );
};