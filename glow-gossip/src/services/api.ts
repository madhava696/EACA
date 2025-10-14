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
  provider?: string;
}

export interface StreamChunk {
  content: string;
  done: boolean;
  emotion_used?: string;
  provider?: string;
  error?: boolean;
}

export interface ApiResponse<T = any> {
  message?: string;
  token?: string;
  data?: T;
  error?: string;
  reply?: string;
  emotion_used?: string;
  provider?: string;
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

  // Updated chat method with streaming support
  async sendChatMessage(data: ChatRequest): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.getAuthHeader(),
      },
      body: JSON.stringify({
        ...data,
        history: [],
        stream: false
      }),
    });
    
    if (!response.ok) {
      throw new Error('Failed to send message');
    }
    
    return response.json();
  }
}

// Streaming function (standalone export)
export const streamChatMessage = async (message: string, emotion: string = "neutral"): Promise<AsyncIterable<StreamChunk>> => {
  const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      emotion,
      history: [],
      stream: true
    }),
  });

  if (!response.ok) {
    throw new Error('Stream request failed');
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) {
    throw new Error('No reader available');
  }

  return {
    async *[Symbol.asyncIterator]() {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data.trim() === '') continue;

              try {
                const parsed = JSON.parse(data);
                yield parsed;
                
                // Stop if we get a done signal
                if (parsed.done) {
                  return;
                }
              } catch (e) {
                console.error('Error parsing SSE data:', e);
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    }
  };
};

export const api = new ApiService();