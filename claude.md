# Threat Modeling Pipeline - Repository Documentation

## Repository Overview

This repository contains an AI-powered threat modeling pipeline that analyzes security requirements documents and generates comprehensive threat assessments. The system uses a 5-step pipeline process to extract data flow diagrams (DFDs), identify threats, improve threat quality, and analyze attack paths. It features a React-based web interface with real-time updates via WebSocket, support for multiple LLM providers (Scaleway and Ollama), and includes a review system for human validation of AI-generated results.

## Recent Updates

### Enhanced Settings Modal System
The application now features a completely redesigned settings management system with:
- **Modular TypeScript Architecture**: Settings are now managed through separate TypeScript modules for types, constants, storage, validation, and integration
- **React-based Modal UI**: A new tabbed interface replacing the legacy modal with sections for LLM, Processing, Debug, and Pipeline Steps configuration
- **Real-time Validation**: Settings are validated before saving with detailed error messages
- **Backend Synchronization**: Settings are automatically synced with the backend and persisted across sessions
- **Step-specific Configuration**: Each pipeline step can now be configured individually with specific parameters

## File Descriptions

### Root Configuration Files

**`app.py`** - Main Flask application entry point that initializes the web server, loads environment variables, sets up CORS and WebSocket support, and registers all API routes.

**`index.html`** - Single-page application HTML that loads React, Babel, Chart.js, D3.js, Socket.io, and Mermaid.js libraries, and provides the settings modal structure.

### Python Backend Scripts

**`info_to_dfds.py`** - Step 2 pipeline script that extracts Data Flow Diagrams from uploaded documents using LLM analysis with enhanced session handling and file discovery.

**`dfd_to_threats.py`** - Step 3 pipeline script that generates threats from DFD components with async/sync processing modes and detailed progress tracking.

**`improve_threat_quality.py`** - Step 4 pipeline script that refines and enriches threats using modular services for quality improvement.

**`attack_path_analyzer.py`** - Step 5 pipeline script that analyzes attack paths using graph algorithms and generates exploit chains.

### API Routes (`api/`)

**`api/routes.py`** - Core API endpoints for health checks, configuration management, file uploads, and system status monitoring.

**`api/review_routes.py`** - Endpoints for the review system allowing human validation of AI-generated threats and DFD components.

**`api/pipeline_routes.py`** - Pipeline execution endpoints for running individual steps, checking progress, and managing pipeline state.

**`api/websockets.py`** - WebSocket handlers for real-time progress updates and review notifications.

**`api/config_routes.py`** - Configuration management endpoints for saving, loading, and resetting system settings.

### Configuration (`config/`)

**`config/settings.py`** - Central configuration management with environment variable loading, async processing settings, and debug mode options.

### Services (`services/`)

**`services/document_loader_service.py`** - Handles loading documents from Step 1 output with session-specific file handling and fallback mechanisms.

**`services/document_service.py`** - Processes file uploads, extracts text content, and ensures files are available for the pipeline.

**`services/document_analysis_service.py`** - Validates document content suitability for DFD extraction and analyzes technical terminology.

**`services/dfd_extraction_service.py`** - Orchestrates DFD extraction from documents using LLM-based analysis with quality checks.

**`services/llm_service.py`** - Provides LLM integration for DFD extraction supporting both Scaleway and Ollama providers with async capabilities.

**`services/llm_threat_service.py`** - Specialized LLM service for threat generation with progress tracking and call counting.

**`services/threat_generation_service.py`** - Main service for generating threats from DFD components (implementation not shown).

**`services/threat_quality_improvement_service.py`** - Service for refining threats with quality scoring and enrichment (implementation not shown).

**`services/attack_path_analyzer_service.py`** - Analyzes attack paths and generates exploit chains (implementation not shown).

**`services/pipeline_service.py`** - Manages pipeline execution, step transitions, and progress tracking across all stages.

**`services/review_service.py`** - Handles review item generation, similarity detection, and confidence calculations for human validation.

**`services/threat_suppression_service.py`** - Suppresses irrelevant threats based on implemented controls and CVE relevance.

**`services/validation_service.py`** - Validates pipeline outputs and data structures (implementation not shown).

**`services/mermaid_generator.py`** - Generates Mermaid diagram syntax from DFD components (implementation not shown).

**`services/external_data_service.py`** - Integrates with external data sources like MITRE ATT&CK (implementation not shown).

**`services/rag_populate.py`** - Manages Qdrant vector database for RAG functionality with document deduplication.

### Models (`models/`)

**`models/pipeline_state.py`** - Manages pipeline execution state and progress tracking (implementation not shown).

**`models/dfd_models.py`** - Data models for DFD components and structures (implementation not shown).

### Utilities (`utils/`)

**`utils/sample_documents.py`** - Generates comprehensive sample requirements documents for testing the pipeline.

**`utils/logging_utils.py`** - Provides structured logging with color coding and emojis (implementation not shown).

**`utils/progress_utils.py`** - Handles progress tracking and kill signal checking (implementation not shown).

**`utils/file_utils.py`** - File handling utilities for text extraction and validation (implementation not shown).

### Frontend JavaScript (`js/`)

**`js/main.js`** - Master JavaScript loader that orchestrates module loading, handles configuration management, initializes the React application, and now integrates with the enhanced settings system.

**`js/core-utilities.js`** - Essential utilities including API configuration, debounce/throttle functions, storage helpers, and browser compatibility checks.

**`js/ui-components.js`** - Reusable React UI components including the notification system with auto-dismiss and progress tracking.

**`js/sidebar-components.js`** - Sidebar navigation components with collapsible design, pipeline step indicators, and connection status display.

**`js/pipeline-components.js`** - Pipeline-specific components including file upload, step content display, threat/DFD viewers, and JSON syntax highlighting.

**`js/review-system.js`** - Review panel components for threat validation with decision cards, attribute selection, and comment submission.

**`js/main-app.js`** - Main React application component that manages state, WebSocket connections, and orchestrates the entire UI.

### Enhanced Settings System (`js/settings/`)

**`js/settings/types.ts`** - TypeScript type definitions for the entire settings system including LLM configuration, processing options, and validation interfaces.

**`js/settings/constants.ts`** - Constants and default values for all configuration options including LLM providers, models, and pipeline steps.

**`js/settings/storage.ts`** - Handles persistence of settings to localStorage and backend synchronization with deep merge capabilities.

**`js/settings/validation.ts`** - Comprehensive validation logic for all settings with detailed error reporting and type checking.

**`js/settings/integration.js`** - Bridges the new settings system with the legacy codebase, providing backward compatibility and initialization.

**`js/settings/SettingsModal.tsx`** - React component for the enhanced settings modal with tabbed interface, real-time validation, and auto-save functionality.

### Frontend CSS (`css/`)

**`css/main.css`** - Master CSS import file that orchestrates the entire styling system with modular architecture.

**`css/base.css`** - Foundation styles with CSS variables, typography, and browser resets (implementation not shown).

**`css/components.css`** - Reusable UI component styles for buttons, forms, cards, and modals.

**`css/sidebar.css`** - Sidebar layout styles with responsive design (implementation not shown).

**`css/pipeline-steps.css`** - Pipeline step visualization styles (implementation not shown).

**`css/notifications.css`** - Notification system styling (implementation not shown).

**`css/review-system.css`** - Review panel and decision interface styles with threat-specific formatting.

**`css/settings-styles.css`** - Styles for the enhanced settings modal including tabbed layout, form controls, and validation states.

**`css/utilities.css`** - Helper classes and utility styles (implementation not shown).

## Core Functionality

The threat modeling pipeline operates through five sequential steps:

1. **Document Upload** - Users upload security requirements documents (PDF, DOCX, TXT) which are processed and text is extracted
2. **DFD Extraction** - AI analyzes the document to identify external entities, processes, data stores, and data flows
3. **Threat Generation** - Based on the DFD, the system generates security threats using STRIDE methodology
4. **Threat Refinement** - Threats are enriched with MITRE ATT&CK mappings, CVE data, and quality improvements
5. **Attack Path Analysis** - The system analyzes potential attack chains and exploit paths

The system supports both cloud-based LLMs (Scaleway) and local models (Ollama), with async processing for improved performance. A comprehensive review system allows security experts to validate and refine AI-generated results before finalizing the threat model.