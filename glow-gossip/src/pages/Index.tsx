import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { ChatMessage } from '@/components/ChatMessage';
import { TypingIndicator } from '@/components/TypingIndicator';
import { EmotionIndicator } from '@/components/EmotionIndicator';
import { WebcamPreview } from '@/components/WebcamPreview';
import { VoiceControls } from '@/components/VoiceControls';
import { SettingsModal } from '@/components/SettingsModal';
import { MessageInput } from '@/components/MessageInput';
import { Button } from '@/components/ui/button';
import { Bot, User, LogOut } from 'lucide-react';
import { toast } from 'sonner';
import { api, streamChatMessage } from '@/services/api';
import { getLatestEmotion, setEmotion } from '@/services/emotionStorage';

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
  }, []);

  // Save chat history to localStorage
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    }
  }, [messages]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Apply text size
  useEffect(() => {
    document.documentElement.style.fontSize = `${textSize}px`;
  }, [textSize]);

  // NEW: Streaming message handler
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

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Get current emotion from local storage
      const emotion = getLatestEmotion();
      
      // Use streaming for real-time response
      await handleStreamingMessage(content, emotion);
      
    } catch (error) {
      console.error('Streaming error, falling back to regular chat:', error);
      // Fallback to non-streaming
      await handleRegularMessage(content, emotion);
    } finally {
      setIsLoading(false);
    }
  };

  // NEW: Streaming message handler
  const handleStreamingMessage = async (content: string, emotion: string) => {
    let fullResponse = '';
    
    // Add typing indicator
    setMessages((prev) => [...prev, { 
      id: 'typing', 
      role: 'assistant', 
      content: '', 
      timestamp: Date.now(),
      isTyping: true 
    }]);
    
    try {
      const stream = await streamChatMessage(content, emotion);
      
      // Remove typing indicator and add empty assistant message
      setMessages((prev) => {
        const newMessages = prev.filter(msg => msg.id !== 'typing');
        return [...newMessages, { 
          id: 'streaming', 
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
            const newMessages = prev.map(msg => 
              msg.id === 'streaming' 
                ? { ...msg, content: fullResponse, emotion: chunk.emotion_used || emotion, provider: chunk.provider || 'streaming' }
                : msg
            );
            return newMessages;
          });
        }
        
        if (chunk.done) {
          // Convert streaming message to permanent message
          setMessages((prev) => {
            const newMessages = prev.map(msg => 
              msg.id === 'streaming' 
                ? { 
                    ...msg, 
                    id: Date.now().toString(),
                    isTyping: false 
                  }
                : msg
            );
            return newMessages;
          });
          break;
        }
      }
    } catch (streamError) {
      console.error('Streaming failed:', streamError);
      throw streamError; // Re-throw to trigger fallback
    }
  };

  // NEW: Regular message handler (fallback)
  const handleRegularMessage = async (content: string, emotion: string) => {
    try {
      const response = await api.sendChatMessage({
        message: content,
        emotion: emotion,
      });
      
      if (response.reply) {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.reply,
          timestamp: Date.now(),
          emotion: response.emotion_used,
          provider: 'api'
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        throw new Error(response.error || 'Failed to get response');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      toast.error('Failed to send message. Using demo mode.');
      
      // Demo response for when backend is unavailable
      const demoResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `I received your message: "${content}"\n\n**Demo Mode**: Backend connection unavailable. This is a placeholder response to demonstrate the UI features.\n\n\`\`\`python\n# Example code snippet\ndef hello_world():\n    print("Hello, World!")\n\`\`\``,
        timestamp: Date.now(),
        emotion: emotion,
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
      const token = localStorage.getItem('jwt_token');
      const response = await fetch('http://127.0.0.1:8000/api/voice', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to process voice message');
      }

      const data = await response.json();
      if (data.text) {
        sendMessage(data.text);
      }
    } catch (error) {
      console.error('Error processing voice message:', error);
      toast.error('Voice processing unavailable');
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