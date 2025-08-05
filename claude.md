# Threat Modeling Pipeline - Repository Documentation

## Repository Overview

This repository contains an AI-powered threat modeling pipeline that analyzes security requirements documents and generates comprehensive threat assessments. The system uses a 5-step pipeline process to extract data flow diagrams (DFDs), identify threats, improve threat quality, and analyze attack paths. It features a **React-based web interface** with real-time updates via WebSocket, support for multiple LLM providers (Scaleway and Ollama), and includes a review system for human validation of AI-generated results.

## Recent Updates - React Migration

### Complete React TypeScript Migration
The application has been fully migrated from vanilla JavaScript to a modern React TypeScript architecture:
- **React 18.3.1** with TypeScript 5.9.2 for type-safe component development
- **Modular Component Architecture**: Components are organized into logical folders (common, pipeline, review, settings, sidebar)
- **Enhanced Development Experience**: Full TypeScript support with strict typing, ESLint configuration, and proper error boundaries
- **Improved Build System**: react-scripts 5.0.1 with optimized production builds
- **Better State Management**: React hooks and context for application state

### New Frontend Structure
```
src/
├── components/          # React components
│   ├── common/         # Reusable UI components
│   ├── pipeline/       # Pipeline-specific components
│   ├── review/         # Review system components
│   ├── settings/       # Settings modal components
│   └── sidebar/        # Sidebar navigation
├── hooks/              # Custom React hooks
├── services/           # API and external services
├── types/              # TypeScript type definitions
├── utils/              # Utility functions
├── context/            # React context providers
└── index.tsx          # Application entry point
```

## File Descriptions

### Root Configuration Files

**`app.py`** - Main Flask application entry point that initializes the web server, loads environment variables, sets up CORS and WebSocket support, and registers all API routes.

**`package.json`** - Node.js configuration file defining React dependencies, build scripts, and project metadata for the frontend application.

**`tsconfig.json`** - TypeScript configuration for the React application with strict type checking and modern ES module support.

**`.env`** - Environment configuration for React app with API endpoints and development settings.

**`.gitignore`** - Comprehensive ignore file for Python, Node.js, and React build artifacts.

### React Frontend Application (`src/`)

**`src/index.tsx`** - React application entry point that renders the main App component with error boundary protection.

**`src/App.tsx`** - Main application component that orchestrates the UI layout, manages global state, and handles WebSocket connections.

**`src/types/index.ts`** - Centralized TypeScript type definitions for pipeline state, API responses, and component props.

### React Components (`src/components/`)

**`src/components/common/ErrorBoundary.tsx`** - React error boundary component for graceful error handling across the application.

**`src/components/sidebar/Sidebar.tsx`** - Collapsible sidebar navigation with pipeline step indicators and connection status.

**`src/components/pipeline/StepContentDisplay.tsx`** - Dynamic component for displaying content of each pipeline step with view mode switching.

**`src/components/pipeline/FileUpload.tsx`** - File upload component with drag-and-drop support and validation.

**`src/components/pipeline/ThreatDataViewer.tsx`** - Component for viewing threats in formatted or JSON view with refinement details.

**`src/components/pipeline/DFDViewer.tsx`** - Data Flow Diagram viewer with Mermaid.js integration.

**`src/components/review/ReviewPanel.tsx`** - Review system interface for validating AI-generated threats and DFD components.

**`src/components/settings/SettingsModal.tsx`** - Enhanced settings modal with tabbed interface for LLM, processing, and debug configuration.

### React Hooks and Services (`src/hooks/`, `src/services/`)

**`src/hooks/useWebSocket.ts`** - Custom hook for managing WebSocket connections and real-time updates.

**`src/services/api.ts`** - Centralized API service for all backend communication with proper error handling.

**`src/utils/constants.ts`** - Application constants including API endpoints and pipeline step definitions.

### Python Backend Scripts

**`info_to_dfds.py`** - Step 2 pipeline script that extracts Data Flow Diagrams from uploaded documents using LLM analysis.

**`dfd_to_threats.py`** - Step 3 pipeline script that generates threats from DFD components with async/sync processing modes.

**`improve_threat_quality.py`** - Step 4 pipeline script that refines and enriches threats using modular services.

**`attack_path_analyzer.py`** - Step 5 pipeline script that analyzes attack paths using graph algorithms.

### API Routes (`api/`)

**`api/routes.py`** - Core API endpoints for health checks, configuration management, file uploads, and system status.

**`api/review_routes.py`** - Endpoints for the review system allowing human validation of AI-generated threats.

**`api/pipeline_routes.py`** - Pipeline execution endpoints for running individual steps and checking progress.

**`api/websockets.py`** - WebSocket handlers for real-time progress updates and review notifications.

**`api/config_routes.py`** - Configuration management endpoints for saving and loading system settings.

### Configuration (`config/`)

**`config/settings.py`** - Central configuration management with environment variable loading and async processing settings.

### Services (`services/`)

**`services/document_loader_service.py`** - Handles loading documents from Step 1 output with session-specific file handling.

**`services/document_service.py`** - Processes file uploads, extracts text content, and manages document storage.

**`services/document_analysis_service.py`** - Validates document content suitability for DFD extraction.

**`services/dfd_extraction_service.py`** - Orchestrates DFD extraction from documents using LLM-based analysis.

**`services/llm_service.py`** - Provides LLM integration for both Scaleway and Ollama providers with async capabilities.

**`services/llm_threat_service.py`** - Specialized LLM service for threat generation with progress tracking.

**`services/threat_generation_service.py`** - Main service for generating threats from DFD components.

**`services/threat_quality_improvement_service.py`** - Service for refining threats with quality scoring and enrichment.

**`services/attack_path_analyzer_service.py`** - Analyzes attack paths and generates exploit chains.

**`services/pipeline_service.py`** - Manages pipeline execution, step transitions, and progress tracking.

**`services/review_service.py`** - Handles review item generation, similarity detection, and confidence calculations.

**`services/threat_suppression_service.py`** - Suppresses irrelevant threats based on implemented controls.

**`services/validation_service.py`** - Validates pipeline outputs and data structures.

**`services/mermaid_generator.py`** - Generates Mermaid diagram syntax from DFD components.

**`services/external_data_service.py`** - Integrates with external data sources like MITRE ATT&CK.

**`services/rag_populate.py`** - Manages Qdrant vector database for RAG functionality.

### Models (`models/`)

**`models/pipeline_state.py`** - Manages pipeline execution state and progress tracking.

**`models/dfd_models.py`** - Data models for DFD components and structures.

### Utilities (`utils/`)

**`utils/sample_documents.py`** - Generates comprehensive sample requirements documents for testing.

**`utils/logging_utils.py`** - Provides structured logging with color coding and emojis.

**`utils/progress_utils.py`** - Handles progress tracking and kill signal checking.

**`utils/file_utils.py`** - File handling utilities for text extraction and validation.

### Legacy JavaScript Files (Backup)

The original JavaScript files have been migrated to React components but are preserved in the backup directory for reference during the transition period.

### CSS Styles (`css/`, `public/css/`)

**`css/main.css`** - Master CSS import file that orchestrates the entire styling system.

**`css/base.css`** - Foundation styles with CSS variables, typography, and browser resets.

**`css/components.css`** - Reusable UI component styles for buttons, forms, cards, and modals.

**`css/sidebar.css`** - Sidebar layout styles with responsive design.

**`css/pipeline-steps.css`** - Pipeline step visualization styles.

**`css/notifications.css`** - Notification system styling.

**`css/review-system.css`** - Review panel and decision interface styles.

**`css/settings-styles.css`** - Styles for the enhanced settings modal.

**`css/utilities.css`** - Helper classes and utility styles.

## Development Setup

### Prerequisites
- Python 3.8+ with Flask
- Node.js 16+ and npm 8+
- Git

### Installation
1. Clone the repository
2. Install Python dependencies: `pip install -r requirements.txt`
3. Install Node dependencies: `npm install`
4. Copy `.env.example` to `.env` and configure
5. Start the Flask backend: `python app.py`
6. Start the React dev server: `npm start`

### Build for Production
```bash
npm run build
```
This creates an optimized production build in the `build/` directory.

## Core Functionality

The threat modeling pipeline operates through five sequential steps:

1. **Document Upload** - Users upload security requirements documents (PDF, DOCX, TXT) which are processed and text is extracted
2. **DFD Extraction** - AI analyzes the document to identify external entities, processes, data stores, and data flows
3. **Threat Generation** - Based on the DFD, the system generates security threats using STRIDE methodology
4. **Threat Refinement** - Threats are enriched with MITRE ATT&CK mappings, CVE data, and quality improvements
5. **Attack Path Analysis** - The system analyzes potential attack chains and exploit paths

The system supports both cloud-based LLMs (Scaleway) and local models (Ollama), with async processing for improved performance. A comprehensive review system allows security experts to validate and refine AI-generated results before finalizing the threat model.

## Migration Notes

The application has been successfully migrated from a vanilla JavaScript implementation to a modern React TypeScript architecture. Key improvements include:

- **Type Safety**: Full TypeScript coverage for better development experience and fewer runtime errors
- **Component Reusability**: Modular React components that can be easily maintained and tested
- **Performance**: React's virtual DOM and optimized rendering for better UI performance
- **Development Experience**: Hot module replacement, better debugging tools, and modern build pipeline
- **Future-Ready**: Prepared for additional features like state management libraries, testing frameworks, and CI/CD integration