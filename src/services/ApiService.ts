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
