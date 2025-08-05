#!/bin/bash

echo "Fixing API endpoints to match Flask backend..."

# Update ApiService with correct endpoints
cat > src/services/ApiService.ts << 'EOF'
import { ApiResponse, UploadResponse, ModelConfig } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

class ApiServiceClass {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      // First check if the response is JSON
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        // If not JSON, it's probably an HTML error page
        const text = await response.text();
        console.error('Non-JSON response:', text);
        
        if (response.status === 405) {
          throw new Error('Method not allowed. Check the API endpoint and HTTP method.');
        } else if (response.status === 404) {
          throw new Error('API endpoint not found. Please check if the backend is running correctly.');
        } else if (response.status === 400) {
          throw new Error('Bad request. The server rejected the request data.');
        } else {
          throw new Error(`Server error (${response.status}). Please check the backend logs.`);
        }
      }

      const data = await response.json();

      if (!response.ok) {
        // Extract error message from response
        const errorMessage = data.error || data.message || `HTTP error! status: ${response.status}`;
        throw new Error(errorMessage);
      }

      return data;
    } catch (error: any) {
      // If it's a network error or parsing error
      if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
        throw new Error('Cannot connect to server. Please make sure the backend is running on port 5000.');
      }
      throw error;
    }
  }

  // File upload
  async uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${this.baseUrl}/api/upload`, {
        method: 'POST',
        body: formData,
      });

      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        console.error('Non-JSON response:', text);
        throw new Error('Invalid response from server. Please check the backend.');
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || data.message || 'Upload failed');
      }

      return data;
    } catch (error: any) {
      if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
        throw new Error('Cannot connect to server. Please make sure the backend is running.');
      }
      throw error;
    }
  }

  // Pipeline operations - Use the correct endpoint structure
  async runPipelineStep(stepName: string): Promise<ApiResponse> {
    // Map step names to step numbers for the backend
    const stepMap: { [key: string]: number } = {
      'extract_dfd': 2,
      'generate_threats': 3,
      'refine_threats': 4,
      'analyze_attack_paths': 5
    };

    const stepNumber = stepMap[stepName] || 2;

    // The Flask backend expects POST to /api/run-step with JSON body
    return this.request<ApiResponse>('/api/run-step', {
      method: 'POST',
      body: JSON.stringify({
        step: stepNumber,
        input: {} // Add any required input data here
      }),
    });
  }

  // Configuration
  async getConfig(): Promise<ModelConfig> {
    try {
      const response = await this.request<{ success: boolean; config: ModelConfig }>('/api/config', {
        method: 'GET'
      });
      return response.config;
    } catch (error) {
      // Return default config if backend is not ready
      console.log('Using default config');
      return {
        llm_provider: 'scaleway',
        llm_model: 'mixtral-8x7b-instruct',
        api_key: '',
        base_url: '',
        max_tokens: 2000,
        temperature: 0.7,
        timeout: 300
      };
    }
  }

  async updateConfig(config: ModelConfig): Promise<ApiResponse> {
    return this.request<ApiResponse>('/api/config', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  // Review operations
  async reviewItem(
    itemId: string,
    decision: 'approve' | 'reject' | 'modify',
    comments?: string,
    modifications?: any
  ): Promise<ApiResponse> {
    return this.request<ApiResponse>('/api/review-item/' + itemId, {
      method: 'POST',
      body: JSON.stringify({
        decision,
        comments,
        modifications,
      }),
    });
  }

  // Health check
  async healthCheck(): Promise<{ status: string }> {
    try {
      return await this.request<{ status: string }>('/api/health', {
        method: 'GET'
      });
    } catch (error) {
      return { status: 'error' };
    }
  }

  // Check pipeline status
  async getPipelineStatus(): Promise<any> {
    try {
      return await this.request<any>('/api/pipeline-status', {
        method: 'GET'
      });
    } catch (error) {
      console.error('Failed to get pipeline status:', error);
      return null;
    }
  }

  // Get progress for a specific session
  async getProgress(sessionId: string = 'latest'): Promise<any> {
    try {
      return await this.request<any>(`/api/progress/${sessionId}`, {
        method: 'GET'
      });
    } catch (error) {
      console.error('Failed to get progress:', error);
      return null;
    }
  }
}

export const ApiService = new ApiServiceClass();
EOF

# Create a test script to verify the backend endpoints
cat > test_flask_api.py << 'EOF'
#!/usr/bin/env python3
"""Test the Flask API endpoints to verify they work correctly."""

import requests
import json
import sys

BASE_URL = "http://localhost:5000"

def test_endpoint(method, endpoint, data=None, description=""):
    """Test a single endpoint."""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'='*60}")
    print(f"Testing: {method} {endpoint}")
    if description:
        print(f"Purpose: {description}")
    
    try:
        headers = {'Content-Type': 'application/json'} if data else {}
        
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            if data:
                response = requests.post(url, json=data, headers=headers)
            else:
                response = requests.post(url, headers=headers)
        
        print(f"Status: {response.status_code}")
        
        # Check content type
        content_type = response.headers.get('content-type', '')
        print(f"Content-Type: {content_type}")
        
        # Try to parse response
        if 'application/json' in content_type:
            try:
                json_data = response.json()
                print(f"Response: {json.dumps(json_data, indent=2)}")
            except:
                print(f"Failed to parse JSON: {response.text[:200]}")
        else:
            print(f"Response (HTML): {response.text[:200]}...")
            
        return response.status_code
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to Flask backend at http://localhost:5000")
        print("Make sure the Flask server is running!")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def main():
    """Run all API tests."""
    print("Flask API Endpoint Test")
    print("=" * 60)
    
    # Test health endpoint
    test_endpoint("GET", "/api/health", description="Health check")
    
    # Test the main endpoint
    test_endpoint("GET", "/api/test", description="Test endpoint")
    
    # Test config endpoint
    test_endpoint("GET", "/api/config", description="Get configuration")
    
    # Test run-step with proper JSON body
    print("\n" + "="*60)
    print("Testing pipeline step execution...")
    
    # Test with proper JSON body
    step_data = {
        "step": 2,
        "input": {}
    }
    test_endpoint("POST", "/api/run-step", data=step_data, 
                 description="Run pipeline step 2 (DFD Extraction)")
    
    # Test progress endpoint
    test_endpoint("GET", "/api/progress/latest", description="Get latest progress")
    
    print("\n" + "="*60)
    print("\nSummary:")
    print("- If you see 'Cannot connect', start your Flask backend: python app.py")
    print("- If you see 405 errors, check that you're using the correct HTTP method")
    print("- If you see 400 errors, check that you're sending proper JSON data")
    print("- The /api/run-step endpoint expects POST with JSON body: {\"step\": 2, \"input\": {}}")

if __name__ == "__main__":
    main()
EOF

chmod +x test_flask_api.py

echo "API endpoints fixed!"
echo ""
echo "The key fix: /api/run-step expects a POST request with JSON body:"
echo '{"step": 2, "input": {}}'
echo ""
echo "To test your Flask API:"
echo "python3 test_flask_api.py"
echo ""
echo "This will show you exactly what the Flask backend expects."