"""
Simple graph implementation to replace NetworkX dependency.
"""
from collections import defaultdict, deque
from typing import List, Dict, Any, Optional, Tuple, Set

class SimpleGraph:
    """Lightweight graph implementation."""
    
    def __init__(self):
        self.nodes = {}
        self.edges = defaultdict(list)
        self.reverse_edges = defaultdict(list)
    
    def add_node(self, node: str, **attrs):
        """Add a node with attributes."""
        self.nodes[node] = attrs
    
    def add_edge(self, source: str, dest: str, **attrs):
        """Add an edge with attributes."""
        self.edges[source].append((dest, attrs))
        self.reverse_edges[dest].append((source, attrs))
    
    def has_node(self, node: str) -> bool:
        """Check if node exists."""
        return node in self.nodes
    
    def predecessors(self, node: str) -> List[str]:
        """Get predecessors of a node."""
        return [src for src, _ in self.reverse_edges[node]]
    
    def successors(self, node: str) -> List[str]:
        """Get successors of a node."""
        return [dest for dest, _ in self.edges[node]]
    
    def degree(self, node: str) -> int:
        """Get degree of a node."""
        return len(self.edges[node]) + len(self.reverse_edges[node])
    
    def number_of_nodes(self) -> int:
        """Get number of nodes."""
        return len(self.nodes)
    
    def number_of_edges(self) -> int:
        """Get number of edges."""
        return sum(len(edges) for edges in self.edges.values())
    
    def find_paths(self, start: str, end: str, max_length: int = 5) -> List[List[str]]:
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
    
    def shortest_path(self, start: str, end: str) -> Optional[List[str]]:
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