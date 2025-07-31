#!/usr/bin/env python3
# attack_path_analyzer.py

"""
Attack Path Analysis Module for Threat Modeling Pipeline
Analyzes refined threats to identify and score potential attack chains
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
import networkx as nx
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import hashlib

from dotenv import load_dotenv
from openai import OpenAI
import ollama

# Load environment variables
load_dotenv()

# Enums for better type safety
class ThreatLikelihood(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

class ThreatImpact(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class PathFeasibility(str, Enum):
    THEORETICAL = "Theoretical"
    REALISTIC = "Realistic"
    HIGHLY_LIKELY = "Highly Likely"

class AttackerProfile(str, Enum):
    SCRIPT_KIDDIE = "Script Kiddie"
    CYBERCRIMINAL = "Cybercriminal"
    APT = "APT"
    INSIDER = "Insider"

class TimeToCompromise(str, Enum):
    HOURS = "Hours"
    DAYS = "Days"
    WEEKS = "Weeks"
    MONTHS = "Months"

# Configuration
@dataclass
class Config:
    """Configuration for attack path analysis."""
    # Paths
    input_dir: str = field(default_factory=lambda: os.getenv("INPUT_DIR", "./output"))
    refined_threats_path: str = field(default="")
    dfd_path: str = field(default="")
    attack_paths_output: str = field(default="")
    
    # LLM Configuration
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "scaleway").lower())
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "llama-3.3-70b-instruct"))
    scaleway_api_key: str = field(default_factory=lambda: os.getenv("SCALEWAY_API_KEY", os.getenv("SCW_API_KEY", "")))
    scaleway_project_id: str = field(default_factory=lambda: os.getenv("SCALEWAY_PROJECT_ID", "4a8fd76b-8606-46e6-afe6-617ce8eeb948"))
    
    # Analysis parameters
    max_path_length: int = field(default_factory=lambda: int(os.getenv("MAX_PATH_LENGTH", "5")))
    min_path_likelihood: str = field(default_factory=lambda: os.getenv("MIN_PATH_LIKELIHOOD", "Low"))
    focus_on_critical_assets: bool = field(default_factory=lambda: os.getenv("FOCUS_CRITICAL_ASSETS", "true").lower() == "true")
    max_paths_to_analyze: int = field(default_factory=lambda: int(os.getenv("MAX_PATHS_TO_ANALYZE", "20")))
    enable_llm_enrichment: bool = field(default_factory=lambda: os.getenv("ENABLE_LLM_ENRICHMENT", "true").lower() == "true")
    
    # Vector store configuration
    enable_vector_store: bool = field(default_factory=lambda: os.getenv("ENABLE_VECTOR_STORE", "true").lower() == "true")
    qdrant_url: str = field(default_factory=lambda: os.getenv("QDRANT_URL", "http://homebase:6333"))
    qdrant_api_key: Optional[str] = field(default_factory=lambda: os.getenv("QDRANT_API_KEY"))
    project_name: str = field(default_factory=lambda: os.getenv("PROJECT_NAME", "Unknown Project"))
    project_industry: str = field(default_factory=lambda: os.getenv("PROJECT_INDUSTRY", "General"))
    project_tech_stack: str = field(default_factory=lambda: os.getenv("PROJECT_TECH_STACK", ""))
    project_compliance: str = field(default_factory=lambda: os.getenv("PROJECT_COMPLIANCE", ""))
    
    def __post_init__(self):
        """Initialize derived paths if not set."""
        if not self.refined_threats_path:
            self.refined_threats_path = os.path.join(self.input_dir, "refined_threats.json")
        if not self.dfd_path:
            self.dfd_path = os.path.join(self.input_dir, "dfd_components.json")
        if not self.attack_paths_output:
            self.attack_paths_output = os.path.join(self.input_dir, "attack_paths.json")
        
        # Validate paths exist
        if not os.path.exists(self.refined_threats_path):
            raise FileNotFoundError(f"Refined threats file not found: {self.refined_threats_path}")
        if not os.path.exists(self.dfd_path):
            raise FileNotFoundError(f"DFD file not found: {self.dfd_path}")

# Pydantic Models with validation
class AttackStep(BaseModel):
    step_number: int
    component: str
    threat_id: str
    threat_description: str
    stride_category: str
    technique_id: Optional[str] = Field(None, description="MITRE ATT&CK technique")
    prerequisites: List[str] = Field(default_factory=list)
    enables: List[str] = Field(default_factory=list)
    required_access: Optional[str] = Field(None, description="Required access level")
    detection_difficulty: Optional[str] = Field(None, description="How hard to detect: Easy/Medium/Hard")
    
    @field_validator('stride_category')
    @classmethod
    def validate_stride(cls, v):
        valid_categories = ['S', 'T', 'R', 'I', 'D', 'E']
        if v not in valid_categories:
            raise ValueError(f"Invalid STRIDE category: {v}")
        return v

class AttackPath(BaseModel):
    path_id: str
    scenario_name: str
    entry_point: str
    target_asset: str
    path_steps: List[AttackStep]
    total_steps: int
    combined_likelihood: ThreatLikelihood
    combined_impact: ThreatImpact
    path_feasibility: PathFeasibility
    attacker_profile: AttackerProfile
    time_to_compromise: TimeToCompromise
    key_chokepoints: List[str] = Field(description="Critical controls that would block this path")
    detection_opportunities: List[str] = Field(default_factory=list, description="Where detection is possible")
    required_resources: List[str] = Field(default_factory=list, description="Attacker resources needed")
    path_complexity: str = Field(default="Medium", description="Low/Medium/High complexity")
    
    @field_validator('path_id')
    @classmethod
    def validate_path_id(cls, v):
        if not v.startswith('AP_'):
            raise ValueError("Path ID must start with 'AP_'")
        return v

class ThreatRelationship(BaseModel):
    from_threat: str
    to_threat: str
    relationship_type: str
    explanation: str
    required_capability: str
    
    @field_validator('relationship_type')
    @classmethod
    def validate_relationship_type(cls, v):
        valid_types = ['enables', 'requires', 'blocks', 'amplifies']
        if v not in valid_types:
            raise ValueError(f"Invalid relationship type: {v}")
        return v

class AttackPathAnalysis(BaseModel):
    attack_paths: List[AttackPath]
    critical_scenarios: List[str]
    defense_priorities: List[Dict[str, Any]]
    threat_coverage: Dict[str, Any] = Field(default_factory=dict, description="How many threats are covered")
    vector_store_insights: Optional[Dict[str, Any]] = Field(default=None, description="Insights from vector store")
    metadata: Dict[str, Any]

# Enhanced LLM Client with retry logic
class LLMClient:
    """LLM client with improved error handling and retry logic."""
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.LLMClient")
        self.client = self._init_client()
        self.max_retries = 3
    
    def _init_client(self):
        if self.config.llm_provider == "scaleway":
            if not self.config.scaleway_api_key:
                raise ValueError("Scaleway API key required")
            return OpenAI(
                base_url=f"https://api.scaleway.ai/{self.config.scaleway_project_id}/v1",
                api_key=self.config.scaleway_api_key
            )
        return None
    
    def _call_llm_with_retry(self, prompt: str, temperature: float = 0.3) -> str:
        """Call LLM with retry logic."""
        for attempt in range(self.max_retries):
            try:
                if self.config.llm_provider == "scaleway":
                    response = self.client.chat.completions.create(
                        model=self.config.llm_model,
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"},
                        temperature=temperature,
                        max_tokens=2000
                    )
                    return response.choices[0].message.content
                else:
                    response = ollama.generate(
                        model=self.config.llm_model,
                        prompt=prompt + "\n\nOutput only valid JSON.",
                        options={"temperature": temperature}
                    )
                    return response['response']
            except Exception as e:
                self.logger.warning(f"LLM call failed (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise
        return "{}"
    
    def analyze_threat_relationships(self, threats: List[Dict], dfd_data: Dict) -> List[ThreatRelationship]:
        """Use LLM to identify threat relationships and dependencies."""
        prompt = f"""You are a cybersecurity expert analyzing threat relationships for attack path modeling.

Given these threats and system components, identify:
1. Which threats could enable other threats (prerequisite relationships)
2. Natural attack progression between components
3. Required attacker capabilities for each progression

System Architecture:
{json.dumps(dfd_data, indent=2)}

Identified Threats (showing first 20):
{json.dumps(threats[:20], indent=2)}

For each meaningful threat relationship, output a JSON object:
{{
    "relationships": [
        {{
            "from_threat": "threat_id_1",
            "to_threat": "threat_id_2",
            "relationship_type": "enables|requires|blocks|amplifies",
            "explanation": "why this relationship exists",
            "required_capability": "what attacker needs"
        }}
    ]
}}

Focus on realistic attack progressions that would occur in real-world scenarios.
Consider:
- Initial access threats that enable lateral movement
- Privilege escalation enabling data access
- Information disclosure enabling further attacks
- Defense evasion techniques enabling persistence"""

        try:
            response = self._call_llm_with_retry(prompt, temperature=0.3)
            data = json.loads(response)
            relationships = []
            for rel in data.get('relationships', []):
                try:
                    relationships.append(ThreatRelationship(**rel))
                except Exception as e:
                    self.logger.warning(f"Invalid relationship data: {e}")
            return relationships
        except Exception as e:
            self.logger.error(f"Failed to analyze threat relationships: {e}")
            return []
    
    def analyze_attack_scenario(self, path: List[Dict], dfd_data: Dict) -> Dict[str, Any]:
        """Analyze a specific attack path for feasibility and details."""
        prompt = f"""You are a cybersecurity expert evaluating an attack path.

Attack Path:
{json.dumps(path, indent=2)}

System Context:
- Industry: {dfd_data.get('industry_context', 'General')}
- Key Assets: {', '.join(dfd_data.get('assets', []))}

Analyze this attack path and provide a realistic assessment:
{{
    "scenario_name": "descriptive name for this attack (e.g., 'Credential Theft to Database Breach')",
    "attacker_profile": "Script Kiddie|Cybercriminal|APT|Insider",
    "path_feasibility": "Theoretical|Realistic|Highly Likely",
    "time_to_compromise": "Hours|Days|Weeks|Months",
    "combined_likelihood": "Low|Medium|High",
    "key_chokepoints": ["specific defensive controls that would stop this"],
    "detection_opportunities": ["specific detection points in the attack chain"],
    "required_resources": ["tools, skills, or resources the attacker needs"],
    "similar_incidents": ["real-world examples if applicable"],
    "path_complexity": "Low|Medium|High",
    "expert_assessment": "paragraph explaining why this attack path matters"
}}

Consider real-world factors like:
- Required attacker sophistication
- Common defensive controls
- Detection capabilities
- Time and resource investment"""

        try:
            response = self._call_llm_with_retry(prompt, temperature=0.4)
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Failed to analyze attack scenario: {e}")
            return {}

# Enhanced Attack Path Analyzer
class AttackPathAnalyzer:
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.AttackPathAnalyzer")
        self.llm = LLMClient(config) if config.enable_llm_enrichment else None
        self.graph = nx.DiGraph()
        self.threat_map = {}
        self.component_threats = defaultdict(list)
        self.threat_graph = nx.DiGraph()
        
    def load_data(self) -> Tuple[List[Dict], Dict]:
        """Load refined threats and DFD data with validation."""
        try:
            with open(self.config.refined_threats_path, 'r') as f:
                threats_data = json.load(f)
            threats = threats_data.get('threats', [])
            
            with open(self.config.dfd_path, 'r') as f:
                dfd_data = json.load(f)
                
            # Handle nested DFD structure
            if 'dfd' in dfd_data:
                dfd_data = dfd_data['dfd']
                
            # Validate data
            if not threats:
                raise ValueError("No threats found in refined threats file")
            if not any([dfd_data.get('external_entities'), dfd_data.get('processes'), 
                       dfd_data.get('assets')]):
                raise ValueError("No components found in DFD file")
                
            return threats, dfd_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in input files: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load data: {e}")
            raise
    
    def build_component_graph(self, dfd_data: Dict) -> nx.DiGraph():
        """Build a directed graph of system components from DFD."""
        G = nx.DiGraph()
        
        # Track all components for validation
        all_components = set()
        
        # Add external entities
        for entity in dfd_data.get('external_entities', []):
            G.add_node(entity, type='external_entity', 
                      criticality='high' if entity == 'U' else 'medium',
                      trust_level='untrusted')
            all_components.add(entity)
            
        # Add processes
        for process in dfd_data.get('processes', []):
            G.add_node(process, type='process', criticality='medium',
                      trust_level='semi-trusted')
            all_components.add(process)
            
        # Add assets
        for asset in dfd_data.get('assets', []):
            G.add_node(asset, type='asset', criticality='critical',
                      trust_level='trusted')
            all_components.add(asset)
            
        # Add edges from data flows with enhanced metadata
        for flow in dfd_data.get('data_flows', []):
            if isinstance(flow, dict) and 'source' in flow and 'destination' in flow:
                source = flow['source']
                dest = flow['destination']
                
                # Validate components exist
                if source in all_components and dest in all_components:
                    G.add_edge(
                        source, dest,
                        data_classification=flow.get('data_classification', 'Unknown'),
                        protocol=flow.get('protocol', 'Unknown'),
                        authentication=flow.get('authentication', 'Unknown'),
                        encryption=flow.get('encryption', False)
                    )
                    
                    # Add reverse edge for bidirectional communication
                    if flow.get('bidirectional', True):
                        G.add_edge(dest, source,
                                 data_classification=flow.get('data_classification', 'Unknown'),
                                 protocol=flow.get('protocol', 'Unknown'))
                else:
                    self.logger.warning(f"Skipping flow from {source} to {dest} - component not found")
                    
        return G
    
    def map_threats_to_components(self, threats: List[Dict]) -> Dict[str, List[Dict]]:
        """Map threats to their components with improved extraction."""
        component_mapping = defaultdict(list)
        
        for i, threat in enumerate(threats):
            # Ensure threat has an ID
            if 'threat_id' not in threat:
                threat['threat_id'] = f"T{i:03d}"
            
            threat_id = threat['threat_id']
            self.threat_map[threat_id] = threat
            
            # Extract component(s) from threat
            components = self.extract_components_from_threat(threat)
            for component in components:
                component_mapping[component].append(threat)
                self.component_threats[component].append(threat)
                
        self.logger.info(f"Mapped threats to {len(component_mapping)} components")
        return dict(component_mapping)
    
    def extract_components_from_threat(self, threat: Dict) -> List[str]:
        """Extract all components mentioned in a threat."""
        components = []
        component_name = threat.get('component_name', '')
        
        # Handle data flow format "A to B"
        if ' to ' in component_name:
            parts = component_name.split(' to ')
            components.extend([p.strip() for p in parts])
        elif component_name:
            components.append(component_name.strip())
            
        # Also check threat description for component mentions
        description = threat.get('threat_description', '')
        for node in self.graph.nodes():
            if node in description and node not in components:
                components.append(node)
                
        return components
    
    def build_threat_graph(self, threats: List[Dict], relationships: List[ThreatRelationship]) -> nx.DiGraph():
        """Build a graph of threat relationships."""
        G = nx.DiGraph()
        
        # Add all threats as nodes
        for threat in threats:
            G.add_node(threat['threat_id'], 
                      threat_data=threat,
                      stride=threat.get('stride_category', 'U'))
        
        # Add relationships as edges
        for rel in relationships:
            if rel.from_threat in G and rel.to_threat in G:
                G.add_edge(rel.from_threat, rel.to_threat,
                         relationship_type=rel.relationship_type,
                         explanation=rel.explanation,
                         required_capability=rel.required_capability)
                         
        return G
    
    def identify_entry_points(self) -> List[str]:
        """Identify potential entry points with scoring."""
        entry_points = []
        
        for node in self.graph.nodes():
            node_data = self.graph.nodes[node]
            score = 0
            
            # External entities are primary entry points
            if node_data.get('type') == 'external_entity':
                score += 10
                
            # Untrusted components
            if node_data.get('trust_level') == 'untrusted':
                score += 5
                
            # Internet-facing components
            if 'U' in self.graph.predecessors(node):
                score += 3
                
            # Components with many connections
            degree = self.graph.degree(node)
            if degree > 3:
                score += 2
                
            if score > 0:
                entry_points.append((node, score))
                
        # Sort by score and return component names
        entry_points.sort(key=lambda x: x[1], reverse=True)
        return [ep[0] for ep in entry_points]
    
    def identify_critical_assets(self, dfd_data: Dict) -> List[str]:
        """Identify high-value targets with improved ranking."""
        asset_scores = defaultdict(int)
        
        # All data stores are critical
        for asset in dfd_data.get('assets', []):
            asset_scores[asset] += 10
        
        # Components handling sensitive data
        for flow in dfd_data.get('data_flows', []):
            if isinstance(flow, dict):
                classification = flow.get('data_classification', '')
                score_map = {
                    'PII': 8, 'PHI': 9, 'PCI': 8, 
                    'Confidential': 7, 'Internal': 5, 'Public': 1
                }
                score = score_map.get(classification, 3)
                
                if 'destination' in flow:
                    asset_scores[flow['destination']] += score
                if 'source' in flow:
                    asset_scores[flow['source']] += score // 2
                    
        # Central components (high betweenness centrality)
        if self.graph.number_of_nodes() > 0:
            centrality = nx.betweenness_centrality(self.graph)
            for node, cent in centrality.items():
                if cent > 0.1:  # Threshold for central nodes
                    asset_scores[node] += int(cent * 10)
                    
        # Sort by score and return top assets
        sorted_assets = sorted(asset_scores.items(), key=lambda x: x[1], reverse=True)
        return [asset[0] for asset in sorted_assets if asset[1] > 5]
    
    def find_attack_paths(self, entry_points: List[str], targets: List[str]) -> List[List[str]]:
        """Find potential attack paths with optimization."""
        all_paths = []
        path_set = set()  # To avoid duplicates
        
        self.logger.info(f"Finding paths from {len(entry_points)} entry points to {len(targets)} targets")
        
        for entry in entry_points[:10]:  # Limit entry points for performance
            for target in targets[:10]:  # Limit targets for performance
                if entry != target and self.graph.has_node(entry) and self.graph.has_node(target):
                    try:
                        # Find shortest paths first (most likely)
                        try:
                            shortest = nx.shortest_path(self.graph, entry, target)
                            path_tuple = tuple(shortest)
                            if path_tuple not in path_set and len(shortest) <= self.config.max_path_length:
                                all_paths.append(shortest)
                                path_set.add(path_tuple)
                        except nx.NetworkXNoPath:
                            pass
                        
                        # Then find alternative paths
                        paths = nx.all_simple_paths(
                            self.graph, entry, target, 
                            cutoff=self.config.max_path_length
                        )
                        
                        # Limit paths per source-target pair
                        path_count = 0
                        for path in paths:
                            path_tuple = tuple(path)
                            if path_tuple not in path_set:
                                all_paths.append(path)
                                path_set.add(path_tuple)
                                path_count += 1
                                if path_count >= 3:  # Max 3 paths per pair
                                    break
                                    
                    except nx.NetworkXError as e:
                        self.logger.debug(f"No path from {entry} to {target}: {e}")
                        
        self.logger.info(f"Found {len(all_paths)} unique paths")
        return all_paths
    
    def build_attack_path_details(self, path: List[str], 
                                 threat_chains: Dict[str, List[str]]) -> Optional[AttackPath]:
        """Build detailed attack path with enhanced threat selection."""
        path_steps = []
        path_threats = []
        used_threat_ids = set()
        
        for i, component in enumerate(path):
            # Get threats for this component
            component_threats = [t for t in self.component_threats.get(component, [])
                               if t['threat_id'] not in used_threat_ids]
            
            if component_threats:
                # Select the most relevant threat
                relevant_threat = self.select_relevant_threat(
                    component_threats, 
                    previous_threats=path_threats,
                    threat_chains=threat_chains,
                    step_position=i,
                    total_steps=len(path)
                )
                
                if relevant_threat:
                    # Determine prerequisites
                    prerequisites = []
                    if path_threats:
                        # Last threat is a prerequisite
                        prerequisites.append(path_threats[-1]['threat_id'])
                        # Check for other enabling threats
                        for prev_threat in path_threats:
                            if relevant_threat['threat_id'] in threat_chains.get(prev_threat['threat_id'], []):
                                prerequisites.append(prev_threat['threat_id'])
                    
                    # Determine what this enables
                    enables = threat_chains.get(relevant_threat['threat_id'], [])
                    
                    step = AttackStep(
                        step_number=i + 1,
                        component=component,
                        threat_id=relevant_threat['threat_id'],
                        threat_description=relevant_threat['threat_description'],
                        stride_category=relevant_threat['stride_category'],
                        technique_id=relevant_threat.get('mitre_attack_id'),
                        prerequisites=list(set(prerequisites)),
                        enables=enables[:3],  # Limit for readability
                        required_access=self._determine_required_access(i, len(path)),
                        detection_difficulty=self._assess_detection_difficulty(relevant_threat)
                    )
                    path_steps.append(step)
                    path_threats.append(relevant_threat)
                    used_threat_ids.add(relevant_threat['threat_id'])
                    
        if len(path_steps) < 2:
            return None  # Path too short
            
        # Calculate combined metrics
        combined_impact = self._calculate_combined_impact(path_threats)
        combined_likelihood = self._calculate_combined_likelihood(path_threats)
        
        # Generate unique path ID
        path_string = "->".join(path)
        path_hash = hashlib.md5(path_string.encode()).hexdigest()[:8]
        path_id = f"AP_{path_hash}"
        
        return AttackPath(
            path_id=path_id,
            scenario_name=f"{path[0]} → {path[-1]} Attack Chain",
            entry_point=path[0],
            target_asset=path[-1],
            path_steps=path_steps,
            total_steps=len(path_steps),
            combined_likelihood=combined_likelihood,
            combined_impact=combined_impact,
            path_feasibility=PathFeasibility.REALISTIC,
            attacker_profile=AttackerProfile.CYBERCRIMINAL,
            time_to_compromise=TimeToCompromise.DAYS,
            key_chokepoints=[],
            detection_opportunities=[],
            required_resources=[],
            path_complexity="Medium"
        )
    
    def select_relevant_threat(self, threats: List[Dict], previous_threats: List[Dict], 
                             threat_chains: Dict[str, List[str]], step_position: int,
                             total_steps: int) -> Optional[Dict]:
        """Select the most relevant threat for the current attack step."""
        if not threats:
            return None
            
        # Score each threat
        threat_scores = []
        
        for threat in threats:
            score = 0
            
            # Position-based scoring
            if step_position == 0:
                # First step - prefer authentication/access threats
                if threat['stride_category'] in ['S', 'A']:  # Spoofing or Authentication
                    score += 10
                if 'authentication' in threat['threat_description'].lower():
                    score += 5
            elif step_position == total_steps - 1:
                # Last step - prefer data access/tampering
                if threat['stride_category'] in ['T', 'I', 'D']:  # Tampering, Info Disclosure, DoS
                    score += 10
            else:
                # Middle steps - prefer elevation/lateral movement
                if threat['stride_category'] in ['E', 'T']:  # Elevation, Tampering
                    score += 5
                    
            # Chain-based scoring
            if previous_threats:
                last_threat_id = previous_threats[-1]['threat_id']
                if threat['threat_id'] in threat_chains.get(last_threat_id, []):
                    score += 15  # Strong preference for chained threats
                    
            # Impact-based scoring
            impact_scores = {'Critical': 8, 'High': 6, 'Medium': 4, 'Low': 2}
            score += impact_scores.get(threat.get('impact', 'Medium'), 3)
            
            # Likelihood-based scoring
            likelihood_scores = {'High': 5, 'Medium': 3, 'Low': 1}
            score += likelihood_scores.get(threat.get('likelihood', 'Medium'), 2)
            
            threat_scores.append((threat, score))
            
        # Sort by score and return the best match
        threat_scores.sort(key=lambda x: x[1], reverse=True)
        return threat_scores[0][0] if threat_scores else None
    
    def _determine_required_access(self, step: int, total_steps: int) -> str:
        """Determine required access level for a step."""
        if step == 0:
            return "External/Unauthenticated"
        elif step < total_steps // 2:
            return "User-level"
        elif step < total_steps - 1:
            return "Privileged"
        else:
            return "Administrative"
    
    def _assess_detection_difficulty(self, threat: Dict) -> str:
        """Assess how difficult it is to detect this threat."""
        description = threat.get('threat_description', '').lower()
        
        # Keywords indicating easy detection
        if any(word in description for word in ['brute force', 'dos', 'flood', 'scan']):
            return "Easy"
        # Keywords indicating hard detection
        elif any(word in description for word in ['stealth', 'encrypted', 'legitimate', 'insider']):
            return "Hard"
        else:
            return "Medium"
    
    def _calculate_combined_impact(self, threats: List[Dict]) -> ThreatImpact:
        """Calculate the combined impact of a threat chain."""
        if not threats:
            return ThreatImpact.LOW
            
        impact_values = {
            ThreatImpact.CRITICAL: 4,
            ThreatImpact.HIGH: 3,
            ThreatImpact.MEDIUM: 2,
            ThreatImpact.LOW: 1
        }
        
        # Get the maximum impact
        max_impact = ThreatImpact.LOW
        max_value = 0
        
        for threat in threats:
            impact_str = threat.get('impact', 'Low')
            try:
                impact = ThreatImpact(impact_str)
                if impact_values[impact] > max_value:
                    max_value = impact_values[impact]
                    max_impact = impact
            except ValueError:
                continue
                
        return max_impact
    
    def _calculate_combined_likelihood(self, threats: List[Dict]) -> ThreatLikelihood:
        """Calculate the combined likelihood of a threat chain."""
        if not threats:
            return ThreatLikelihood.LOW
            
        likelihood_values = {
            ThreatLikelihood.HIGH: 3,
            ThreatLikelihood.MEDIUM: 2,
            ThreatLikelihood.LOW: 1
        }
        
        # Use the minimum likelihood (weakest link)
        min_likelihood = ThreatLikelihood.HIGH
        min_value = 3
        
        for threat in threats:
            likelihood_str = threat.get('likelihood', 'Medium')
            try:
                likelihood = ThreatLikelihood(likelihood_str)
                if likelihood_values[likelihood] < min_value:
                    min_value = likelihood_values[likelihood]
                    min_likelihood = likelihood
            except ValueError:
                continue
                
        return min_likelihood
    
    def enrich_attack_paths(self, paths: List[AttackPath], dfd_data: Dict) -> List[AttackPath]:
        """Use LLM to enrich attack paths with realistic assessments."""
        if not self.llm:
            self.logger.info("LLM enrichment disabled")
            return paths
            
        enriched_paths = []
        
        for i, path in enumerate(paths[:self.config.max_paths_to_analyze]):
            self.logger.info(f"Enriching path {i+1}/{min(len(paths), self.config.max_paths_to_analyze)}")
            
            try:
                # Convert to simple format for LLM
                path_summary = [
                    {
                        "step": step.step_number,
                        "component": step.component,
                        "threat": step.threat_description,
                        "category": step.stride_category,
                        "access_required": step.required_access
                    }
                    for step in path.path_steps
                ]
                
                analysis = self.llm.analyze_attack_scenario(path_summary, dfd_data)
                
                if analysis:
                    # Update path with LLM insights
                    path.scenario_name = analysis.get('scenario_name', path.scenario_name)
                    
                    # Safe enum conversions
                    try:
                        path.attacker_profile = AttackerProfile(analysis.get('attacker_profile', 'Cybercriminal'))
                    except ValueError:
                        pass
                        
                    try:
                        path.path_feasibility = PathFeasibility(analysis.get('path_feasibility', 'Realistic'))
                    except ValueError:
                        pass
                        
                    try:
                        path.time_to_compromise = TimeToCompromise(analysis.get('time_to_compromise', 'Days'))
                    except ValueError:
                        pass
                        
                    try:
                        path.combined_likelihood = ThreatLikelihood(analysis.get('combined_likelihood', 'Medium'))
                    except ValueError:
                        pass
                    
                    path.key_chokepoints = analysis.get('key_chokepoints', [])[:5]
                    path.detection_opportunities = analysis.get('detection_opportunities', [])[:5]
                    path.required_resources = analysis.get('required_resources', [])[:5]
                    path.path_complexity = analysis.get('path_complexity', 'Medium')
                
                enriched_paths.append(path)
                
            except Exception as e:
                self.logger.error(f"Failed to enrich path {path.path_id}: {e}")
                enriched_paths.append(path)  # Keep original
                
        # Add remaining paths without enrichment
        enriched_paths.extend(paths[self.config.max_paths_to_analyze:])
        
        return enriched_paths
    
    def generate_defense_priorities(self, paths: List[AttackPath]) -> List[Dict[str, Any]]:
        """Generate prioritized defensive recommendations."""
        # Track statistics
        component_criticality = defaultdict(int)
        chokepoint_effectiveness = defaultdict(int)
        technique_frequency = defaultdict(int)
        detection_gaps = defaultdict(int)
        
        # Analyze paths
        for path in paths:
            # Weight by feasibility and impact
            weight_map = {
                PathFeasibility.HIGHLY_LIKELY: 3,
                PathFeasibility.REALISTIC: 2,
                PathFeasibility.THEORETICAL: 1
            }
            weight = weight_map.get(path.path_feasibility, 1)
            
            impact_weight = {
                ThreatImpact.CRITICAL: 4,
                ThreatImpact.HIGH: 3,
                ThreatImpact.MEDIUM: 2,
                ThreatImpact.LOW: 1
            }
            weight *= impact_weight.get(path.combined_impact, 1)
            
            # Count component occurrences
            for step in path.path_steps:
                component_criticality[step.component] += weight
                
                # Track MITRE techniques
                if step.technique_id:
                    technique_frequency[step.technique_id] += weight
                    
                # Track detection gaps
                if step.detection_difficulty == "Hard":
                    detection_gaps[step.component] += weight
                    
            # Count chokepoint effectiveness
            for chokepoint in path.key_chokepoints:
                chokepoint_effectiveness[chokepoint] += weight
                
        # Generate prioritized recommendations
        priorities = []
        
        # Top chokepoints (most effective controls)
        top_chokepoints = sorted(chokepoint_effectiveness.items(), 
                               key=lambda x: x[1], reverse=True)[:5]
        for control, effectiveness in top_chokepoints:
            priorities.append({
                "type": "preventive_control",
                "recommendation": f"Implement {control}",
                "impact": f"Would mitigate {effectiveness} weighted attack paths",
                "priority": "Critical" if effectiveness > 20 else "High",
                "effort": "Variable",
                "category": "Prevention"
            })
            
        # Critical components needing hardening
        critical_components = sorted(component_criticality.items(), 
                                   key=lambda x: x[1], reverse=True)[:5]
        for component, criticality in critical_components:
            priorities.append({
                "type": "component_hardening",
                "recommendation": f"Harden {component}",
                "impact": f"Component appears in {criticality} weighted attack paths",
                "priority": "High" if criticality > 10 else "Medium",
                "effort": "Medium",
                "category": "Defense in Depth"
            })
            
        # Detection improvements
        detection_improvements = sorted(detection_gaps.items(), 
                                      key=lambda x: x[1], reverse=True)[:3]
        for component, gap_score in detection_improvements:
            priorities.append({
                "type": "detection_enhancement",
                "recommendation": f"Improve monitoring for {component}",
                "impact": f"Would detect {gap_score} hard-to-detect attack steps",
                "priority": "High",
                "effort": "Low to Medium",
                "category": "Detection"
            })
            
        # MITRE technique coverage
        top_techniques = sorted(technique_frequency.items(), 
                              key=lambda x: x[1], reverse=True)[:3]
        for technique, frequency in top_techniques:
            priorities.append({
                "type": "technique_mitigation",
                "recommendation": f"Implement defenses for MITRE technique {technique}",
                "impact": f"Technique used in {frequency} weighted attack steps",
                "priority": "Medium",
                "effort": "Medium",
                "category": "Technique-specific Defense"
            })
            
        return priorities
    
    def calculate_threat_coverage(self, paths: List[AttackPath], all_threats: List[Dict]) -> Dict[str, int]:
        """Calculate how many threats are covered by the attack paths."""
        covered_threats = set()
        total_threats = len(all_threats)
        
        for path in paths:
            for step in path.path_steps:
                covered_threats.add(step.threat_id)
                
        coverage_percentage = (len(covered_threats) / total_threats * 100) if total_threats > 0 else 0
        
        return {
            "total_threats": total_threats,
            "covered_threats": len(covered_threats),
            "coverage_percentage": round(coverage_percentage, 2),
            "uncovered_threats": total_threats - len(covered_threats)
        }
    
    def analyze(self) -> AttackPathAnalysis:
        """Main analysis function with improved error handling."""
        self.logger.info("=== Starting Attack Path Analysis ===")
        
        try:
            # Load data
            threats, dfd_data = self.load_data()
            self.logger.info(f"Loaded {len(threats)} threats")
            
            # Build component graph
            self.graph = self.build_component_graph(dfd_data)
            self.logger.info(f"Built graph with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
            
            # Map threats to components
            component_mapping = self.map_threats_to_components(threats)
            self.logger.info(f"Mapped threats to components: {len(component_mapping)} components have threats")
            
            # Analyze threat relationships using LLM
            threat_chains = {}
            if self.config.enable_llm_enrichment and self.llm:
                try:
                    relationships = self.llm.analyze_threat_relationships(threats, dfd_data)
                    self.threat_graph = self.build_threat_graph(threats, relationships)
                    
                    # Convert to simple chain format
                    for rel in relationships:
                        if rel.relationship_type in ['enables', 'amplifies']:
                            if rel.from_threat not in threat_chains:
                                threat_chains[rel.from_threat] = []
                            threat_chains[rel.from_threat].append(rel.to_threat)
                            
                    self.logger.info(f"Identified {len(relationships)} threat relationships")
                except Exception as e:
                    self.logger.warning(f"Failed to analyze threat relationships: {e}")
            
            # Identify entry points and targets
            entry_points = self.identify_entry_points()
            targets = self.identify_critical_assets(dfd_data)
            self.logger.info(f"Found {len(entry_points)} entry points and {len(targets)} critical assets")
            
            if not entry_points or not targets:
                raise ValueError("No entry points or targets identified")
            
            # Find attack paths
            raw_paths = self.find_attack_paths(entry_points, targets)
            self.logger.info(f"Found {len(raw_paths)} potential paths")
            
            # Build detailed attack paths
            attack_paths = []
            for path in raw_paths[:self.config.max_paths_to_analyze * 2]:  # Process more than we'll analyze
                detailed_path = self.build_attack_path_details(path, threat_chains)
                if detailed_path:
                    attack_paths.append(detailed_path)
                    
            self.logger.info(f"Built {len(attack_paths)} detailed attack paths")
            
            if not attack_paths:
                self.logger.warning("No valid attack paths found")
                return AttackPathAnalysis(
                    attack_paths=[],
                    critical_scenarios=[],
                    defense_priorities=[],
                    threat_coverage={},
                    vector_store_insights=None,
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "error": "No valid attack paths found"
                    }
                )
            
            # Enrich with LLM analysis
            if self.config.enable_llm_enrichment:
                attack_paths = self.enrich_attack_paths(attack_paths, dfd_data)
            
            # Sort by criticality
            def path_score(p):
                feasibility_score = {
                    PathFeasibility.HIGHLY_LIKELY: 3,
                    PathFeasibility.REALISTIC: 2,
                    PathFeasibility.THEORETICAL: 1
                }
                impact_score = {
                    ThreatImpact.CRITICAL: 4,
                    ThreatImpact.HIGH: 3,
                    ThreatImpact.MEDIUM: 2,
                    ThreatImpact.LOW: 1
                }
                return (feasibility_score.get(p.path_feasibility, 1) * 
                       impact_score.get(p.combined_impact, 1))
            
            attack_paths.sort(key=path_score, reverse=True)
            
            # Generate defense priorities
            defense_priorities = self.generate_defense_priorities(attack_paths)
            
            # Identify critical scenarios
            critical_scenarios = []
            for p in attack_paths:
                if (p.path_feasibility != PathFeasibility.THEORETICAL and 
                    p.combined_impact in [ThreatImpact.CRITICAL, ThreatImpact.HIGH]):
                    critical_scenarios.append(p.scenario_name)
                    if len(critical_scenarios) >= 5:
                        break
            
            # Calculate threat coverage
            threat_coverage = self.calculate_threat_coverage(attack_paths, threats)
            
            # Process with vector store if enabled
            vector_store_insights = None
            if self.config.enable_vector_store:
                try:
                    vector_store_insights = self._process_vector_store(
                        attack_paths[:self.config.max_paths_to_analyze],
                        dfd_data,
                        defense_priorities
                    )
                except Exception as e:
                    self.logger.error(f"Vector store processing failed: {e}")
                    # Continue without vector store insights
            
            return AttackPathAnalysis(
                attack_paths=attack_paths[:self.config.max_paths_to_analyze],
                critical_scenarios=critical_scenarios,
                defense_priorities=defense_priorities,
                threat_coverage=threat_coverage,
                vector_store_insights=vector_store_insights,
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "total_paths_analyzed": len(raw_paths),
                    "detailed_paths_built": len(attack_paths),
                    "total_threats": len(threats),
                    "entry_points": entry_points[:10],  # Limit for output size
                    "critical_assets": targets[:10],
                    "llm_model": self.config.llm_model if self.config.enable_llm_enrichment else "None",
                    "llm_enrichment_enabled": self.config.enable_llm_enrichment,
                    "vector_store_enabled": self.config.enable_vector_store,
                    "max_path_length": self.config.max_path_length
                }
            )
            
        except Exception as e:
            self.logger.error(f"Attack path analysis failed: {e}", exc_info=True)
            raise
    
    def _process_vector_store(self, attack_paths: List[AttackPath], 
                             dfd_data: Dict, defense_priorities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process attack paths with vector store for cross-project insights."""
        try:
            # Lazy import to avoid dependency if not used
            from attack_path_vector_store import (
                VectorStoreConfig, AttackPathVectorStore, 
                VectorStoreIntegration, SearchQuery
            )
            
            self.logger.info("="*60)
            self.logger.info("VECTOR STORE PROCESSING STARTED")
            self.logger.info(f"Qdrant URL: {self.config.qdrant_url}")
            self.logger.info(f"Project Name: {self.config.project_name}")
            self.logger.info(f"Number of paths to store: {len(attack_paths)}")
            self.logger.info("="*60)
            
            # Create vector store configuration
            vector_config = VectorStoreConfig(
                qdrant_url=self.config.qdrant_url,
                qdrant_api_key=self.config.qdrant_api_key
            )
            
            # Initialize vector store
            vector_store = AttackPathVectorStore(vector_config)
            integration = VectorStoreIntegration(vector_store)
            
            # Prepare project metadata
            project_metadata = {
                "name": self.config.project_name,
                "industry": self.config.project_industry or dfd_data.get("industry_context", "General"),
                "tech_stack": self.config.project_tech_stack.split(",") if self.config.project_tech_stack else [],
                "compliance": self.config.project_compliance.split(",") if self.config.project_compliance else [],
                "analysis_date": datetime.now().isoformat(),
                "dfd_components": {
                    "external_entities": dfd_data.get("external_entities", []),
                    "processes": dfd_data.get("processes", []),
                    "assets": dfd_data.get("assets", [])
                }
            }
            
            self.logger.info(f"Project metadata prepared: {project_metadata['name']}")
            
            # Store attack paths and get insights
            insights = {
                "stored_paths": 0,
                "similar_attacks": [],
                "cross_project_patterns": [],
                "enhanced_defenses": [],
                "project_risk_comparison": {}
            }
            
            # Store each attack path
            for i, path in enumerate(attack_paths):
                try:
                    self.logger.info(f"Storing path {i+1}/{len(attack_paths)}: {path.path_id}")
                    path_id = vector_store.store_attack_path(path, project_metadata)
                    insights["stored_paths"] += 1
                    self.logger.info(f"✓ Successfully stored path {path.path_id} with ID: {path_id}")
                    
                    # Find similar attacks from other projects
                    similar_query = SearchQuery(
                        query_type="path",
                        query=path,
                        filters={"exclude_project": project_metadata["name"]},
                        limit=3,
                        min_similarity=0.7
                    )
                    similar_paths = vector_store.search_similar_paths(similar_query)
                    
                    if similar_paths:
                        self.logger.info(f"  Found {len(similar_paths)} similar paths")
                        insights["similar_attacks"].append({
                            "current_path": path.scenario_name,
                            "similar_scenarios": [
                                {
                                    "scenario": sim[0].scenario_name,
                                    "project": sim[2]["project"]["name"],
                                    "similarity": round(sim[1], 3),
                                    "defenses": sim[0].key_chokepoints[:3]
                                }
                                for sim in similar_paths
                            ]
                        })
                    
                    # Get enhanced defense recommendations
                    defense_recs = vector_store.find_defense_recommendations(path, limit=3)
                    for rec in defense_recs:
                        insights["enhanced_defenses"].append({
                            "path": path.scenario_name,
                            "control": rec.control_name,
                            "effectiveness": round(rec.effectiveness_score, 2),
                            "evidence_count": rec.similar_paths_blocked
                        })
                        
                except Exception as e:
                    self.logger.error(f"Failed to process path {path.path_id} in vector store: {e}", exc_info=True)
            
            self.logger.info(f"Storage complete: {insights['stored_paths']} paths stored successfully")
            
            # Get cross-project patterns
            try:
                patterns = vector_store.identify_attack_patterns(min_frequency=2)
                insights["cross_project_patterns"] = [
                    {
                        "pattern": p.pattern_name,
                        "frequency": p.frequency,
                        "projects_affected": len(p.affected_projects),
                        "typical_impact": p.typical_impact,
                        "common_defenses": p.common_defenses[:3]
                    }
                    for p in patterns[:5]
                ]
                self.logger.info(f"Identified {len(patterns)} attack patterns")
            except Exception as e:
                self.logger.warning(f"Failed to identify patterns: {e}")
            
            # Get project statistics and risk comparison
            try:
                project_stats = vector_store.get_project_statistics(project_metadata["name"])
                insights["project_risk_comparison"] = {
                    "current_project": {
                        "name": project_metadata["name"],
                        "risk_score": project_stats.get("risk_score", 0),
                        "total_paths": project_stats.get("total_paths", 0),
                        "critical_paths": project_stats.get("impact_distribution", {}).get("Critical", 0)
                    }
                }
                self.logger.info(f"Project risk score: {project_stats.get('risk_score', 0)}")
                
                # Compare with similar projects if any found
                if insights["similar_attacks"]:
                    similar_projects = list(set(
                        scenario["project"] 
                        for attack in insights["similar_attacks"] 
                        for scenario in attack["similar_scenarios"]
                    ))[:3]
                    
                    comparison = vector_store.compare_projects([project_metadata["name"]] + similar_projects)
                    insights["project_risk_comparison"]["comparison"] = comparison.get("risk_comparison", {})
                    
            except Exception as e:
                self.logger.warning(f"Failed to get project statistics: {e}")
            
            self.logger.info("="*60)
            self.logger.info(f"VECTOR STORE PROCESSING COMPLETE")
            self.logger.info(f"Total paths stored: {insights['stored_paths']}")
            self.logger.info(f"Similar attacks found: {len(insights['similar_attacks'])}")
            self.logger.info(f"Patterns identified: {len(insights['cross_project_patterns'])}")
            self.logger.info("="*60)
            
            return insights
            
        except ImportError as e:
            self.logger.error(f"Vector store module not found: {e}")
            self.logger.error("Please ensure attack_path_vector_store.py is in the same directory")
            return {"error": "Vector store module not available"}
        except Exception as e:
            self.logger.error(f"Vector store processing failed: {e}", exc_info=True)
            return {"error": str(e)}


def main():
    """Main execution function."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('attack_path_analysis.log'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=== Starting Attack Path Analysis ===")
    
    try:
        # Load configuration
        config = Config()
        
        # Validate configuration
        logger.info("Configuration loaded:")
        logger.info(f"  Input directory: {config.input_dir}")
        logger.info(f"  Max path length: {config.max_path_length}")
        logger.info(f"  LLM enrichment: {config.enable_llm_enrichment}")
        
        # Create analyzer
        analyzer = AttackPathAnalyzer(config)
        
        # Run analysis
        results = analyzer.analyze()
        
        # Save results
        output_data = results.dict()
        with open(config.attack_paths_output, 'w') as f:
            json.dump(output_data, f, indent=2)
            
        logger.info(f"Analysis complete. Results saved to {config.attack_paths_output}")
        
        # Print summary
        print("\n" + "="*60)
        print("ATTACK PATH ANALYSIS SUMMARY")
        print("="*60)
        print(f"Total attack paths identified: {len(results.attack_paths)}")
        print(f"Critical scenarios: {len(results.critical_scenarios)}")
        print(f"Defense priorities: {len(results.defense_priorities)}")
        print(f"Threat coverage: {results.threat_coverage.get('coverage_percentage', 0):.1f}%")
        
        if results.critical_scenarios:
            print("\n📊 Top Critical Scenarios:")
            for i, scenario in enumerate(results.critical_scenarios[:3], 1):
                print(f"  {i}. {scenario}")
                
        if results.defense_priorities:
            print("\n🛡️ Top Defense Priorities:")
            for i, priority in enumerate(results.defense_priorities[:5], 1):
                print(f"  {i}. {priority['recommendation']}")
                print(f"     Priority: {priority['priority']} | Impact: {priority['impact']}")
                
        if results.attack_paths:
            print("\n🎯 Most Critical Attack Path:")
            path = results.attack_paths[0]
            print(f"  Scenario: {path.scenario_name}")
            print(f"  Entry: {path.entry_point} → Target: {path.target_asset}")
            print(f"  Steps: {path.total_steps} | Feasibility: {path.path_feasibility}")
            print(f"  Impact: {path.combined_impact} | Time: {path.time_to_compromise}")
            
        # Display vector store insights if available
        if results.vector_store_insights and results.vector_store_insights.get("stored_paths", 0) > 0:
            print("\n🔍 Vector Store Insights:")
            insights = results.vector_store_insights
            print(f"  Stored paths: {insights['stored_paths']}")
            
            if insights.get("similar_attacks"):
                print(f"  Similar attacks found: {len(insights['similar_attacks'])}")
                for attack in insights["similar_attacks"][:2]:
                    print(f"    - {attack['current_path']} similar to:")
                    for sim in attack["similar_scenarios"][:1]:
                        print(f"      • {sim['scenario']} from {sim['project']} (similarity: {sim['similarity']})")
                        
            if insights.get("cross_project_patterns"):
                print(f"  Cross-project patterns: {len(insights['cross_project_patterns'])}")
                for pattern in insights["cross_project_patterns"][:2]:
                    print(f"    - {pattern['pattern']} (seen {pattern['frequency']} times)")
                    
            if insights.get("project_risk_comparison", {}).get("current_project"):
                risk_info = insights["project_risk_comparison"]["current_project"]
                print(f"  Project risk score: {risk_info.get('risk_score', 'N/A')}/100")
            
        print("\n✅ Analysis completed successfully!")
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"Required file not found: {e}")
        print(f"\n❌ Error: {e}")
        print("Please ensure the threat modeling pipeline has been run first.")
        return 1
        
    except Exception as e:
        logger.error(f"Attack path analysis failed: {e}", exc_info=True)
        print(f"\n❌ Analysis failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())