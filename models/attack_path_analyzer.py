#!/usr/bin/env python3
"""
Simplified Attack Path Analysis Module for Threat Modeling Pipeline
Analyzes refined threats to identify and score potential attack chains

Compatible version with minimal dependencies and improved error handling.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple, Any, Union
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
import hashlib
import sys
import re

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def get_config():
    """Get configuration from environment with defaults."""
    return {
        'input_dir': os.getenv('INPUT_DIR', './output'),
        'refined_threats_path': os.getenv('REFINED_THREATS_PATH', ''),
        'dfd_path': os.getenv('DFD_PATH', ''),
        'attack_paths_output': os.getenv('ATTACK_PATHS_OUTPUT', ''),
        'llm_provider': os.getenv('LLM_PROVIDER', 'scaleway'),
        'llm_model': os.getenv('LLM_MODEL', 'llama-3.3-70b-instruct'),
        'scw_api_url': os.getenv('SCW_API_URL', 'https://api.scaleway.ai/v1'),
        'scw_secret_key': os.getenv('SCW_SECRET_KEY') or os.getenv('SCW_API_KEY'),
        'max_path_length': int(os.getenv('MAX_PATH_LENGTH', '5')),
        'max_paths_to_analyze': int(os.getenv('MAX_PATHS_TO_ANALYZE', '20')),
        'enable_llm_enrichment': os.getenv('ENABLE_LLM_ENRICHMENT', 'true').lower() == 'true',
        'enable_vector_store': os.getenv('ENABLE_VECTOR_STORE', 'false').lower() == 'true',
        'project_name': os.getenv('PROJECT_NAME', 'Unknown Project'),
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        'output_dir': os.getenv('OUTPUT_DIR', './output')
    }

# Get configuration
config = get_config()

# Configure logging
logging.basicConfig(
    level=getattr(logging, config['log_level']),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Progress Tracking Functions ---
def write_progress(step: int, current: int, total: int, message: str, details: str = ""):
    """Write progress information to a file that the frontend can read."""
    try:
        progress_data = {
            'step': step,
            'current': current,
            'total': total,
            'progress': round((current / total * 100) if total > 0 else 0, 1),
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        
        progress_file = os.path.join(config['output_dir'], f'step_{step}_progress.json')
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
            
    except Exception as e:
        logger.warning(f"Could not write progress: {e}")

def check_kill_signal(step: int) -> bool:
    """Check if user requested to kill this step."""
    try:
        kill_file = os.path.join(config['output_dir'], f'step_{step}_kill.flag')
        if os.path.exists(kill_file):
            logger.info("Kill signal detected, stopping execution")
            return True
        return False
    except:
        return False

# Simple graph implementation to replace NetworkX
class SimpleGraph:
    """Lightweight graph implementation."""
    
    def __init__(self):
        self.nodes = {}
        self.edges = defaultdict(list)
        self.reverse_edges = defaultdict(list)
    
    def add_node(self, node, **attrs):
        """Add a node with attributes."""
        self.nodes[node] = attrs
    
    def add_edge(self, source, dest, **attrs):
        """Add an edge with attributes."""
        self.edges[source].append((dest, attrs))
        self.reverse_edges[dest].append((source, attrs))
    
    def has_node(self, node):
        """Check if node exists."""
        return node in self.nodes
    
    def predecessors(self, node):
        """Get predecessors of a node."""
        return [src for src, _ in self.reverse_edges[node]]
    
    def successors(self, node):
        """Get successors of a node."""
        return [dest for dest, _ in self.edges[node]]
    
    def degree(self, node):
        """Get degree of a node."""
        return len(self.edges[node]) + len(self.reverse_edges[node])
    
    def number_of_nodes(self):
        """Get number of nodes."""
        return len(self.nodes)
    
    def number_of_edges(self):
        """Get number of edges."""
        return sum(len(edges) for edges in self.edges.values())
    
    def find_paths(self, start, end, max_length=5):
        """Find all simple paths between start and end."""
        if start not in self.nodes or end not in self.nodes:
            return []
        
        paths = []
        queue = deque([(start, [start])])
        
        while queue:
            current, path = queue.popleft()
            
            if len(path) > max_length:
                continue
            
            if current == end and len(path) > 1:
                paths.append(path)
                continue
            
            for neighbor, _ in self.edges[current]:
                if neighbor not in path:  # Avoid cycles
                    new_path = path + [neighbor]
                    queue.append((neighbor, new_path))
        
        return paths
    
    def shortest_path(self, start, end):
        """Find shortest path using BFS."""
        if start not in self.nodes or end not in self.nodes:
            return None
        
        queue = deque([(start, [start])])
        visited = {start}
        
        while queue:
            current, path = queue.popleft()
            
            if current == end:
                return path
            
            for neighbor, _ in self.edges[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None

# Configuration
@dataclass
class Config:
    """Configuration for attack path analysis."""
    input_dir: str = config['input_dir']
    refined_threats_path: str = config['refined_threats_path']
    dfd_path: str = config['dfd_path']
    attack_paths_output: str = config['attack_paths_output']
    llm_provider: str = config['llm_provider']
    llm_model: str = config['llm_model']
    scw_api_url: str = config['scw_api_url']
    scw_secret_key: str = config['scw_secret_key']
    max_path_length: int = config['max_path_length']
    max_paths_to_analyze: int = config['max_paths_to_analyze']
    enable_llm_enrichment: bool = config['enable_llm_enrichment']
    enable_vector_store: bool = config['enable_vector_store']
    project_name: str = config['project_name']
    output_dir: str = config['output_dir']
    
    def __post_init__(self):
        """Initialize derived paths if not set."""
        if not self.refined_threats_path:
            self.refined_threats_path = os.path.join(self.input_dir, "refined_threats.json")
        if not self.dfd_path:
            self.dfd_path = os.path.join(self.input_dir, "dfd_components.json")
        if not self.attack_paths_output:
            self.attack_paths_output = os.path.join(self.input_dir, "attack_paths.json")

# Simple data classes (replacing Pydantic for compatibility)
@dataclass
class AttackStep:
    step_number: int
    component: str
    threat_id: str
    threat_description: str
    stride_category: str
    technique_id: Optional[str] = None
    prerequisites: List[str] = field(default_factory=list)
    enables: List[str] = field(default_factory=list)
    required_access: Optional[str] = None
    detection_difficulty: Optional[str] = None

@dataclass
class AttackPath:
    path_id: str
    scenario_name: str
    entry_point: str
    target_asset: str
    path_steps: List[AttackStep]
    total_steps: int
    combined_likelihood: str
    combined_impact: str
    path_feasibility: str = "Realistic"
    attacker_profile: str = "Cybercriminal"
    time_to_compromise: str = "Days"
    key_chokepoints: List[str] = field(default_factory=list)
    detection_opportunities: List[str] = field(default_factory=list)
    required_resources: List[str] = field(default_factory=list)
    path_complexity: str = "Medium"

@dataclass
class AttackPathAnalysis:
    attack_paths: List[AttackPath]
    critical_scenarios: List[str]
    defense_priorities: List[Dict[str, Any]]
    threat_coverage: Dict[str, Any] = field(default_factory=dict)
    vector_store_insights: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

# Simplified LLM Client
class LLMClient:
    """Simplified LLM client with basic error handling."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.LLMClient")
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize the appropriate LLM client."""
        try:
            if self.config.llm_provider == "scaleway" and self.config.scw_secret_key:
                from openai import OpenAI
                self.client = OpenAI(
                    base_url=self.config.scw_api_url,
                    api_key=self.config.scw_secret_key
                )
                self.logger.info("Scaleway client initialized")
            elif self.config.llm_provider == "ollama":
                try:
                    import ollama
                    self.client = ollama
                    self.logger.info("Ollama client initialized")
                except ImportError:
                    self.logger.warning("Ollama not available")
            else:
                self.logger.warning("No valid LLM configuration found")
        except Exception as e:
            self.logger.warning(f"Failed to initialize LLM client: {e}")
    
    def analyze_attack_scenario(self, path_steps: List[Dict], dfd_data: Dict) -> Dict[str, Any]:
        """Analyze a specific attack path for feasibility and details."""
        if not self.client:
            return self._get_default_analysis()
        
        prompt = f"""You are a cybersecurity expert evaluating an attack path.

Attack Path Steps:
{json.dumps(path_steps, indent=2)}

System Context:
- Project: {dfd_data.get('project_name', 'Unknown')}
- Industry: {dfd_data.get('industry_context', 'General')}
- Key Assets: {', '.join(dfd_data.get('assets', []))}

Analyze this attack path and provide a realistic assessment in JSON format:
{{
    "scenario_name": "descriptive name for this attack",
    "attacker_profile": "Script Kiddie|Cybercriminal|APT|Insider",
    "path_feasibility": "Theoretical|Realistic|Highly Likely",
    "time_to_compromise": "Hours|Days|Weeks|Months",
    "combined_likelihood": "Low|Medium|High",
    "key_chokepoints": ["specific defensive controls that would stop this"],
    "detection_opportunities": ["specific detection points in the attack chain"],
    "required_resources": ["tools, skills, or resources the attacker needs"],
    "path_complexity": "Low|Medium|High",
    "expert_assessment": "brief explanation of why this attack path matters"
}}

Consider real-world factors like required attacker sophistication, common defensive controls, and detection capabilities."""

        try:
            if self.config.llm_provider == "scaleway":
                response = self.client.chat.completions.create(
                    model=self.config.llm_model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.3,
                    max_tokens=1000
                )
                return json.loads(response.choices[0].message.content)
            elif self.config.llm_provider == "ollama":
                response = self.client.generate(
                    model=self.config.llm_model,
                    prompt=prompt + "\n\nOutput only valid JSON.",
                    options={"temperature": 0.3}
                )
                return json.loads(response['response'])
        except Exception as e:
            self.logger.warning(f"LLM analysis failed: {e}")
            return self._get_default_analysis()
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        """Get default analysis when LLM is unavailable."""
        return {
            "scenario_name": "Multi-step Attack Chain",
            "attacker_profile": "Cybercriminal",
            "path_feasibility": "Realistic",
            "time_to_compromise": "Days",
            "combined_likelihood": "Medium",
            "key_chokepoints": ["Multi-factor authentication", "Network segmentation"],
            "detection_opportunities": ["Authentication logs", "Network monitoring"],
            "required_resources": ["Basic hacking tools", "Network access"],
            "path_complexity": "Medium",
            "expert_assessment": "Standard multi-step attack requiring moderate skills"
        }

# Main Attack Path Analyzer
class AttackPathAnalyzer:
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.AttackPathAnalyzer")
        self.llm = LLMClient(config) if config.enable_llm_enrichment else None
        self.graph = SimpleGraph()
        self.threat_map = {}
        self.component_threats = defaultdict(list)
        
    def load_data(self) -> Tuple[List[Dict], Dict]:
        """Load refined threats and DFD data with validation."""
        try:
            # Load threats
            self.logger.info(f"Loading threats from: {self.config.refined_threats_path}")
            write_progress(5, 5, 100, "Loading data", "Reading threat files")
            
            with open(self.config.refined_threats_path, 'r', encoding='utf-8') as f:
                threats_data = json.load(f)
            threats = threats_data.get('threats', [])
            
            # Load DFD data
            self.logger.info(f"Loading DFD from: {self.config.dfd_path}")
            write_progress(5, 10, 100, "Loading data", "Reading DFD components")
            
            with open(self.config.dfd_path, 'r', encoding='utf-8') as f:
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
                
            self.logger.info(f"Loaded {len(threats)} threats and DFD with {len(dfd_data.get('data_flows', []))} flows")
            write_progress(5, 15, 100, "Data loaded", f"Found {len(threats)} threats")
            return threats, dfd_data
            
        except FileNotFoundError as e:
            self.logger.error(f"Required file not found: {e}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in input files: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load data: {e}")
            raise
    
    def build_component_graph(self, dfd_data: Dict) -> SimpleGraph:
        """Build a directed graph of system components from DFD."""
        write_progress(5, 20, 100, "Building graph", "Creating component relationships")
        
        G = SimpleGraph()
        
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
            
        # Add edges from data flows
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
                        authentication=flow.get('authentication_mechanism', 'Unknown')
                    )
                    
                    # Add reverse edge for bidirectional communication
                    G.add_edge(dest, source,
                             data_classification=flow.get('data_classification', 'Unknown'),
                             protocol=flow.get('protocol', 'Unknown'))
                else:
                    self.logger.warning(f"Skipping flow from {source} to {dest} - component not found")
                    
        self.logger.info(f"Built graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
        write_progress(5, 25, 100, "Graph built", f"{G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G
    
    def map_threats_to_components(self, threats: List[Dict]) -> Dict[str, List[Dict]]:
        """Map threats to their components."""
        write_progress(5, 30, 100, "Mapping threats", "Associating threats with components")
        
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
        for node in self.graph.nodes:
            if node in description and node not in components:
                components.append(node)
                
        return components
    
    def identify_entry_points(self) -> List[str]:
        """Identify potential entry points with scoring."""
        write_progress(5, 35, 100, "Finding entry points", "Identifying attack surface")
        
        entry_points = []
        
        for node in self.graph.nodes:
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
        """Identify high-value targets."""
        write_progress(5, 40, 100, "Finding targets", "Identifying critical assets")
        
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
                    
        # Sort by score and return top assets
        sorted_assets = sorted(asset_scores.items(), key=lambda x: x[1], reverse=True)
        return [asset[0] for asset in sorted_assets if asset[1] > 5]
    
    def find_attack_paths(self, entry_points: List[str], targets: List[str]) -> List[List[str]]:
        """Find potential attack paths."""
        all_paths = []
        path_set = set()  # To avoid duplicates
        
        self.logger.info(f"Finding paths from {len(entry_points)} entry points to {len(targets)} targets")
        write_progress(5, 45, 100, "Finding paths", f"Analyzing {len(entry_points)} entry points")
        
        total_combinations = min(len(entry_points), 5) * min(len(targets), 5)
        current_combination = 0
        
        for entry in entry_points[:5]:  # Limit entry points for performance
            for target in targets[:5]:  # Limit targets for performance
                if check_kill_signal(5):
                    return all_paths
                    
                current_combination += 1
                progress = 45 + int((current_combination / total_combinations) * 25)
                write_progress(5, progress, 100, 
                             f"Finding paths ({current_combination}/{total_combinations})", 
                             f"{entry} → {target}")
                
                if entry != target and self.graph.has_node(entry) and self.graph.has_node(target):
                    try:
                        # Find shortest path first
                        shortest = self.graph.shortest_path(entry, target)
                        if shortest and len(shortest) <= self.config.max_path_length:
                            path_tuple = tuple(shortest)
                            if path_tuple not in path_set:
                                all_paths.append(shortest)
                                path_set.add(path_tuple)
                        
                        # Find alternative paths
                        paths = self.graph.find_paths(entry, target, self.config.max_path_length)
                        
                        # Add unique paths
                        for path in paths[:3]:  # Max 3 paths per pair
                            path_tuple = tuple(path)
                            if path_tuple not in path_set:
                                all_paths.append(path)
                                path_set.add(path_tuple)
                                
                    except Exception as e:
                        self.logger.debug(f"No path from {entry} to {target}: {e}")
                        
        self.logger.info(f"Found {len(all_paths)} unique paths")
        write_progress(5, 70, 100, "Paths found", f"Discovered {len(all_paths)} attack paths")
        return all_paths
    
    def build_attack_path_details(self, path: List[str]) -> Optional[AttackPath]:
        """Build detailed attack path."""
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
                    step_position=i,
                    total_steps=len(path)
                )
                
                if relevant_threat:
                    step = AttackStep(
                        step_number=i + 1,
                        component=component,
                        threat_id=relevant_threat['threat_id'],
                        threat_description=relevant_threat['threat_description'],
                        stride_category=relevant_threat['stride_category'],
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
            combined_impact=combined_impact
        )
    
    def select_relevant_threat(self, threats: List[Dict], step_position: int, total_steps: int) -> Optional[Dict]:
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
                if threat['stride_category'] in ['S']:  # Spoofing
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
    
    def _calculate_combined_impact(self, threats: List[Dict]) -> str:
        """Calculate the combined impact of a threat chain."""
        if not threats:
            return "Low"
            
        impact_values = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        
        # Get the maximum impact
        max_impact = "Low"
        max_value = 0
        
        for threat in threats:
            impact_str = threat.get('impact', 'Low')
            value = impact_values.get(impact_str, 1)
            if value > max_value:
                max_value = value
                max_impact = impact_str
                
        return max_impact
    
    def _calculate_combined_likelihood(self, threats: List[Dict]) -> str:
        """Calculate the combined likelihood of a threat chain."""
        if not threats:
            return "Low"
            
        likelihood_values = {"High": 3, "Medium": 2, "Low": 1}
        
        # Use the minimum likelihood (weakest link)
        min_likelihood = "High"
        min_value = 3
        
        for threat in threats:
            likelihood_str = threat.get('likelihood', 'Medium')
            value = likelihood_values.get(likelihood_str, 2)
            if value < min_value:
                min_value = value
                min_likelihood = likelihood_str
                
        return min_likelihood
    
    def enrich_attack_paths(self, paths: List[AttackPath], dfd_data: Dict) -> List[AttackPath]:
        """Use LLM to enrich attack paths with realistic assessments."""
        if not self.llm or not self.llm.client:
            self.logger.info("LLM enrichment disabled or unavailable")
            return paths
            
        enriched_paths = []
        
        for i, path in enumerate(paths[:self.config.max_paths_to_analyze]):
            if check_kill_signal(5):
                return enriched_paths
                
            progress = 75 + int((i / min(len(paths), self.config.max_paths_to_analyze)) * 15)
            write_progress(5, progress, 100, 
                         f"Enriching path {i+1}/{min(len(paths), self.config.max_paths_to_analyze)}", 
                         f"Analyzing: {path.scenario_name}")
            
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
                    path.attacker_profile = analysis.get('attacker_profile', 'Cybercriminal')
                    path.path_feasibility = analysis.get('path_feasibility', 'Realistic')
                    path.time_to_compromise = analysis.get('time_to_compromise', 'Days')
                    path.combined_likelihood = analysis.get('combined_likelihood', path.combined_likelihood)
                    path.key_chokepoints = analysis.get('key_chokepoints', [])[:5]
                    path.detection_opportunities = analysis.get('detection_opportunities', [])[:5]
                    path.required_resources = analysis.get('required_resources', [])[:5]
                    path.path_complexity = analysis.get('path_complexity', 'Medium')
                
                enriched_paths.append(path)
                
            except Exception as e:
                self.logger.warning(f"Failed to enrich path {path.path_id}: {e}")
                enriched_paths.append(path)  # Keep original
                
        # Add remaining paths without enrichment
        enriched_paths.extend(paths[self.config.max_paths_to_analyze:])
        
        return enriched_paths
    
    def generate_defense_priorities(self, paths: List[AttackPath]) -> List[Dict[str, Any]]:
        """Generate prioritized defensive recommendations."""
        write_progress(5, 92, 100, "Generating recommendations", "Analyzing defense priorities")
        
        # Track statistics
        component_criticality = defaultdict(int)
        chokepoint_effectiveness = defaultdict(int)
        detection_gaps = defaultdict(int)
        
        # Analyze paths
        for path in paths:
            # Weight by feasibility and impact
            weight_map = {"Highly Likely": 3, "Realistic": 2, "Theoretical": 1}
            weight = weight_map.get(path.path_feasibility, 1)
            
            impact_weight = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
            weight *= impact_weight.get(path.combined_impact, 1)
            
            # Count component occurrences
            for step in path.path_steps:
                component_criticality[step.component] += weight
                    
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
        """Main analysis function."""
        self.logger.info("=== Starting Attack Path Analysis ===")
        write_progress(5, 0, 100, "Starting analysis", "Initializing attack path analyzer")
        
        try:
            # Load data
            threats, dfd_data = self.load_data()
            self.logger.info(f"Loaded {len(threats)} threats")
            
            # Build component graph
            self.graph = self.build_component_graph(dfd_data)
            
            # Map threats to components
            component_mapping = self.map_threats_to_components(threats)
            self.logger.info(f"Mapped threats to components: {len(component_mapping)} components have threats")
            
            # Identify entry points and targets
            entry_points = self.identify_entry_points()
            targets = self.identify_critical_assets(dfd_data)
            self.logger.info(f"Found {len(entry_points)} entry points and {len(targets)} critical assets")
            
            if not entry_points or not targets:
                self.logger.warning("No entry points or targets identified")
                write_progress(5, 100, 100, "Complete", "No attack paths found")
                return AttackPathAnalysis(
                    attack_paths=[],
                    critical_scenarios=[],
                    defense_priorities=[],
                    threat_coverage={},
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "error": "No entry points or targets identified"
                    }
                )
            
            # Find attack paths
            raw_paths = self.find_attack_paths(entry_points, targets)
            self.logger.info(f"Found {len(raw_paths)} potential paths")
            
            # Build detailed attack paths
            attack_paths = []
            total_raw_paths = min(len(raw_paths), self.config.max_paths_to_analyze * 2)
            
            for i, path in enumerate(raw_paths[:total_raw_paths]):
                if check_kill_signal(5):
                    break
                    
                progress = 70 + int((i / total_raw_paths) * 5)
                write_progress(5, progress, 100, 
                             f"Building path {i+1}/{total_raw_paths}", 
                             f"{path[0]} → {path[-1]}")
                
                detailed_path = self.build_attack_path_details(path)
                if detailed_path:
                    attack_paths.append(detailed_path)
                    
            self.logger.info(f"Built {len(attack_paths)} detailed attack paths")
            
            if not attack_paths:
                self.logger.warning("No valid attack paths found")
                write_progress(5, 100, 100, "Complete", "No valid attack paths found")
                return AttackPathAnalysis(
                    attack_paths=[],
                    critical_scenarios=[],
                    defense_priorities=[],
                    threat_coverage={},
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
                feasibility_score = {"Highly Likely": 3, "Realistic": 2, "Theoretical": 1}
                impact_score = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
                return (feasibility_score.get(p.path_feasibility, 1) * 
                       impact_score.get(p.combined_impact, 1))
            
            attack_paths.sort(key=path_score, reverse=True)
            
            # Generate defense priorities
            defense_priorities = self.generate_defense_priorities(attack_paths)
            
            # Identify critical scenarios
            critical_scenarios = []
            for p in attack_paths:
                if (p.path_feasibility != "Theoretical" and 
                    p.combined_impact in ["Critical", "High"]):
                    critical_scenarios.append(p.scenario_name)
                    if len(critical_scenarios) >= 5:
                        break
            
            # Calculate threat coverage
            threat_coverage = self.calculate_threat_coverage(attack_paths, threats)
            
            write_progress(5, 98, 100, "Finalizing analysis", "Generating report")
            
            return AttackPathAnalysis(
                attack_paths=attack_paths[:self.config.max_paths_to_analyze],
                critical_scenarios=critical_scenarios,
                defense_priorities=defense_priorities,
                threat_coverage=threat_coverage,
                vector_store_insights=None,  # Simplified version doesn't include vector store
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "total_paths_analyzed": len(raw_paths),
                    "detailed_paths_built": len(attack_paths),
                    "total_threats": len(threats),
                    "entry_points": entry_points[:10],
                    "critical_assets": targets[:10],
                    "llm_model": self.config.llm_model if self.config.enable_llm_enrichment else "None",
                    "llm_enrichment_enabled": self.config.enable_llm_enrichment,
                    "max_path_length": self.config.max_path_length
                }
            )
            
        except Exception as e:
            self.logger.error(f"Attack path analysis failed: {e}")
            write_progress(5, 100, 100, "Failed", str(e))
            return AttackPathAnalysis(
                attack_paths=[],
                critical_scenarios=[],
                defense_priorities=[],
                threat_coverage={},
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }
            )


def main():
    """Main execution function."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("=== Starting Attack Path Analysis ===")
    write_progress(5, 0, 100, "Initializing", "Starting attack path analysis")
    
    try:
        # Load configuration
        config = Config()
        
        # Validate paths exist
        if not os.path.exists(config.refined_threats_path):
            logger.error(f"Refined threats file not found: {config.refined_threats_path}")
            logger.error("Please run the threat refinement step first.")
            write_progress(5, 100, 100, "Failed", "Missing refined threats file")
            return 1
        if not os.path.exists(config.dfd_path):
            logger.error(f"DFD file not found: {config.dfd_path}")
            logger.error("Please run the DFD extraction step first.")
            write_progress(5, 100, 100, "Failed", "Missing DFD file")
            return 1
        
        # Log configuration
        logger.info("Configuration loaded:")
        logger.info(f"  Input directory: {config.input_dir}")
        logger.info(f"  Max path length: {config.max_path_length}")
        logger.info(f"  LLM enrichment: {config.enable_llm_enrichment}")
        
        # Create analyzer
        analyzer = AttackPathAnalyzer(config)
        
        # Run analysis
        results = analyzer.analyze()
        
        # Convert to dict for JSON serialization
        def convert_to_dict(obj):
            if hasattr(obj, '__dict__'):
                return {k: convert_to_dict(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, list):
                return [convert_to_dict(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: convert_to_dict(v) for k, v in obj.items()}
            else:
                return obj
        
        output_data = convert_to_dict(results)
        
        # Save results
        write_progress(5, 99, 100, "Saving results", config.attack_paths_output)
        with open(config.attack_paths_output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
            
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
            
        print("\n✅ Analysis completed successfully!")
        write_progress(5, 100, 100, "Complete", f"Found {len(results.attack_paths)} attack paths")
        
        # Clean up progress file after success
        try:
            progress_file = os.path.join(config.output_dir, 'step_5_progress.json')
            if os.path.exists(progress_file):
                os.remove(progress_file)
        except:
            pass
        
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"Required file not found: {e}")
        print(f"\n❌ Error: {e}")
        print("Please ensure the threat modeling pipeline has been run first.")
        write_progress(5, 100, 100, "Failed", str(e))
        return 1
        
    except Exception as e:
        logger.error(f"Attack path analysis failed: {e}")
        print(f"\n❌ Analysis failed: {e}")
        write_progress(5, 100, 100, "Failed", str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())