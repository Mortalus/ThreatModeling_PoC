#!/bin/bash

echo "Fixing API methods and error handling..."

# Update ApiService with correct HTTP methods
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
          throw new Error('Method not allowed. The API endpoint does not support this HTTP method.');
        } else if (response.status === 404) {
          throw new Error('API endpoint not found. Please check if the backend is running correctly.');
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

  // Pipeline operations - Try GET first, fallback to POST
  async runPipelineStep(stepName: string): Promise<ApiResponse> {
    // Map step names to step numbers for the backend
    const stepMap: { [key: string]: number } = {
      'extract_dfd': 2,
      'generate_threats': 3,
      'refine_threats': 4,
      'analyze_attack_paths': 5
    };

    const stepNumber = stepMap[stepName] || 2;

    // First try GET (some Flask apps use GET for triggering actions)
    try {
      return await this.request<ApiResponse>(`/api/run-step/${stepNumber}`, {
        method: 'GET',
      });
    } catch (error: any) {
      // If GET fails with 405, try POST
      if (error.message.includes('Method not allowed')) {
        console.log('GET failed, trying POST...');
        return this.request<ApiResponse>(`/api/run-step/${stepNumber}`, {
          method: 'POST',
          body: JSON.stringify({}),
        });
      }
      throw error;
    }
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
    return this.request<ApiResponse>('/api/review', {
      method: 'POST',
      body: JSON.stringify({
        item_id: itemId,
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
}

export const ApiService = new ApiServiceClass();
EOF

# Also create a simple Python test script to check the backend
cat > test_backend.py << 'EOF'
#!/usr/bin/env python3
"""Test script to check if the Flask backend is running correctly."""

import requests
import json
import sys

BASE_URL = "http://localhost:5000"

def test_endpoint(method, endpoint, data=None):
    """Test a single endpoint."""
    url = f"{BASE_URL}{endpoint}"
    print(f"\nTesting {method} {url}")
    
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, json=data or {}, headers=headers)
        
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        # Try to parse as JSON
        try:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        except:
            print(f"Response (text): {response.text[:200]}...")
            
        return response.status_code
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to backend. Is it running?")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def main():
    """Run all tests."""
    print("Testing Flask Backend API Endpoints")
    print("=" * 40)
    
    # Test health endpoint
    test_endpoint("GET", "/api/health")
    
    # Test config endpoint
    test_endpoint("GET", "/api/config")
    
    # Test pipeline status
    test_endpoint("GET", "/api/pipeline-status")
    
    # Test run-step endpoints
    for step in range(2, 6):
        # Try both GET and POST
        get_status = test_endpoint("GET", f"/api/run-step/{step}")
        if get_status == 405:  # Method not allowed
            test_endpoint("POST", f"/api/run-step/{step}")

if __name__ == "__main__":
    main()
EOF

chmod +x test_backend.py

echo "API methods fixed!"
echo ""
echo "Changes made:"
echo "1. Added proper content-type checking to handle HTML error pages"
echo "2. Try GET method first for run-step endpoints, fallback to POST"
echo "3. Better error messages for different HTTP status codes"
echo "4. Created test_backend.py script to check your Flask API"
echo ""
echo "To test your backend API:"
echo "python3 test_backend.py"
echo ""
echo "This will show you which endpoints are available and what methods they accept."