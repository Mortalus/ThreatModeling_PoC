class ValidationService:
    @staticmethod
    def validate_json_structure(data, step):
        errors = []
        warnings = []
        try:
            if step == 2:
                if 'dfd' not in data:
                    errors.append("Missing 'dfd' key in output")
                else:
                    dfd = data['dfd']
                    required_fields = ['project_name', 'external_entities', 'processes', 'assets', 'data_flows']
                    for field in required_fields:
                        if field not in dfd:
                            errors.append(f"Missing required field: {field}")
                        elif not dfd[field]:
                            warnings.append(f"Empty field: {field}")
                    if 'data_flows' in dfd and isinstance(dfd['data_flows'], list):
                        for i, flow in enumerate(dfd['data_flows']):
                            if not isinstance(flow, dict):
                                errors.append(f"Data flow {i} is not a dictionary")
                            else:
                                for req in ['source', 'destination']:
                                    if req not in flow:
                                        errors.append(f"Data flow {i} missing '{req}'")
            elif step == 3 or step == 4:
                if 'threats' not in data:
                    errors.append("Missing 'threats' key in output")
                else:
                    threats = data['threats']
                    if not isinstance(threats, list):
                        errors.append("'threats' must be a list")
                    else:
                        for i, threat in enumerate(threats):
                            if not isinstance(threat, dict):
                                errors.append(f"Threat {i} is not a dictionary")
                            else:
                                required = ['component_name', 'stride_category', 'threat_description',
                                            'mitigation_suggestion', 'impact', 'likelihood']
                                for field in required:
                                    if field not in threat:
                                        errors.append(f"Threat {i} missing '{field}'")
            elif step == 5:
                if 'attack_paths' not in data:
                    errors.append("Missing 'attack_paths' key in output")
                else:
                    paths = data['attack_paths']
                    if not isinstance(paths, list):
                        errors.append("'attack_paths' must be a list")
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }