import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { ChatMessage } from '@/components/ChatMessage';
import { EmotionIndicator } from '@/components/EmotionIndicator';
import { RobotAvatar } from '@/components/RobotAvatar';
import { WebcamPreview } from '@/components/WebcamPreview';
import { VoiceControls } from '@/components/VoiceControls';
import { SettingsModal } from '@/components/SettingsModal';
import { MessageInput } from '@/components/MessageInput';
import { Button } from '@/components/ui/button';
import { Bot, User, LogOut } from 'lucide-react';
import { toast } from 'sonner';
import { api, streamChatMessage, ChatMessagePart, ChatRequest } from '@/services/api';
import { getLatestEmotion } from '@/services/emotionStorage';

type EmotionState = 'neutral' | 'happy' | 'sad' | 'angry' | 'surprised' | 'fearful' | 'disgusted';
type BehaviorState = 'idle' | 'typing' | 'analyzing' | 'explaining' | 'celebrating' | 'thinking';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  isTyping?: boolean;
  emotion?: string;
  provider?: string;
}

const STORAGE_KEY = 'emotion-aware-chat-history';

const Index = () => {
  const { user, isGuest, guestMessageCount, incrementGuestCount, logout } = useAuth();
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [emotionDetection, setEmotionDetection] = useState(true);
  const [textSize, setTextSize] = useState(16);
  const [darkMode, setDarkMode] = useState(true);
  const [robotEmotion, setRobotEmotion] = useState<EmotionState>('neutral');
  const [robotBehavior, setRobotBehavior] = useState<BehaviorState>('idle');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load chat history from localStorage
  useEffect(() => {
    const savedMessages = localStorage.getItem(STORAGE_KEY);
    if (savedMessages) {
      try {
        setMessages(JSON.parse(savedMessages));
      } catch (error) {
        console.error('Error loading chat history:', error);
      }
    }
    // Set initial dark mode state from class
    setDarkMode(document.documentElement.classList.contains('dark'));
  }, []);

  // Save chat history to localStorage
  useEffect(() => {
    if (messages.length > 0) {
      // Filter out temporary messages before saving (like the streaming placeholder)
      const savableMessages = messages.filter(msg => msg.id !== 'streaming');
      localStorage.setItem(STORAGE_KEY, JSON.stringify(savableMessages));
    }
  }, [messages]);

  // Handle dark mode change
  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
  }, [darkMode]);


  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Apply text size
  useEffect(() => {
    document.documentElement.style.fontSize = `${textSize}px`;
  }, [textSize]);

  // Utility to convert current state messages to API history format
  const getApiHistory = (): ChatMessagePart[] => {
    return messages
      .filter(msg => msg.role !== 'system' && msg.id !== 'streaming') // Filter out temporary messages
      .map(msg => ({
        role: msg.role === 'assistant' ? 'bot' : 'user',
        content: msg.content
      }));
  };

  // --- Core Message Sending Logic ---
  const sendMessage = async (content: string) => {
    // Check guest limit
    if (isGuest && !incrementGuestCount()) {
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: Date.now(),
    };

    // Use current messages state to build history BEFORE adding the new user message
    const history = getApiHistory();

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    let emotion: string;
    
    // -----------------------------------------------------
    // ✅ FIX 1: Only get and use emotion if detection is enabled
    // -----------------------------------------------------
    if (emotionDetection) {
        emotion = getLatestEmotion();
    } else {
        // If disabled, explicitly use 'neutral'
        emotion = 'neutral';
    }

    setRobotEmotion(emotion as EmotionState);
    setRobotBehavior('analyzing');

    try {
      // Pass history array
      await handleStreamingMessage(content, emotion, history);
      setRobotBehavior('celebrating');
      setTimeout(() => setRobotBehavior('idle'), 2000);
      
    } catch (error) {
      console.error('Streaming error, falling back to regular chat:', error);
      // Fallback to non-streaming, passing history and user message
      await handleRegularMessage(content, emotion, history);
      setRobotBehavior('idle');
    } finally {
      setIsLoading(false);
    }
  };

  // --- Streaming Message Handler (Groq / SSE) ---
  const handleStreamingMessage = async (content: string, emotion: string, history: ChatMessagePart[]) => {
    let fullResponse = '';
    
    // Add typing indicator
    const typingId = 'typing';
    setMessages((prev) => [...prev, { 
      id: typingId, 
      role: 'assistant', 
      content: '', 
      timestamp: Date.now(),
      isTyping: true 
    }]);
    
    try {
      // Pass the user's message, emotion, AND the history
      const stream = await streamChatMessage(content, emotion, [...history, { role: 'user', content }]);
      
      // Remove typing indicator and add empty assistant message placeholder
      const streamingId = 'streaming';
      setMessages((prev) => {
        const newMessages = prev.filter(msg => msg.id !== typingId);
        return [...newMessages, { 
          id: streamingId, 
          role: 'assistant', 
          content: '', 
          timestamp: Date.now(),
          emotion,
          provider: 'streaming'
        }];
      });
      
      // Process stream
      for await (const chunk of stream) {
        if (chunk.content) {
          fullResponse += chunk.content;
          
          // Update the streaming message with new content
          setMessages((prev) => {
            return prev.map(msg => 
              msg.id === streamingId
                ? { 
                    ...msg, 
                    content: fullResponse, 
                    emotion: chunk.emotion_used as EmotionState || emotion, 
                    provider: chunk.provider || 'streaming' 
                  }
                : msg
            );
          });
        }
        
        if (chunk.done) {
          // Convert streaming message to permanent message
          setMessages((prev) => {
            return prev.map(msg => 
              msg.id === streamingId
                ? { 
                    ...msg, 
                    id: Date.now().toString(),
                    isTyping: false 
                  }
                : msg
            );
          });
          break;
        }
      }
    } catch (streamError) {
      // Remove any lingering indicators before re-throwing
      setMessages((prev) => prev.filter(msg => msg.id !== typingId && msg.id !== 'streaming'));
      console.error('Error during streaming:', streamError);
      toast.error('Stream connection failed. Trying non-streaming fallback.');
      throw streamError; // Re-throw to trigger handleRegularMessage
    }
  };

  // --- Regular Message Handler (Fallback) ---
  const handleRegularMessage = async (content: string, emotion: string, history: ChatMessagePart[]) => {
    try {
      const chatRequest: ChatRequest = {
        message: content,
        emotion: emotion,
        history: [...history, { role: 'user', content }], // Include the new user message
      };
      
      const response = await api.sendChatMessage(chatRequest);
      
      if (response.reply) {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.reply,
          timestamp: Date.now(),
          emotion: response.emotion_used as EmotionState,
          provider: 'api'
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        throw new Error('Failed to get response from backend');
      }
    } catch (error) {
      console.error('Error sending message (fallback):', error);
      toast.error('Failed to send message. Using demo mode.');
      
      // Demo response for when backend is unavailable
      const demoResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `I received your message: "${content}"\n\n**Demo Mode**: Backend connection unavailable. This is a placeholder response to demonstrate the UI features.\n\n\`\`\`python\n# Example code snippet\ndef hello_world():\n    print("Hello, World!")\n\`\`\``,
        timestamp: Date.now(),
        emotion: emotion as EmotionState,
        provider: 'demo'
      };
      
      setTimeout(() => {
        setMessages((prev) => [...prev, demoResponse]);
      }, 1500);
    }
  };


  const handleVoiceMessage = async (audioBlob: Blob) => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');

    try {
      toast.info('Processing voice message...', { duration: 3000 });
      const token = localStorage.getItem('jwt_token');
      // The API call uses fetch directly, ensuring the Authorization header is handled.
      // This works because the backend/main.py now handles the /api/voice endpoint.
      const response = await fetch('http://127.0.0.1:8000/api/voice', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {}, // Pass token here
        body: formData,
      });

      if (!response.ok) {
        // Voice endpoint returns 503 if all providers fail
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to process voice message');
      }

      const data = await response.json();
      if (data.text) {
        toast.success(`Transcribed: "${data.text}"`);
        sendMessage(data.text);
      }
    } catch (error) {
      console.error('Error processing voice message:', error);
      toast.error(`Voice processing failed: ${error.message}`);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const clearHistory = () => {
    setMessages([]);
    localStorage.removeItem(STORAGE_KEY);
    toast.success('Chat history cleared');
  };

  return (
    <div className="min-h-screen bg-background flex flex-col relative overflow-hidden">
      {/* Animated background gradient */}
      <div className="fixed inset-0 bg-gradient-to-br from-primary/5 via-background to-accent/5 pointer-events-none" />
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-transparent to-transparent pointer-events-none" />

      {/* EACA-Bot Robot Avatar - Fixed position */}
      <div className="fixed bottom-24 right-8 w-48 h-48 z-40 glass-effect rounded-2xl border-primary/30 p-2 animate-fade-in shadow-lg">
        <RobotAvatar 
          emotion={robotEmotion} 
          behavior={robotBehavior}
          isActive={isLoading}
        />
      </div>

      {/* Settings Button */}
      <SettingsModal
        emotionDetection={emotionDetection}
        onEmotionDetectionChange={setEmotionDetection}
        textSize={textSize}
        onTextSizeChange={setTextSize}
        darkMode={darkMode}
        onDarkModeChange={setDarkMode}
      />

      {/* Emotion Indicator */}
      {/* ----------------------------------------------------- */}
      {/* ✅ FIX 2: Conditionally render EmotionIndicator */}
      {/* ----------------------------------------------------- */}
      <EmotionIndicator enabled={emotionDetection} />

      {/* Webcam Preview */}
      <WebcamPreview enabled={emotionDetection} />

      {/* Header */}
      <header className="relative border-b border-border/50 backdrop-blur-xl">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary/20 border border-primary/50 flex items-center justify-center glow-primary">
                <Bot className="w-6 h-6 text-primary" />
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                  Emotion-Aware Coding Assistant
                </h1>
                <p className="text-xs text-muted-foreground">
                  {isGuest 
                    ? `Guest Mode: ${guestMessageCount}/20 messages` 
                    : user?.email || 'AI-powered coding help'}
                  {emotionDetection && ` • Emotion: ${getLatestEmotion()}`}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <VoiceControls onVoiceMessage={handleVoiceMessage} backendUrl="http://127.0.0.1:8000" />
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigate('/profile')}
                title="Profile"
              >
                <User className="w-5 h-5" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleLogout}
                title="Logout"
              >
                <LogOut className="w-5 h-5" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Chat Messages */}
      <main className="flex-1 relative overflow-hidden">
        <div className="h-full overflow-y-auto">
          <div className="max-w-5xl mx-auto px-4 py-6">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center min-h-[60vh] text-center space-y-4">
                <div className="w-20 h-20 rounded-2xl bg-primary/10 border border-primary/30 flex items-center justify-center glow-primary animate-pulse-glow">
                  <Bot className="w-10 h-10 text-primary" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold mb-2">Welcome to Your AI Coding Assistant</h2>
                  <p className="text-muted-foreground max-w-md">
                    Ask me anything about coding, algorithms, or software development. I'm here to help! 🚀
                  </p>
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg) => (
                  <ChatMessage 
                    key={msg.id} 
                    role={msg.role} 
                    content={msg.content} 
                    isTyping={msg.isTyping}
                  />
                ))}
              </>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>
      </main>

      {/* Message Input */}
      <footer className="relative border-t border-border/50 backdrop-blur-xl">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <MessageInput onSendMessage={sendMessage} disabled={isLoading} />
          {messages.length > 0 && (
            <div className="flex justify-center mt-2">
              <button
                onClick={clearHistory}
                className="text-xs text-muted-foreground hover:text-primary transition-colors"
              >
                Clear chat history
              </button>
            </div>
          )}
        </div>
      </footer>
    </div>
  );
};

export default Index;
