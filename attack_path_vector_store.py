#!/usr/bin/env python3
# attack_path_vector_store.py

"""
Vector Store Module for Attack Paths using Qdrant
Provides semantic search, similarity matching, and cross-project intelligence
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib
from enum import Enum

import numpy as np
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, 
    Filter, FieldCondition, MatchValue, Range,
    SearchRequest, UpdateStatus, CollectionStatus,
    CreateCollection, OptimizersConfig, SearchParams
)
from sentence_transformers import SentenceTransformer
import torch

from dotenv import load_dotenv

# Import models from attack path analyzer
from attack_path_analyzer import (
    AttackPath, AttackStep, ThreatLikelihood, 
    ThreatImpact, PathFeasibility, AttackerProfile
)

# Load environment variables
load_dotenv()

# Configuration
@dataclass
class VectorStoreConfig:
    """Configuration for Qdrant vector store."""
    qdrant_url: str = field(default_factory=lambda: os.getenv("QDRANT_URL", "http://homebase:6333"))
    qdrant_api_key: Optional[str] = field(default_factory=lambda: os.getenv("QDRANT_API_KEY"))
    collection_name: str = field(default_factory=lambda: os.getenv("QDRANT_COLLECTION", "attack_paths"))
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
    vector_size: int = 384  # for all-MiniLM-L6-v2
    
    # Search parameters
    default_search_limit: int = 10
    similarity_threshold: float = 0.7
    
    # Advanced features
    enable_cross_project_search: bool = True
    enable_pattern_learning: bool = True
    enable_defense_recommendations: bool = True
    
    def __post_init__(self):
        """Adjust vector size based on embedding model."""
        # Model to dimension mapping
        model_dimensions = {
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
            "all-distilroberta-v1": 768,
            "multi-qa-mpnet-base-dot-v1": 768,
            "all-MiniLM-L12-v2": 384,
            "paraphrase-multilingual-MiniLM-L12-v2": 384,
            "paraphrase-albert-small-v2": 768,
            "paraphrase-MiniLM-L3-v2": 384,
        }
        
        # Set vector size based on model
        if self.embedding_model in model_dimensions:
            self.vector_size = model_dimensions[self.embedding_model]
        else:
            # Default to 384 for unknown models
            self.vector_size = 384

# Extended models for vector store
class PathEmbedding(BaseModel):
    """Represents an embedded attack path."""
    path_id: str
    embedding: List[float]
    narrative: str
    step_embeddings: Dict[int, List[float]]
    metadata: Dict[str, Any]

class SearchQuery(BaseModel):
    """Search query parameters."""
    query_type: str = Field(description="text|path|technique|component|impact")
    query: Union[str, AttackPath, Dict[str, Any]]
    filters: Optional[Dict[str, Any]] = None
    limit: int = 10
    include_cross_project: bool = True
    min_similarity: float = 0.5

class DefenseRecommendation(BaseModel):
    """Defensive control recommendation based on similar paths."""
    control_name: str
    effectiveness_score: float
    similar_paths_blocked: int
    implementation_complexity: str
    evidence: List[str]

class AttackPattern(BaseModel):
    """Recurring attack pattern identified across paths."""
    pattern_id: str
    pattern_name: str
    description: str
    common_steps: List[str]
    frequency: int
    affected_projects: List[str]
    typical_impact: str
    typical_attacker: str
    common_defenses: List[str]

# Main Vector Store Class
class AttackPathVectorStore:
    """Manages attack paths in Qdrant vector database."""
    
    def __init__(self, config: VectorStoreConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.AttackPathVectorStore")
        
        # Initialize Qdrant client
        self.client = QdrantClient(
            url=config.qdrant_url,
            api_key=config.qdrant_api_key
        )
        
        # Initialize embedding model
        self.logger.info(f"Loading embedding model: {config.embedding_model}")
        self.embedding_model = SentenceTransformer(config.embedding_model)
        
        # Ensure collection exists
        self._ensure_collection()
        
    def _ensure_collection(self):
        """Ensure the Qdrant collection exists with proper configuration."""
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            exists = any(c.name == self.config.collection_name for c in collections)
            
            if not exists:
                self.logger.info(f"Creating collection: {self.config.collection_name}")
                self.client.create_collection(
                    collection_name=self.config.collection_name,
                    vectors_config=VectorParams(
                        size=self.config.vector_size,
                        distance=Distance.COSINE
                    )
                    # OptimizersConfig is optional and will use defaults if not specified
                )
                
                # Create indexes for common filters
                self._create_indexes()
            else:
                self.logger.info(f"Collection {self.config.collection_name} already exists")
                
                # Check if vector dimensions match
                collection_info = self.client.get_collection(self.config.collection_name)
                existing_size = collection_info.config.params.vectors.size
                
                if existing_size != self.config.vector_size:
                    self.logger.warning(
                        f"Vector dimension mismatch! Collection has {existing_size} dimensions, "
                        f"but model '{self.config.embedding_model}' produces {self.config.vector_size} dimensions."
                    )
                    
                    # Option 1: Delete and recreate (data loss!)
                    if os.getenv("RECREATE_COLLECTION_ON_MISMATCH", "false").lower() == "true":
                        self.logger.warning(f"Deleting and recreating collection {self.config.collection_name}")
                        self.client.delete_collection(self.config.collection_name)
                        self.client.create_collection(
                            collection_name=self.config.collection_name,
                            vectors_config=VectorParams(
                                size=self.config.vector_size,
                                distance=Distance.COSINE
                            )
                        )
                    else:
                        # Option 2: Use a different collection name
                        new_collection_name = f"{self.config.collection_name}_{self.config.vector_size}d"
                        self.logger.warning(f"Using alternative collection name: {new_collection_name}")
                        self.config.collection_name = new_collection_name
                        
                        # Recursively ensure the new collection exists
                        self._ensure_collection()
                        return
                
        except Exception as e:
            self.logger.error(f"Failed to ensure collection: {e}")
            raise
    
    def _create_indexes(self):
        """Create indexes for efficient filtering."""
        # Qdrant automatically indexes payload fields
        self.logger.info("Qdrant will automatically index payload fields for filtering")
    
    def store_attack_path(self, path: AttackPath, project_metadata: Dict[str, Any]) -> str:
        """
        Store an attack path with embeddings and metadata.
        
        Args:
            path: The attack path to store
            project_metadata: Project information (name, industry, tech_stack, etc.)
            
        Returns:
            The ID of the stored path
        """
        try:
            # Generate embeddings
            path_embedding = self._create_path_embedding(path)
            
            # Create comprehensive payload
            payload = {
                # Path information
                "path_id": path.path_id,
                "scenario_name": path.scenario_name,
                "entry_point": path.entry_point,
                "target_asset": path.target_asset,
                "total_steps": path.total_steps,
                
                # Risk metrics
                "impact": path.combined_impact.value,
                "likelihood": path.combined_likelihood.value,
                "feasibility": path.path_feasibility.value,
                "attacker_profile": path.attacker_profile.value,
                "time_to_compromise": path.time_to_compromise.value,
                "path_complexity": path.path_complexity,
                
                # Detailed steps
                "steps": [self._serialize_step(step) for step in path.path_steps],
                "step_count": len(path.path_steps),
                
                # Threat categories
                "stride_categories": list(set(s.stride_category for s in path.path_steps)),
                "mitre_techniques": [s.technique_id for s in path.path_steps if s.technique_id],
                
                # Defensive information
                "key_chokepoints": path.key_chokepoints,
                "detection_opportunities": path.detection_opportunities,
                "required_resources": path.required_resources,
                
                # Project context
                "project": project_metadata,
                
                # Metadata
                "timestamp": datetime.now().isoformat(),
                "narrative": path_embedding.narrative,
                
                # Components involved
                "components": list(set(s.component for s in path.path_steps)),
                
                # Search optimization fields
                "search_text": self._create_search_text(path),
                "hash": hashlib.md5(f"{path.path_id}{project_metadata.get('name', '')}".encode()).hexdigest()
            }
            
            # Create point
            point_id = self._generate_point_id(path.path_id, project_metadata.get('name', 'default'))
            point = PointStruct(
                id=point_id,
                vector=path_embedding.embedding,
                payload=payload
            )
            
            # Store in Qdrant
            self.client.upsert(
                collection_name=self.config.collection_name,
                points=[point]
            )
            
            # Store step embeddings separately for granular search
            self._store_step_embeddings(path, path_embedding, project_metadata)
            
            self.logger.info(f"Stored attack path: {path.path_id} for project {project_metadata.get('name')}")
            return str(point_id)
            
        except Exception as e:
            self.logger.error(f"Failed to store attack path: {e}")
            raise
    
    def search_similar_paths(self, query: SearchQuery) -> List[Tuple[AttackPath, float, Dict[str, Any]]]:
        """
        Search for similar attack paths based on various criteria.
        
        Returns:
            List of tuples (attack_path, similarity_score, metadata)
        """
        try:
            # Generate query embedding based on query type
            query_vector = self._create_query_embedding(query)
            
            # Build filter conditions
            filter_conditions = self._build_filter_conditions(query)
            
            # Perform search
            search_result = self.client.search(
                collection_name=self.config.collection_name,
                query_vector=query_vector,
                query_filter=filter_conditions,
                limit=query.limit,
                score_threshold=query.min_similarity
            )
            
            # Convert results to AttackPath objects
            results = []
            for scored_point in search_result:
                if scored_point.score >= query.min_similarity:
                    attack_path = self._reconstruct_attack_path(scored_point.payload)
                    metadata = {
                        "project": scored_point.payload.get("project", {}),
                        "timestamp": scored_point.payload.get("timestamp"),
                        "matched_components": self._find_matched_components(query, scored_point.payload)
                    }
                    results.append((attack_path, scored_point.score, metadata))
            
            return results
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []
    
    def find_defense_recommendations(self, path: AttackPath, limit: int = 5) -> List[DefenseRecommendation]:
        """
        Find defensive control recommendations based on similar paths that were successfully defended.
        """
        try:
            # Search for similar paths
            query = SearchQuery(
                query_type="path",
                query=path,
                limit=50,  # Get more results to analyze
                min_similarity=0.6
            )
            similar_paths = self.search_similar_paths(query)
            
            # Analyze defenses from similar paths
            defense_effectiveness = defaultdict(lambda: {"count": 0, "projects": set(), "evidence": []})
            
            for similar_path, similarity, metadata in similar_paths:
                # Weight by similarity
                weight = similarity
                
                # Analyze chokepoints
                for chokepoint in similar_path.key_chokepoints:
                    defense_effectiveness[chokepoint]["count"] += weight
                    defense_effectiveness[chokepoint]["projects"].add(metadata["project"].get("name", "Unknown"))
                    defense_effectiveness[chokepoint]["evidence"].append(
                        f"Blocked {similar_path.scenario_name} (similarity: {similarity:.2f})"
                    )
            
            # Create recommendations
            recommendations = []
            for defense, stats in sorted(defense_effectiveness.items(), key=lambda x: x[1]["count"], reverse=True)[:limit]:
                rec = DefenseRecommendation(
                    control_name=defense,
                    effectiveness_score=stats["count"],
                    similar_paths_blocked=len(stats["evidence"]),
                    implementation_complexity=self._estimate_complexity(defense),
                    evidence=stats["evidence"][:3]  # Top 3 examples
                )
                recommendations.append(rec)
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to find defense recommendations: {e}")
            return []
    
    def identify_attack_patterns(self, min_frequency: int = 3) -> List[AttackPattern]:
        """
        Identify recurring attack patterns across all stored paths.
        """
        try:
            # Retrieve all paths (with pagination for large datasets)
            all_paths = self._retrieve_all_paths()
            
            # Analyze patterns
            pattern_candidates = defaultdict(lambda: {
                "paths": [],
                "projects": set(),
                "steps": [],
                "impacts": [],
                "attackers": [],
                "defenses": set()
            })
            
            # Group by similar step sequences
            for path_data in all_paths:
                # Create step sequence signature
                step_sequence = self._create_step_sequence_signature(path_data["steps"])
                
                pattern_candidates[step_sequence]["paths"].append(path_data["path_id"])
                pattern_candidates[step_sequence]["projects"].add(path_data["project"].get("name", "Unknown"))
                pattern_candidates[step_sequence]["steps"] = [s["threat_description"] for s in path_data["steps"]]
                pattern_candidates[step_sequence]["impacts"].append(path_data["impact"])
                pattern_candidates[step_sequence]["attackers"].append(path_data["attacker_profile"])
                pattern_candidates[step_sequence]["defenses"].update(path_data["key_chokepoints"])
            
            # Create AttackPattern objects for frequent patterns
            patterns = []
            for pattern_sig, data in pattern_candidates.items():
                if len(data["paths"]) >= min_frequency:
                    # Determine most common characteristics
                    most_common_impact = max(set(data["impacts"]), key=data["impacts"].count)
                    most_common_attacker = max(set(data["attackers"]), key=data["attackers"].count)
                    
                    pattern = AttackPattern(
                        pattern_id=f"PAT_{hashlib.md5(pattern_sig.encode()).hexdigest()[:8]}",
                        pattern_name=self._generate_pattern_name(data["steps"]),
                        description=f"Attack pattern observed in {len(data['paths'])} instances across {len(data['projects'])} projects",
                        common_steps=data["steps"][:5],  # First 5 steps
                        frequency=len(data["paths"]),
                        affected_projects=list(data["projects"])[:10],  # Top 10 projects
                        typical_impact=most_common_impact,
                        typical_attacker=most_common_attacker,
                        common_defenses=list(data["defenses"])[:5]
                    )
                    patterns.append(pattern)
            
            # Sort by frequency
            patterns.sort(key=lambda p: p.frequency, reverse=True)
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Failed to identify attack patterns: {e}")
            return []
    
    def get_project_statistics(self, project_name: str) -> Dict[str, Any]:
        """
        Get attack path statistics for a specific project.
        """
        try:
            # Query paths for this project
            project_filter = Filter(
                must=[
                    FieldCondition(
                        key="project.name",
                        match=MatchValue(value=project_name)
                    )
                ]
            )
            
            results = self.client.search(
                collection_name=self.config.collection_name,
                query_vector=np.zeros(self.config.vector_size).tolist(),  # Dummy vector
                query_filter=project_filter,
                limit=1000,  # Get all paths for project
                score_threshold=0  # Get all results
            )
            
            # Analyze results
            stats = {
                "project_name": project_name,
                "total_paths": len(results),
                "impact_distribution": defaultdict(int),
                "attacker_distribution": defaultdict(int),
                "common_entry_points": defaultdict(int),
                "common_targets": defaultdict(int),
                "average_path_length": 0,
                "common_techniques": defaultdict(int),
                "recommended_controls": [],
                "risk_score": 0
            }
            
            total_length = 0
            all_chokepoints = defaultdict(int)
            
            for point in results:
                payload = point.payload
                
                # Count distributions
                stats["impact_distribution"][payload["impact"]] += 1
                stats["attacker_distribution"][payload["attacker_profile"]] += 1
                stats["common_entry_points"][payload["entry_point"]] += 1
                stats["common_targets"][payload["target_asset"]] += 1
                
                # Path length
                total_length += payload["step_count"]
                
                # MITRE techniques
                for technique in payload.get("mitre_techniques", []):
                    if technique:
                        stats["common_techniques"][technique] += 1
                
                # Chokepoints
                for chokepoint in payload.get("key_chokepoints", []):
                    all_chokepoints[chokepoint] += 1
            
            # Calculate averages and top items
            if results:
                stats["average_path_length"] = total_length / len(results)
                
                # Top 5 recommended controls
                stats["recommended_controls"] = [
                    {"control": control, "paths_blocked": count}
                    for control, count in sorted(all_chokepoints.items(), key=lambda x: x[1], reverse=True)[:5]
                ]
                
                # Calculate risk score (0-100)
                stats["risk_score"] = self._calculate_project_risk_score(stats)
            
            # Convert defaultdicts to regular dicts
            for key in ["impact_distribution", "attacker_distribution", "common_entry_points", 
                       "common_targets", "common_techniques"]:
                stats[key] = dict(stats[key])
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get project statistics: {e}")
            return {}
    
    def compare_projects(self, project_names: List[str]) -> Dict[str, Any]:
        """
        Compare attack paths across multiple projects.
        """
        comparison = {
            "projects": project_names,
            "comparison_date": datetime.now().isoformat(),
            "summary": {},
            "common_patterns": [],
            "unique_threats": {},
            "risk_comparison": {}
        }
        
        # Get statistics for each project
        project_stats = {}
        for project in project_names:
            project_stats[project] = self.get_project_statistics(project)
            comparison["risk_comparison"][project] = project_stats[project].get("risk_score", 0)
        
        # Find common patterns
        all_patterns = self.identify_attack_patterns(min_frequency=2)
        for pattern in all_patterns:
            involved_projects = [p for p in project_names if p in pattern.affected_projects]
            if len(involved_projects) >= 2:
                comparison["common_patterns"].append({
                    "pattern_name": pattern.pattern_name,
                    "projects": involved_projects,
                    "frequency": pattern.frequency,
                    "description": pattern.description
                })
        
        # Identify unique threats per project
        for project in project_names:
            stats = project_stats[project]
            unique_entry_points = set(stats.get("common_entry_points", {}).keys())
            
            # Compare with other projects
            for other_project in project_names:
                if other_project != project:
                    other_stats = project_stats[other_project]
                    other_entry_points = set(other_stats.get("common_entry_points", {}).keys())
                    unique_entry_points -= other_entry_points
            
            comparison["unique_threats"][project] = list(unique_entry_points)
        
        return comparison
    
    # Helper methods
    def _create_path_embedding(self, path: AttackPath) -> PathEmbedding:
        """Create embeddings for an attack path."""
        # Create narrative description
        narrative = self._create_path_narrative(path)
        
        # Embed the narrative
        path_embedding = self.embedding_model.encode(narrative).tolist()
        
        # Embed individual steps
        step_embeddings = {}
        for step in path.path_steps:
            step_text = f"{step.component}: {step.threat_description} ({step.stride_category})"
            step_embeddings[step.step_number] = self.embedding_model.encode(step_text).tolist()
        
        return PathEmbedding(
            path_id=path.path_id,
            embedding=path_embedding,
            narrative=narrative,
            step_embeddings=step_embeddings,
            metadata={"total_steps": len(path.path_steps)}
        )
    
    def _create_path_narrative(self, path: AttackPath) -> str:
        """Create a narrative description of the attack path."""
        narrative_parts = [
            f"Attack scenario: {path.scenario_name}",
            f"Entry point: {path.entry_point}",
            f"Target: {path.target_asset}",
            f"Attacker profile: {path.attacker_profile.value}",
            f"Impact: {path.combined_impact.value}",
            "Attack steps:"
        ]
        
        for step in path.path_steps:
            narrative_parts.append(
                f"Step {step.step_number} at {step.component}: {step.threat_description} "
                f"(STRIDE: {step.stride_category})"
            )
        
        narrative_parts.extend([
            f"Key defenses: {', '.join(path.key_chokepoints) if path.key_chokepoints else 'None identified'}",
            f"Time to compromise: {path.time_to_compromise.value}",
            f"Complexity: {path.path_complexity}"
        ])
        
        return " ".join(narrative_parts)
    
    def _create_search_text(self, path: AttackPath) -> str:
        """Create searchable text for keyword-based queries."""
        search_parts = [
            path.scenario_name,
            path.entry_point,
            path.target_asset,
            path.attacker_profile.value,
            path.combined_impact.value,
            path.path_feasibility.value
        ]
        
        # Add all threat descriptions
        for step in path.path_steps:
            search_parts.append(step.threat_description)
            if step.technique_id:
                search_parts.append(step.technique_id)
        
        # Add defensive information
        search_parts.extend(path.key_chokepoints)
        search_parts.extend(path.detection_opportunities)
        
        return " ".join(search_parts).lower()
    
    def _serialize_step(self, step: AttackStep) -> Dict[str, Any]:
        """Serialize an attack step for storage."""
        return {
            "step_number": step.step_number,
            "component": step.component,
            "threat_id": step.threat_id,
            "threat_description": step.threat_description,
            "stride_category": step.stride_category,
            "technique_id": step.technique_id,
            "prerequisites": step.prerequisites,
            "enables": step.enables,
            "required_access": step.required_access,
            "detection_difficulty": step.detection_difficulty
        }
    
    def _generate_point_id(self, path_id: str, project_name: str) -> int:
        """Generate a unique point ID for Qdrant."""
        # Create a hash of path_id and project_name
        hash_str = f"{path_id}_{project_name}"
        hash_bytes = hashlib.md5(hash_str.encode()).digest()
        # Convert first 8 bytes to integer
        return int.from_bytes(hash_bytes[:8], byteorder='big') % (2**63)  # Ensure it fits in int64
    
    def _store_step_embeddings(self, path: AttackPath, path_embedding: PathEmbedding, 
                              project_metadata: Dict[str, Any]):
        """Store individual step embeddings for granular search."""
        # This could be implemented if you want to search for specific attack steps
        # For now, we'll include step information in the main path payload
        pass
    
    def _create_query_embedding(self, query: SearchQuery) -> List[float]:
        """Create embedding vector from search query."""
        if query.query_type == "text":
            # Direct text query
            return self.embedding_model.encode(query.query).tolist()
        
        elif query.query_type == "path":
            # Query is an AttackPath object
            narrative = self._create_path_narrative(query.query)
            return self.embedding_model.encode(narrative).tolist()
        
        elif query.query_type == "technique":
            # Query for specific MITRE technique
            query_text = f"Attack using MITRE technique {query.query}"
            return self.embedding_model.encode(query_text).tolist()
        
        elif query.query_type == "component":
            # Query for attacks on specific component
            query_text = f"Attack targeting {query.query} component"
            return self.embedding_model.encode(query_text).tolist()
        
        elif query.query_type == "impact":
            # Query by impact level
            query_text = f"Attack with {query.query} impact on system"
            return self.embedding_model.encode(query_text).tolist()
        
        else:
            # Default: treat as text
            return self.embedding_model.encode(str(query.query)).tolist()
    
    def _build_filter_conditions(self, query: SearchQuery) -> Optional[Filter]:
        """Build Qdrant filter conditions from search query."""
        conditions = []
        
        if query.filters:
            # Project filter
            if "project" in query.filters:
                conditions.append(
                    FieldCondition(
                        key="project.name",
                        match=MatchValue(value=query.filters["project"])
                    )
                )
            
            # Impact filter
            if "impact" in query.filters:
                conditions.append(
                    FieldCondition(
                        key="impact",
                        match=MatchValue(value=query.filters["impact"])
                    )
                )
            
            # Attacker profile filter
            if "attacker_profile" in query.filters:
                conditions.append(
                    FieldCondition(
                        key="attacker_profile",
                        match=MatchValue(value=query.filters["attacker_profile"])
                    )
                )
            
            # Time range filter
            if "date_from" in query.filters:
                conditions.append(
                    FieldCondition(
                        key="timestamp",
                        range=Range(
                            gte=query.filters["date_from"],
                            lte=query.filters.get("date_to", datetime.now().isoformat())
                        )
                    )
                )
            
            # Component filter
            if "component" in query.filters:
                conditions.append(
                    FieldCondition(
                        key="components",
                        match=MatchValue(value=query.filters["component"])
                    )
                )
            
            # MITRE technique filter
            if "mitre_technique" in query.filters:
                conditions.append(
                    FieldCondition(
                        key="mitre_techniques",
                        match=MatchValue(value=query.filters["mitre_technique"])
                    )
                )
        
        # Cross-project search filter
        if not query.include_cross_project and "current_project" in query.filters:
            conditions.append(
                FieldCondition(
                    key="project.name",
                    match=MatchValue(value=query.filters["current_project"])
                )
            )
        
        if conditions:
            return Filter(must=conditions)
        return None
    
    def _reconstruct_attack_path(self, payload: Dict[str, Any]) -> AttackPath:
        """Reconstruct AttackPath object from stored payload."""
        # Reconstruct steps
        steps = []
        for step_data in payload["steps"]:
            step = AttackStep(
                step_number=step_data["step_number"],
                component=step_data["component"],
                threat_id=step_data["threat_id"],
                threat_description=step_data["threat_description"],
                stride_category=step_data["stride_category"],
                technique_id=step_data.get("technique_id"),
                prerequisites=step_data.get("prerequisites", []),
                enables=step_data.get("enables", []),
                required_access=step_data.get("required_access"),
                detection_difficulty=step_data.get("detection_difficulty")
            )
            steps.append(step)
        
        # Reconstruct path
        path = AttackPath(
            path_id=payload["path_id"],
            scenario_name=payload["scenario_name"],
            entry_point=payload["entry_point"],
            target_asset=payload["target_asset"],
            path_steps=steps,
            total_steps=payload["total_steps"],
            combined_likelihood=ThreatLikelihood(payload["likelihood"]),
            combined_impact=ThreatImpact(payload["impact"]),
            path_feasibility=PathFeasibility(payload["feasibility"]),
            attacker_profile=AttackerProfile(payload["attacker_profile"]),
            time_to_compromise=payload["time_to_compromise"],
            key_chokepoints=payload.get("key_chokepoints", []),
            detection_opportunities=payload.get("detection_opportunities", []),
            required_resources=payload.get("required_resources", []),
            path_complexity=payload.get("path_complexity", "Medium")
        )
        
        return path
    
    def _find_matched_components(self, query: SearchQuery, payload: Dict[str, Any]) -> List[str]:
        """Find which components matched the search query."""
        matched = []
        
        if query.query_type == "component" and isinstance(query.query, str):
            if query.query in payload.get("components", []):
                matched.append(query.query)
        
        # Could be extended to find other matches
        return matched
    
    def _estimate_complexity(self, defense: str) -> str:
        """Estimate implementation complexity of a defense."""
        # Simple heuristic - could be enhanced with a knowledge base
        defense_lower = defense.lower()
        
        if any(word in defense_lower for word in ["mfa", "2fa", "multi-factor"]):
            return "Low"
        elif any(word in defense_lower for word in ["encryption", "certificate", "pki"]):
            return "Medium"
        elif any(word in defense_lower for word in ["zero trust", "microsegmentation", "siem"]):
            return "High"
        else:
            return "Medium"
    
    def _retrieve_all_paths(self, batch_size: int = 100) -> List[Dict[str, Any]]:
        """Retrieve all paths from the collection."""
        all_paths = []
        offset = 0
        
        while True:
            # Use scroll API for efficient retrieval
            results = self.client.scroll(
                collection_name=self.config.collection_name,
                limit=batch_size,
                offset=offset
            )
            
            if not results:
                break
                
            all_paths.extend([point.payload for point in results[0]])
            offset += batch_size
            
            if len(results[0]) < batch_size:
                break
        
        return all_paths
    
    def _create_step_sequence_signature(self, steps: List[Dict[str, Any]]) -> str:
        """Create a signature for a sequence of attack steps."""
        # Create a normalized representation of the step sequence
        stride_sequence = "-".join([step["stride_category"] for step in steps])
        
        # Include key components
        key_components = []
        for step in steps:
            component = step["component"]
            if component not in key_components:
                key_components.append(component)
        
        component_sequence = "-".join(key_components[:3])  # First 3 unique components
        
        return f"{stride_sequence}_{component_sequence}"
    
    def _generate_pattern_name(self, steps: List[str]) -> str:
        """Generate a descriptive name for an attack pattern."""
        # Extract key terms from steps
        key_terms = []
        
        common_terms = ["attack", "threat", "vulnerability", "exploit", "access", "breach"]
        
        for step in steps[:3]:  # Look at first 3 steps
            words = step.lower().split()
            for word in words:
                if len(word) > 4 and word not in common_terms and word not in key_terms:
                    key_terms.append(word.capitalize())
                    if len(key_terms) >= 3:
                        break
        
        if key_terms:
            return f"{' '.join(key_terms[:2])} Attack Pattern"
        else:
            return f"Multi-Step Attack Pattern"
    
    def _calculate_project_risk_score(self, stats: Dict[str, Any]) -> float:
        """Calculate a risk score for a project based on its attack paths."""
        score = 0.0
        
        # Impact distribution (max 40 points)
        impact_weights = {"Critical": 10, "High": 7, "Medium": 4, "Low": 1}
        total_paths = stats["total_paths"]
        
        if total_paths > 0:
            for impact, count in stats["impact_distribution"].items():
                score += (count / total_paths) * impact_weights.get(impact, 0) * 4
        
        # Attacker sophistication (max 20 points)
        attacker_weights = {"APT": 10, "Cybercriminal": 7, "Insider": 8, "Script Kiddie": 2}
        if total_paths > 0:
            for attacker, count in stats["attacker_distribution"].items():
                score += (count / total_paths) * attacker_weights.get(attacker, 0) * 2
        
        # Path complexity (max 20 points)
        avg_length = stats["average_path_length"]
        if avg_length > 0:
            # Longer paths might indicate more complex attacks
            score += min(avg_length * 4, 20)
        
        # Defensive coverage (max 20 points)
        # More recommended controls = better defense options = lower risk
        control_count = len(stats["recommended_controls"])
        if control_count > 0:
            score += max(20 - (control_count * 4), 0)
        else:
            score += 20  # No controls = high risk
        
        # Normalize to 0-100
        return min(max(score, 0), 100)


# Integration with Attack Path Analyzer
class VectorStoreIntegration:
    """Integration helper for attack path analyzer."""
    
    def __init__(self, vector_store: AttackPathVectorStore):
        self.vector_store = vector_store
        self.logger = logging.getLogger(f"{__name__}.VectorStoreIntegration")
    
    def process_analysis_results(self, analysis_results: Dict[str, Any], 
                               project_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process attack path analysis results and store in vector database.
        
        Args:
            analysis_results: Output from attack path analyzer
            project_metadata: Project information
            
        Returns:
            Summary of stored paths and insights
        """
        stored_paths = []
        insights = {
            "similar_attacks_found": [],
            "recommended_defenses": [],
            "cross_project_patterns": []
        }
        
        # Store each attack path
        for path_data in analysis_results.get("attack_paths", []):
            try:
                # Convert dict to AttackPath object if needed
                if isinstance(path_data, dict):
                    path = self._dict_to_attack_path(path_data)
                else:
                    path = path_data
                
                # Store in vector database
                path_id = self.vector_store.store_attack_path(path, project_metadata)
                stored_paths.append(path_id)
                
                # Find similar attacks from other projects
                similar_query = SearchQuery(
                    query_type="path",
                    query=path,
                    filters={"exclude_project": project_metadata.get("name")},
                    limit=5,
                    min_similarity=0.7
                )
                similar_paths = self.vector_store.search_similar_paths(similar_query)
                
                if similar_paths:
                    insights["similar_attacks_found"].append({
                        "current_path": path.scenario_name,
                        "similar_paths": [
                            {
                                "scenario": sim_path[0].scenario_name,
                                "project": sim_path[2]["project"]["name"],
                                "similarity": sim_path[1]
                            }
                            for sim_path in similar_paths[:3]
                        ]
                    })
                
                # Get defense recommendations
                defenses = self.vector_store.find_defense_recommendations(path, limit=3)
                if defenses:
                    insights["recommended_defenses"].extend([
                        {
                            "path": path.scenario_name,
                            "control": d.control_name,
                            "effectiveness": d.effectiveness_score
                        }
                        for d in defenses
                    ])
                
            except Exception as e:
                self.logger.error(f"Failed to process path {path_data.get('path_id', 'unknown')}: {e}")
        
        # Identify cross-project patterns
        patterns = self.vector_store.identify_attack_patterns(min_frequency=2)
        insights["cross_project_patterns"] = [
            {
                "pattern": p.pattern_name,
                "frequency": p.frequency,
                "projects": p.affected_projects[:5]
            }
            for p in patterns[:5]
        ]
        
        return {
            "stored_paths": len(stored_paths),
            "path_ids": stored_paths,
            "insights": insights,
            "project_stats": self.vector_store.get_project_statistics(project_metadata.get("name", "Unknown"))
        }
    
    def _dict_to_attack_path(self, path_dict: Dict[str, Any]) -> AttackPath:
        """Convert dictionary to AttackPath object."""
        # Implementation depends on exact structure of your dict
        # This is a placeholder that should match your actual data structure
        steps = []
        for step_dict in path_dict.get("path_steps", []):
            step = AttackStep(**step_dict)
            steps.append(step)
        
        return AttackPath(
            path_id=path_dict["path_id"],
            scenario_name=path_dict["scenario_name"],
            entry_point=path_dict["entry_point"],
            target_asset=path_dict["target_asset"],
            path_steps=steps,
            total_steps=path_dict["total_steps"],
            combined_likelihood=ThreatLikelihood(path_dict["combined_likelihood"]),
            combined_impact=ThreatImpact(path_dict["combined_impact"]),
            path_feasibility=PathFeasibility(path_dict["path_feasibility"]),
            attacker_profile=AttackerProfile(path_dict["attacker_profile"]),
            time_to_compromise=path_dict["time_to_compromise"],
            key_chokepoints=path_dict.get("key_chokepoints", []),
            detection_opportunities=path_dict.get("detection_opportunities", []),
            required_resources=path_dict.get("required_resources", []),
            path_complexity=path_dict.get("path_complexity", "Medium")
        )


def main():
    """Example usage and testing."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize vector store
        config = VectorStoreConfig()
        vector_store = AttackPathVectorStore(config)
        
        logger.info("Vector store initialized successfully")
        
        # Example: Create and store a sample attack path
        sample_path = AttackPath(
            path_id="AP_test001",
            scenario_name="SQL Injection to Data Exfiltration",
            entry_point="Web Application",
            target_asset="Customer Database",
            path_steps=[
                AttackStep(
                    step_number=1,
                    component="Web Application",
                    threat_id="T001",
                    threat_description="SQL injection through login form",
                    stride_category="T",
                    technique_id="T1190",
                    prerequisites=[],
                    enables=["T002"],
                    required_access="External/Unauthenticated",
                    detection_difficulty="Medium"
                ),
                AttackStep(
                    step_number=2,
                    component="Database Server",
                    threat_id="T002",
                    threat_description="Database query manipulation",
                    stride_category="I",
                    technique_id="T1005",
                    prerequisites=["T001"],
                    enables=["T003"],
                    required_access="Database Access",
                    detection_difficulty="Hard"
                )
            ],
            total_steps=2,
            combined_likelihood=ThreatLikelihood.HIGH,
            combined_impact=ThreatImpact.CRITICAL,
            path_feasibility=PathFeasibility.REALISTIC,
            attacker_profile=AttackerProfile.CYBERCRIMINAL,
            time_to_compromise=TimeToCompromise.HOURS,
            key_chokepoints=["Input validation", "WAF", "Database activity monitoring"],
            detection_opportunities=["Anomalous SQL queries", "Large data transfers"],
            required_resources=["SQL injection tools", "Basic web knowledge"],
            path_complexity="Low"
        )
        
        # Store the path
        project_meta = {
            "name": "E-Commerce Platform",
            "industry": "Retail",
            "tech_stack": ["PHP", "MySQL", "Apache"],
            "compliance": ["PCI-DSS"]
        }
        
        path_id = vector_store.store_attack_path(sample_path, project_meta)
        logger.info(f"Stored sample path with ID: {path_id}")
        
        # Search for similar paths
        search_query = SearchQuery(
            query_type="text",
            query="SQL injection attack on database",
            limit=5
        )
        
        results = vector_store.search_similar_paths(search_query)
        logger.info(f"Found {len(results)} similar paths")
        
        # Get project statistics
        stats = vector_store.get_project_statistics("E-Commerce Platform")
        logger.info(f"Project statistics: {json.dumps(stats, indent=2)}")
        
        print("\n✅ Vector store test completed successfully!")
        
    except Exception as e:
        logger.error(f"Vector store test failed: {e}", exc_info=True)
        print(f"\n❌ Test failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())