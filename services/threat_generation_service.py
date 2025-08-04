"""
Main service for orchestrating threat generation from DFD.
Enhanced with async processing, detailed progress tracking, and proper error handling.
"""
import os
import json
import logging
import time
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from models.threat_models import ThreatModel, ComponentAnalysis
from services.component_risk_analyzer import ComponentRiskAnalyzer
from services.stride_threat_generator import StrideThreatGenerator
from services.threat_deduplication_service import ThreatDeduplicationService

logger = logging.getLogger(__name__)

class ThreatGenerationService:
    """Main service for threat generation with async support."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.risk_analyzer = ComponentRiskAnalyzer(
            min_risk_score=config.get('min_risk_score', 3)
        )
        self.threat_generator = StrideThreatGenerator(config)
        self.dedup_service = ThreatDeduplicationService(
            similarity_threshold=config.get('similarity_threshold', 0.70)
        )
    
    def generate_threats_from_dfd(self, dfd_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate threats from DFD data using sync or async mode."""
        if self.config.get('enable_async_processing', True):
            logger.info("⚡ Using async processing for threat generation")
            return asyncio.run(self._generate_threats_async(dfd_data))
        else:
            logger.info("🔄 Using sync processing for threat generation")
            return self._generate_threats_sync(dfd_data)
    
    def _generate_threats_sync(self, dfd_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate threats synchronously."""
        logger.info("=== Starting Realistic Threat Modeling Analysis (Sync) ===")
        start_time = time.time()
        
        # Extract and analyze components
        components = self.risk_analyzer.analyze_components(dfd_data)
        
        # Filter to only analyze high-risk components
        high_risk_components = [
            c for c in components 
            if self.risk_analyzer.should_analyze_component(c)
        ]
        
        # Limit total components to analyze
        max_components = self.config.get('max_components_to_analyze', 20)
        if len(high_risk_components) > max_components:
            logger.info(f"Limiting analysis to top {max_components} highest risk components")
            high_risk_components = high_risk_components[:max_components]
        
        logger.info(f"Total components: {len(components)}")
        logger.info(f"High-risk components to analyze: {len(high_risk_components)}")
        
        # Calculate expected LLM calls for progress tracking
        expected_calls = self._calculate_expected_calls(high_risk_components)
        self.threat_generator.set_expected_calls(expected_calls)
        
        # Log component breakdown
        self._log_component_breakdown(components)
        
        # Generate threats for each component
        all_threats = []
        
        for i, component in enumerate(high_risk_components):
            logger.info(f"Analyzing component {i+1}/{len(high_risk_components)}: {component.name}")
            
            try:
                threats = self.threat_generator.generate_threats_for_component(component)
                all_threats.extend(threats)
                
                # Rate limiting for better quality if using LLM
                if self.config.get('llm_provider') and i < len(high_risk_components) - 1:
                    time.sleep(1)
                    
            except Exception as e:
                if self.config.get('debug_mode', False):
                    logger.warning(f"⚠️ Failed to generate threats for {component.name}: {e}")
                    continue
                else:
                    logger.error(f"❌ Failed to generate threats for {component.name}: {e}")
                    raise
        
        elapsed = time.time() - start_time
        logger.info(f"Generated {len(all_threats)} initial threats in {elapsed:.1f}s")
        
        return self._post_process_threats(all_threats, dfd_data, components, high_risk_components)
    
    async def _generate_threats_async(self, dfd_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate threats asynchronously with concurrent processing."""
        logger.info("=== Starting Realistic Threat Modeling Analysis (Async) ===")
        start_time = time.time()
        
        # Extract and analyze components
        components = self.risk_analyzer.analyze_components(dfd_data)
        
        # Filter to only analyze high-risk components
        high_risk_components = [
            c for c in components 
            if self.risk_analyzer.should_analyze_component(c)
        ]
        
        # Limit total components to analyze
        max_components = self.config.get('max_components_to_analyze', 20)
        if len(high_risk_components) > max_components:
            logger.info(f"Limiting analysis to top {max_components} highest risk components")
            high_risk_components = high_risk_components[:max_components]
        
        logger.info(f"Total components: {len(components)}")
        logger.info(f"High-risk components to analyze: {len(high_risk_components)}")
        
        # Calculate expected LLM calls for progress tracking
        expected_calls = self._calculate_expected_calls(high_risk_components)
        self.threat_generator.set_expected_calls(expected_calls)
        
        # Log component breakdown
        self._log_component_breakdown(components)
        
        # Generate all component-category combinations for batch processing
        component_categories = []
        for component in high_risk_components:
            stride_categories = self.threat_generator.get_stride_categories_for_component(component)
            for cat_letter, (cat_name, cat_def) in stride_categories.items():
                component_categories.append((component, cat_letter, cat_name, cat_def))
        
        logger.info(f"⚡ Processing {len(component_categories)} threat generation tasks concurrently")
        
        try:
            # Use the LLM service's batch processing method
            all_threats = await self.threat_generator.generate_threats_for_components_batch(component_categories)
            
            elapsed = time.time() - start_time
            logger.info(f"Generated {len(all_threats)} initial threats in {elapsed:.1f}s (async)")
            
            return self._post_process_threats(all_threats, dfd_data, components, high_risk_components)
            
        except Exception as e:
            if self.config.get('debug_mode', False):
                logger.warning(f"⚠️ Async threat generation failed: {e} - falling back to sync")
                return self._generate_threats_sync(dfd_data)
            else:
                logger.error(f"❌ Async threat generation failed: {e}")
                raise
    
    def _calculate_expected_calls(self, components: List[ComponentAnalysis]) -> int:
        """Calculate the expected number of LLM calls for progress tracking."""
        total_calls = 0
        for component in components:
            # Each component gets analyzed for applicable STRIDE categories
            stride_categories = self.threat_generator.get_stride_categories_for_component(component)
            total_calls += len(stride_categories)
        
        logger.info(f"📊 Calculated {total_calls} expected LLM calls for {len(components)} components")
        return total_calls
    
    def _post_process_threats(self, all_threats: List[ThreatModel], dfd_data: Dict[str, Any], 
                            all_components: List[ComponentAnalysis], 
                            analyzed_components: List[ComponentAnalysis]) -> Dict[str, Any]:
        """Post-process threats: deduplicate, filter, and create output."""
        logger.info(f"Starting post-processing of {len(all_threats)} threats")
        
        # Deduplicate threats
        pre_dedup_count = len(all_threats)
        all_threats = self.dedup_service.deduplicate_threats(all_threats)
        logger.info(f"After deduplication: {len(all_threats)} threats (removed {pre_dedup_count - len(all_threats)})")
        
        # Filter low-quality threats
        pre_filter_count = len(all_threats)
        all_threats = self.dedup_service.filter_quality_threats(all_threats)
        logger.info(f"After quality filtering: {len(all_threats)} threats (removed {pre_filter_count - len(all_threats)})")
        
        # Sort by risk score
        risk_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        all_threats.sort(key=lambda t: risk_order.get(t.risk_score, 0), reverse=True)
        
        # Create output structure
        return self._create_output(all_threats, dfd_data, all_components, analyzed_components)
    
    def _log_component_breakdown(self, components: List[ComponentAnalysis]):
        """Log component type breakdown."""
        component_types = {}
        for comp in components:
            comp_type = comp.type
            component_types[comp_type] = component_types.get(comp_type, 0) + 1
        
        logger.info("Component breakdown:")
        for comp_type, count in component_types.items():
            logger.info(f"  - {comp_type}: {count}")
    
    def _create_output(self, threats: List[ThreatModel], dfd_data: Dict, 
                      all_components: List[ComponentAnalysis], 
                      analyzed_components: List[ComponentAnalysis]) -> Dict[str, Any]:
        """Create comprehensive output structure."""
        # Convert threats to dictionaries
        threat_dicts = [threat.to_dict() for threat in threats]
        
        # Calculate risk breakdown
        risk_breakdown = {
            "Critical": sum(1 for t in threats if t.risk_score == 'Critical'),
            "High": sum(1 for t in threats if t.risk_score == 'High'),
            "Medium": sum(1 for t in threats if t.risk_score == 'Medium'),
            "Low": sum(1 for t in threats if t.risk_score == 'Low')
        }
        
        # Determine generation method
        generation_method = "LLM"
        if self.config.get('force_rule_based', False):
            generation_method = "Rule-based"
        elif not self.threat_generator.llm_service.is_available():
            generation_method = "Rule-based (fallback)"
        
        # Determine processing mode
        processing_mode = "Async" if self.config.get('enable_async_processing', True) else "Sync"
        if self.config.get('enable_async_processing', True) and generation_method.startswith("Rule-based"):
            processing_mode = "Sync (fallback)"
        
        return {
            "threats": threat_dicts,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "source_dfd": os.path.basename(self.config.get('dfd_input_path', '')),
                "llm_provider": self.config.get('llm_provider', 'unknown'),
                "llm_model": self.config.get('llm_model', 'unknown'),
                "total_threats": len(threats),
                "total_components": len(all_components),
                "components_analyzed": len(analyzed_components),
                "generation_method": generation_method,
                "processing_mode": processing_mode,
                "analysis_approach": "Risk-based with STRIDE filtering",
                "min_risk_score": self.config.get('min_risk_score', 3),
                "max_components_analyzed": self.config.get('max_components_to_analyze', 20),
                "max_concurrent_calls": self.config.get('max_concurrent_calls', 5),
                "debug_mode": self.config.get('debug_mode', False),
                "async_enabled": self.config.get('enable_async_processing', True),
                "detailed_logging": self.config.get('detailed_llm_logging', True),
                "risk_breakdown": risk_breakdown,
                "dfd_structure": {
                    "project_name": dfd_data.get('project_name', 'Unknown'),
                    "industry_context": dfd_data.get('industry_context', 'Unknown')
                }
            }
        }