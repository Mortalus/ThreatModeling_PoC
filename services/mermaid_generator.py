"""
Service for generating Mermaid diagrams from DFD data.
"""
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class MermaidGenerator:
    """Generate Mermaid diagrams for threat modeling visualization."""
    
    @staticmethod
    def generate_threat_modeling_diagram(dfd_data: Dict[str, Any]) -> str:
        """Generate a threat modeling focused Mermaid diagram."""
        logger.info("🎨 Generating threat modeling Mermaid diagram...")
        
        if not dfd_data or 'dfd' not in dfd_data:
            logger.warning("No DFD data available for Mermaid generation")
            return ""
        
        dfd = dfd_data['dfd']
        lines = ['graph TB']
        
        # Group components by trust zones
        zones = MermaidGenerator._categorize_components(dfd)
        all_components = MermaidGenerator._create_component_mapping(dfd, zones)
        
        # Generate trust zone subgraphs
        lines.extend(MermaidGenerator._generate_zone_subgraphs(zones))
        
        # Add data flows
        lines.extend(MermaidGenerator._generate_data_flows(dfd, all_components))
        
        # Add styling
        lines.extend(MermaidGenerator._generate_styling(zones))
        
        # Add legend
        lines.extend(MermaidGenerator._generate_legend())
        
        result = '\n'.join(lines)
        logger.info(f"✅ Generated Mermaid diagram with {len(lines)} lines")
        return result
    
    @staticmethod
    def safe_id(text: str) -> str:
        """Create safe Mermaid node ID."""
        if not text:
            return 'unknown'
        # Replace non-alphanumeric with underscore, limit length
        safe = re.sub(r'[^a-zA-Z0-9]', '_', str(text))
        safe = re.sub(r'_+', '_', safe).strip('_')
        if safe and safe[0].isdigit():
            safe = 'node_' + safe
        return safe[:20] or 'unknown'
    
    @staticmethod
    def _get_trust_zone(name: str, comp_type: str) -> str:
        """Determine trust zone for component."""
        name_lower = name.lower()
        
        if comp_type == 'external' or any(keyword in name_lower for keyword in 
            ['user', 'client', 'external', 'internet', 'public']):
            return 'external'
        elif any(keyword in name_lower for keyword in 
            ['gateway', 'proxy', 'load balancer', 'firewall', 'waf']):
            return 'dmz'
        elif any(keyword in name_lower for keyword in 
            ['database', 'db', 'storage', 'cache', 'repository']):
            return 'data'
        else:
            return 'application'
    
    @staticmethod
    def _categorize_components(dfd: Dict) -> Dict[str, List[Dict]]:
        """Categorize components into trust zones."""
        zones = {'external': [], 'dmz': [], 'application': [], 'data': []}
        
        # Process components
        for entity in dfd.get('external_entities', []):
            zone = MermaidGenerator._get_trust_zone(entity, 'external')
            comp_id = MermaidGenerator.safe_id(entity)
            zones[zone].append({'id': comp_id, 'name': entity, 'type': 'entity'})
        
        for process in dfd.get('processes', []):
            zone = MermaidGenerator._get_trust_zone(process, 'process')
            comp_id = MermaidGenerator.safe_id(process)
            zones[zone].append({'id': comp_id, 'name': process, 'type': 'process'})
        
        for asset in dfd.get('assets', []):
            zone = MermaidGenerator._get_trust_zone(asset, 'asset')
            comp_id = MermaidGenerator.safe_id(asset)
            zones[zone].append({'id': comp_id, 'name': asset, 'type': 'asset'})
        
        return zones
    
    @staticmethod
    def _create_component_mapping(dfd: Dict, zones: Dict) -> Dict[str, str]:
        """Create mapping from component names to IDs."""
        all_components = {}
        
        for entity in dfd.get('external_entities', []):
            all_components[entity] = MermaidGenerator.safe_id(entity)
        
        for process in dfd.get('processes', []):
            all_components[process] = MermaidGenerator.safe_id(process)
        
        for asset in dfd.get('assets', []):
            all_components[asset] = MermaidGenerator.safe_id(asset)
        
        return all_components
    
    @staticmethod
    def _generate_zone_subgraphs(zones: Dict) -> List[str]:
        """Generate subgraph definitions for trust zones."""
        lines = []
        zone_titles = {
            'external': '🌐 External Zone (Untrusted)',
            'dmz': '🛡️ DMZ Zone (Semi-Trusted)', 
            'application': '🏢 Application Zone (Trusted)',
            'data': '💾 Data Zone (Critical Assets)'
        }
        
        for zone, components in zones.items():
            if components:
                lines.append(f'    subgraph {zone}["{zone_titles[zone]}"]')
                for comp in components:
                    icon = '👤' if comp['type'] == 'entity' else '💾' if comp['type'] == 'asset' else '⚙️'
                    lines.append(f'        {comp["id"]}["{icon} {comp["name"]}"]')
                lines.append('    end')
                lines.append('')
        
        return lines
    
    @staticmethod
    def _generate_data_flows(dfd: Dict, all_components: Dict) -> List[str]:
        """Generate data flow connections."""
        lines = ['    %% Data Flows with Security Context']
        
        for flow in dfd.get('data_flows', []):
            source_id = all_components.get(flow.get('source'))
            dest_id = all_components.get(flow.get('destination'))
            
            if not source_id or not dest_id:
                continue
            
            # Determine arrow style based on risk
            data_class = flow.get('data_classification', 'Internal')
            if data_class in ['PII', 'PHI', 'PCI']:
                arrow = '==>'  # High risk
            elif data_class == 'Confidential':
                arrow = '-->'  # Medium risk
            else:
                arrow = '-.->'  # Low risk
            
            # Create label
            protocol = flow.get('protocol', 'Unknown')
            auth = flow.get('authentication_mechanism', 'None')
            encrypted = '🔒' if flow.get('encryption_in_transit') else '🔓'
            
            label = f"{protocol}|{data_class}|{auth[:10]}|{encrypted}"
            lines.append(f'    {source_id} {arrow}|"{label}"| {dest_id}')
        
        return lines
    
    @staticmethod
    def _generate_styling(zones: Dict) -> List[str]:
        """Generate styling for the diagram."""
        lines = [
            '',
            '    %% Trust Zone Styling',
            '    classDef external fill:#ff4757,stroke:#ff3742,stroke-width:3px,color:#fff',
            '    classDef dmz fill:#ffa502,stroke:#ff8c00,stroke-width:2px,color:#000',
            '    classDef application fill:#3742fa,stroke:#2f40fa,stroke-width:2px,color:#fff',
            '    classDef data fill:#2ed573,stroke:#20bf6b,stroke-width:2px,color:#000',
            ''
        ]
        
        # Apply zone classes
        for zone, components in zones.items():
            if components:
                comp_ids = [comp['id'] for comp in components]
                lines.append(f'    class {",".join(comp_ids)} {zone}')
        
        return lines
    
    @staticmethod
    def _generate_legend() -> List[str]:
        """Generate legend comments."""
        return [
            '',
            '    %% THREAT MODELING LEGEND:',
            '    %% 🌐 Red External: Untrusted attack surface',
            '    %% 🛡️ Orange DMZ: Semi-trusted exposed services', 
            '    %% 🏢 Blue Application: Trusted business logic',
            '    %% 💾 Green Data: Critical assets needing protection',
            '    %% === High-risk data flows (PII/PHI/PCI)',
            '    %% --- Medium-risk flows (Confidential)',
            '    %% -.- Low-risk flows (Internal/Public)'
        ]