const API_BASE_URL = 'http://127.0.0.1:8000';

export interface RegisterData {
  email: string;
  password: string;
  secret_key: string;
}

export interface LoginData {
  email: string;
  password: string;
  secret_key: string;
}

export interface UserProfile {
  email: string;
  created_at: string;
}

export interface UpdateProfileData {
  email?: string;
  password?: string;
  secret_key?: string;
}

export interface ChatRequest {
  message: string;
  emotion: string;
}

export interface ChatResponse {
  reply: string;
  emotion_used: string;
}

export interface ApiResponse<T = any> {
  message?: string;
  token?: string;
  data?: T;
  error?: string;
  reply?: string;
  emotion_used?: string;
}

class ApiService {
  private getAuthHeader() {
    const token = localStorage.getItem('jwt_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async register(data: RegisterData): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE_URL}/api/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    return response.json();
  }

  async login(data: LoginData): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE_URL}/api/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    return response.json();
  }

  async getProfile(): Promise<ApiResponse<UserProfile>> {
    const response = await fetch(`${API_BASE_URL}/api/me`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...this.getAuthHeader(),
      },
    });
    return response.json();
  }

  async sendChatMessage(data: ChatRequest): Promise<ApiResponse<ChatResponse>> {
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.getAuthHeader(),
      },
      body: JSON.stringify(data),
    });
    return response.json();
  }

  async updateProfile(data: UpdateProfileData): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE_URL}/api/me`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...this.getAuthHeader(),
      },
      body: JSON.stringify(data),
    });
    return response.json();
  }

  async deleteEmotionData(): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE_URL}/api/me/emotion-data`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        ...this.getAuthHeader(),
      },
    });
    return response.json();
  }
}

export const api = new ApiService();
