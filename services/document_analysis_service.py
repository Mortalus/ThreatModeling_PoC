"""
Service for analyzing document content and structure.
"""
import re
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

class DocumentAnalysisService:
    """Service for analyzing document content to guide DFD extraction."""
    
    @staticmethod
    def validate_document_content(content: str, filename: str = "") -> Tuple[bool, str, str]:
        """
        Validate that the document content is suitable for DFD extraction.
        Returns: (is_valid, cleaned_content, validation_message)
        """
        if not content or not isinstance(content, str):
            return False, "", "Document content is empty or invalid"
        
        # Clean the content
        content = content.strip()
        
        # Check minimum length
        min_length = 100
        if len(content) < min_length:
            return False, content, f"Document too short ({len(content)} chars, minimum {min_length})"
        
        # Check maximum length
        max_length = 1000000
        if len(content) > max_length:
            content = content[:max_length]
            logger.warning(f"Document truncated to {max_length} characters")
        
        # Check if content looks like a diagram or code rather than requirements
        diagram_indicators = [
            'graph TD', 'graph TB', 'graph LR', 'flowchart',
            'subgraph', 'classDef', 'class ',
            '<?xml', '<svg',
            'digraph', 'node [', 'edge [',
            'participant ', 'activate ', 'deactivate ',
        ]
        
        content_lower = content.lower()
        diagram_count = sum(1 for indicator in diagram_indicators if indicator in content_lower)
        
        if diagram_count >= 3:
            return False, content, f"Content appears to be a diagram/code file rather than requirements (found {diagram_count} diagram indicators)"
        
        # Check for basic technical content
        technical_indicators = [
            'system', 'user', 'data', 'process', 'service', 'application',
            'database', 'server', 'client', 'api', 'security', 'authentication',
            'requirement', 'functional', 'non-functional', 'interface',
            'architecture', 'component', 'module', 'flow'
        ]
        
        technical_count = sum(1 for indicator in technical_indicators if indicator in content_lower)
        
        if technical_count < 3:
            return False, content, f"Content lacks technical/requirements terminology (found only {technical_count} technical terms)"
        
        # Content appears valid
        return True, content, f"Valid document content ({len(content)} characters, {technical_count} technical terms)"

    @staticmethod
    def analyze_document_content(content: str) -> Dict[str, Any]:
        """Analyze document content to guide extraction."""
        content_lower = content.lower()
        
        # Detect document type
        doc_type = "technical_requirements"
        if "architecture" in content_lower:
            doc_type = "architecture_document"
        elif "api" in content_lower and ("endpoint" in content_lower or "rest" in content_lower):
            doc_type = "api_documentation"
        elif "security" in content_lower and "threat" in content_lower:
            doc_type = "security_document"
        
        # Detect industry
        industry = DocumentAnalysisService._detect_industry(content_lower)
        
        # Calculate complexity
        complexity = min(len(content) / 10000, 1.0)
        technical_terms = len(re.findall(r'\b(?:system|service|database|api|server|user|data|process)\b', content_lower))
        complexity += min(technical_terms / 50, 1.0)
        complexity = min(complexity / 2, 1.0)
        
        return {
            "document_type": doc_type,
            "industry_context": industry,
            "complexity_score": complexity,
            "content_length": len(content),
            "technical_term_count": technical_terms
        }
    
    @staticmethod
    def _detect_industry(content_lower: str) -> str:
        """Detect industry context from content."""
        industry_keywords = {
            "Financial": ["payment", "transaction", "banking", "fintech", "pci", "fraud"],
            "Healthcare": ["patient", "medical", "hipaa", "phi", "healthcare", "clinical"],
            "E-commerce": ["cart", "checkout", "order", "product", "inventory", "customer"],
            "SaaS": ["tenant", "subscription", "api", "saas", "software"]
        }
        
        for industry_name, keywords in industry_keywords.items():
            if sum(1 for keyword in keywords if keyword in content_lower) >= 2:
                return industry_name
        
        return "General"