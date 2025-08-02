import re
from datetime import datetime
import uuid
from collections import Counter
from utils.file_utils import save_step_data

class ReviewService:
    @staticmethod
    def calculate_confidence(value, value_type):
        confidence = 0.5
        if value_type == 'entity':
            common_entities = ['user', 'admin', 'customer', 'system', 'api', 'external']
            if any(entity in value.lower() for entity in common_entities):
                confidence += 0.3
            if re.match(r'^[A-Z][a-zA-Z0-9_]*$', value):
                confidence += 0.1
        elif value_type == 'asset':
            if any(db in value.lower() for db in ['db', 'database', 'store', 'cache']):
                confidence += 0.2
            if any(fs in value.lower() for fs in ['file', 'storage', 'blob', 's3']):
                confidence += 0.2
        elif value_type == 'process':
            if any(svc in value.lower() for svc in ['service', 'server', 'api', 'gateway']):
                confidence += 0.3
        elif value_type == 'data_flow':
            if all(key in value for key in ['source', 'destination', 'protocol']):
                confidence += 0.2
            if 'authentication_mechanism' in value and value['authentication_mechanism'] != 'Unknown':
                confidence += 0.2
        return min(confidence, 0.95)

    @staticmethod
    def infer_criticality_hint(asset_name):
        asset_lower = asset_name.lower()
        if any(critical in asset_lower for critical in ['payment', 'billing', 'credential', 'secret', 'key']):
            return "Likely Critical - handles sensitive financial or authentication data"
        elif any(high in asset_lower for high in ['user', 'customer', 'profile', 'personal']):
            return "Likely High - contains user PII data"
        elif any(medium in asset_lower for medium in ['log', 'cache', 'session', 'temp']):
            return "Likely Medium - temporary or derived data"
        return "Consider data sensitivity and business impact"

    @staticmethod
    def infer_exposure_hint(asset_name):
        asset_lower = asset_name.lower()
        if any(public in asset_lower for public in ['public', 'cdn', 'static', 'frontend']):
            return "Likely Internet-facing - public resources"
        elif any(dmz in asset_lower for dmz in ['api', 'gateway', 'proxy', 'load']):
            return "Likely DMZ - exposed but protected services"
        elif any(internal in asset_lower for internal in ['db', 'database', 'internal', 'private']):
            return "Likely Internal - should not be directly exposed"
        return "Consider network architecture and access patterns"

    @staticmethod
    def group_similar_threats(threats):
        groups = []
        processed = set()
        for i, threat1 in enumerate(threats):
            if i in processed:
                continue
            group = [threat1]
            processed.add(i)
            for j, threat2 in enumerate(threats[i+1:], i+1):
                if j in processed:
                    continue
                if (threat1.get('component_name') == threat2.get('component_name') and
                    threat1.get('stride_category') == threat2.get('stride_category')):
                    words1 = set(threat1.get('threat_description', '').lower().split())
                    words2 = set(threat2.get('threat_description', '').lower().split())
                    if len(words1 & words2) > len(words1) * 0.5:
                        group.append(threat2)
                        processed.add(j)
            if len(group) > 1:
                groups.append(group)
        return groups

    @staticmethod
    def generate_review_items(step, step_data):
        items = []
        if step == 2:
            dfd = step_data.get('dfd', {})
            quality_warnings = step_data.get('metadata', {}).get('quality_warnings', {})
            if quality_warnings:
                items.extend(ReviewService.generate_dfd_quality_review_items(dfd, quality_warnings))
            for entity in dfd.get('external_entities', []):
                confidence = ReviewService.calculate_confidence(entity, 'entity')
                if confidence < 0.8:
                    items.append({
                        'id': str(uuid.uuid4()),
                        'type': 'external_entity',
                        'value': entity,
                        'confidence': confidence,
                        'status': 'pending',
                        'questions': [
                            'Is this correctly identified as an external entity?',
                            'Should this be classified as a process instead?'
                        ],
                        'suggestions': []
                    })
            for asset in dfd.get('assets', []):
                items.append({
                    'id': str(uuid.uuid4()),
                    'type': 'asset',
                    'value': asset,
                    'confidence': 0.6,
                    'status': 'pending',
                    'attributes_needed': {
                        'criticality': {
                            'question': 'What is the criticality level?',
                            'options': ['Critical', 'High', 'Medium', 'Low'],
                            'hint': ReviewService.infer_criticality_hint(asset)
                        },
                        'exposure': {
                            'question': 'What is the exposure level?',
                            'options': ['Internet-facing', 'DMZ', 'Internal', 'Isolated'],
                            'hint': ReviewService.infer_exposure_hint(asset)
                        },
                        'data_classification': {
                            'question': 'What type of data does this store?',
                            'options': ['PII', 'PHI', 'PCI', 'Confidential', 'Public'],
                            'multiple': True
                        }
                    }
                })
            for flow in dfd.get('data_flows', []):
                confidence = ReviewService.calculate_confidence(flow, 'data_flow')
                if not flow.get('authentication_mechanism') or flow['authentication_mechanism'] == 'Unknown':
                    items.append({
                        'id': str(uuid.uuid4()),
                        'type': 'data_flow',
                        'value': flow,
                        'confidence': confidence,
                        'status': 'pending',
                        'missing_fields': ['authentication_mechanism'],
                        'questions': [
                            'What authentication method is used for this data flow?',
                            'Is encryption in transit implemented?'
                        ]
                    })
        elif step == 3:
            threats = step_data.get('threats', [])
            threat_groups = ReviewService.group_similar_threats(threats)
            for group in threat_groups:
                if len(group) > 1:
                    items.append({
                        'id': str(uuid.uuid4()),
                        'type': 'duplicate_threats',
                        'value': group,
                        'confidence': 0.4,
                        'status': 'pending',
                        'action_needed': 'merge_or_differentiate',
                        'questions': [
                            'Are these threats describing the same vulnerability?',
                            'Should they be merged or kept separate?'
                        ]
                    })
            for threat in threats:
                if threat.get('impact') == 'Critical' and threat.get('likelihood') == 'High':
                    items.append({
                        'id': str(uuid.uuid4()),
                        'type': 'high_risk_threat',
                        'value': threat,
                        'confidence': 0.9,
                        'status': 'pending',
                        'validation_needed': True,
                        'questions': [
                            'Is this risk assessment accurate?',
                            'Are there compensating controls in place?'
                        ]
                    })
        return items

    @staticmethod
    def generate_dfd_quality_review_items(dfd_data: dict, anomalies: dict) -> list:
        review_items = []
        for orphan in anomalies.get('orphan_components', []):
            review_items.append({
                'id': str(uuid.uuid4()),
                'type': 'orphan_component',
                'value': orphan,
                'confidence': 0.3,
                'status': 'pending',
                'questions': [
                    f"Component '{orphan}' is not connected to any data flows. Should it be removed?",
                    "If keeping it, what data flows should connect to this component?"
                ],
                'action_options': ['Remove', 'Add Flows', 'Keep as-is']
            })
        for dead_end in anomalies.get('dead_end_processes', []):
            review_items.append({
                'id': str(uuid.uuid4()),
                'type': 'dead_end_process',
                'value': dead_end,
                'confidence': 0.4,
                'status': 'pending',
                'questions': [
                    f"Process '{dead_end}' only receives data but never sends any. Is this correct?",
                    "What happens to the data after it reaches this process?"
                ],
                'suggestions': [
                    "Add outgoing data flows to downstream components",
                    "Mark as a terminal process (e.g., logging service)"
                ]
            })
        for undefined in anomalies.get('undefined_references', []):
            review_items.append({
                'id': str(uuid.uuid4()),
                'type': 'undefined_reference',
                'value': undefined,
                'confidence': 0.1,
                'status': 'pending',
                'critical': True,
                'questions': [
                    f"Data flow references {undefined}, but this component is not defined.",
                    "Should this component be added to the appropriate list?"
                ],
                'required_action': 'Define component or fix reference'
            })
        return review_items

    @staticmethod
    def apply_review_corrections(step, item, corrections, pipeline_state, output_folder):
        step_data = pipeline_state.state['step_outputs'].get(step, {})
        if step == 2:
            dfd = step_data.get('dfd', {})
            if item['type'] == 'asset' and corrections:
                for i, asset in enumerate(dfd.get('assets', [])):
                    if asset == item['value']:
                        if 'assets_metadata' not in dfd:
                            dfd['assets_metadata'] = {}
                        dfd['assets_metadata'][asset] = {
                            'criticality': corrections.get('criticality'),
                            'exposure': corrections.get('exposure'),
                            'data_classification': corrections.get('data_classification'),
                            'reviewed': True,
                            'reviewer': item['review']['reviewer'],
                            'review_date': item['review']['timestamp']
                        }
                        break
            elif item['type'] == 'data_flow' and corrections:
                for flow in dfd.get('data_flows', []):
                    if flow == item['value']:
                        flow.update(corrections)
                        flow['reviewed'] = True
                        break
        save_step_data(step, step_data, output_folder)

    @staticmethod
    def calculate_quality_metrics(review_history):
        metrics = {
            'total_reviews': len(review_history),
            'approval_rate': 0,
            'average_confidence_improvement': 0,
            'most_common_issues': {},
            'reviewer_stats': {}
        }
        if review_history:
            approvals = len([r for r in review_history if r['decision'] == 'approve'])
            metrics['approval_rate'] = approvals / len(review_history)
            for review in review_history:
                reviewer = review['reviewer']
                if reviewer not in metrics['reviewer_stats']:
                    metrics['reviewer_stats'][reviewer] = {'count': 0, 'approvals': 0}
                metrics['reviewer_stats'][reviewer]['count'] += 1
                if review['decision'] == 'approve':
                    metrics['reviewer_stats'][reviewer]['approvals'] += 1
        return metrics