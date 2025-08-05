import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { PipelineState, PipelineStep } from '../types';

// Initial pipeline state
const initialPipelineState: PipelineState = {
  steps: [
    { id: 0, name: 'Document Upload', status: 'pending', data: null, percentage: 0 },
    { id: 1, name: 'DFD Extraction', status: 'pending', data: null, percentage: 0 },
    { id: 2, name: 'Threat Identification', status: 'pending', data: null, percentage: 0 },
    { id: 3, name: 'Threat Refinement', status: 'pending', data: null, percentage: 0 },
    { id: 4, name: 'Attack Path Analysis', status: 'pending', data: null, percentage: 0 }
  ]
};

// Action types
type PipelineAction =
  | { type: 'UPDATE_STEP_STATE'; payload: { stepIndex: number; status: PipelineStep['status']; data?: any; percentage?: number } }
  | { type: 'UPDATE_STEP_DATA'; payload: { stepIndex: number; data: any } }
  | { type: 'UPDATE_STEP_PERCENTAGE'; payload: { stepIndex: number; percentage: number } }
  | { type: 'RESET_PIPELINE' }
  | { type: 'SET_STEP_ERROR'; payload: { stepIndex: number; error: string } }
  | { type: 'BATCH_UPDATE_STEPS'; payload: PipelineStep[] };

// Reducer
const pipelineReducer = (state: PipelineState, action: PipelineAction): PipelineState => {
  switch (action.type) {
    case 'UPDATE_STEP_STATE':
      return {
        ...state,
        steps: state.steps.map((step, index) =>
          index === action.payload.stepIndex
            ? {
                ...step,
                status: action.payload.status,
                data: action.payload.data !== undefined ? action.payload.data : step.data,
                percentage: action.payload.percentage !== undefined ? action.payload.percentage : step.percentage
              }
            : step
        )
      };

    case 'UPDATE_STEP_DATA':
      return {
        ...state,
        steps: state.steps.map((step, index) =>
          index === action.payload.stepIndex
            ? { ...step, data: action.payload.data }
            : step
        )
      };

    case 'UPDATE_STEP_PERCENTAGE':
      return {
        ...state,
        steps: state.steps.map((step, index) =>
          index === action.payload.stepIndex
            ? { ...step, percentage: action.payload.percentage }
            : step
        )
      };

    case 'SET_STEP_ERROR':
      return {
        ...state,
        steps: state.steps.map((step, index) =>
          index === action.payload.stepIndex
            ? { ...step, status: 'error', percentage: 0, data: { error: action.payload.error } }
            : step
        )
      };

    case 'BATCH_UPDATE_STEPS':
      return {
        ...state,
        steps: action.payload
      };

    case 'RESET_PIPELINE':
      return initialPipelineState;

    default:
      return state;
  }
};

// Context types
interface PipelineContextType {
  pipelineState: PipelineState;
  updateStepState: (stepIndex: number, status: PipelineStep['status'], data?: any, percentage?: number) => void;
  updateStepData: (stepIndex: number, data: any) => void;
  updateStepPercentage: (stepIndex: number, percentage: number) => void;
  setStepError: (stepIndex: number, error: string) => void;
  batchUpdateSteps: (steps: PipelineStep[]) => void;
  resetPipeline: () => void;
  isStepAccessible: (stepIndex: number) => boolean;
  getStepByIndex: (stepIndex: number) => PipelineStep | undefined;
  getCurrentRunningStep: () => PipelineStep | undefined;
  getCompletedSteps: () => PipelineStep[];
  getStepProgress: (stepIndex: number) => number;
}

// Create context
const PipelineStateContext = createContext<PipelineContextType | undefined>(undefined);

// Provider component
interface PipelineStateProviderProps {
  children: ReactNode;
  initialState?: PipelineState;
}

export const PipelineStateProvider: React.FC<PipelineStateProviderProps> = ({ 
  children, 
  initialState = initialPipelineState 
}) => {
  const [pipelineState, dispatch] = useReducer(pipelineReducer, initialState);

  // Action creators
  const updateStepState = (
    stepIndex: number, 
    status: PipelineStep['status'], 
    data?: any, 
    percentage?: number
  ) => {
    dispatch({
      type: 'UPDATE_STEP_STATE',
      payload: { stepIndex, status, data, percentage }
    });
  };

  const updateStepData = (stepIndex: number, data: any) => {
    dispatch({
      type: 'UPDATE_STEP_DATA',
      payload: { stepIndex, data }
    });
  };

  const updateStepPercentage = (stepIndex: number, percentage: number) => {
    dispatch({
      type: 'UPDATE_STEP_PERCENTAGE',
      payload: { stepIndex, percentage }
    });
  };

  const setStepError = (stepIndex: number, error: string) => {
    dispatch({
      type: 'SET_STEP_ERROR',
      payload: { stepIndex, error }
    });
  };

  const batchUpdateSteps = (steps: PipelineStep[]) => {
    dispatch({
      type: 'BATCH_UPDATE_STEPS',
      payload: steps
    });
  };

  const resetPipeline = () => {
    dispatch({ type: 'RESET_PIPELINE' });
  };

  // Utility functions
  const isStepAccessible = (stepIndex: number): boolean => {
    if (stepIndex === 0) return true;
    const previousStep = pipelineState.steps[stepIndex - 1];
    return previousStep?.status === 'completed';
  };

  const getStepByIndex = (stepIndex: number): PipelineStep | undefined => {
    return pipelineState.steps[stepIndex];
  };

  const getCurrentRunningStep = (): PipelineStep | undefined => {
    return pipelineState.steps.find(step => step.status === 'running');
  };

  const getCompletedSteps = (): PipelineStep[] => {
    return pipelineState.steps.filter(step => step.status === 'completed');
  };

  const getStepProgress = (stepIndex: number): number => {
    const step = pipelineState.steps[stepIndex];
    return step?.percentage || 0;
  };

  const contextValue: PipelineContextType = {
    pipelineState,
    updateStepState,
    updateStepData,
    updateStepPercentage,
    setStepError,
    batchUpdateSteps,
    resetPipeline,
    isStepAccessible,
    getStepByIndex,
    getCurrentRunningStep,
    getCompletedSteps,
    getStepProgress
  };

  return (
    <PipelineStateContext.Provider value={contextValue}>
      {children}
    </PipelineStateContext.Provider>
  );
};

// Custom hook
export const usePipelineState = (): PipelineContextType => {
  const context = useContext(PipelineStateContext);
  if (context === undefined) {
    throw new Error('usePipelineState must be used within a PipelineStateProvider');
  }
  return context;
};

// Additional hooks for specific use cases
export const useCurrentStep = (currentStepIndex: number) => {
  const { getStepByIndex } = usePipelineState();
  return getStepByIndex(currentStepIndex);
};

export const useStepAccessibility = () => {
  const { isStepAccessible } = usePipelineState();
  return { isStepAccessible };
};

export const useRunningStep = () => {
  const { getCurrentRunningStep } = usePipelineState();
  return getCurrentRunningStep();
};

export const useCompletedSteps = () => {
  const { getCompletedSteps } = usePipelineState();
  return getCompletedSteps();
};