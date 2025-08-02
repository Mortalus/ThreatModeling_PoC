"""
Service for analyzing attack paths through the system.
"""
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime

from models.attack_path_models import AttackPath, AttackStep, AttackPathAnalysis
from services.simple_graph import SimpleGraph
from services.llm_service import LLMService

logger = logging.getLogger(__name__)

class AttackPathAnalyzerService:
    """Service for analyzing attack paths."""
    
    def __init__(self, config: dict):
        self.config = config
        self.llm_service = LLMService(config) if config.get('enable_llm_enrichment') else None
        self.graph = SimpleGraph()
        self.threat_map = {}
        self.component_threats = defaultdict(list)
    
    def analyze_attack_paths(self, threats: List[Dict], dfd_data: Dict) -> AttackPathAnalysis:
        """Analyze attack paths from threats and DFD data."""
        logger.info("Starting attack path analysis")
        
        # Build component graph
        self.graph = self._build_component_graph(dfd_data)
        
        # Map threats to components
        self._map_threats_to_components(threats)
        
        # Identify entry points and targets
        entry_points = self._identify_entry_points()
        targets = self._identify_critical_assets(dfd_data)
        
        if not entry_points or not targets:
            logger.warning("No entry points or targets identified")
            return self._create_empty_analysis("No entry points or targets identified")
        
        # Find attack paths
        raw_paths = self._find_attack_paths(entry_points, targets)
        logger.info(f"Found {len(raw_paths)} potential paths")
        
        # Build detailed attack paths
        attack_paths = []
        for path in raw_paths[:self.config.get('max_paths_to_analyze', 20) * 2]:
            detailed_path = self._build_attack_path_details(path)
            if detailed_path:
                attack_paths.append(detailed_path)
        
        if not attack_paths:
            logger.warning("No valid attack paths found")
            return self._create_empty_analysis("No valid attack paths found")
        
        # Enrich with LLM analysis if enabled
        if self.config.get('enable_llm_enrichment') and self.llm_service:
            attack_paths = self._enrich_attack_paths(attack_paths, dfd_data)
        
        # Sort by criticality
        attack_paths.sort(key=self._path_score, reverse=True)
        
        # Generate defense priorities
        defense_priorities = self._generate_defense_priorities(attack_paths)
        
        # Identify critical scenarios
        critical_scenarios = [
            p.scenario_name for p in attack_paths
            if p.path_feasibility != "Theoretical" and p.combined_impact in ["Critical", "High"]
        ][:5]
        
        # Calculate threat coverage
        threat_coverage = self._calculate_threat_coverage(attack_paths, threats)
        
        return AttackPathAnalysis(
            attack_paths=attack_paths[:self.config.get('max_paths_to_analyze', 20)],
            critical_scenarios=critical_scenarios,
            defense_priorities=defense_priorities,
            threat_coverage=threat_coverage,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "total_paths_analyzed": len(raw_paths),
                "detailed_paths_built": len(attack_paths),
                "total_threats": len(threats),
                "entry_points": entry_points[:10],
                "critical_assets": targets[:10],
                "llm_enrichment_enabled": self.config.get('enable_llm_enrichment', False),
                "max_path_length": self.config.get('max_path_length', 5)
            }
        )
    
    def _build_component_graph(self, dfd_data: Dict) -> SimpleGraph:
        """Build a directed graph of system components from DFD."""
        graph = SimpleGraph()
        
        # Track all components
        all_components = set()
        
        # Add nodes
        for entity in dfd_data.get('external_entities', []):
            graph.add_node(entity, type='external_entity', 
                          criticality='high' if entity == 'U' else 'medium',
                          trust_level='untrusted')
            all_components.add(entity)
            
        for process in dfd_data.get('processes', []):
            graph.add_node(process, type='process', criticality='medium',
                          trust_level='semi-trusted')
            all_components.add(process)
            
        for asset in dfd_data.get('assets', []):
            graph.add_node(asset, type='asset', criticality='critical',
                          trust_level='trusted')
            all_components.add(asset)
        
        # Add edges from data flows
        for flow in dfd_data.get('data_flows', []):
            if isinstance(flow, dict) and 'source' in flow and 'destination' in flow:
                source = flow['source']
                dest = flow['destination']
                
                if source in all_components and dest in all_components:
                    graph.add_edge(
                        source, dest,
                        data_classification=flow.get('data_classification', 'Unknown'),
                        protocol=flow.get('protocol', 'Unknown'),
                        authentication=flow.get('authentication_mechanism', 'Unknown')
                    )
                    
                    # Add reverse edge for bidirectional communication
                    graph.add_edge(dest, source,
                                 data_classification=flow.get('data_classification', 'Unknown'),
                                 protocol=flow.get('protocol', 'Unknown'))
        
        logger.info(f"Built graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
        return graph
    
    def _map_threats_to_components(self, threats: List[Dict]):
        """Map threats to their components."""
        for i, threat in enumerate(threats):
            # Ensure threat has an ID
            if 'threat_id' not in threat:
                threat['threat_id'] = f"T{i:03d}"
            
            threat_id = threat['threat_id']
            self.threat_map[threat_id] = threat
            
            # Extract component(s) from threat
            components = self._extract_components_from_threat(threat)
            for component in components:
                self.component_threats[component].append(threat)
    
    def _extract_components_from_threat(self, threat: Dict) -> List[str]:
        """Extract all components mentioned in a threat."""
        components = []
        component_name = threat.get('component_name', '')
        
        # Handle data flow format "A to B" or "A → B"
        if ' to ' in component_name:
            parts = component_name.split(' to ')
            components.extend([p.strip() for p in parts])
        elif ' → ' in component_name:
            parts = component_name.split(' → ')
            components.extend([p.strip() for p in parts])
        elif component_name:
            components.append(component_name.strip())
        
        return components
    
    def _identify_entry_points(self) -> List[str]:
        """Identify potential entry points with scoring."""
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
    
    def _identify_critical_assets(self, dfd_data: Dict) -> List[str]:
        """Identify high-value targets."""
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
    
    def _find_attack_paths(self, entry_points: List[str], targets: List[str]) -> List[List[str]]:
        """Find potential attack paths."""
        all_paths = []
        path_set = set()
        
        for entry in entry_points[:5]:  # Limit for performance
            for target in targets[:5]:
                if entry != target and self.graph.has_node(entry) and self.graph.has_node(target):
                    # Find shortest path first
                    shortest = self.graph.shortest_path(entry, target)
                    if shortest and len(shortest) <= self.config.get('max_path_length', 5):
                        path_tuple = tuple(shortest)
                        if path_tuple not in path_set:
                            all_paths.append(shortest)
                            path_set.add(path_tuple)
                    
                    # Find alternative paths
                    paths = self.graph.find_paths(entry, target, self.config.get('max_path_length', 5))
                    
                    for path in paths[:3]:  # Max 3 paths per pair
                        path_tuple = tuple(path)
                        if path_tuple not in path_set:
                            all_paths.append(path)
                            path_set.add(path_tuple)
        
        return all_paths
    
    def _build_attack_path_details(self, path: List[str]) -> Optional[AttackPath]:
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
                relevant_threat = self._select_relevant_threat(
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
            return None
        
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
    
    def _select_relevant_threat(self, threats: List[Dict], step_position: int, 
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
                if threat['stride_category'] in ['S']:
                    score += 10
                if 'authentication' in threat['threat_description'].lower():
                    score += 5
            elif step_position == total_steps - 1:
                # Last step - prefer data access/tampering
                if threat['stride_category'] in ['T', 'I', 'D']:
                    score += 10
            else:
                # Middle steps - prefer elevation/lateral movement
                if threat['stride_category'] in ['E', 'T']:
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
        max_value = 0
        max_impact = "Low"
        
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
        min_value = 3
        min_likelihood = "High"
        
        for threat in threats:
            likelihood_str = threat.get('likelihood', 'Medium')
            value = likelihood_values.get(likelihood_str, 2)
            if value < min_value:
                min_value = value
                min_likelihood = likelihood_str
        
        return min_likelihood
    
    def _enrich_attack_paths(self, paths: List[AttackPath], dfd_data: Dict) -> List[AttackPath]:
        """Use LLM to enrich attack paths with realistic assessments."""
        if not self.llm_service:
            return paths
        
        enriched_paths = []
        
        for path in paths[:self.config.get('max_paths_to_analyze', 20)]:
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
                
                analysis = self.llm_service.analyze_attack_scenario(path_summary, dfd_data)
                
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
                logger.warning(f"Failed to enrich path {path.path_id}: {e}")
                enriched_paths.append(path)
        
        # Add remaining paths without enrichment
        enriched_paths.extend(paths[self.config.get('max_paths_to_analyze', 20):])
        
        return enriched_paths
    
    def _generate_defense_priorities(self, paths: List[AttackPath]) -> List[Dict[str, Any]]:
        """Generate prioritized defensive recommendations."""
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
        
        # Top chokepoints
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
    
    def _calculate_threat_coverage(self, paths: List[AttackPath], all_threats: List[Dict]) -> Dict[str, int]:
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
    
    def _path_score(self, path: AttackPath) -> int:
        """Calculate path score for sorting."""
        feasibility_score = {"Highly Likely": 3, "Realistic": 2, "Theoretical": 1}
        impact_score = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        return (feasibility_score.get(path.path_feasibility, 1) * 
                impact_score.get(path.combined_impact, 1))
    
    def _create_empty_analysis(self, error_message: str) -> AttackPathAnalysis:
        """Create empty analysis result with error message."""
        return AttackPathAnalysis(
            attack_paths=[],
            critical_scenarios=[],
            defense_priorities=[],
            threat_coverage={},
            metadata={
                "timestamp": datetime.now().isoformat(),
                "error": error_message
            }
        )