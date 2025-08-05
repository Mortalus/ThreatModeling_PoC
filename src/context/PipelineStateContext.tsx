// src/context/PipelineStateContext.tsx

import React, { createContext, useContext, useState, ReactNode } from 'react';
import { PipelineState, PipelineStep } from '../types';

const initialPipelineState: PipelineState = {
  steps: [
    { id: 0, name: 'Document Upload', status: 'idle', data: null, percentage: 0 },
    { id: 1, name: 'DFD Extraction', status: 'idle', data: null, percentage: 0 },
    { id: 2, name: 'Threat Identification', status: 'idle', data: null, percentage: 0 },
    { id: 3, name: 'Threat Refinement', status: 'idle', data: null, percentage: 0 },
    { id: 4, name: 'Attack Path Analysis', status: 'idle', data: null, percentage: 0 }
  ],
  currentStep: 0,
  isRunning: false
};

interface PipelineStateContextType {
  pipelineState: PipelineState;
  updateStepStatus: (stepId: number, status: PipelineStep['status'], data?: any, percentage?: number) => void;
  setCurrentStep: (stepId: number) => void;
  resetPipeline: () => void;
  setIsRunning: (isRunning: boolean) => void;
}

const PipelineStateContext = createContext<PipelineStateContextType | undefined>(undefined);

export const PipelineStateProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [pipelineState, setPipelineState] = useState<PipelineState>(initialPipelineState);

  const updateStepStatus = (stepId: number, status: PipelineStep['status'], data?: any, percentage?: number) => {
    setPipelineState(prev => ({
      ...prev,
      steps: prev.steps.map(step =>
        step.id === stepId
          ? {
              ...step,
              status,
              data: data !== undefined ? data : step.data,
              percentage: percentage !== undefined ? percentage : step.percentage
            }
          : step
      )
    }));
  };

  const setCurrentStep = (stepId: number) => {
    setPipelineState(prev => ({
      ...prev,
      currentStep: stepId
    }));
  };

  const resetPipeline = () => {
    setPipelineState(initialPipelineState);
  };

  const setIsRunning = (isRunning: boolean) => {
    setPipelineState(prev => ({
      ...prev,
      isRunning
    }));
  };

  return (
    <PipelineStateContext.Provider
      value={{
        pipelineState,
        updateStepStatus,
        setCurrentStep,
        resetPipeline,
        setIsRunning
      }}
    >
      {children}
    </PipelineStateContext.Provider>
  );
};

export const usePipelineState = () => {
  const context = useContext(PipelineStateContext);
  if (!context) {
    throw new Error('usePipelineState must be used within a PipelineStateProvider');
  }
  return context;
};