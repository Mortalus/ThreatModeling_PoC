#!/usr/bin/env python3
"""
Simplified and Compatible Threat Quality Improvement Script

This script refines and enriches threat model data by:
- Deduplicating similar threats using basic text similarity
- Standardizing component names against DFD data
- Suppressing irrelevant threats based on controls
- Enriching threats with business risk context and prioritization

Simplified to work without heavy ML dependencies.
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
import hashlib
import sys
import re
import logging

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def get_config():
    """Get configuration from environment with defaults."""
    return {
        'input_dir': os.getenv('INPUT_DIR', './output'),
        'dfd_input_path': os.getenv('DFD_INPUT_PATH', ''),
        'threats_input_path': os.getenv('THREATS_INPUT_PATH', ''),
        'refined_threats_output_path': os.getenv('REFINED_THREATS_OUTPUT_PATH', ''),
        'controls_input_path': os.getenv('CONTROLS_INPUT_PATH', ''),
        
        # External APIs
        'nvd_api_url': os.getenv('NVD_API_URL', 'https://services.nvd.nist.gov/rest/json/cves/2.0'),
        'cisa_kev_url': os.getenv('CISA_KEV_URL', 'https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json'),
        
        # Processing parameters
        'similarity_threshold': float(os.getenv('SIMILARITY_THRESHOLD', '0.70')),
        'cve_relevance_years': int(os.getenv('CVE_RELEVANCE_YEARS', '5')),
        'client_industry': os.getenv('CLIENT_INDUSTRY', 'Generic'),
        
        # Performance settings
        'api_timeout': int(os.getenv('API_TIMEOUT', '30')),
        
        # Logging
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        
        # Output directory for progress files
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

@dataclass
class Config:
    """Configuration class for threat refinement pipeline."""
    input_dir: str = config['input_dir']
    dfd_input_path: str = config['dfd_input_path']
    threats_input_path: str = config['threats_input_path']
    refined_threats_output_path: str = config['refined_threats_output_path']
    controls_input_path: str = config['controls_input_path']
    nvd_api_url: str = config['nvd_api_url']
    cisa_kev_url: str = config['cisa_kev_url']
    similarity_threshold: float = config['similarity_threshold']
    cve_relevance_years: int = config['cve_relevance_years']
    client_industry: str = config['client_industry']
    api_timeout: int = config['api_timeout']
    log_level: str = config['log_level']
    output_dir: str = config['output_dir']
    
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

@dataclass
class ThreatStats:
    """Statistics for threat processing."""
    original_count: int = 0
    suppressed_count: int = 0
    deduplicated_count: int = 0
    final_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

class ExternalDataManager:
    """Manages external API calls with simplified error handling."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def fetch_cisa_kev_catalog(self) -> Set[str]:
        """Fetch CISA KEV catalog with basic async handling."""
        try:
            self.logger.info("Fetching CISA KEV catalog...")
            write_progress(4, 5, 100, "Fetching external data", "Downloading CISA KEV catalog")
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.api_timeout)) as session:
                async with session.get(self.config.cisa_kev_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        kev_set = {vuln['cveID'] for vuln in data.get('vulnerabilities', [])}
                        self.logger.info(f"Successfully loaded {len(kev_set)} entries from CISA KEV catalog")
                        write_progress(4, 10, 100, "External data loaded", f"Found {len(kev_set)} known exploited vulnerabilities")
                        return kev_set
                    else:
                        self.logger.warning(f"Failed to fetch CISA KEV catalog: HTTP {response.status}")
                        return set()
        except Exception as e:
            self.logger.warning(f"Failed to fetch CISA KEV catalog: {e}")
            return set()
    
    def check_cve_relevance(self, cve_id: str, kev_catalog: Set[str]) -> bool:
        """Check if a CVE is relevant based on age and exploitation status."""
        # Always consider KEV CVEs as relevant
        if cve_id in kev_catalog:
            self.logger.debug(f"CVE {cve_id} is in CISA KEV catalog - relevant")
            return True
        
        try:
            # Extract year from CVE ID format: CVE-YYYY-NNNNN
            parts = cve_id.split('-')
            if len(parts) >= 2:
                year = int(parts[1])
                cutoff_year = datetime.now().year - self.config.cve_relevance_years
                
                if year >= cutoff_year:
                    return True
                else:
                    self.logger.debug(f"CVE {cve_id} ({year}) is older than {self.config.cve_relevance_years} years - not relevant")
                    return False
        except (ValueError, IndexError):
            self.logger.warning(f"Could not parse year from CVE ID {cve_id} - assuming relevant")
            return True
        
        return False

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
            if default is not None:
                return default
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
            "centralized_logging": False
        }
        return self.load_json_file(self.config.controls_input_path, default_controls)

class SimpleSimilarityMatcher:
    """Simple text similarity matching without ML dependencies."""
    
    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple similarity between two texts."""
        # Convert to lowercase and split into words
        words1 = set(re.findall(r'\b\w+\b', text1.lower()))
        words2 = set(re.findall(r'\b\w+\b', text2.lower()))
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def find_similar_threats(self, threats: List[Dict]) -> List[List[int]]:
        """Find groups of similar threats."""
        n = len(threats)
        similar_groups = []
        processed = set()
        
        for i in range(n):
            if i in processed:
                continue
            
            current_group = [i]
            threat_text_i = f"{threats[i].get('threat_description', '')} {threats[i].get('mitigation_suggestion', '')}"
            
            for j in range(i + 1, n):
                if j in processed:
                    continue
                
                threat_text_j = f"{threats[j].get('threat_description', '')} {threats[j].get('mitigation_suggestion', '')}"
                
                # Check if they're for the same component and have similar text
                if (threats[i].get('component_name') == threats[j].get('component_name') and
                    threats[i].get('stride_category') == threats[j].get('stride_category') and
                    self.calculate_similarity(threat_text_i, threat_text_j) >= self.threshold):
                    
                    current_group.append(j)
                    processed.add(j)
            
            if len(current_group) > 1:
                similar_groups.append(current_group)
            
            processed.add(i)
        
        return similar_groups

class ThreatProcessor:
    """Core threat processing logic."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.similarity_matcher = SimpleSimilarityMatcher(config.similarity_threshold)
        self.stats = ThreatStats()
    
    def standardize_component_name(self, original_name: str, valid_flows: List[Dict]) -> str:
        """Standardize component names to match DFD format."""
        valid_names = {f"{flow['source']} to {flow['destination']}" for flow in valid_flows 
                      if 'source' in flow and 'destination' in flow}
        
        # Clean and normalize the name
        normalized = original_name.replace("Data Flow from ", "").replace(" data flow", "").strip()
        normalized = " ".join(normalized.split()).replace(" to ", " to ")
        
        if normalized in valid_names:
            return normalized
        
        # Try fuzzy matching
        normalized_lower = normalized.lower()
        for valid_name in valid_names:
            if valid_name.lower() in normalized_lower or normalized_lower in valid_name.lower():
                self.logger.debug(f"Fuzzy matched '{original_name}' to '{valid_name}'")
                return valid_name
        
        self.logger.warning(f"Component name '{original_name}' not found in DFD flows")
        return original_name
    
    def calculate_risk_score(self, impact: str, likelihood: str) -> str:
        """Calculate risk score based on impact and likelihood matrix."""
        impact_values = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        likelihood_values = {"High": 3, "Medium": 2, "Low": 1}
        
        # Calculate numeric score
        impact_val = impact_values.get(impact, 1)
        likelihood_val = likelihood_values.get(likelihood, 1)
        score = impact_val * likelihood_val
        
        # Return appropriate risk score string based on calculation
        if score >= 9:
            return "Critical"
        elif score >= 6:
            return "High"
        elif score >= 3:
            return "Medium"
        else:
            return "Low"
    
    def assess_exploitability(self, threat: Dict, dfd_data: Dict) -> str:
        """Assess exploitability based on component exposure."""
        component_name = threat["component_name"]
        flows = dfd_data.get("data_flows", [])
        
        # Find corresponding flow
        flow = next((f for f in flows 
                    if f"{f.get('source', '')} to {f.get('destination', '')}" == component_name), None)
        
        if not flow:
            return "Medium"  # Default for unknown flows
        
        # Check if externally exposed
        if flow.get("source") == "U" or flow.get("destination") == "U":
            return "High"
        
        # Check protocol security
        protocol = flow.get("protocol", "").upper()
        if any(secure in protocol for secure in ["TLS", "HTTPS", "SSH", "SFTP"]):
            return "Medium"
        elif any(insecure in protocol for insecure in ["HTTP", "FTP", "TELNET"]):
            return "High"
        
        return "Low"  # Internal with unknown/secure protocol
    
    def assess_mitigation_maturity(self, mitigation: str) -> str:
        """Assess the maturity level of proposed mitigation."""
        mitigation_lower = mitigation.lower()
        
        # Advanced mitigations
        advanced_keywords = ["end-to-end encryption", "certificate pinning", "zero trust", "hardware security module"]
        if any(keyword in mitigation_lower for keyword in advanced_keywords):
            return "Advanced"
        
        # Mature mitigations
        mature_keywords = ["mtls", "waf", "rate limiting", "secrets management", "multi-factor", "rbac"]
        if any(keyword in mitigation_lower for keyword in mature_keywords):
            return "Mature"
        
        # Immature mitigations
        immature_keywords = ["logging", "monitoring", "manual review", "periodic check"]
        if any(keyword in mitigation_lower for keyword in immature_keywords):
            return "Immature"
        
        return "Mature"  # Default assumption
    
    def generate_justification(self, threat: Dict, flow_details: Optional[Dict]) -> str:
        """Generate justification for impact and likelihood ratings."""
        impact = threat.get('impact', 'Medium')
        likelihood = threat.get('likelihood', 'Medium')
        
        # Build impact justification
        impact_reasons = []
        if flow_details:
            data_classification = flow_details.get("data_classification", "Unclassified")
            if data_classification in ["PII", "PHI", "PCI", "Confidential"]:
                impact_reasons.append(f"handles {data_classification} data with regulatory implications")
            elif data_classification != "Unclassified":
                impact_reasons.append(f"processes {data_classification} data")
        
        if "database" in threat["component_name"].lower():
            impact_reasons.append("involves critical data storage")
        
        impact_justification = f"Impact rated {impact}"
        if impact_reasons:
            impact_justification += f" due to: {', '.join(impact_reasons)}"
        
        # Build likelihood justification
        likelihood_reasons = []
        if flow_details and flow_details.get("source") == "U":
            likelihood_reasons.append("internet-facing component increases attack surface")
        
        stride_category = threat.get("stride_category", "")
        if stride_category in ["S", "T"]:  # Spoofing, Tampering
            likelihood_reasons.append("authentication/integrity threats are commonly exploited")
        
        likelihood_justification = f"Likelihood rated {likelihood}"
        if likelihood_reasons:
            likelihood_justification += f" because: {', '.join(likelihood_reasons)}"
        
        return f"{impact_justification}. {likelihood_justification}."
    
    def generate_risk_statement(self, threat: Dict, flow_details: Optional[Dict]) -> str:
        """Generate business-contextualized risk statement."""
        impact_descriptions = {
            "Critical": "severe financial loss (>$1M), major regulatory fines, and long-term reputational damage",
            "High": "significant financial loss (>$500K), regulatory fines, or reputational damage",
            "Medium": "moderate financial loss ($50K-$500K) or operational disruption",
            "Low": "minimal financial or operational impact"
        }
        
        component = threat["component_name"]
        impact = threat.get("impact", "Medium")
        
        # Build base risk statement
        risk_statement = f"Exploitation of '{threat['threat_description']}' in the '{component}' component could result in {impact_descriptions[impact]}."
        
        # Add industry-specific context
        if flow_details:
            data_classification = flow_details.get("data_classification", "")
            if self.config.client_industry == "Finance" and data_classification == "PCI":
                risk_statement += " This may result in PCI-DSS compliance violations."
            elif self.config.client_industry == "Healthcare" and data_classification == "PHI":
                risk_statement += " This may result in HIPAA regulatory violations."
        
        # Add mitigation impact
        if threat.get('residual_risk_score') != threat.get('risk_score'):
            risk_statement += f" Implementing the proposed mitigation is expected to reduce risk to '{threat.get('residual_risk_score', 'Medium')}' level."
        
        return risk_statement
    
    def suppress_threats(self, threats: List[Dict], controls: Dict, dfd_data: Dict, kev_catalog: Set[str]) -> List[Dict]:
        """Suppress threats based on implemented controls and CVE relevance."""
        data_manager = ExternalDataManager(self.config)
        active_threats = []
        total_threats = len(threats)
        
        for i, threat in enumerate(threats):
            if check_kill_signal(4):
                return active_threats
                
            # Update progress
            progress = 20 + int((i / total_threats) * 15)
            write_progress(4, progress, 100, 
                         f"Suppressing threats ({i+1}/{total_threats})", 
                         f"Analyzing: {threat.get('component_name', 'Unknown')}")
            
            suppress = False
            component = threat["component_name"]
            
            # Control-based suppression
            if controls.get("mtls_enabled") and "spoof" in threat["threat_description"].lower():
                self.logger.info(f"Suppressing spoofing threat for '{component}' due to mTLS control")
                suppress = True
                self.stats.suppressed_count += 1
            
            if controls.get("secrets_manager") and any(keyword in threat["threat_description"].lower() 
                                                    for keyword in ["cleartext", "hardcoded", "plain text"]):
                self.logger.info(f"Suppressing credential threat for '{component}' due to secrets manager")
                suppress = True
                self.stats.suppressed_count += 1
            
            if controls.get("waf_enabled") and "injection" in threat["threat_description"].lower():
                self.logger.info(f"Suppressing injection threat for '{component}' due to WAF")
                suppress = True
                self.stats.suppressed_count += 1
            
            # CVE relevance filtering
            if not suppress and threat.get("references"):
                relevant_references = []
                for ref in threat["references"]:
                    if ref.startswith("CVE-"):
                        if data_manager.check_cve_relevance(ref, kev_catalog):
                            relevant_references.append(ref)
                        else:
                            self.logger.debug(f"Filtering out irrelevant CVE: {ref}")
                    else:
                        relevant_references.append(ref)
                
                # Suppress if all CVE references were irrelevant
                if threat["references"] and not relevant_references and all(ref.startswith("CVE-") for ref in threat["references"]):
                    self.logger.info(f"Suppressing threat for '{component}' - all CVE references were irrelevant")
                    suppress = True
                    self.stats.suppressed_count += 1
                else:
                    threat["references"] = relevant_references
            
            if not suppress:
                active_threats.append(threat)
        
        return active_threats
    
    def deduplicate_threats(self, threats: List[Dict]) -> List[Dict]:
        """Deduplicate threats using simple similarity matching."""
        if len(threats) <= 1:
            return threats
        
        self.logger.info(f"Deduplicating {len(threats)} threats using simple similarity matching")
        write_progress(4, 40, 100, "Deduplicating threats", f"Analyzing {len(threats)} threats for similarity")
        
        # Find similar threat groups
        similar_groups = self.similarity_matcher.find_similar_threats(threats)
        
        # Create a set of indices that will be merged
        indices_to_remove = set()
        deduplicated_threats = []
        merged_count = 0
        
        # Process similar groups
        for group_idx, group in enumerate(similar_groups):
            # Update progress
            progress = 40 + int((group_idx / len(similar_groups)) * 10) if similar_groups else 50
            write_progress(4, progress, 100, 
                         f"Processing similar group {group_idx+1}/{len(similar_groups)}", 
                         f"Merging {len(group)} similar threats")
            
            # Select primary threat (most detailed description)
            primary_idx = max(group, key=lambda i: len(threats[i].get('threat_description', '')))
            primary_threat = threats[primary_idx].copy()
            
            # Merge data from other threats in the group
            for idx in group:
                if idx != primary_idx:
                    other_threat = threats[idx]
                    
                    # Take the best mitigation (most detailed)
                    if len(other_threat.get('mitigation_suggestion', '')) > len(primary_threat.get('mitigation_suggestion', '')):
                        primary_threat['mitigation_suggestion'] = other_threat.get('mitigation_suggestion', '')
                    
                    # Combine all unique references
                    primary_refs = set(primary_threat.get("references", []))
                    other_refs = set(other_threat.get("references", []))
                    primary_threat["references"] = sorted(list(primary_refs.union(other_refs)))
                    
                    # Take the highest impact/likelihood from the group
                    impact_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
                    likelihood_order = {"High": 3, "Medium": 2, "Low": 1}
                    
                    current_impact = primary_threat.get("impact", "Low")
                    other_impact = other_threat.get("impact", "Low")
                    if impact_order.get(other_impact, 1) > impact_order.get(current_impact, 1):
                        primary_threat["impact"] = other_impact
                    
                    current_likelihood = primary_threat.get("likelihood", "Low")
                    other_likelihood = other_threat.get("likelihood", "Low")
                    if likelihood_order.get(other_likelihood, 1) > likelihood_order.get(current_likelihood, 1):
                        primary_threat["likelihood"] = other_likelihood
                    
                    indices_to_remove.add(idx)
            
            deduplicated_threats.append(primary_threat)
            merged_count += len(group) - 1
            
            self.logger.debug(f"Merged {len(group)} similar threats for component '{primary_threat.get('component_name', 'Unknown')}'")
        
        # Add non-similar threats
        for i, threat in enumerate(threats):
            if i not in indices_to_remove and not any(i in group for group in similar_groups):
                deduplicated_threats.append(threat)
        
        self.stats.deduplicated_count = merged_count
        self.logger.info(f"Deduplication merged {merged_count} threats, resulting in {len(deduplicated_threats)} unique threats")
        write_progress(4, 50, 100, "Deduplication complete", f"Reduced to {len(deduplicated_threats)} unique threats")
        
        return deduplicated_threats
    
    def enrich_threat(self, threat: Dict, flow_details: Optional[Dict], dfd_data: Dict) -> Dict:
        """Enrich a single threat with calculated fields and assessments."""
        # Upgrade impact based on data classification
        if flow_details and flow_details.get("data_classification") in ["PII", "PHI", "PCI", "Confidential"]:
            current_impact = threat.get("impact", "Medium")
            if current_impact == "Medium":
                threat["impact"] = "High"
            elif current_impact == "High":
                threat["impact"] = "Critical"
        
        # Calculate derived fields
        threat["risk_score"] = self.calculate_risk_score(threat.get("impact", "Medium"), threat.get("likelihood", "Medium"))
        
        # Calculate residual risk (assume mitigation reduces likelihood by one level)
        current_likelihood = threat.get("likelihood", "Medium")
        mitigated_likelihood = {
            "High": "Medium",
            "Medium": "Low",
            "Low": "Low"
        }.get(current_likelihood, "Low")
        
        threat["residual_risk_score"] = self.calculate_risk_score(threat.get("impact", "Medium"), mitigated_likelihood)
        
        # Assess exploitability and mitigation maturity
        threat["exploitability"] = self.assess_exploitability(threat, dfd_data)
        threat["mitigation_maturity"] = self.assess_mitigation_maturity(threat.get("mitigation_suggestion", ""))
        
        # Generate human-readable fields
        threat["justification"] = self.generate_justification(threat, flow_details)
        threat["risk_statement"] = self.generate_risk_statement(threat, flow_details)
        
        return threat

class ThreatRefiner:
    """Main threat refinement orchestrator."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.data_loader = DataLoader(config)
        self.processor = ThreatProcessor(config)
        self.external_data = ExternalDataManager(config)
    
    async def refine_threats(self) -> bool:
        """Main refinement pipeline."""
        try:
            self.logger.info("=== Starting Threat Refinement Pipeline ===")
            write_progress(4, 0, 100, "Starting threat refinement", "Initializing pipeline")
            
            # Ensure output directory exists
            Path(self.config.input_dir).mkdir(parents=True, exist_ok=True)
            
            # Load input data
            self.logger.info("Loading input data...")
            write_progress(4, 2, 100, "Loading data", "Reading threat and DFD files")
            
            threats = self.data_loader.load_threats()
            dfd_data = self.data_loader.load_dfd_components()
            controls = self.data_loader.load_controls()
            
            self.processor.stats.original_count = len(threats)
            self.logger.info(f"Loaded {len(threats)} initial threats")
            write_progress(4, 5, 100, "Data loaded", f"Found {len(threats)} threats to refine")
            
            # Fetch external data (with fallback)
            try:
                if check_kill_signal(4):
                    return False
                kev_catalog = await self.external_data.fetch_cisa_kev_catalog()
            except Exception as e:
                self.logger.warning(f"Failed to fetch CISA KEV catalog, continuing without it: {e}")
                kev_catalog = set()
                write_progress(4, 10, 100, "External data skipped", "Continuing without KEV catalog")
            
            # Step 1: Standardize component names
            if check_kill_signal(4):
                return False
            write_progress(4, 15, 100, "Standardizing names", "Matching components to DFD")
            
            dfd_flows = dfd_data.get("data_flows", [])
            for threat in threats:
                threat["component_name"] = self.processor.standardize_component_name(
                    threat.get("component_name", ""), dfd_flows
                )
            
            # Step 2: Suppress irrelevant threats
            if check_kill_signal(4):
                return False
            self.logger.info("Suppressing irrelevant threats based on controls and CVE analysis...")
            write_progress(4, 20, 100, "Suppressing threats", "Analyzing controls and CVEs")
            threats = self.processor.suppress_threats(threats, controls, dfd_data, kev_catalog)
            
            # Step 3: Deduplicate similar threats
            if check_kill_signal(4):
                return False
            self.logger.info("Deduplicating similar threats...")
            threats = self.processor.deduplicate_threats(threats)
            
            # Step 4: Enrich threats with business context
            if check_kill_signal(4):
                return False
            self.logger.info("Enriching threats with business risk context...")
            write_progress(4, 55, 100, "Enriching threats", "Adding business context")
            
            enriched_threats = []
            total_threats = len(threats)
            
            for i, threat in enumerate(threats):
                if check_kill_signal(4):
                    return False
                    
                # Update progress
                progress = 55 + int((i / total_threats) * 35)
                write_progress(4, progress, 100, 
                             f"Enriching threat {i+1}/{total_threats}", 
                             threat.get('component_name', 'Unknown'))
                
                # Find corresponding data flow
                flow_details = next(
                    (f for f in dfd_flows if f"{f.get('source', '')} to {f.get('destination', '')}" == threat.get("component_name", "")),
                    None
                )
                
                if flow_details and not flow_details.get("data_classification"):
                    self.logger.warning(f"Data flow '{threat.get('component_name', '')}' missing data_classification")
                
                enriched_threat = self.processor.enrich_threat(threat, flow_details, dfd_data)
                enriched_threats.append(enriched_threat)
            
            # Step 5: Sort by risk priority
            if check_kill_signal(4):
                return False
            write_progress(4, 92, 100, "Sorting threats", "Prioritizing by risk score")
            
            risk_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
            enriched_threats.sort(
                key=lambda t: risk_order.get(t.get("risk_score", "Low"), 1),
                reverse=True
            )
            
            # Update final statistics
            self.processor.stats.final_count = len(enriched_threats)
            for threat in enriched_threats:
                risk_score = threat.get("risk_score", "Low")
                if risk_score == "Critical":
                    self.processor.stats.critical_count += 1
                elif risk_score == "High":
                    self.processor.stats.high_count += 1
                elif risk_score == "Medium":
                    self.processor.stats.medium_count += 1
                else:
                    self.processor.stats.low_count += 1
            
            # Step 6: Generate and save output
            if check_kill_signal(4):
                return False
            write_progress(4, 95, 100, "Saving results", "Writing refined threats")
            await self._save_outputs(enriched_threats, dfd_data)
            
            self.logger.info("=== Threat Refinement Pipeline Completed Successfully ===")
            self._log_statistics()
            write_progress(4, 100, 100, "Complete", f"Refined {len(enriched_threats)} threats")
            
            # Clean up progress file after success
            try:
                progress_file = os.path.join(self.config.output_dir, 'step_4_progress.json')
                if os.path.exists(progress_file):
                    os.remove(progress_file)
            except:
                pass
            
            return True
            
        except Exception as e:
            self.logger.error(f"Threat refinement failed: {e}")
            write_progress(4, 100, 100, "Failed", str(e))
            return False
    
    async def _save_outputs(self, threats: List[Dict], dfd_data: Dict):
        """Save all output files."""
        # Prepare main output
        output_data = {
            "threats": threats,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "source_dfd": Path(self.config.dfd_input_path).name,
                "source_threats": Path(self.config.threats_input_path).name,
                "refined_threat_count": len(threats),
                "original_threat_count": self.processor.stats.original_count,
                "industry_context": self.config.client_industry,
                "processing_config": {
                    "similarity_threshold": self.config.similarity_threshold,
                    "cve_relevance_years": self.config.cve_relevance_years
                }
            }
        }
        
        # Save refined threats
        with open(self.config.refined_threats_output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved refined threats to: {self.config.refined_threats_output_path}")
        
        # Generate and save summary report
        summary_path = os.path.join(self.config.input_dir, "refinement_summary.json")
        summary = {
            "statistics": asdict(self.processor.stats),
            "risk_distribution": {
                "critical": self.processor.stats.critical_count,
                "high": self.processor.stats.high_count,
                "medium": self.processor.stats.medium_count,
                "low": self.processor.stats.low_count
            },
            "suppression_reasons": {
                "controls_applied": self.processor.stats.suppressed_count,
                "threats_deduplicated": self.processor.stats.deduplicated_count
            },
            "timestamp": datetime.now().isoformat()
        }
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info(f"Saved refinement summary to: {summary_path}")
    
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


def get_event_loop():
    """Get or create an event loop (works in various environments)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


async def main():
    """Main entry point."""
    config = Config()
    refiner = ThreatRefiner(config)
    success = await refiner.refine_threats()
    return success


def run_threat_refiner(config: Optional[Config] = None):
    """Synchronous wrapper for running the threat refiner."""
    if config is None:
        config = Config()
    
    refiner = ThreatRefiner(config)
    
    # Handle different async environments
    try:
        # Check if we're in an environment with an existing event loop
        try:
            loop = asyncio.get_running_loop()
            # If we get here, we're in an async context (like Jupyter)
            # Try to use nest_asyncio if available
            try:
                import nest_asyncio
                nest_asyncio.apply()
                success = loop.run_until_complete(refiner.refine_threats())
            except ImportError:
                # Fallback: create a new loop in a thread
                import threading
                result = [None]
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result[0] = new_loop.run_until_complete(refiner.refine_threats())
                    new_loop.close()
                
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()
                success = result[0]
        except RuntimeError:
            # No existing event loop, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(refiner.refine_threats())
            loop.close()
    except Exception as e:
        logger.error(f"Failed to run threat refiner: {e}")
        success = False
    
    return success


if __name__ == "__main__":
    # Configure logging for main execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("--- Starting Threat Quality Improvement Script ---")
    
    try:
        # Run the main function
        success = run_threat_refiner()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Script failed with error: {e}")
        sys.exit(1)