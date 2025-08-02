"""
Main service for orchestrating DFD extraction from documents.
"""
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple
from models.dfd_models import SimpleDFDComponents
from services.document_analysis_service import DocumentAnalysisService
from services.llm_service import LLMService
from services.mermaid_generator import MermaidGenerator
from utils.file_utils import extract_text_from_file

logger = logging.getLogger(__name__)

class DFDExtractionService:
    """Main service for DFD extraction."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.doc_analyzer = DocumentAnalysisService()
        self.llm_service = LLMService(config)
        self.mermaid_generator = MermaidGenerator()
    
    def extract_from_documents(self, documents: List[str], document_info: List[str]) -> Dict[str, Any]:
        """Extract DFD from documents with improved processing."""
        
        logger.info("🚀 Starting improved DFD extraction")
        
        # Combine and analyze documents
        combined_content = "\n\n--- DOCUMENT SEPARATOR ---\n\n".join(documents)
        total_length = len(combined_content)
        
        logger.info(f"📝 Processing {total_length} characters from {len(documents)} documents")
        logger.info(f"📄 Documents: {document_info}")
        
        # Document analysis
        doc_analysis = self.doc_analyzer.analyze_document_content(combined_content)
        logger.info(f"📊 Analysis: {doc_analysis['document_type']} | {doc_analysis['industry_context']}")
        
        # Extract components
        extraction_result = self.llm_service.extract_dfd_components(combined_content, doc_analysis)
        
        if not extraction_result:
            logger.error("Component extraction failed")
            return self._create_error_result("Component extraction failed")
        
        # Validate and improve extraction
        validation_results = self._validate_extraction(extraction_result)
        
        # Convert to dictionary format
        dfd_dict = extraction_result.to_dict()
        
        # Generate Mermaid diagram
        mermaid_diagram = ""
        if self.config.get('enable_mermaid', True):
            try:
                mermaid_diagram = self.mermaid_generator.generate_threat_modeling_diagram({"dfd": dfd_dict})
                logger.info("🎨 Mermaid diagram generated successfully")
            except Exception as e:
                logger.warning(f"Mermaid generation failed: {e}")
        
        # Store global reference for frontend
        import __main__
        __main__.currentDfdData = {"dfd": dfd_dict}
        
        # Create final output
        final_result = {
            "dfd": dfd_dict,
            "mermaid": mermaid_diagram,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "extraction_version": "4.0_improved",
                "source_documents": document_info,
                "document_analysis": doc_analysis,
                "validation_results": validation_results,
                "llm_provider": self.config.get('llm_provider', 'unknown'),
                "llm_model": self.config.get('llm_model', 'unknown'),
                "total_content_length": total_length,
                "extraction_stats": self._get_extraction_stats(dfd_dict),
                "quality_indicators": self._get_quality_indicators(dfd_dict)
            }
        }
        
        logger.info("✅ DFD extraction completed successfully")
        
        return final_result
    
    def _validate_extraction(self, extraction: SimpleDFDComponents) -> Dict[str, Any]:
        """Validate extraction results."""
        validation = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "completeness_score": 0.0
        }
        
        # Check minimum components
        total_components = (len(extraction.external_entities) + 
                          len(extraction.processes) + 
                          len(extraction.assets))
        
        if total_components < 3:
            validation["errors"].append(f"Insufficient components: {total_components} < 3")
            validation["is_valid"] = False
        
        # Check data flow consistency
        all_components = set(extraction.external_entities + extraction.processes + extraction.assets)
        
        for i, flow in enumerate(extraction.data_flows):
            if hasattr(flow, 'source'):
                source = flow.source
                dest = flow.destination
            else:
                source = flow.get('source', '')
                dest = flow.get('destination', '')
            
            if source not in all_components:
                validation["errors"].append(f"Data flow {i+1}: source '{source}' not in components")
            if dest not in all_components:
                validation["errors"].append(f"Data flow {i+1}: destination '{dest}' not in components")
        
        # Calculate completeness
        factors = {
            "has_external_entities": len(extraction.external_entities) > 0,
            "has_processes": len(extraction.processes) > 0,
            "has_assets": len(extraction.assets) > 0,
            "has_data_flows": len(extraction.data_flows) > 0,
            "has_trust_boundaries": len(extraction.trust_boundaries) > 0
        }
        
        validation["completeness_score"] = sum(factors.values()) / len(factors)
        
        logger.info(f"🔍 Validation: {len(validation['errors'])} errors, {len(validation['warnings'])} warnings")
        
        return validation
    
    def _get_extraction_stats(self, dfd_dict: Dict) -> Dict[str, int]:
        """Get extraction statistics."""
        return {
            "external_entities": len(dfd_dict.get('external_entities', [])),
            "processes": len(dfd_dict.get('processes', [])),
            "assets": len(dfd_dict.get('assets', [])),
            "data_flows": len(dfd_dict.get('data_flows', [])),
            "trust_boundaries": len(dfd_dict.get('trust_boundaries', []))
        }
    
    def _get_quality_indicators(self, dfd_dict: Dict) -> Dict[str, bool]:
        """Get quality indicators."""
        return {
            "has_trust_boundaries": len(dfd_dict.get('trust_boundaries', [])) > 0,
            "has_data_classification": any(
                flow.get('data_classification') not in ['Unknown', 'Internal'] 
                for flow in dfd_dict.get('data_flows', [])
            ),
            "has_authentication": any(
                flow.get('authentication_mechanism') not in ['Unknown', 'None']
                for flow in dfd_dict.get('data_flows', [])
            )
        }
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result structure."""
        return {
            "dfd": {
                "project_name": "Error",
                "project_version": "1.0",
                "industry_context": "unknown",
                "external_entities": [],
                "processes": [],
                "assets": [],
                "trust_boundaries": [],
                "data_flows": [],
                "error": error_message
            },
            "mermaid": "",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "error": error_message,
                "extraction_version": "4.0_improved",
                "status": "failed"
            }
        }