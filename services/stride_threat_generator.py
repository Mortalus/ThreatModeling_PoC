"""
STRIDE-based threat generator with LLM integration.
Enhanced with async support and detailed progress tracking.
"""
import logging
import asyncio
from typing import List, Dict, Any, Tuple, Optional, Callable
from models.threat_models import ThreatModel, ComponentAnalysis, DEFAULT_STRIDE_DEFINITIONS
from services.llm_threat_service import LLMThreatService
from services.rule_based_threat_generator import RuleBasedThreatGenerator

logger = logging.getLogger(__name__)

class StrideThreatGenerator:
    """STRIDE-based threat generator with async support."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.stride_definitions = self._load_stride_definitions()
        
        # Component type to STRIDE category mappings
        self.component_stride_mappings = {
            'External Entity': ['S', 'R'],
            'Process': ['S', 'T', 'R', 'I', 'D', 'E'],
            'Data Store': ['T', 'R', 'I', 'D'],
            'Data Flow': ['T', 'I', 'D'],
            'Trust Boundary': ['S', 'T', 'E'],
            'Asset': ['T', 'I', 'D'],
            'Database': ['T', 'R', 'I', 'D'],
            'API': ['S', 'T', 'R', 'I', 'D', 'E'],
            'Service': ['S', 'T', 'R', 'I', 'D', 'E'],
            'Unknown': ['S', 'T', 'R', 'I', 'D', 'E']  # Default for unknown types
        }
        
        # Initialize services
        self.llm_service = LLMThreatService(config, self.stride_definitions)
        self.rule_generator = RuleBasedThreatGenerator(self.stride_definitions)
        
        # Progress tracking
        self.expected_calls = 0
        self.completed_calls = 0
        self.progress_callback: Optional[Callable] = None
    
    def _load_stride_definitions(self) -> Dict[str, Tuple[str, str]]:
        """Load STRIDE definitions from config or use defaults."""
        # Could load from file if available
        return DEFAULT_STRIDE_DEFINITIONS
    
    def set_expected_calls(self, count: int):
        """Set expected number of LLM calls for progress tracking."""
        self.expected_calls = count
        self.completed_calls = 0
        self.llm_service.set_expected_calls(count)
    
    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates."""
        self.progress_callback = callback
        if hasattr(self.llm_service, 'set_progress_callback'):
            self.llm_service.set_progress_callback(callback)
    
    def get_stride_categories_for_component(self, component: ComponentAnalysis) -> Dict[str, Tuple[str, str]]:
        """Get applicable STRIDE categories for a component."""
        component_type = component.type
        
        # Get applicable STRIDE categories for this component type
        applicable_categories = self.component_stride_mappings.get(
            component_type, 
            self.component_stride_mappings['Unknown']
        )
        
        # Return dictionary with category details
        categories = {}
        for cat_letter in applicable_categories:
            if cat_letter in self.stride_definitions:
                cat_name, cat_def = self.stride_definitions[cat_letter]
                categories[cat_letter] = (cat_name, cat_def)
        
        return categories
    
    def generate_threats_for_component(self, component: ComponentAnalysis) -> List[ThreatModel]:
        """Generate threats for a single component using sync processing."""
        logger.info(f"Generating threats for component: {component.name} ({component.type})")
        
        # Get applicable STRIDE categories
        stride_categories = self.get_stride_categories_for_component(component)
        
        all_threats = []
        
        # Generate threats for each applicable STRIDE category
        for cat_letter, (cat_name, cat_def) in stride_categories.items():
            try:
                if self.config.get('force_rule_based', False) or not self.llm_service.is_available():
                    # Use rule-based generation
                    threats = self.rule_generator.generate_threats(component, cat_letter, cat_name, cat_def)
                else:
                    # Use LLM for threat generation
                    threats = self.llm_service.generate_threats(component, cat_letter, cat_name, cat_def)
                
                all_threats.extend(threats)
                
                # Update progress
                self.completed_calls += 1
                if self.progress_callback:
                    self.progress_callback(
                        self.completed_calls, 
                        f"Generated {cat_name} threats for {component.name}"
                    )
                
            except Exception as e:
                if self.config.get('debug_mode', False):
                    logger.warning(f"⚠️ Failed to generate {cat_name} threats for {component.name}: {e}")
                    # Try rule-based as fallback in debug mode
                    try:
                        fallback_threats = self.rule_generator.generate_threats(component, cat_letter, cat_name, cat_def)
                        all_threats.extend(fallback_threats)
                    except:
                        pass
                else:
                    logger.error(f"❌ Failed to generate {cat_name} threats for {component.name}: {e}")
                    raise
        
        logger.info(f"Generated {len(all_threats)} threats for {component.name}")
        return all_threats
    
    async def generate_threats_for_components_batch(self, 
                                                  component_categories: List[Tuple[ComponentAnalysis, str, str, str]]) -> List[ThreatModel]:
        """Generate threats for multiple component-category combinations using async processing."""
        logger.info(f"⚡ Starting batch threat generation for {len(component_categories)} tasks")
        
        if not self.config.get('enable_async_processing', True):
            # Fall back to sequential processing
            logger.info("🔄 Async disabled, using sequential processing")
            return self._generate_threats_sequential(component_categories)
        
        if self.config.get('force_rule_based', False) or not self.llm_service.is_available():
            logger.info("🔧 Using rule-based generation")
            return self._generate_threats_rule_based_batch(component_categories)
        
        try:
            # Use the LLM service's batch processing
            return await self.llm_service.generate_threats_for_components_batch(component_categories)
        except Exception as e:
            if self.config.get('debug_mode', False):
                logger.warning(f"⚠️ Batch async generation failed: {e} - falling back to sequential")
                return self._generate_threats_sequential(component_categories)
            else:
                logger.error(f"❌ Batch async generation failed: {e}")
                raise
    
    def _generate_threats_sequential(self, 
                                   component_categories: List[Tuple[ComponentAnalysis, str, str, str]]) -> List[ThreatModel]:
        """Generate threats sequentially for fallback scenarios."""
        all_threats = []
        
        for component, cat_letter, cat_name, cat_def in component_categories:
            try:
                if self.config.get('force_rule_based', False) or not self.llm_service.is_available():
                    threats = self.rule_generator.generate_threats(component, cat_letter, cat_name, cat_def)
                else:
                    threats = self.llm_service.generate_threats(component, cat_letter, cat_name, cat_def)
                
                all_threats.extend(threats)
                
                # Update progress
                self.completed_calls += 1
                if self.progress_callback:
                    self.progress_callback(
                        self.completed_calls,
                        f"Generated {cat_name} threats for {component.name}"
                    )
                
            except Exception as e:
                if self.config.get('debug_mode', False):
                    logger.warning(f"⚠️ Failed to generate {cat_name} threats for {component.name}: {e}")
                    try:
                        fallback_threats = self.rule_generator.generate_threats(component, cat_letter, cat_name, cat_def)
                        all_threats.extend(fallback_threats)
                    except:
                        pass
                else:
                    logger.error(f"❌ Failed to generate {cat_name} threats for {component.name}: {e}")
                    raise
        
        return all_threats
    
    def _generate_threats_rule_based_batch(self, 
                                         component_categories: List[Tuple[ComponentAnalysis, str, str, str]]) -> List[ThreatModel]:
        """Generate threats using rule-based approach for all component-category combinations."""
        all_threats = []
        
        for component, cat_letter, cat_name, cat_def in component_categories:
            try:
                threats = self.rule_generator.generate_threats(component, cat_letter, cat_name, cat_def)
                all_threats.extend(threats)
                
                # Update progress
                self.completed_calls += 1
                if self.progress_callback:
                    self.progress_callback(
                        self.completed_calls,
                        f"Generated {cat_name} threats for {component.name} (rule-based)"
                    )
                    
            except Exception as e:
                logger.error(f"Rule-based generation failed for {component.name}: {e}")
                if not self.config.get('debug_mode', False):
                    raise
        
        return all_threats