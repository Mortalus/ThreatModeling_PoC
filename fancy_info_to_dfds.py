#!/usr/bin/env python3
# threat_refiner_enhanced.py

"""
Enhanced threat model refinement script with real-time threat intelligence integration.
Designed for Fortune 500 enterprise environments with:
- Attack chain analysis and multi-step threat detection
- MITRE ATT&CK mapping and enrichment
- Real-time CVE/threat intelligence from NVD and CISA KEV
- STRIDE-specific risk scoring with environmental factors
- Advanced threat correlation and business impact analysis
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple, Any, Union
from dataclasses import dataclass, asdict, field
from concurrent.futures import ThreadPoolExecutor
import hashlib
import sys
import re
from collections import defaultdict
from enum import Enum

# Third-party imports
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError, field_validator
import logging
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN
import pandas as pd
from cachetools import TTLCache
import backoff
import networkx as nx

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# --- Configuration ---
@dataclass
class Config:
    """Enhanced configuration for threat refinement pipeline."""
    # File paths
    input_dir: str = os.getenv("INPUT_DIR", "./output")
    dfd_input_path: str = os.getenv("DFD_INPUT_PATH", "")
    threats_input_path: str = os.getenv("THREATS_INPUT_PATH", "")
    refined_threats_output_path: str = os.getenv("REFINED_THREATS_OUTPUT_PATH", "")
    controls_input_path: str = os.getenv("CONTROLS_INPUT_PATH", "")
    
    # External API configurations
    nvd_api_url: str = os.getenv("NVD_API_URL", "https://services.nvd.nist.gov/rest/json/cves/2.0")
    nvd_api_key: str = os.getenv("NVD_API_KEY", "")  # Get from https://nvd.nist.gov/developers/request-an-api-key
    cisa_kev_url: str = os.getenv("CISA_KEV_URL", "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json")
    mitre_attack_url: str = os.getenv("MITRE_ATTACK_URL", "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json")
    
    # Processing parameters
    similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.80"))
    cve_relevance_years: int = int(os.getenv("CVE_RELEVANCE_YEARS", "5"))
    client_industry: str = os.getenv("CLIENT_INDUSTRY", "Generic")
    company_size: str = os.getenv("COMPANY_SIZE", "Fortune 500")
    
    # Attack chain analysis
    enable_attack_chains: bool = os.getenv("ENABLE_ATTACK_CHAINS", "true").lower() == "true"
    max_chain_length: int = int(os.getenv("MAX_CHAIN_LENGTH", "5"))
    chain_confidence_threshold: float = float(os.getenv("CHAIN_CONFIDENCE_THRESHOLD", "0.70"))
    
    # STRIDE-specific weights
    stride_weights: Dict[str, float] = field(default_factory=lambda: {
        "S": 1.2,  # Spoofing - high impact in enterprise
        "T": 1.3,  # Tampering - critical for data integrity
        "R": 1.0,  # Repudiation - baseline
        "I": 1.1,  # Information Disclosure - regulatory impact
        "D": 1.4,  # Denial of Service - business continuity
        "E": 1.5   # Elevation of Privilege - highest risk
    })
    
    # Environmental factors
    environmental_factors: Dict[str, float] = field(default_factory=lambda: {
        "internet_facing": 1.5,
        "internal_only": 0.7,
        "dmz": 1.3,
        "critical_infrastructure": 1.6,
        "development": 0.5,
        "production": 1.4
    })
    
    # Model configuration
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-mpnet-base-v2")
    clustering_eps: float = float(os.getenv("CLUSTERING_EPS", "0.20"))
    clustering_min_samples: int = int(os.getenv("CLUSTERING_MIN_SAMPLES", "1"))
    
    # Performance settings
    max_workers: int = int(os.getenv("MAX_WORKERS", "4"))
    api_timeout: int = int(os.getenv("API_TIMEOUT", "30"))
    cache_ttl: int = int(os.getenv("CACHE_TTL", "3600"))
    api_rate_limit_delay: float = float(os.getenv("API_RATE_LIMIT_DELAY", "0.6"))  # NVD rate limit compliance
    
    def __post_init__(self):
        """Set default paths based on input_dir if not provided."""
        if not self.dfd_input_path:
            self.dfd_input_path = os.path.join(self.input_dir, "dfd_components.json")
        if not self.threats_input_path:
            self.threats_input_path = os.path.join(self.input_dir, "identified_threats.json")
        if not self.refined_threats_output_path:
            self.refined_threats_output_path = os.path.join(self.input_dir, "refined_threats.json")
        if not self.controls_input_path:
            self.controls_input_path = os.path.join(self.input_dir, "controls.json")

# --- Enums and Constants ---
class ThreatStatus(str, Enum):
    ACTIVE = "active"
    MITIGATED = "mitigated"
    SUPPRESSED = "suppressed"
    ACCEPTED = "accepted"

class AttackStage(str, Enum):
    INITIAL_ACCESS = "Initial Access"
    EXECUTION = "Execution"
    PERSISTENCE = "Persistence"
    PRIVILEGE_ESCALATION = "Privilege Escalation"
    DEFENSE_EVASION = "Defense Evasion"
    CREDENTIAL_ACCESS = "Credential Access"
    DISCOVERY = "Discovery"
    LATERAL_MOVEMENT = "Lateral Movement"
    COLLECTION = "Collection"
    COMMAND_AND_CONTROL = "Command and Control"
    EXFILTRATION = "Exfiltration"
    IMPACT = "Impact"

# Map STRIDE to MITRE ATT&CK tactics
STRIDE_TO_ATTACK_STAGE = {
    "S": [AttackStage.INITIAL_ACCESS, AttackStage.CREDENTIAL_ACCESS],
    "T": [AttackStage.EXECUTION, AttackStage.PERSISTENCE],
    "R": [AttackStage.DEFENSE_EVASION],
    "I": [AttackStage.COLLECTION, AttackStage.EXFILTRATION],
    "D": [AttackStage.IMPACT],
    "E": [AttackStage.PRIVILEGE_ESCALATION, AttackStage.LATERAL_MOVEMENT]
}

# --- Pydantic Models ---
class MitreAttackTechnique(BaseModel):
    technique_id: str = Field(..., description="MITRE ATT&CK technique ID (e.g., T1078)")
    name: str = Field(..., description="Technique name")
    tactic: str = Field(..., description="Associated tactic")
    description: Optional[str] = Field(None, description="Technique description")
    detection: Optional[str] = Field(None, description="Detection methods")
    mitigation: Optional[str] = Field(None, description="Mitigation strategies")

class AttackChain(BaseModel):
    chain_id: str = Field(..., description="Unique identifier for the attack chain")
    threats: List[str] = Field(..., description="Ordered list of threat IDs in the chain")
    stages: List[AttackStage] = Field(..., description="Attack stages covered")
    confidence: float = Field(..., description="Confidence score for the chain")
    impact_multiplier: float = Field(..., description="Combined impact multiplier")
    description: str = Field(..., description="Natural language description of the attack chain")
    mitre_techniques: List[str] = Field(default_factory=list, description="Related MITRE ATT&CK techniques")

class ThreatIntelligence(BaseModel):
    cve_active_exploits: List[str] = Field(default_factory=list, description="CVEs with known active exploits")
    cisa_kev: List[str] = Field(default_factory=list, description="CISA Known Exploited Vulnerabilities")
    threat_actors: List[str] = Field(default_factory=list, description="Associated threat actors")
    campaigns: List[str] = Field(default_factory=list, description="Known campaigns using this technique")
    ttps: List[str] = Field(default_factory=list, description="Tactics, Techniques, and Procedures")
    last_seen: Optional[datetime] = Field(None, description="Last observed in the wild")
    prevalence: str = Field("Unknown", description="How common this threat is: Rare, Uncommon, Common, Widespread")

class EnhancedThreat(BaseModel):
    threat_id: str = Field(..., description="Unique threat identifier")
    component_name: str = Field(..., description="Standardized component name")
    stride_category: str = Field(..., pattern="^[STRIDE]$")
    threat_description: str = Field(...)
    mitigation_suggestion: str = Field(...)
    impact: str = Field(..., pattern="^(Critical|High|Medium|Low)$")
    likelihood: str = Field(..., pattern="^(Low|Medium|High)$")
    references: List[str] = Field(default_factory=list)
    risk_score: str = Field(...)
    residual_risk_score: str = Field(...)
    exploitability: str = Field(..., pattern="^(Low|Medium|High)$")
    mitigation_maturity: str = Field(..., pattern="^(Immature|Mature|Advanced)$")
    justification: str = Field(...)
    risk_statement: str = Field(...)
    
    # New enhanced fields
    status: ThreatStatus = Field(default=ThreatStatus.ACTIVE)
    mitre_attack_mapping: List[MitreAttackTechnique] = Field(default_factory=list)
    attack_chains: List[str] = Field(default_factory=list, description="IDs of attack chains this threat participates in")
    threat_intelligence: Optional[ThreatIntelligence] = Field(None)
    environmental_score: float = Field(1.0, description="Environmental factor multiplier")
    business_impact_score: float = Field(0.0, description="Quantified business impact (0-100)")
    detection_difficulty: str = Field("Medium", pattern="^(Low|Medium|High)$")
    time_to_exploit: str = Field("Days", pattern="^(Minutes|Hours|Days|Weeks|Months)$")
    control_effectiveness: Dict[str, float] = Field(default_factory=dict, description="Effectiveness of each control")
    prerequisites: List[str] = Field(default_factory=list, description="Other threat IDs that must succeed first")
    enables: List[str] = Field(default_factory=list, description="Threat IDs this enables if successful")
    priority_score: float = Field(0.0, description="Calculated priority score")

    @field_validator('threat_id', mode='before')
    @classmethod
    def generate_threat_id(cls, v, info):
        if not v:
            # Generate ID from component and stride category
            values = info.data
            component = values.get('component_name', 'unknown').replace(' ', '_')
            stride = values.get('stride_category', 'X')
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            v = f"THR-{stride}-{component[:20]}-{timestamp}"
        return v

class RefinedThreatsOutput(BaseModel):
    threats: List[EnhancedThreat]
    attack_chains: List[AttackChain]
    metadata: Dict[str, Any]
    executive_summary: Dict[str, Any]

# --- Enhanced Statistics ---
@dataclass
class EnhancedThreatStats:
    """Enhanced statistics for threat processing."""
    original_count: int = 0
    suppressed_count: int = 0
    deduplicated_count: int = 0
    final_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    
    # New statistics
    attack_chains_identified: int = 0
    threats_with_active_exploits: int = 0
    threats_in_cisa_kev: int = 0
    mitre_techniques_mapped: int = 0
    average_business_impact: float = 0.0
    coverage_by_stride: Dict[str, int] = field(default_factory=dict)
    top_attack_vectors: List[Tuple[str, int]] = field(default_factory=list)
    control_gap_analysis: Dict[str, float] = field(default_factory=dict)

# --- Threat Intelligence Manager ---
class ThreatIntelligenceManager:
    """Manages real-time threat intelligence from multiple sources."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.cache = TTLCache(maxsize=5000, ttl=config.cache_ttl)
        self.mitre_attack_data = None
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.api_timeout))
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    @backoff.on_exception(backoff.expo, aiohttp.ClientError, max_tries=3)
    async def fetch_cisa_kev_catalog(self) -> Set[str]:
        """Fetch CISA Known Exploited Vulnerabilities catalog."""
        cache_key = "cisa_kev"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            self.logger.info("Fetching CISA KEV catalog...")
            async with self.session.get(self.config.cisa_kev_url) as response:
                response.raise_for_status()
                data = await response.json()
                
            kev_set = {vuln['cveID'] for vuln in data.get('vulnerabilities', [])}
            self.cache[cache_key] = kev_set
            
            self.logger.info(f"Loaded {len(kev_set)} CVEs from CISA KEV catalog")
            return kev_set
            
        except Exception as e:
            self.logger.error(f"Failed to fetch CISA KEV catalog: {e}")
            return set()
    
    @backoff.on_exception(backoff.expo, aiohttp.ClientError, max_tries=3)
    async def fetch_mitre_attack_data(self) -> Dict[str, Any]:
        """Fetch MITRE ATT&CK framework data."""
        cache_key = "mitre_attack"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            self.logger.info("Fetching MITRE ATT&CK data...")
            async with self.session.get(self.config.mitre_attack_url) as response:
                response.raise_for_status()
                text = await response.text()
                data = json.loads(text)  # Parse JSON from text
            
            # Process MITRE data into usable format
            techniques = {}
            for obj in data.get('objects', []):
                if obj.get('type') == 'attack-pattern':
                    technique_id = None
                    for ref in obj.get('external_references', []):
                        if ref.get('source_name') == 'mitre-attack':
                            technique_id = ref.get('external_id')
                            break
                    
                    if technique_id:
                        techniques[technique_id] = {
                            'name': obj.get('name'),
                            'description': obj.get('description'),
                            'kill_chain_phases': [phase.get('phase_name') for phase in obj.get('kill_chain_phases', [])]
                        }
            
            self.cache[cache_key] = techniques
            self.logger.info(f"Loaded {len(techniques)} MITRE ATT&CK techniques")
            return techniques
            
        except Exception as e:
            self.logger.error(f"Failed to fetch MITRE ATT&CK data: {e}")
            return {}
    
    async def enrich_cve_data(self, cve_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch detailed CVE information from NVD."""
        if not cve_ids:
            return {}
        
        cve_data = {}
        headers = {}
        if self.config.nvd_api_key:
            headers['apiKey'] = self.config.nvd_api_key
        
        for cve_id in cve_ids[:10]:  # Limit to prevent rate limiting
            cache_key = f"cve_{cve_id}"
            if cache_key in self.cache:
                cve_data[cve_id] = self.cache[cache_key]
                continue
            
            try:
                # Respect NVD rate limits
                await asyncio.sleep(self.config.api_rate_limit_delay)
                
                url = f"{self.config.nvd_api_url}?cveId={cve_id}"
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        vulnerabilities = data.get('vulnerabilities', [])
                        
                        if vulnerabilities:
                            cve_info = vulnerabilities[0].get('cve', {})
                            metrics = cve_info.get('metrics', {})
                            
                            # Extract CVSS scores
                            cvss_data = {}
                            if 'cvssMetricV31' in metrics:
                                cvss_data['cvss_v3'] = metrics['cvssMetricV31'][0]['cvssData']['baseScore']
                            elif 'cvssMetricV30' in metrics:
                                cvss_data['cvss_v3'] = metrics['cvssMetricV30'][0]['cvssData']['baseScore']
                            
                            # Check if actively exploited
                            description = cve_info.get('descriptions', [{}])[0].get('value', '').lower()
                            is_actively_exploited = any(term in description for term in 
                                ['actively exploited', 'in the wild', 'active exploitation'])
                            
                            cve_data[cve_id] = {
                                'description': description,
                                'cvss_scores': cvss_data,
                                'published_date': cve_info.get('published'),
                                'last_modified': cve_info.get('lastModified'),
                                'is_actively_exploited': is_actively_exploited
                            }
                            
                            self.cache[cache_key] = cve_data[cve_id]
                    
            except Exception as e:
                self.logger.warning(f"Failed to fetch CVE data for {cve_id}: {e}")
        
        return cve_data
    
    def map_to_mitre_attack(self, threat_description: str, stride_category: str) -> List[MitreAttackTechnique]:
        """Map threat to MITRE ATT&CK techniques using NLP and heuristics."""
        if not self.mitre_attack_data:
            return []
        
        mapped_techniques = []
        description_lower = threat_description.lower()
        
        # Keyword mapping for common threat patterns
        keyword_to_techniques = {
            'sql injection': ['T1190'],  # Exploit Public-Facing Application
            'command injection': ['T1190', 'T1059'],  # Command and Scripting Interpreter
            'credential': ['T1078', 'T1110'],  # Valid Accounts, Brute Force
            'privilege escalation': ['T1068', 'T1055'],  # Exploitation for Privilege Escalation
            'lateral movement': ['T1021', 'T1072'],  # Remote Services
            'data exfiltration': ['T1041', 'T1048'],  # Exfiltration Over C2 Channel
            'denial of service': ['T1499', 'T1498'],  # Endpoint/Network DoS
            'spoofing': ['T1134', 'T1036'],  # Access Token Manipulation, Masquerading
            'tampering': ['T1565', 'T1491'],  # Data Manipulation
            'repudiation': ['T1070', 'T1202'],  # Indicator Removal
            'information disclosure': ['T1005', 'T1039'],  # Data from Local System
        }
        
        # Check for keyword matches
        for keyword, technique_ids in keyword_to_techniques.items():
            if keyword in description_lower:
                for tech_id in technique_ids:
                    if tech_id in self.mitre_attack_data:
                        tech_data = self.mitre_attack_data[tech_id]
                        mapped_techniques.append(MitreAttackTechnique(
                            technique_id=tech_id,
                            name=tech_data['name'],
                            tactic=tech_data['kill_chain_phases'][0] if tech_data['kill_chain_phases'] else "",
                            description=tech_data['description'][:200] + "..." if len(tech_data['description']) > 200 else tech_data['description']
                        ))
        
        # Use STRIDE mapping as fallback
        if not mapped_techniques and stride_category in STRIDE_TO_ATTACK_STAGE:
            stages = STRIDE_TO_ATTACK_STAGE[stride_category]
            # Add generic techniques based on attack stage
            for stage in stages[:2]:  # Limit to prevent too many mappings
                mapped_techniques.append(MitreAttackTechnique(
                    technique_id=f"T{hash(stage.value) % 1000:04d}",  # Placeholder
                    name=f"Generic {stage.value} Technique",
                    tactic=stage.value,
                    description=f"Mapped from STRIDE category {stride_category}"
                ))
        
        return mapped_techniques[:3]  # Limit to top 3 most relevant

# --- Attack Chain Analyzer ---
class AttackChainAnalyzer:
    """Analyzes threats to identify potential attack chains."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.chains = []
        
    def build_threat_graph(self, threats: List[Dict]) -> nx.DiGraph:
        """Build a directed graph of threat relationships."""
        G = nx.DiGraph()
        
        # Add nodes for each threat
        for threat in threats:
            G.add_node(
                threat.get('threat_id', ''),
                component=threat.get('component_name', ''),
                stride=threat.get('stride_category', ''),
                description=threat.get('threat_description', ''),
                impact=threat.get('impact', 'Medium')
            )
        
        # Add edges based on component flow and STRIDE progression
        for i, threat1 in enumerate(threats):
            for j, threat2 in enumerate(threats):
                if i != j:
                    # Check if threats are on connected components
                    if self._can_chain(threat1, threat2):
                        confidence = self._calculate_chain_confidence(threat1, threat2)
                        if confidence >= self.config.chain_confidence_threshold:
                            G.add_edge(
                                threat1.get('threat_id', ''),
                                threat2.get('threat_id', ''),
                                confidence=confidence
                            )
        
        return G
    
    def _can_chain(self, threat1: Dict, threat2: Dict) -> bool:
        """Determine if two threats can form a chain."""
        # Check component connectivity (simplified - you'd check actual DFD)
        comp1 = threat1.get('component_name', '')
        comp2 = threat2.get('component_name', '')
        
        # Same component or adjacent components can chain
        if comp1 == comp2:
            return True
        
        # Check if output of comp1 feeds into comp2
        if 'to' in comp1 and comp2.startswith(comp1.split('to')[-1].strip()):
            return True
        
        # Check STRIDE progression logic
        stride1 = threat1.get('stride_category', '')
        stride2 = threat2.get('stride_category', '')
        
        # Natural STRIDE progressions
        stride_flow = {
            'S': ['T', 'E', 'I'],  # Spoofing can lead to tampering, elevation, or info disclosure
            'T': ['I', 'D'],       # Tampering can lead to info disclosure or DoS
            'R': ['T', 'I'],       # Repudiation can enable tampering or info disclosure
            'I': ['E', 'T'],       # Info disclosure can enable elevation or tampering
            'D': [],               # DoS is usually an end state
            'E': ['T', 'I', 'D']   # Elevation enables many attacks
        }
        
        return stride2 in stride_flow.get(stride1, [])
    
    def _calculate_chain_confidence(self, threat1: Dict, threat2: Dict) -> float:
        """Calculate confidence score for a threat chain."""
        confidence = 0.5  # Base confidence
        
        # Same component increases confidence
        if threat1.get('component_name') == threat2.get('component_name'):
            confidence += 0.2
        
        # Natural STRIDE progression increases confidence
        stride_progression_bonus = {
            ('S', 'E'): 0.3,  # Spoofing to Elevation is very common
            ('E', 'T'): 0.3,  # Elevation to Tampering is very common
            ('I', 'E'): 0.2,  # Info Disclosure to Elevation
            ('S', 'T'): 0.2,  # Spoofing to Tampering
        }
        
        stride_pair = (threat1.get('stride_category', ''), threat2.get('stride_category', ''))
        confidence += stride_progression_bonus.get(stride_pair, 0.1)
        
        # Similar CVE references increase confidence
        refs1 = set(threat1.get('references', []))
        refs2 = set(threat2.get('references', []))
        if refs1 & refs2:  # Intersection
            confidence += 0.15
        
        return min(confidence, 1.0)
    
    def identify_attack_chains(self, threats: List[Dict]) -> List[AttackChain]:
        """Identify multi-step attack chains from threats."""
        if not self.config.enable_attack_chains:
            return []
        
        G = self.build_threat_graph(threats)
        chains = []
        
        # Find all paths of length 2 to max_chain_length
        threat_ids = [t.get('threat_id', '') for t in threats]
        threat_map = {t.get('threat_id', ''): t for t in threats}
        
        for start_node in G.nodes():
            for end_node in G.nodes():
                if start_node != end_node:
                    try:
                        # Find all simple paths
                        paths = list(nx.all_simple_paths(
                            G, start_node, end_node,
                            cutoff=self.config.max_chain_length
                        ))
                        
                        for path in paths:
                            if len(path) >= 2:
                                chain = self._create_attack_chain(path, G, threat_map)
                                if chain and chain.confidence >= self.config.chain_confidence_threshold:
                                    chains.append(chain)
                    except nx.NetworkXNoPath:
                        continue
        
        # Deduplicate chains (keep highest confidence version)
        unique_chains = {}
        for chain in chains:
            key = tuple(sorted(chain.threats))
            if key not in unique_chains or chain.confidence > unique_chains[key].confidence:
                unique_chains[key] = chain
        
        # Sort by impact and confidence
        final_chains = sorted(
            unique_chains.values(),
            key=lambda c: (c.impact_multiplier * c.confidence),
            reverse=True
        )
        
        return final_chains[:20]  # Top 20 chains
    
    def _create_attack_chain(self, path: List[str], graph: nx.DiGraph, threat_map: Dict) -> Optional[AttackChain]:
        """Create an AttackChain object from a path."""
        if len(path) < 2:
            return None
        
        threats_in_chain = []
        stages = set()
        total_confidence = 1.0
        impact_scores = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        max_impact = 1
        
        for i, threat_id in enumerate(path):
            threat = threat_map.get(threat_id)
            if not threat:
                continue
                
            threats_in_chain.append(threat_id)
            
            # Add attack stages
            stride = threat.get('stride_category', '')
            if stride in STRIDE_TO_ATTACK_STAGE:
                stages.update(STRIDE_TO_ATTACK_STAGE[stride])
            
            # Track impact
            impact = threat.get('impact', 'Medium')
            max_impact = max(max_impact, impact_scores.get(impact, 2))
            
            # Calculate chain confidence
            if i > 0:
                edge_data = graph.get_edge_data(path[i-1], threat_id)
                if edge_data:
                    total_confidence *= edge_data.get('confidence', 0.5)
        
        if not threats_in_chain:
            return None
        
        # Calculate impact multiplier based on chain length and max impact
        impact_multiplier = 1.0 + (len(path) - 1) * 0.3  # Each step adds 30%
        impact_multiplier *= (max_impact / 2)  # Scale by impact level
        
        # Generate description
        description = self._generate_chain_description(threats_in_chain, threat_map)
        
        # Generate unique chain ID
        chain_id = f"CHAIN-{hashlib.md5('-'.join(sorted(threats_in_chain)).encode()).hexdigest()[:8]}"
        
        return AttackChain(
            chain_id=chain_id,
            threats=threats_in_chain,
            stages=list(stages),
            confidence=total_confidence,
            impact_multiplier=impact_multiplier,
            description=description,
            mitre_techniques=[]  # Will be populated later
        )
    
    def _generate_chain_description(self, threat_ids: List[str], threat_map: Dict) -> str:
        """Generate human-readable description of attack chain."""
        if not threat_ids:
            return "Unknown attack chain"
        
        descriptions = []
        for tid in threat_ids:
            threat = threat_map.get(tid, {})
            stride = threat.get('stride_category', 'X')
            component = threat.get('component_name', 'unknown')
            descriptions.append(f"{self._stride_to_action(stride)} on {component}")
        
        return "Attack chain: " + " → ".join(descriptions)
    
    def _stride_to_action(self, stride: str) -> str:
        """Convert STRIDE category to action verb."""
        actions = {
            'S': "Spoof identity",
            'T': "Tamper with data",
            'R': "Repudiate actions",
            'I': "Disclose information",
            'D': "Deny service",
            'E': "Elevate privileges"
        }
        return actions.get(stride, "Perform attack")

# --- Enhanced Threat Processor ---
class EnhancedThreatProcessor:
    """Processes and enriches threats with advanced analysis."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.model = SentenceTransformer(config.embedding_model)
        self.threat_intel_manager = None
        self.attack_chain_analyzer = AttackChainAnalyzer(config)
        self.stats = EnhancedThreatStats()
        
    async def initialize_threat_intelligence(self):
        """Initialize threat intelligence manager."""
        self.threat_intel_manager = ThreatIntelligenceManager(self.config)
        await self.threat_intel_manager.__aenter__()
        # Pre-fetch MITRE ATT&CK data
        self.threat_intel_manager.mitre_attack_data = await self.threat_intel_manager.fetch_mitre_attack_data()
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.threat_intel_manager:
            await self.threat_intel_manager.__aexit__(None, None, None)
    
    def deduplicate_threats_advanced(self, threats: List[Dict]) -> List[Dict]:
        """Advanced threat deduplication using semantic similarity."""
        if not threats:
            return threats
        
        # Generate embeddings for threat descriptions
        descriptions = [t.get('threat_description', '') for t in threats]
        embeddings = self.model.encode(descriptions)
        
        # Cluster similar threats
        clustering = DBSCAN(
            eps=self.config.clustering_eps,
            min_samples=self.config.clustering_min_samples,
            metric='cosine'
        )
        clusters = clustering.fit_predict(embeddings)
        
        # Select representative threat from each cluster
        unique_threats = []
        seen_clusters = set()
        
        for i, cluster_id in enumerate(clusters):
            if cluster_id == -1:  # Noise points are unique
                unique_threats.append(threats[i])
            elif cluster_id not in seen_clusters:
                # Find best representative from cluster
                cluster_indices = [j for j, c in enumerate(clusters) if c == cluster_id]
                
                # Select threat with highest risk score from cluster
                best_idx = max(cluster_indices, key=lambda idx: (
                    {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}.get(
                        threats[idx].get('impact', 'Medium'), 2
                    )
                ))
                
                unique_threats.append(threats[best_idx])
                seen_clusters.add(cluster_id)
                
                # Track deduplication
                self.stats.deduplicated_count += len(cluster_indices) - 1
        
        self.logger.info(f"Reduced {len(threats)} threats to {len(unique_threats)} unique threats")
        return unique_threats
    
    async def process_threat(self, threat: Dict, flow_details: Optional[Dict],
                           dfd_data: Dict, controls: Dict, kev_catalog: Set[str]) -> EnhancedThreat:
        """Process and enrich a single threat with all enhancements."""
        # Calculate environmental score
        environmental_score = self._calculate_environmental_score(threat, flow_details, dfd_data)
        
        # Calculate business impact
        business_impact = self._calculate_business_impact(threat, flow_details, dfd_data)
        
        # Assess control effectiveness
        control_effectiveness = self._assess_control_effectiveness(threat, controls)
        
        # Map to MITRE ATT&CK
        mitre_techniques = self.threat_intel_manager.map_to_mitre_attack(
            threat.get('threat_description', ''),
            threat.get('stride_category', '')
        )
        
        if mitre_techniques:
            self.stats.mitre_techniques_mapped += len(mitre_techniques)
        
        # Extract CVE references
        cve_refs = self._extract_cve_references(threat.get('references', []))
        
        # Enrich CVE data
        cve_data = {}
        if cve_refs:
            cve_data = await self.threat_intel_manager.enrich_cve_data(cve_refs)
        
        # Build threat intelligence
        threat_intel = self._build_threat_intelligence(cve_refs, cve_data, kev_catalog)
        
        if threat_intel.cisa_kev:
            self.stats.threats_in_cisa_kev += 1
        if threat_intel.cve_active_exploits:
            self.stats.threats_with_active_exploits += 1
        
        # Determine detection difficulty and time to exploit
        detection_difficulty = self._assess_detection_difficulty(threat, controls)
        time_to_exploit = self._estimate_time_to_exploit(threat, threat_intel)
        
        # Adjust risk scores based on all factors
        adjusted_risk = self._adjust_risk_score(
            threat.get('risk_score', 'Medium'),
            environmental_score,
            business_impact,
            threat_intel,
            control_effectiveness
        )
        
        # Create enhanced threat object
        enhanced_threat = EnhancedThreat(
            threat_id=threat.get('threat_id', ''),
            component_name=threat.get('component_name', ''),
            stride_category=threat.get('stride_category', ''),
            threat_description=threat.get('threat_description', ''),
            mitigation_suggestion=threat.get('mitigation_suggestion', ''),
            impact=threat.get('impact', 'Medium'),
            likelihood=threat.get('likelihood', 'Medium'),
            references=threat.get('references', []),
            risk_score=adjusted_risk,
            residual_risk_score=threat.get('residual_risk_score', adjusted_risk),
            exploitability=threat.get('exploitability', 'Medium'),
            mitigation_maturity=threat.get('mitigation_maturity', 'Immature'),
            justification=threat.get('justification', ''),
            risk_statement=threat.get('risk_statement', ''),
            status=ThreatStatus.ACTIVE,
            mitre_attack_mapping=mitre_techniques,
            threat_intelligence=threat_intel,
            environmental_score=environmental_score,
            business_impact_score=business_impact,
            detection_difficulty=detection_difficulty,
            time_to_exploit=time_to_exploit,
            control_effectiveness=control_effectiveness
        )
        
        return enhanced_threat
    
    def _calculate_environmental_score(self, threat: Dict, flow_details: Optional[Dict],
                                     dfd_data: Dict) -> float:
        """Calculate environmental factor score."""
        score = 1.0
        
        if not flow_details:
            return score
        
        # Check if internet-facing
        if flow_details.get('crosses_trust_boundary'):
            score *= self.config.environmental_factors.get('internet_facing', 1.5)
        
        # Check environment type
        if 'production' in threat.get('component_name', '').lower():
            score *= self.config.environmental_factors.get('production', 1.4)
        elif 'dev' in threat.get('component_name', '').lower():
            score *= self.config.environmental_factors.get('development', 0.5)
        
        # Apply STRIDE weight
        stride = threat.get('stride_category', '')
        score *= self.config.stride_weights.get(stride, 1.0)
        
        return round(score, 2)
    
    def _calculate_business_impact(self, threat: Dict, flow_details: Optional[Dict],
                                 dfd_data: Dict) -> float:
        """Calculate quantified business impact score (0-100)."""
        base_impact = {"Critical": 100, "High": 75, "Medium": 50, "Low": 25}
        score = base_impact.get(threat.get('impact', 'Medium'), 50)
        
        # Industry-specific adjustments
        if self.config.client_industry == "Finance":
            if 'transaction' in threat.get('threat_description', '').lower():
                score *= 1.5
            if 'payment' in threat.get('threat_description', '').lower():
                score *= 1.4
        elif self.config.client_industry == "Healthcare":
            if 'patient' in threat.get('threat_description', '').lower():
                score *= 1.6
            if 'phi' in threat.get('threat_description', '').lower():
                score *= 1.5
        
        # Data classification impact
        if flow_details:
            data_class = flow_details.get('data_classification', 'internal')
            if data_class == 'restricted':
                score *= 1.5
            elif data_class == 'confidential':
                score *= 1.3
        
        # Availability impact for Fortune 500
        if self.config.company_size == "Fortune 500" and threat.get('stride_category') == 'D':
            score *= 1.4  # DoS has high business impact
        
        return min(round(score, 1), 100.0)
    
    def _assess_control_effectiveness(self, threat: Dict, controls: Dict) -> Dict[str, float]:
        """Assess how effective each control is against this threat."""
        effectiveness = {}
        threat_desc = threat.get('threat_description', '').lower()
        
        # Map controls to threat types
        control_mappings = {
            'https_enabled': ['eavesdropping', 'man-in-the-middle', 'data interception'],
            'mtls_enabled': ['spoofing', 'impersonation', 'unauthorized access'],
            'waf_enabled': ['injection', 'xss', 'web attack'],
            'rate_limiting': ['dos', 'brute force', 'resource exhaustion'],
            'centralized_logging': ['repudiation', 'audit', 'forensics'],
            'encryption_at_rest': ['data theft', 'unauthorized access', 'data breach'],
            'mfa': ['credential', 'authentication', 'account takeover'],
            'zero_trust': ['lateral movement', 'privilege escalation', 'insider threat']
        }
        
        for control, keywords in control_mappings.items():
            if controls.get(control, False):
                # Check if control is relevant to threat
                relevance = any(keyword in threat_desc for keyword in keywords)
                
                if relevance:
                    # Base effectiveness based on control maturity
                    base_effectiveness = 0.7
                    
                    # Adjust based on threat sophistication
                    if threat.get('exploitability') == 'High':
                        base_effectiveness *= 0.8
                    elif threat.get('exploitability') == 'Low':
                        base_effectiveness *= 1.1
                    
                    effectiveness[control] = round(min(base_effectiveness, 0.95), 2)
                else:
                    effectiveness[control] = 0.3  # Minimal effectiveness if not directly relevant
        
        return effectiveness
    
    def _extract_cve_references(self, references: List[str]) -> List[str]:
        """Extract CVE IDs from references."""
        cve_pattern = re.compile(r'CVE-\d{4}-\d{4,}')
        cve_ids = []
        
        for ref in references:
            matches = cve_pattern.findall(ref)
            cve_ids.extend(matches)
        
        return list(set(cve_ids))  # Unique CVEs
    
    def _build_threat_intelligence(self, cve_refs: List[str], cve_data: Dict[str, Dict],
                                 kev_catalog: Set[str]) -> ThreatIntelligence:
        """Build comprehensive threat intelligence."""
        active_exploits = []
        cisa_kev = []
        
        for cve in cve_refs:
            if cve in kev_catalog:
                cisa_kev.append(cve)
            
            if cve in cve_data and cve_data[cve].get('is_actively_exploited'):
                active_exploits.append(cve)
        
        # Determine prevalence based on various factors
        prevalence = "Unknown"
        if len(active_exploits) > 2:
            prevalence = "Widespread"
        elif len(active_exploits) > 0:
            prevalence = "Common"
        elif len(cisa_kev) > 0:
            prevalence = "Uncommon"
        else:
            prevalence = "Rare"
        
        return ThreatIntelligence(
            cve_active_exploits=active_exploits,
            cisa_kev=cisa_kev,
            prevalence=prevalence
        )
    
    def _assess_detection_difficulty(self, threat: Dict, controls: Dict) -> str:
        """Assess how difficult it is to detect this threat."""
        # Base difficulty on threat type
        if threat.get('stride_category') == 'R':  # Repudiation is hard to detect
            base_difficulty = "High"
        elif threat.get('stride_category') in ['S', 'E']:  # Spoofing and Elevation
            base_difficulty = "Medium"
        else:
            base_difficulty = "Low"
        
        # Adjust based on controls
        if controls.get('centralized_logging') and controls.get('siem'):
            # Good monitoring reduces difficulty
            if base_difficulty == "High":
                return "Medium"
            elif base_difficulty == "Medium":
                return "Low"

# --- Data Loader ---
class DataLoader:
    """Handles loading and validation of input data."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def load_json_file(self, file_path: str, default: Any = None) -> Any:
        """Load JSON file with error handling."""
        try:
            if Path(file_path).exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.logger.info(f"Successfully loaded {file_path}")
                return data
            else:
                self.logger.warning(f"File not found: {file_path}")
                return default
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {file_path}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load {file_path}: {e}")
            if default is not None:
                return default
            raise
    
    def load_dfd_components(self) -> Dict[str, Any]:
        """Load DFD components data."""
        return self.load_json_file(self.config.dfd_input_path, {})
    
    def load_threats(self) -> List[Dict[str, Any]]:
        """Load initial threats data."""
        data = self.load_json_file(self.config.threats_input_path, {"threats": []})
        threats = data.get("threats", [])
        if not threats:
            raise ValueError(f"No threats found in {self.config.threats_input_path}")
        return threats
    
    def load_controls(self) -> Dict[str, Any]:
        """Load security controls configuration."""
        default_controls = {
            "https_enabled": False,
            "tls_version": "1.2",
            "mtls_enabled": False,
            "secrets_manager": False,
            "waf_enabled": False,
            "rate_limiting": False,
            "centralized_logging": False,
            "ids_ips": False,
            "siem": False,
            "dlp": False,
            "encryption_at_rest": False,
            "key_management": False,
            "mfa": False,
            "privileged_access_management": False,
            "network_segmentation": False,
            "zero_trust": False
        }
        loaded = self.load_json_file(self.config.controls_input_path, default_controls)
        # Merge with defaults to ensure all keys exist
        return {**default_controls, **loaded}

# --- Executive Summary Generator ---
class ExecutiveSummaryGenerator:
    """Generates executive-level insights and recommendations."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def generate_summary(self, threats: List[EnhancedThreat], chains: List[AttackChain], 
                        stats: EnhancedThreatStats) -> Dict[str, Any]:
        """Generate comprehensive executive summary."""
        total_threats = len(threats)
        critical_threats = [t for t in threats if t.risk_score == "Critical"]
        high_threats = [t for t in threats if t.risk_score == "High"]
        
        # Calculate financial exposure
        financial_exposure = self._calculate_financial_exposure(threats)
        
        # Identify top risks
        top_risks = self._identify_top_risks(threats, chains)
        
        # Generate recommendations
        quick_wins = self._identify_quick_wins(threats)
        strategic_recommendations = self._generate_strategic_recommendations(threats, stats)
        
        # Control gap analysis
        control_gaps = self._analyze_control_gaps(threats)
        
        # Compliance implications
        compliance_risks = self._assess_compliance_risks(threats)
        
        summary = {
            "report_date": datetime.now().isoformat(),
            "threat_landscape": {
                "total_threats": total_threats,
                "critical_threats": len(critical_threats),
                "high_threats": len(high_threats),
                "threats_with_active_exploits": stats.threats_with_active_exploits,
                "threats_in_cisa_kev": stats.threats_in_cisa_kev,
                "attack_chains_identified": stats.attack_chains_identified
            },
            "risk_exposure": {
                "estimated_financial_exposure": financial_exposure,
                "top_business_risks": top_risks,
                "compliance_implications": compliance_risks
            },
            "stride_coverage": stats.coverage_by_stride,
            "recommendations": {
                "immediate_actions": quick_wins,
                "strategic_initiatives": strategic_recommendations,
                "control_improvements": control_gaps
            },
            "threat_intelligence_insights": {
                "prevalent_attack_patterns": self._get_prevalent_patterns(threats),
                "emerging_threats": self._identify_emerging_threats(threats),
                "industry_specific_concerns": self._get_industry_concerns(threats)
            },
            "metrics": {
                "average_time_to_exploit": self._calculate_avg_tte(threats),
                "detection_capability_score": self._calculate_detection_score(threats),
                "mitigation_effectiveness": self._calculate_mitigation_effectiveness(threats)
            }
        }
        
        return summary
    
    def _calculate_financial_exposure(self, threats: List[EnhancedThreat]) -> Dict[str, str]:
        """Estimate financial exposure from threats."""
        exposure_by_impact = {
            "Critical": 5000000,  # $5M+
            "High": 1000000,      # $1M
            "Medium": 500000,     # $500K
            "Low": 50000          # $50K
        }
        
        total_exposure = 0
        for threat in threats:
            if threat.status == ThreatStatus.ACTIVE:
                base_exposure = exposure_by_impact.get(threat.risk_score, 50000)
                # Adjust for business impact
                adjusted_exposure = base_exposure * (threat.business_impact_score / 50)
                total_exposure += adjusted_exposure
        
        # Format exposure ranges
        if total_exposure > 10000000:
            return {
                "range": ">$10M",
                "estimate": f"${total_exposure/1000000:.1f}M",
                "confidence": "Medium"
            }
        elif total_exposure > 5000000:
            return {
                "range": "$5M-$10M",
                "estimate": f"${total_exposure/1000000:.1f}M",
                "confidence": "High"
            }
        elif total_exposure > 1000000:
            return {
                "range": "$1M-$5M",
                "estimate": f"${total_exposure/1000000:.1f}M",
                "confidence": "High"
            }
        else:
            return {
                "range": "<$1M",
                "estimate": f"${total_exposure/1000:.0f}K",
                "confidence": "High"
            }
    
    def _identify_top_risks(self, threats: List[EnhancedThreat], chains: List[AttackChain]) -> List[Dict]:
        """Identify top business risks."""
        risks = []
        
        # High-impact single threats
        critical_threats = sorted(
            [t for t in threats if t.risk_score in ["Critical", "High"]],
            key=lambda t: t.business_impact_score,
            reverse=True
        )[:5]
        
        for threat in critical_threats:
            risks.append({
                "type": "Single Threat",
                "description": threat.risk_statement,
                "business_impact": f"{threat.business_impact_score:.0f}/100",
                "likelihood": threat.likelihood,
                "mitigation_priority": "Immediate" if threat.risk_score == "Critical" else "High"
            })
        
        # High-impact attack chains
        for chain in chains[:3]:  # Top 3 chains
            chain_threats = [t for t in threats if t.threat_id in chain.threats]
            if chain_threats:
                max_impact = max(t.business_impact_score for t in chain_threats)
                risks.append({
                    "type": "Attack Chain",
                    "description": chain.description,
                    "business_impact": f"{max_impact * chain.impact_multiplier:.0f}/100",
                    "likelihood": "Medium",  # Chains are generally less likely but higher impact
                    "mitigation_priority": "Strategic"
                })
        
        return sorted(risks, key=lambda r: float(r['business_impact'].split('/')[0]), reverse=True)[:5]
    
    def _identify_quick_wins(self, threats: List[EnhancedThreat]) -> List[Dict]:
        """Identify quick wins - high impact, easy to implement mitigations."""
        quick_wins = []
        
        for threat in threats:
            if (threat.mitigation_maturity == "Immature" and 
                threat.risk_score in ["High", "Critical"] and
                threat.time_to_exploit in ["Minutes", "Hours", "Days"]):
                
                quick_wins.append({
                    "threat": threat.threat_description[:100] + "...",
                    "mitigation": threat.mitigation_suggestion,
                    "impact_reduction": f"{threat.risk_score} → {threat.residual_risk_score}",
                    "implementation_effort": "Low",
                    "estimated_time": "1-2 weeks"
                })
        
        # Sort by impact reduction
        return sorted(quick_wins, key=lambda w: 
            (w['impact_reduction'].split(' → ')[0] == "Critical", 
             w['impact_reduction'].split(' → ')[0] == "High"),
            reverse=True)[:5]
    
    def _generate_strategic_recommendations(self, threats: List[EnhancedThreat], 
                                          stats: EnhancedThreatStats) -> List[Dict]:
        """Generate strategic security recommendations."""
        recommendations = []
        
        # Check for systemic issues
        stride_gaps = {k: v for k, v in stats.coverage_by_stride.items() if v == 0}
        if stride_gaps:
            recommendations.append({
                "initiative": "STRIDE Coverage Gap Analysis",
                "description": f"No threats identified for STRIDE categories: {', '.join(stride_gaps.keys())}. "
                              "Conduct focused threat modeling sessions.",
                "priority": "High",
                "timeline": "Q1",
                "expected_risk_reduction": "20-30%"
            })
        
        # Check for widespread control gaps
        control_effectiveness = defaultdict(list)
        for threat in threats:
            for control, effectiveness in threat.control_effectiveness.items():
                control_effectiveness[control].append(effectiveness)
        
        weak_controls = []
        for control, effectiveness_list in control_effectiveness.items():
            avg_effectiveness = sum(effectiveness_list) / len(effectiveness_list)
            if avg_effectiveness < 0.5:
                weak_controls.append(control)
        
        if weak_controls:
            recommendations.append({
                "initiative": "Security Control Enhancement",
                "description": f"Upgrade weak controls: {', '.join(weak_controls)}",
                "priority": "High",
                "timeline": "Q1-Q2",
                "expected_risk_reduction": "30-40%"
            })
        
        # Industry-specific recommendations
        if self.config.client_industry == "Finance":
            recommendations.append({
                "initiative": "Zero Trust Architecture Implementation",
                "description": "Implement zero trust principles for financial transaction systems",
                "priority": "Strategic",
                "timeline": "6-12 months",
                "expected_risk_reduction": "40-50%"
            })
        elif self.config.client_industry == "Healthcare":
            recommendations.append({
                "initiative": "Enhanced PHI Protection Program",
                "description": "Implement advanced encryption and access controls for PHI data",
                "priority": "Critical",
                "timeline": "Q1-Q2",
                "expected_risk_reduction": "35-45%"
            })
        
        return recommendations[:5]
    
    def _analyze_control_gaps(self, threats: List[EnhancedThreat]) -> List[Dict]:
        """Analyze gaps in security controls."""
        control_coverage = defaultdict(int)
        control_effectiveness_sum = defaultdict(float)
        
        for threat in threats:
            for control, effectiveness in threat.control_effectiveness.items():
                control_coverage[control] += 1
                control_effectiveness_sum[control] += effectiveness
        
        gaps = []
        for control in control_coverage:
            avg_effectiveness = control_effectiveness_sum[control] / control_coverage[control]
            coverage_percent = (control_coverage[control] / len(threats)) * 100
            
            if avg_effectiveness < 0.6 or coverage_percent < 50:
                gaps.append({
                    "control": control.replace('_', ' ').title(),
                    "coverage": f"{coverage_percent:.0f}%",
                    "average_effectiveness": f"{avg_effectiveness:.0%}",
                    "recommendation": self._get_control_recommendation(control, avg_effectiveness)
                })
        
        return sorted(gaps, key=lambda g: float(g['average_effectiveness'].strip('%')))[:5]
    
    def _get_control_recommendation(self, control: str, effectiveness: float) -> str:
        """Get specific recommendation for control improvement."""
        recommendations = {
            'waf_enabled': "Deploy next-generation WAF with ML-based threat detection",
            'mtls_enabled': "Implement mutual TLS for all service-to-service communication",
            'secrets_manager': "Migrate all secrets to centralized vault with rotation policies",
            'rate_limiting': "Implement adaptive rate limiting with behavioral analysis",
            'centralized_logging': "Deploy SIEM with automated threat detection rules",
            'zero_trust': "Begin zero trust architecture pilot for critical services"
        }
        return recommendations.get(control, f"Enhance {control} implementation and coverage")
    
    def _assess_compliance_risks(self, threats: List[EnhancedThreat]) -> List[Dict]:
        """Assess compliance and regulatory risks."""
        compliance_risks = []
        
        # Check for data protection risks
        data_risks = [t for t in threats if any(
            data_type in t.threat_description.lower() 
            for data_type in ['pii', 'personal', 'phi', 'health', 'payment', 'card']
        )]
        
        if data_risks:
            if self.config.client_industry == "Healthcare":
                compliance_risks.append({
                    "regulation": "HIPAA",
                    "risk_level": "High" if any(t.risk_score == "Critical" for t in data_risks) else "Medium",
                    "potential_fines": "$50K - $1.5M per violation",
                    "key_concerns": [t.threat_description[:100] for t in data_risks[:3]]
                })
            
            # GDPR applies to Fortune 500 companies
            if self.config.company_size == "Fortune 500":
                compliance_risks.append({
                    "regulation": "GDPR",
                    "risk_level": "High",
                    "potential_fines": "Up to 4% of global annual revenue",
                    "key_concerns": ["Data breach notification requirements", "Right to erasure compliance"]
                })
        
        # PCI DSS for payment data
        payment_risks = [t for t in threats if 'payment' in t.threat_description.lower() or 'pci' in t.threat_description.lower()]
        if payment_risks:
            compliance_risks.append({
                "regulation": "PCI DSS",
                "risk_level": "Critical",
                "potential_fines": "$5K - $100K per month",
                "key_concerns": ["Payment data encryption", "Network segmentation"]
            })
        
        return compliance_risks
    
    def _get_prevalent_patterns(self, threats: List[EnhancedThreat]) -> List[str]:
        """Identify prevalent attack patterns."""
        patterns = defaultdict(int)
        
        for threat in threats:
            # Count MITRE techniques
            for technique in threat.mitre_attack_mapping:
                patterns[technique.name] += 1
            
            # Count threat categories
            if 'injection' in threat.threat_description.lower():
                patterns['Injection Attacks'] += 1
            if 'authentication' in threat.threat_description.lower():
                patterns['Authentication Bypass'] += 1
            if 'encryption' not in threat.threat_description.lower() and 'cleartext' in threat.threat_description.lower():
                patterns['Unencrypted Data'] += 1
        
        # Return top patterns
        sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)
        return [f"{pattern} ({count} instances)" for pattern, count in sorted_patterns[:5]]
    
    def _identify_emerging_threats(self, threats: List[EnhancedThreat]) -> List[str]:
        """Identify emerging or trending threats."""
        emerging = []
        
        # Check for supply chain threats
        supply_chain = [t for t in threats if 'supply chain' in t.threat_description.lower() or 'third party' in t.threat_description.lower()]
        if supply_chain:
            emerging.append("Supply chain attacks targeting third-party dependencies")
        
        # Check for AI/ML threats
        ai_threats = [t for t in threats if any(term in t.threat_description.lower() for term in ['ai', 'ml', 'model', 'machine learning'])]
        if ai_threats:
            emerging.append("AI/ML model poisoning and adversarial attacks")
        
        # Check for zero-day indicators
        zero_days = [t for t in threats if t.threat_intelligence and len(t.threat_intelligence.cve_active_exploits) > 0]
        if zero_days:
            emerging.append(f"Active exploitation of {len(zero_days)} vulnerabilities")
        
        return emerging
    
    def _get_industry_concerns(self, threats: List[EnhancedThreat]) -> List[str]:
        """Get industry-specific security concerns."""
        concerns = []
        
        if self.config.client_industry == "Finance":
            financial_threats = [t for t in threats if any(
                term in t.threat_description.lower() 
                for term in ['transaction', 'payment', 'financial', 'banking', 'trading']
            )]
            if financial_threats:
                concerns.append(f"Financial transaction security: {len(financial_threats)} threats identified")
            concerns.append("Regulatory compliance with SOX, PCI-DSS requirements")
            
        elif self.config.client_industry == "Healthcare":
            health_threats = [t for t in threats if any(
                term in t.threat_description.lower() 
                for term in ['patient', 'medical', 'health', 'phi', 'ehr']
            )]
            if health_threats:
                concerns.append(f"Patient data protection: {len(health_threats)} threats identified")
            concerns.append("HIPAA compliance and medical device security")
        
        # Generic Fortune 500 concerns
        if self.config.company_size == "Fortune 500":
            concerns.extend([
                "Brand reputation and customer trust impact",
                "Intellectual property and trade secret protection",
                "Executive and board-level reporting requirements"
            ])
        
        return concerns[:5]
    
    def _calculate_avg_tte(self, threats: List[EnhancedThreat]) -> str:
        """Calculate average time to exploit."""
        tte_values = {
            "Minutes": 1,
            "Hours": 24,
            "Days": 168,
            "Weeks": 720,
            "Months": 2160
        }
        
        total_hours = sum(tte_values.get(t.time_to_exploit, 720) for t in threats)
        avg_hours = total_hours / len(threats) if threats else 720
        
        if avg_hours < 24:
            return "Hours"
        elif avg_hours < 168:
            return "Days"
        elif avg_hours < 720:
            return "Weeks"
        else:
            return "Months"
    
    def _calculate_detection_score(self, threats: List[EnhancedThreat]) -> float:
        """Calculate overall detection capability score."""
        detection_values = {"Low": 3, "Medium": 2, "High": 1}
        total_score = sum(detection_values.get(t.detection_difficulty, 2) for t in threats)
        max_score = len(threats) * 3
        return round((total_score / max_score) * 100, 1) if threats else 0.0
    
    def _calculate_mitigation_effectiveness(self, threats: List[EnhancedThreat]) -> float:
        """Calculate average mitigation effectiveness."""
        effectiveness_scores = []
        for threat in threats:
            if threat.control_effectiveness:
                effectiveness_scores.extend(threat.control_effectiveness.values())
        
        return round(sum(effectiveness_scores) / len(effectiveness_scores) * 100, 1) if effectiveness_scores else 0.0

# --- Main Threat Refiner ---
class EnhancedThreatRefiner:
    """Main orchestrator for enhanced threat refinement pipeline."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.data_loader = DataLoader(config)
        self.processor = EnhancedThreatProcessor(config)
        self.summary_generator = ExecutiveSummaryGenerator(config)
    
    async def refine_threats(self) -> bool:
        """Main refinement pipeline with all enhancements."""
        try:
            self.logger.info("=== Starting Enhanced Threat Refinement Pipeline ===")
            self.logger.info(f"Industry: {self.config.client_industry}, Size: {self.config.company_size}")
            
            # Ensure output directory exists
            Path(self.config.input_dir).mkdir(parents=True, exist_ok=True)
            
            # Load input data
            self.logger.info("Loading input data...")
            threats = self.data_loader.load_threats()
            dfd_data = self.data_loader.load_dfd_components()
            controls = self.data_loader.load_controls()
            
            self.processor.stats.original_count = len(threats)
            self.logger.info(f"Loaded {len(threats)} initial threats")
            
            # Initialize threat intelligence
            await self.processor.initialize_threat_intelligence()
            
            # Fetch external threat data
            self.logger.info("Fetching real-time threat intelligence...")
            kev_catalog = await self.processor.threat_intel_manager.fetch_cisa_kev_catalog()
            
            # Step 1: Standardize component names
            dfd_flows = dfd_data.get('data_flows', [])
            for threat in threats:
                threat['component_name'] = self._standardize_component_name(
                    threat.get('component_name', ''), dfd_flows
                )
            
            # Step 2: Initial suppression based on controls
            self.logger.info("Applying control-based suppression...")
            threats = self._suppress_mitigated_threats(threats, controls)
            
            # Step 3: Advanced deduplication
            self.logger.info("Performing advanced threat deduplication...")
            threats = self.processor.deduplicate_threats_advanced(threats)
            
            # Step 4: Process and enrich each threat
            self.logger.info("Enriching threats with intelligence and business context...")
            enhanced_threats = []
            
            for i, threat in enumerate(threats):
                if i % 10 == 0:
                    self.logger.info(f"Processing threat {i+1}/{len(threats)}...")
                
                # Find corresponding data flow
                flow_details = next(
                    (f for f in dfd_flows if f"{f.get('source', '')} to {f.get('destination', '')}" == threat.get('component_name', '')),
                    None
                )
                
                # Process with all enhancements
                enhanced_threat = await self.processor.process_threat(
                    threat, flow_details, dfd_data, controls, kev_catalog
                )
                enhanced_threats.append(enhanced_threat)
                
                # Update STRIDE coverage
                stride = enhanced_threat.stride_category
                self.processor.stats.coverage_by_stride[stride] = self.processor.stats.coverage_by_stride.get(stride, 0) + 1
            
            # Step 5: Identify attack chains
            self.logger.info("Analyzing attack chains...")
            attack_chains = []
            if self.config.enable_attack_chains:
                # Convert enhanced threats back to dicts for chain analysis
                threat_dicts = [t.dict() for t in enhanced_threats]
                attack_chains = self.processor.attack_chain_analyzer.identify_attack_chains(threat_dicts)
                self.processor.stats.attack_chains_identified = len(attack_chains)
                
                # Update threats with chain membership
                for chain in attack_chains:
                    for threat_id in chain.threats:
                        for threat in enhanced_threats:
                            if threat.threat_id == threat_id:
                                threat.attack_chains.append(chain.chain_id)
            
            # Step 6: Final risk prioritization
            self.logger.info("Performing final risk prioritization...")
            enhanced_threats = self._prioritize_threats(enhanced_threats)
            
            # Update final statistics
            self._update_final_statistics(enhanced_threats)
            
            # Step 7: Generate executive summary
            self.logger.info("Generating executive summary...")
            executive_summary = self.summary_generator.generate_summary(
                enhanced_threats, attack_chains, self.processor.stats
            )
            
            # Step 8: Save all outputs
            await self._save_outputs(enhanced_threats, attack_chains, executive_summary, dfd_data)
            
            # Cleanup
            await self.processor.cleanup()
            
            self.logger.info("=== Enhanced Threat Refinement Pipeline Completed Successfully ===")
            self._log_statistics()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Threat refinement failed: {e}", exc_info=True)
            if hasattr(self, 'processor') and self.processor:
                await self.processor.cleanup()
            return False
    
    def _standardize_component_name(self, original_name: str, valid_flows: List[Dict]) -> str:
        """Standardize component names to match DFD format."""
        if not valid_flows:
            # If no DFD data, return original name
            return original_name
            
        valid_names = {f"{flow['source']} to {flow['destination']}" for flow in valid_flows if 'source' in flow and 'destination' in flow}
        
        # Also add individual component names
        for flow in valid_flows:
            if 'source' in flow:
                valid_names.add(flow['source'])
            if 'destination' in flow:
                valid_names.add(flow['destination'])
        
        # Clean and normalize the name
        normalized = original_name.replace("Data Flow from ", "").replace(" data flow", "").strip()
        normalized = " ".join(normalized.split()).replace(" to ", " to ")
        
        # Handle special cases for common abbreviations
        abbreviation_map = {
            'U': 'User',
            'LB': 'Load Balancer',
            'CDN': 'CDN',
            'WS': 'Web Server',
            'MQ': 'Message Queue',
            'WRK': 'Worker',
            'ADM': 'Admin',
            'ADM_P': 'Admin Portal',
            'DB_P': 'Database',
            'DB_B': 'Database Backup'
        }
        
        # Check if it's an abbreviation
        if original_name in abbreviation_map:
            return abbreviation_map[original_name]
        
        # Check for flow notation with arrows
        if '→' in original_name or '->' in original_name:
            # Convert arrow to 'to'
            normalized = original_name.replace('→', ' to ').replace('->', ' to ')
            parts = normalized.split(' to ')
            if len(parts) == 2:
                src = parts[0].strip()
                dst = parts[1].strip()
                # Map abbreviations in flow
                src = abbreviation_map.get(src, src)
                dst = abbreviation_map.get(dst, dst)
                normalized = f"{src} to {dst}"
        
        if normalized in valid_names:
            return normalized
        
        # Try fuzzy matching
        normalized_lower = normalized.lower()
        for valid_name in valid_names:
            if valid_name.lower() in normalized_lower or normalized_lower in valid_name.lower():
                self.logger.debug(f"Fuzzy matched '{original_name}' to '{valid_name}'")
                return valid_name
        
        # If still not found, try to extract component from the name
        for component in valid_names:
            if component.lower() in original_name.lower():
                self.logger.debug(f"Extracted component '{component}' from '{original_name}'")
                return component
        
        self.logger.warning(f"Component name '{original_name}' not found in DFD flows")
        return original_name
    
    def _suppress_mitigated_threats(self, threats: List[Dict], controls: Dict) -> List[Dict]:
        """Suppress threats that are fully mitigated by controls."""
        active_threats = []
        
        for threat in threats:
            suppress = False
            threat_desc = threat.get('threat_description', '').lower()
            
            # Strong control suppressions
            if controls.get('zero_trust') and 'lateral movement' in threat_desc:
                self.logger.info(f"Suppressing lateral movement threat due to zero trust architecture")
                suppress = True
                self.processor.stats.suppressed_count += 1
            
            if controls.get('dlp') and 'data exfiltration' in threat_desc:
                self.logger.info(f"Suppressing data exfiltration threat due to DLP")
                suppress = True
                self.processor.stats.suppressed_count += 1
            
            if not suppress:
                active_threats.append(threat)
        
        return active_threats
    
    def _prioritize_threats(self, threats: List[EnhancedThreat]) -> List[EnhancedThreat]:
        """Final threat prioritization based on multiple factors."""
        # Calculate priority score for each threat
        for threat in threats:
            priority_score = 0.0
            
            # Risk score component (40%)
            risk_values = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
            priority_score += risk_values.get(threat.risk_score, 1) * 0.4
            
            # Business impact component (30%)
            priority_score += (threat.business_impact_score / 100) * 0.3
            
            # Time to exploit component (20%)
            tte_values = {"Minutes": 4, "Hours": 3, "Days": 2, "Weeks": 1, "Months": 0.5}
            priority_score += tte_values.get(threat.time_to_exploit, 1) * 0.2
            
            # Active exploitation component (10%)
            if threat.threat_intelligence and threat.threat_intelligence.cisa_kev:
                priority_score += 0.1
            
            # Store priority score
            threat.priority_score = priority_score
        
        # Sort by priority score
        return sorted(threats, key=lambda t: t.priority_score, reverse=True)
    
    def _update_final_statistics(self, threats: List[EnhancedThreat]):
        """Update final processing statistics."""
        self.processor.stats.final_count = len(threats)
        
        # Risk distribution
        for threat in threats:
            if threat.risk_score == "Critical":
                self.processor.stats.critical_count += 1
            elif threat.risk_score == "High":
                self.processor.stats.high_count += 1
            elif threat.risk_score == "Medium":
                self.processor.stats.medium_count += 1
            else:
                self.processor.stats.low_count += 1
        
        # Business impact average
        if threats:
            self.processor.stats.average_business_impact = sum(t.business_impact_score for t in threats) / len(threats)
        
        # Top attack vectors
        attack_vectors = defaultdict(int)
        for threat in threats:
            for technique in threat.mitre_attack_mapping:
                attack_vectors[technique.name] += 1
        
        self.processor.stats.top_attack_vectors = sorted(
            attack_vectors.items(), key=lambda x: x[1], reverse=True
        )[:10]
    
    async def _save_outputs(self, threats: List[EnhancedThreat], chains: List[AttackChain],
                           executive_summary: Dict[str, Any], dfd_data: Dict):
        """Save all output files."""
        # Convert threats to dict format
        threats_dict = [threat.dict() for threat in threats]
        chains_dict = [chain.dict() for chain in chains]
        
        # Main output
        output_data = {
            "threats": threats_dict,
            "attack_chains": chains_dict,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "source_dfd": Path(self.config.dfd_input_path).name,
                "source_threats": Path(self.config.threats_input_path).name,
                "refined_threat_count": len(threats),
                "original_threat_count": self.processor.stats.original_count,
                "attack_chains_identified": len(chains),
                "industry_context": self.config.client_industry,
                "company_size": self.config.company_size,
                "processing_config": {
                    "similarity_threshold": self.config.similarity_threshold,
                    "cve_relevance_years": self.config.cve_relevance_years,
                    "embedding_model": self.config.embedding_model,
                    "attack_chain_analysis": self.config.enable_attack_chains
                }
            },
            "executive_summary": executive_summary
        }
        
        # Validate output
        try:
            validated_output = RefinedThreatsOutput(
                threats=threats,
                attack_chains=chains,
                metadata=output_data['metadata'],
                executive_summary=executive_summary
            )
            self.logger.info("Output validation successful")
        except ValidationError as e:
            self.logger.error(f"Output validation failed: {e}")
        
        # Save refined threats
        with open(self.config.refined_threats_output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"Saved refined threats to: {self.config.refined_threats_output_path}")
        
        # Save executive report
        executive_report_path = os.path.join(self.config.input_dir, "executive_threat_report.json")
        with open(executive_report_path, 'w', encoding='utf-8') as f:
            json.dump(executive_summary, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"Saved executive report to: {executive_report_path}")
        
        # Save detailed statistics
        stats_path = os.path.join(self.config.input_dir, "threat_refinement_statistics.json")
        stats_dict = asdict(self.processor.stats)
        stats_dict['processing_timestamp'] = datetime.now().isoformat()
        
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats_dict, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"Saved statistics to: {stats_path}")
    
    def _log_statistics(self):
        """Log final processing statistics."""
        stats = self.processor.stats
        self.logger.info("=== Processing Statistics ===")
        self.logger.info(f"Original threats: {stats.original_count}")
        self.logger.info(f"Suppressed threats: {stats.suppressed_count}")
        self.logger.info(f"Deduplicated threats: {stats.deduplicated_count}")
        self.logger.info(f"Final threats: {stats.final_count}")
        self.logger.info("=== Risk Distribution ===")
        self.logger.info(f"Critical: {stats.critical_count}")
        self.logger.info(f"High: {stats.high_count}")
        self.logger.info(f"Medium: {stats.medium_count}")
        self.logger.info(f"Low: {stats.low_count}")
        self.logger.info("=== Threat Intelligence ===")
        self.logger.info(f"Threats with active exploits: {stats.threats_with_active_exploits}")
        self.logger.info(f"Threats in CISA KEV: {stats.threats_in_cisa_kev}")
        self.logger.info(f"MITRE techniques mapped: {stats.mitre_techniques_mapped}")
        self.logger.info(f"Attack chains identified: {stats.attack_chains_identified}")
        self.logger.info(f"Average business impact score: {stats.average_business_impact:.1f}/100")

# --- Utility Functions ---
def get_event_loop():
    """Get or create an event loop (works in Jupyter)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop

async def main():
    """Main entry point."""
    config = Config()
    refiner = EnhancedThreatRefiner(config)
    success = await refiner.refine_threats()
    return success

def run_enhanced_threat_refiner(config: Optional[Config] = None):
    """Synchronous wrapper for running the enhanced threat refiner."""
    if config is None:
        config = Config()
    
    refiner = EnhancedThreatRefiner(config)
    
    # Check if we're in Jupyter/IPython
    try:
        import IPython
        ipython = IPython.get_ipython()
        if ipython is not None:
            # We're in Jupyter, use nest_asyncio
            try:
                import nest_asyncio
                nest_asyncio.apply()
            except ImportError:
                print("Warning: nest_asyncio not installed. Install it for better Jupyter compatibility.")
    except ImportError:
        pass
    
    # Run the async function
    loop = get_event_loop()
    success = loop.run_until_complete(refiner.refine_threats())
    return success

if __name__ == "__main__":
    # Configure logging for main execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the main function
    loop = get_event_loop()
    success = loop.run_until_complete(main())
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
        
    return base_difficulty
    
    def _estimate_time_to_exploit(self, threat: Dict, threat_intel: ThreatIntelligence) -> str:
        """Estimate time required to exploit this threat."""
        # If actively exploited, it's fast
        if threat_intel.cve_active_exploits:
            return "Hours"
        
        # Based on exploitability
        exploitability = threat.get('exploitability', 'Medium')
        if exploitability == 'High':
            return "Days"
        elif exploitability == 'Medium':
            return "Weeks"
        else:
            return "Months"
    
    def _estimate_time_to_exploit(self, threat: Dict, threat_intel: ThreatIntelligence) -> str:
        """Estimate time required to exploit this threat."""
        # If actively exploited, it's fast
        if threat_intel.cve_active_exploits:
            return "Hours"
        
        # Based on exploitability
        exploitability = threat.get('exploitability', 'Medium')
        if exploitability == 'High':
            return "Days"
        elif exploitability == 'Medium':
            return "Weeks"
        else:
            return "Months"
    
    def _adjust_risk_score(self, base_risk: str, environmental_score: float,
                         business_impact: float, threat_intel: ThreatIntelligence,
                         control_effectiveness: Dict[str, float]) -> str:
        """Adjust risk score based on all factors."""
        risk_values = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        base_value = risk_values.get(base_risk, 2)
        
        # Apply environmental factor
        adjusted_value = base_value * environmental_score
        
        # Boost for active exploitation
        if threat_intel.cve_active_exploits or threat_intel.cisa_kev:
            adjusted_value *= 1.3
        
        # Boost for high business impact
        if business_impact > 75:
            adjusted_value *= 1.2
        
        # Reduce based on control effectiveness
        if control_effectiveness:
            avg_effectiveness = sum(control_effectiveness.values()) / len(control_effectiveness)
            adjusted_value *= (1 - avg_effectiveness * 0.3)  # Max 30% reduction
        
        # Map back to risk level
        if adjusted_value >= 3.5:
            return "Critical"
        elif adjusted_value >= 2.5:
            return "High"
        elif adjusted_value >= 1.5:
            return "Medium"
        else:
            return "Low"