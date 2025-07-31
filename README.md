# ThreatModeling_PoC

Step 1:

Script Overview
This script is an automated DFD (Data Flow Diagram) component extractor that:

Loads documents from various sources (TXT and PDF files)
Uses LLM (Large Language Model) to extract structured information
Validates the extracted data against a predefined schema
Outputs a standardized JSON representation of DFD components

Key Components:

Multiple LLM Provider Support: Can use either Ollama (local) or Scaleway (cloud) as the LLM backend
Document Processing: Handles both text and PDF files
Structured Output: Uses the instructor library to ensure LLM outputs conform to Pydantic models
Validation: Ensures extracted data matches the expected DFD schema
Logging: Comprehensive logging of the process including token usage

The Process Flow:

Initialize the appropriate LLM client based on configuration
Load all documents from the input directory
Combine documents and send to LLM with a detailed prompt
Extract structured DFD components (entities, processes, data flows, etc.)
Validate the output against the schema
Save the results as JSON with metadata

Step 2:

Script Overview
This script is a sophisticated AI-powered Threat Modeling Engine that:

Loads DFD components from the output of the previous script
Analyzes each component using STRIDE methodology
Enriches analysis with RAG (Retrieval Augmented Generation) from Qdrant vector database
Augments with web search for current security context
Generates specific threats with risk assessments and mitigations
Processes in parallel for efficiency
Outputs structured threat report with metadata

Key Features:

Multi-LLM Support: Can use Scaleway (cloud) or Ollama (local) LLMs
RAG Integration: Uses Qdrant vector database for historical threat knowledge
Web Search Enhancement: DuckDuckGo integration for current security intelligence
Parallel Processing: Configurable thread pool for analyzing multiple components simultaneously
STRIDE Framework: Systematic analysis across all six threat categories
Risk Scoring: Automatic risk calculation based on impact and likelihood
Caching: Web search results are cached to avoid redundant queries
Extensible: Custom STRIDE definitions can be loaded from configuration

The Process Flow:

Initialize LLM, RAG, and Web Search clients
Load DFD components from JSON
Extract and categorize all analyzable components
For each component, analyze against all STRIDE categories:

Query RAG for similar historical threats
Search web for current vulnerabilities
Generate context-aware threats using LLM


Deduplicate and sort threats by risk score
Output comprehensive threat report

Step 3:

Script Overview
This script is an advanced AI Threat Model Refinement System that:

Deduplicates threats using semantic similarity clustering
Standardizes component names against DFD data
Suppresses irrelevant threats based on implemented controls
Filters outdated CVEs using age and CISA KEV catalog
Enriches threats with business risk context
Calculates residual risk after mitigation
Generates risk statements tailored to the industry

Key Features:

Semantic Deduplication: Uses Sentence Transformers and DBSCAN clustering to identify similar threats
Control-Based Suppression: Automatically suppresses threats mitigated by existing controls (mTLS, WAF, secrets manager)
CVE Intelligence: Integrates with CISA Known Exploited Vulnerabilities catalog
Risk Matrixing: Multi-dimensional risk assessment including exploitability and mitigation maturity
Industry Context: Tailors risk statements for specific industries (Finance, Healthcare)
Async Operations: Efficient external API calls with caching and retry logic
Comprehensive Validation: Pydantic models ensure data quality throughout

The Process Flow:

Load threats, DFD components, and security controls
Fetch external threat intelligence (CISA KEV)
Standardize component names to match DFD
Suppress threats based on:

Implemented security controls
Outdated/irrelevant CVEs


Deduplicate similar threats using ML clustering
Enrich each threat with:

Exploitability assessment
Mitigation maturity rating
Business impact justification
Residual risk calculation


Generate industry-specific risk statements
Output refined, prioritized threat model
