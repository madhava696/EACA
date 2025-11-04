// glow-gossip/src/services/api.ts
export const API_BASE_URL = 'http://127.0.0.1:8000/api'; // ✅ EXPORT ADDED

// --- Interfaces (Keep as before) ---
export interface ChatMessagePart { role: 'user' | 'bot' | 'system'; content: string; }
export interface RegisterData { email: string; password: string; secret_key: string; }
export interface LoginData { email: string; password: string; secret_key: string; }
export interface UserProfile { id: string; email: string; created_at: string; }
export interface UpdateProfileData { email?: string; password?: string; secret_key?: string; }
export interface ChatRequest { message: string; emotion: string; history: ChatMessagePart[]; }
export interface ChatResponse { reply: string; emotion_used: string; provider?: string; }
export interface StreamChunk { content: string; done: boolean; emotion_used?: string; provider?: string; error?: boolean; }
export interface ApiResponse<T = any> { message?: string; token?: string; data?: T; error?: string | any; detail?: string | { msg: string }[] | string; reply?: string; emotion_used?: string; provider?: string; user?: { email: string }; user_id?: string; } // Expanded error type

class ApiService {
  private getAuthHeader() { 
    const token = localStorage.getItem('jwt_token');
    // Ensure the token exists and is not an empty string before adding header
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  // --- Utility to handle API errors ---
  private async handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
    const contentType = response.headers.get("content-type");
    let responseBody: any; // Allow any type initially

    try {
        // Handle no content response explicitly
        if (response.status === 204 || response.headers.get('content-length') === '0') {
             return { message: "Operation successful (No content)" } as ApiResponse<T>;
        }

        if (contentType && contentType.includes("application/json")) {
            responseBody = await response.json();
        } else {
             // Read as text if not JSON
            responseBody = await response.text();
             // If response was OK but not JSON, maybe return as message?
             if (response.ok && typeof responseBody === 'string') {
                 if(responseBody.trim() === '' || responseBody.toLowerCase() === 'ok') {
                      return { message: "Operation successful (OK Text)" } as ApiResponse<T>;
                 }
                 console.warn("API OK response was text:", responseBody);
                 // Treat unexpected text on OK as a potential issue/message
                 return { message: `Received unexpected text response: ${responseBody.substring(0, 100)}...` } as ApiResponse<T>;
             }
             // If not OK and not JSON, the text is the error body
             // This will be handled by the !response.ok check below
        }
    } catch (e) {
        console.error("API Response Parse Error:", e);
        if (!response.ok) {
             return { error: `Failed to parse error response. Status: ${response.status} ${response.statusText}` };
        } else {
             return { error: `Failed to parse successful response. Status: ${response.status}` };
        }
    }

    // Handle based on response.ok status and parsed body
    if (!response.ok) {
        let errorMsg = `HTTP error! Status: ${response.status}`;
        if (typeof responseBody === 'object' && responseBody !== null && responseBody.detail) {
             if (Array.isArray(responseBody.detail) && responseBody.detail.length > 0 && responseBody.detail[0].msg) {
                  errorMsg = responseBody.detail.map((d: any) => `${d.loc?.join('.')}: ${d.msg}`).join('; '); // Better detail message
             } else if (typeof responseBody.detail === 'string') {
                 errorMsg = responseBody.detail;
             }
        } else if (typeof responseBody === 'string' && responseBody.length > 0 && responseBody.length < 500) {
             errorMsg += ` - ${responseBody}`;
        } else if (response.statusText) {
             errorMsg += ` - ${response.statusText}`;
        }
        console.error("API Error Response:", { status: response.status, body: responseBody });
        return { error: errorMsg };
    }

    // If response.ok and we have a parsed body (likely JSON)
    if (typeof responseBody === 'object' && responseBody !== null) {
         // Special handling for getProfile data structure
         if (response.url.endsWith('/auth/me')) {
            return { data: responseBody } as ApiResponse<T>;
         }
         // For login/register, the relevant data might be top-level (token, user)
         // For other endpoints, it might be nested under 'data' or be the whole body
         // We assume the body IS the ApiResponse structure unless handled specifically above
         return responseBody as ApiResponse<T>;
    }

     // If response was OK, but we ended up here (e.g., text response handled above)
     return responseBody as ApiResponse<T> || { message: "Operation successful." } as ApiResponse<T>;
  }


  // --- Auth Endpoints (Keep /auth prefix) ---
  async register(data: RegisterData): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE_URL}/auth/register`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    return this.handleResponse(response);
  }
  async login(data: LoginData): Promise<ApiResponse<{token: string, user: {email: string}}>> {
    const response = await fetch(`${API_BASE_URL}/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    return this.handleResponse(response);
  }
  async getProfile(): Promise<ApiResponse<UserProfile>> {
    const response = await fetch(`${API_BASE_URL}/auth/me`, { method: 'GET', headers: { 'Content-Type': 'application/json', ...this.getAuthHeader() } });
    return this.handleResponse<UserProfile>(response);
  }

  // --- Profile Endpoints (Use /api prefix) ---
   async updateProfile(data: UpdateProfileData): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE_URL}/me`, { method: 'PATCH', headers: { 'Content-Type': 'application/json', ...this.getAuthHeader() }, body: JSON.stringify(data) });
    return this.handleResponse(response);
  }
  async deleteEmotionData(): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE_URL}/me/emotion-data`, { method: 'DELETE', headers: { 'Content-Type': 'application/json', ...this.getAuthHeader() } });
    return this.handleResponse(response);
  }

   // --- Emotion Detection Control (Use /api prefix) ---
   async startEmotionDetection(): Promise<ApiResponse> {
     const response = await fetch(`${API_BASE_URL}/emotion/control?active=true`, { // ✅ Use new endpoint
       method: 'POST', // ✅ Use POST
       headers: this.getAuthHeader(),
     });
     return this.handleResponse(response);
   }
  async getEmotionStatus() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/emotion/status`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    if (!response.ok) throw new Error(`HTTP error ${response.status}`);
    return await response.json(); // expected: { emotion: "happy" }
  } catch (error) {
    console.error("Error fetching emotion status:", error);
    return { emotion: "neutral" }; // fallback
  }
}
   async stopEmotionDetection(): Promise<ApiResponse> {
     const response = await fetch(`${API_BASE_URL}/emotion/control?active=false`, { // ✅ Use new endpoint
       method: 'POST', // ✅ Use POST
       headers: this.getAuthHeader(),
     });
     return this.handleResponse(response);
   }
   async getLatestEmotion(): Promise<ApiResponse<{ dominant_emotion: string; score: number; active: boolean; stale: boolean }>> { // Added active/stale fields
      const response = await fetch(`${API_BASE_URL}/emotion/latest`, { method: 'GET', headers: this.getAuthHeader() });
      return this.handleResponse(response);
   }


  // --- Chat Endpoints (Use /api prefix) ---
  async sendChatMessage(data: ChatRequest): Promise<ApiResponse<ChatResponse>> {
    // Note: sendChatMessage should also send history, updating interface and call
     const historyToSend = data.history.map(m => ({ role: m.role, content: m.content }));
    const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...this.getAuthHeader() },
        body: JSON.stringify({ ...data, history: historyToSend, stream: false })
     });
    return this.handleResponse<ChatResponse>(response);
  }

  // --- Voice Endpoint (Use /api prefix) ---
  async sendVoiceMessage(formData: FormData): Promise<ApiResponse<{ text: string; provider: string }>> {
     try {
        const response = await fetch(`${API_BASE_URL}/voice`, { method: 'POST', headers: this.getAuthHeader(), body: formData });
        return await this.handleResponse<{ text: string; provider: string }>(response);
     } catch (error: any) { console.error("Voice message fetch error:", error); return { error: error.message || "Failed..." }; }
  }

    // --- TTS Endpoint (Use /api prefix) ---
    async getTTSAudio(text: string): Promise<Blob | ApiResponse> { // Return Blob on success
        try {
            const response = await fetch(`${API_BASE_URL}/api/tts`, { method: 'POST', headers: { 'Content-Type': 'application/json', ...this.getAuthHeader() }, body: JSON.stringify({ text }) });
            if (!response.ok) { return await this.handleResponse(response); } // Use handler for errors
             const blob = await response.blob();
             // Add more robust check for audio type
             if (!blob || blob.size === 0 || !(blob.type.startsWith('audio/mpeg') || blob.type.startsWith('audio/wav') || blob.type.startsWith('audio/ogg'))) {
                 console.error("TTS response was OK but not a valid audio blob:", blob?.type, blob?.size);
                 return { error: `Received invalid or empty audio data (type: ${blob?.type}) from TTS endpoint.` };
             }
             return blob; // Return blob directly on success
        } catch (error: any) { console.error("TTS fetch error:", error); return { error: error.message || "Failed..." }; }
    }

} // End of ApiService class


// --- Updated streamChatMessage() ---
// Uses unified /api/chat endpoint with stream: true
export const streamChatMessage = async (
  message: string,
  emotion: string = "neutral",
  history: ChatMessagePart[]
): Promise<AsyncIterable<StreamChunk>> => {
  const token = localStorage.getItem("jwt_token");
  const headers: HeadersInit = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers,
    body: JSON.stringify({ message, emotion, history, stream: true }),
  });

  if (!response.ok || !response.body) {
    const errorText = await response.text();
    console.error("Stream request failed:", response.status, errorText);

    // Return an async generator yielding an error message instead of throwing
    return (async function* () {
      yield {
        content: `Stream request failed: ${errorText}`,
        done: true,
        error: true,
      };
    })();
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  return {
    async *[Symbol.asyncIterator]() {
      let buffer = "";

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            // Handle any final buffered data
            if (buffer.startsWith("data: ")) {
              try {
                const lastChunk = JSON.parse(buffer.slice(6));
                yield lastChunk;
              } catch (e) {
                console.error("Error parsing final SSE chunk:", e, buffer);
              }
            }
            break;
          }

          // Decode chunk and append to buffer
          buffer += decoder.decode(value, { stream: true });

          // Split by SSE message boundary
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || ""; // Keep last incomplete piece

          for (const part of parts) {
            if (!part.startsWith("data:")) continue;

            const data = part.slice(5).trim();
            if (!data || data === "[DONE]") continue;

            try {
              const parsed: StreamChunk = JSON.parse(data);
              yield parsed;

              if (parsed.done) {
                console.log("SSE stream complete.");
                reader.releaseLock();
                return;
              }
            } catch (err) {
              console.error("Error parsing SSE data:", err, data);
            }
          }
        }
      } catch (error: any) {
        console.error("Stream read error:", error);
        yield {
          content: `Stream reading error: ${error.message || error}`,
          done: true,
          error: true,
        };
      } finally {
        try {
          await reader.cancel();
        } catch {
          /* ignore */
        }
        console.log("Stream connection closed.");
      }
    },
  };
};


export const api = new ApiService();
