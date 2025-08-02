"""Main service for threat quality improvement."""
import os
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import asdict

from models.attack_path_models import ThreatStats
from services.external_data_service import ExternalDataService
from services.similarity_matcher import SimpleSimilarityMatcher
from services.threat_enrichment_service import ThreatEnrichmentService
from services.threat_suppression_service import ThreatSuppressionService

logger = logging.getLogger(__name__)

class ThreatQualityImprovementService:
    """Main service for improving threat quality."""

    def __init__(self, config: dict):
        self.config = config
        self.stats = ThreatStats()
        self.external_data = ExternalDataService(config)
        self.similarity_matcher = SimpleSimilarityMatcher(config.get('similarity_threshold', 0.7))
        self.enrichment_service = ThreatEnrichmentService(config)
        self.suppression_service = ThreatSuppressionService(config)

    async def improve_threats(self, threats: List[Dict], dfd_data: Dict,
                              controls: Dict) -> Dict[str, Any]:
        """Main threat improvement pipeline."""
        logger.info("Starting threat quality improvement")

        self.stats.original_count = len(threats)

        # Fetch external data
        try:
            kev_catalog = await self.external_data.fetch_cisa_kev_catalog()
        except Exception as e:
            logger.warning(f"Failed to fetch CISA KEV catalog: {e}")
            kev_catalog = set()

        # Step 1: Standardize component names
        threats = self._standardize_component_names(threats, dfd_data)

        # Step 2: Suppress irrelevant threats
        threats, suppressed_count = self.suppression_service.suppress_threats(
            threats, controls, dfd_data, kev_catalog
        )
        self.stats.suppressed_count = suppressed_count

        # Step 3: Deduplicate similar threats
        threats = self._deduplicate_threats(threats)

        # Step 4: Enrich threats with business context
        threats = self._enrich_threats(threats, dfd_data)

        # Step 5: Sort by risk priority
        risk_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        threats.sort(
            key=lambda t: risk_order.get(t.get("risk_score", "Low"), 1),
            reverse=True
        )

        # Update statistics
        self.stats.final_count = len(threats)
        for threat in threats:
            risk_score = threat.get("risk_score", "Low")
            if risk_score == "Critical":
                self.stats.critical_count += 1
            elif risk_score == "High":
                self.stats.high_count += 1
            elif risk_score == "Medium":
                self.stats.medium_count += 1
            else:
                self.stats.low_count += 1

        return self._create_output(threats, dfd_data)

    def _standardize_component_names(self, threats: List[Dict], dfd_data: Dict) -> List[Dict]:
        """Standardize component names to match DFD format."""
        valid_flows = dfd_data.get('data_flows', [])
        valid_names = {f"{flow['source']} to {flow['destination']}" for flow in valid_flows
                       if 'source' in flow and 'destination' in flow}

        for threat in threats:
            original_name = threat.get('component_name', '')

            # Clean and normalize the name
            normalized = original_name.replace("Data Flow from ", "").replace(" data flow", "").strip()
            normalized = " ".join(normalized.split()).replace(" to ", " to ")

            if normalized in valid_names:
                threat['component_name'] = normalized
            else:
                # Try fuzzy matching
                normalized_lower = normalized.lower()
                for valid_name in valid_names:
                    if valid_name.lower() in normalized_lower or normalized_lower in valid_name.lower():
                        logger.debug(f"Fuzzy matched '{original_name}' to '{valid_name}'")
                        threat['component_name'] = valid_name
                        break

        return threats

    def _deduplicate_threats(self, threats: List[Dict]) -> List[Dict]:
        """Deduplicate threats using similarity matching."""
        if len(threats) <= 1:
            return threats

        logger.info(f"Deduplicating {len(threats)} threats")

        # Find similar threat groups
        similar_groups = self.similarity_matcher.find_similar_threats(threats)

        # Create a set of indices that will be merged
        indices_to_remove = set()
        deduplicated_threats = []
        merged_count = 0

        # Process similar groups
        for group in similar_groups:
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

        # Add non-similar threats
        for i, threat in enumerate(threats):
            if i not in indices_to_remove and not any(i in group for group in similar_groups):
                deduplicated_threats.append(threat)

        self.stats.deduplicated_count = merged_count
        logger.info(f"Deduplication merged {merged_count} threats, resulting in {len(deduplicated_threats)} unique threats")

        return deduplicated_threats

    def _enrich_threats(self, threats: List[Dict], dfd_data: Dict) -> List[Dict]:
        """Enrich threats with business context."""
        logger.info("Enriching threats with business risk context")

        enriched_threats = []
        dfd_flows = dfd_data.get('data_flows', [])

        for threat in threats:
            # Find corresponding data flow
            flow_details = next(
                (f for f in dfd_flows if f"{f.get('source', '')} to {f.get('destination', '')}" == threat.get("component_name", "")),
                None
            )

            if flow_details and not flow_details.get("data_classification"):
                logger.warning(f"Data flow '{threat.get('component_name', '')}' missing data_classification")

            enriched_threat = self.enrichment_service.enrich_threat(threat, flow_details, dfd_data)
            enriched_threats.append(enriched_threat)

        return enriched_threats

    def _create_output(self, threats: List[Dict], dfd_data: Dict) -> Dict[str, Any]:
        """Create output structure."""
        return {
            "threats": threats,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "source_dfd": Path(self.config.get('dfd_input_path', '')).name,
                "source_threats": Path(self.config.get('threats_input_path', '')).name,
                "refined_threat_count": len(threats),
                "original_threat_count": self.stats.original_count,
                "industry_context": self.config.get('client_industry', 'General'),
                "processing_config": {
                    "similarity_threshold": self.config.get('similarity_threshold', 0.7),
                    "cve_relevance_years": self.config.get('cve_relevance_years', 5)
                },
                "statistics": asdict(self.stats),
                "risk_distribution": {
                    "critical": self.stats.critical_count,
                    "high": self.stats.high_count,
                    "medium": self.stats.medium_count,
                    "low": self.stats.low_count
                }
            }
        }