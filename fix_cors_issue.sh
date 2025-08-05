#!/bin/bash

echo "🔧 Fixing CORS and API issues..."

# Fix ApiService to not use credentials for now
cat > src/services/ApiService.ts << 'EOF'
import { ApiResponse, ModelConfig, ReviewItem, UploadResponse, ProgressData } from '../types';

// API Configuration
const API_CONFIG = {
  BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:5000',
  TIMEOUT: 30000,
  MAX_RETRIES: 3,
  RETRY_DELAY: 1000
};

// Request types
interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  headers?: Record<string, string>;
  body?: any;
  timeout?: number;
  retries?: number;
}

class ApiServiceClass {
  private baseUrl: string;
  private defaultHeaders: Record<string, string>;

  constructor() {
    this.baseUrl = API_CONFIG.BASE_URL;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    };
  }

  // Core request method with retry logic
  private async request<T = any>(
    endpoint: string, 
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    const {
      method = 'GET',
      headers = {},
      body,
      timeout = API_CONFIG.TIMEOUT,
      retries = API_CONFIG.MAX_RETRIES
    } = options;

    const url = `${this.baseUrl}${endpoint}`;
    const requestHeaders = { ...this.defaultHeaders, ...headers };

    // Prepare request configuration
    const requestConfig: RequestInit = {
      method,
      headers: requestHeaders,
      // Remove credentials to avoid CORS issues
      signal: AbortSignal.timeout(timeout)
    };

    // Add body for non-GET requests
    if (body && method !== 'GET') {
      if (body instanceof FormData) {
        // Remove Content-Type header for FormData (browser sets it with boundary)
        delete requestHeaders['Content-Type'];
        requestConfig.body = body;
      } else {
        requestConfig.body = JSON.stringify(body);
      }
    }

    let lastError: Error = new Error('Request failed');

    // Retry logic
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        console.log(`API Request: ${method} ${url} (attempt ${attempt + 1})`);
        
        const response = await fetch(url, requestConfig);
        
        // Handle HTTP errors
        if (!response.ok) {
          const errorText = await response.text();
          let errorMessage: string;
          
          try {
            const errorJson = JSON.parse(errorText);
            errorMessage = errorJson.error || errorJson.message || `HTTP ${response.status}`;
          } catch {
            errorMessage = errorText || `HTTP ${response.status}: ${response.statusText}`;
          }
          
          throw new Error(errorMessage);
        }

        // Parse response
        const contentType = response.headers.get('content-type');
        let data: T;
        
        if (contentType?.includes('application/json')) {
          data = await response.json();
        } else {
          data = await response.text() as unknown as T;
        }

        console.log(`API Success: ${method} ${url}`);
        return {
          success: true,
          data,
          message: 'Request successful'
        };

      } catch (error) {
        lastError = error as Error;
        console.error(`API Error (attempt ${attempt + 1}):`, error);

        // Don't retry on certain errors
        if (error instanceof TypeError && error.message.includes('AbortError')) {
          break; // Timeout
        }
        
        if (error instanceof Error && error.message.includes('404')) {
          break; // Not found
        }

        // Wait before retry (exponential backoff)
        if (attempt < retries) {
          const delay = API_CONFIG.RETRY_DELAY * Math.pow(2, attempt);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

    // All retries failed
    console.error('API Error:', lastError.message);
    return {
      success: false,
      error: lastError.message || 'Request failed',
      message: 'Request failed after retries'
    };
  }

  // === HEALTH CHECK ===
  async healthCheck(): Promise<ApiResponse<{ status: string; timestamp: string }>> {
    return await this.request('/api/health');
  }

  // === FILE UPLOAD ===
  async uploadFile(file: File): Promise<ApiResponse<UploadResponse>> {
    const formData = new FormData();
    formData.append('file', file);

    return await this.request('/api/upload', {
      method: 'POST',
      body: formData,
      timeout: 60000 // Longer timeout for file uploads
    });
  }

  // === PIPELINE MANAGEMENT ===
  async runPipelineStep(stepNumber: number): Promise<ApiResponse<{ message: string }>> {
    return await this.request(`/api/pipeline/run/${stepNumber}`, {
      method: 'POST'
    });
  }

  async getPipelineProgress(stepNumber: number): Promise<ApiResponse<ProgressData>> {
    return await this.request(`/api/pipeline/progress/${stepNumber}`);
  }

  async stopPipelineStep(stepNumber: number): Promise<ApiResponse<{ message: string }>> {
    return await this.request(`/api/pipeline/stop/${stepNumber}`, {
      method: 'POST'
    });
  }

  async getPipelineStatus(): Promise<ApiResponse<{ steps: any[] }>> {
    return await this.request('/api/pipeline/status');
  }

  // === CONFIGURATION MANAGEMENT ===
  async getModelConfig(): Promise<ApiResponse<ModelConfig>> {
    return await this.request('/api/config/model');
  }

  async updateModelConfig(config: ModelConfig): Promise<ApiResponse<{ message: string }>> {
    return await this.request('/api/config/model', {
      method: 'PUT',
      body: config
    });
  }

  async getSettings(): Promise<ApiResponse<any>> {
    return await this.request('/api/config/settings');
  }

  async updateSettings(settings: any): Promise<ApiResponse<{ message: string }>> {
    return await this.request('/api/config/settings', {
      method: 'PUT',
      body: settings
    });
  }

  // === REVIEW SYSTEM ===
  async getReviewQueue(): Promise<ApiResponse<ReviewItem[]>> {
    return await this.request('/api/review/queue');
  }

  async submitReview(
    itemId: string, 
    decision: 'approve' | 'reject' | 'modify',
    comments?: string,
    modifications?: any
  ): Promise<ApiResponse<{ message: string }>> {
    return await this.request('/api/review/submit', {
      method: 'POST',
      body: {
        item_id: itemId,
        decision,
        comments,
        modifications
      }
    });
  }

  // === DATA RETRIEVAL ===
  async getStepData(stepNumber: number): Promise<ApiResponse<any>> {
    return await this.request(`/api/data/step/${stepNumber}`);
  }

  async getThreats(): Promise<ApiResponse<any>> {
    return await this.request('/api/data/threats');
  }

  async getDFDComponents(): Promise<ApiResponse<any>> {
    return await this.request('/api/data/dfd');
  }

  async getAttackPaths(): Promise<ApiResponse<any>> {
    return await this.request('/api/data/attack-paths');
  }
}

// Export singleton instance
export const ApiService = new ApiServiceClass();
EOF

# Create a simple Flask CORS fix for the backend
cat > fix-flask-cors.py << 'EOF'
"""
Quick script to check if your Flask app has proper CORS configuration.
Run this to see what CORS headers your Flask app is sending.
"""

import requests
import json

def test_cors():
    base_url = "http://localhost:5000"
    
    # Test the health endpoint
    try:
        print("🔧 Testing Flask CORS configuration...")
        print("=" * 50)
        
        # Make a simple GET request
        response = requests.get(f"{base_url}/api/health", timeout=5)
        print(f"✅ Health check status: {response.status_code}")
        print(f"Response: {response.text}")
        print()
        
        # Check CORS headers
        print("CORS Headers:")
        cors_headers = [
            'Access-Control-Allow-Origin',
            'Access-Control-Allow-Methods', 
            'Access-Control-Allow-Headers',
            'Access-Control-Allow-Credentials'
        ]
        
        for header in cors_headers:
            value = response.headers.get(header, 'NOT SET')
            print(f"  {header}: {value}")
        
        print()
        
        # Test upload endpoint exists
        try:
            # Don't actually upload, just check if endpoint exists
            response = requests.options(f"{base_url}/api/upload", timeout=5)
            print(f"✅ Upload endpoint accessible: {response.status_code}")
        except:
            print("❌ Upload endpoint not accessible")
            
        print()
        print("🎯 Recommendations:")
        print("1. Make sure your Flask app has CORS configured")
        print("2. Add these headers to your Flask responses:")
        print("   - Access-Control-Allow-Origin: http://localhost:3001")
        print("   - Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS")
        print("   - Access-Control-Allow-Headers: Content-Type, Authorization")
        print()
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Flask backend at http://localhost:5000")
        print("Make sure your Flask app is running with: python app.py")
    except Exception as e:
        print(f"❌ Error testing CORS: {e}")

if __name__ == "__main__":
    test_cors()
EOF

echo "✅ Fixed ApiService to remove credentials requirement"
echo "✅ Created Flask CORS test script"
echo ""
echo "🔧 Next steps:"
echo "1. Test your Flask CORS configuration:"
echo "   python fix-flask-cors.py"
echo ""
echo "2. If CORS headers are missing, add this to your Flask app.py:"
echo "   from flask_cors import CORS"
echo "   CORS(app, origins=['http://localhost:3001'])"
echo ""
echo "3. Restart both servers:"
echo "   - React: npm start (should work now)"
echo "   - Flask: python app.py"
echo ""
echo "File uploads should work perfectly now! 🚀"
