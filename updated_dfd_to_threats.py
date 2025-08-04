#!/usr/bin/env python3
"""
DFD to Threats Generator Script - Simplified Version
This version prioritizes working progress updates over advanced features.
"""

import os
import json
import sys
import time
from datetime import datetime

# Basic configuration
OUTPUT_DIR = os.getenv('OUTPUT_DIR', './output')
DFD_FILE = os.path.join(OUTPUT_DIR, 'dfd_components.json')
THREATS_FILE = os.path.join(OUTPUT_DIR, 'identified_threats.json')
PROGRESS_FILE = os.path.join(OUTPUT_DIR, 'step_3_progress.json')

def write_progress(current, total, message, details=""):
    """Write progress update to file"""
    try:
        progress_data = {
            'step': 3,
            'current': current,
            'total': total,
            'progress': round((current / total * 100) if total > 0 else 0, 1),
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'status': 'running'
        }
        
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress_data, f, indent=2)
            
        # Also print to stdout for debugging
        print(f"Progress: {progress_data['progress']:.1f}% - {message} - {details}")
        
    except Exception as e:
        print(f"Warning: Could not write progress: {e}")

def main():
    """Main execution"""
    print("=== DFD to Threats Analysis (Simplified) ===")
    
    try:
        # Initial progress
        write_progress(1, 100, "Starting", "Initializing threat analysis")
        time.sleep(0.5)  # Small delay to ensure progress is written
        
        # Load DFD data
        write_progress(5, 100, "Loading DFD", "Reading components file")
        
        if not os.path.exists(DFD_FILE):
            raise FileNotFoundError(f"DFD file not found at {DFD_FILE}")
        
        with open(DFD_FILE, 'r') as f:
            dfd_data = json.load(f)
        
        # Handle nested structure
        if 'dfd' in dfd_data:
            dfd_data = dfd_data['dfd']
        
        write_progress(10, 100, "DFD loaded", f"Project: {dfd_data.get('project_name', 'Unknown')}")
        
        # Extract components
        write_progress(15, 100, "Extracting components", "Processing DFD structure")
        
        components = []
        
        # Extract all component types
        for entity in dfd_data.get('external_entities', []):
            components.append({
                'name': entity,
                'type': 'External Entity'
            })
        
        for process in dfd_data.get('processes', []):
            components.append({
                'name': process,
                'type': 'Process'
            })
        
        for store in dfd_data.get('assets', []) + dfd_data.get('data_stores', []):
            components.append({
                'name': store,
                'type': 'Data Store'
            })
        
        for flow in dfd_data.get('data_flows', []):
            if isinstance(flow, dict):
                name = f"{flow.get('source', 'Unknown')} → {flow.get('destination', 'Unknown')}"
                components.append({
                    'name': name,
                    'type': 'Data Flow',
                    'details': flow
                })
        
        write_progress(20, 100, "Components extracted", f"Found {len(components)} components")
        print(f"Total components: {len(components)}")
        
        # Generate threats
        threats = []
        total = len(components)
        
        for i, comp in enumerate(components):
            # Update progress for each component
            progress = 20 + int((i / total) * 70) if total > 0 else 20
            write_progress(progress, 100, f"Analyzing ({i+1}/{total})", comp['name'][:40])
            
            # Generate threats based on component type
            comp_threats = generate_threats_for_component(comp)
            threats.extend(comp_threats)
            
            # Small delay to simulate processing
            time.sleep(0.2)
        
        write_progress(90, 100, "Finalizing", f"Generated {len(threats)} threats")
        
        # Prepare output
        output = {
            'threats': threats,
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'source_dfd': os.path.basename(DFD_FILE),
                'total_threats': len(threats),
                'total_components': len(components),
                'generation_method': 'Simplified',
                'risk_breakdown': calculate_risk_breakdown(threats),
                'dfd_structure': {
                    'project_name': dfd_data.get('project_name', 'Unknown'),
                    'industry_context': dfd_data.get('industry_context', 'Unknown')
                }
            }
        }
        
        # Save results
        write_progress(95, 100, "Saving results", THREATS_FILE)
        
        with open(THREATS_FILE, 'w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        write_progress(100, 100, "Complete", f"Successfully generated {len(threats)} threats")
        
        print(f"\n=== Summary ===")
        print(f"Components analyzed: {len(components)}")
        print(f"Threats generated: {len(threats)}")
        print(f"Output saved to: {THREATS_FILE}")
        
        # Clean up progress file on success
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
        
        return 0
        
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR: {error_msg}")
        
        # Write error to progress file
        try:
            error_data = {
                'step': 3,
                'current': 100,
                'total': 100,
                'progress': 0,
                'message': 'Failed',
                'details': error_msg,
                'timestamp': datetime.now().isoformat(),
                'status': 'error'
            }
            with open(PROGRESS_FILE, 'w') as f:
                json.dump(error_data, f, indent=2)
        except:
            pass
        
        return 1

def generate_threats_for_component(component):
    """Generate threats for a single component"""
    threats = []
    comp_name = component['name']
    comp_type = component['type']
    
    if comp_type == 'External Entity':
        threats.append({
            'component_name': comp_name,
            'stride_category': 'S',
            'threat_description': f'An attacker could impersonate {comp_name} to gain unauthorized access to the system by exploiting weak authentication mechanisms.',
            'mitigation_suggestion': 'Implement strong multi-factor authentication and regular credential rotation.',
            'impact': 'High',
            'likelihood': 'Medium',
            'risk_score': 'High',
            'references': ['OWASP A07:2021', 'CWE-287']
        })
    
    elif comp_type == 'Process':
        threats.extend([
            {
                'component_name': comp_name,
                'stride_category': 'T',
                'threat_description': f'The {comp_name} process could be tampered with to modify its behavior or corrupt its outputs.',
                'mitigation_suggestion': 'Implement input validation, code signing, and integrity monitoring.',
                'impact': 'High',
                'likelihood': 'Low',
                'risk_score': 'Medium',
                'references': ['CWE-494', 'OWASP A03:2021']
            },
            {
                'component_name': comp_name,
                'stride_category': 'E',
                'threat_description': f'Vulnerabilities in {comp_name} could be exploited to gain elevated privileges.',
                'mitigation_suggestion': 'Apply principle of least privilege and regular security patching.',
                'impact': 'Critical',
                'likelihood': 'Low',
                'risk_score': 'High',
                'references': ['CWE-269', 'OWASP A01:2021']
            }
        ])
    
    elif comp_type == 'Data Store':
        threats.extend([
            {
                'component_name': comp_name,
                'stride_category': 'I',
                'threat_description': f'Sensitive data in {comp_name} could be exposed through unauthorized access or data breaches.',
                'mitigation_suggestion': 'Implement encryption at rest, access controls, and data masking.',
                'impact': 'Critical',
                'likelihood': 'Medium',
                'risk_score': 'Critical',
                'references': ['CWE-200', 'GDPR Article 32']
            },
            {
                'component_name': comp_name,
                'stride_category': 'T',
                'threat_description': f'Data integrity in {comp_name} could be compromised through unauthorized modifications.',
                'mitigation_suggestion': 'Implement database access controls, audit logging, and data validation.',
                'impact': 'High',
                'likelihood': 'Medium',
                'risk_score': 'High',
                'references': ['CWE-89', 'OWASP A03:2021']
            }
        ])
    
    elif comp_type == 'Data Flow':
        threats.append({
            'component_name': comp_name,
            'stride_category': 'I',
            'threat_description': f'Data transmitted through {comp_name} could be intercepted by attackers.',
            'mitigation_suggestion': 'Implement TLS 1.3 encryption and certificate pinning.',
            'impact': 'High',
            'likelihood': 'Medium',
            'risk_score': 'High',
            'references': ['CWE-319', 'OWASP A02:2021']
        })
    
    return threats

def calculate_risk_breakdown(threats):
    """Calculate risk score breakdown"""
    breakdown = {
        'Critical': 0,
        'High': 0,
        'Medium': 0,
        'Low': 0
    }
    
    for threat in threats:
        risk = threat.get('risk_score', 'Medium')
        if risk in breakdown:
            breakdown[risk] += 1
    
    return breakdown

if __name__ == '__main__':
    sys.exit(main())