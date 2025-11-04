import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { ChatMessage } from '@/components/ChatMessage';
import { TypingIndicator } from '@/components/TypingIndicator';
import { EmotionIndicator } from '@/components/EmotionIndicator';
import { RobotAvatar } from '@/components/RobotAvatar';
import { WebcamPreview } from '@/components/WebcamPreview';
import { VoiceControls } from '@/components/VoiceControls';
import { SettingsModal } from '@/components/SettingsModal';
import { MessageInput } from '@/components/MessageInput';
import { Button } from '@/components/ui/button';
import { Bot, User, LogOut } from 'lucide-react';
import { toast } from 'sonner';
import { useEmotionPoll } from "@/hooks/useEmotionPoll";

// ✅ Import the ChatMessagePart type for the helper function
import { api, streamChatMessage, ChatMessagePart } from '@/services/api';
import { getLatestEmotion, setEmotion } from '@/services/emotionStorage';

type EmotionState = 'neutral' | 'happy' | 'sad' | 'angry' | 'surprised' | 'fearful' | 'disgusted';
type BehaviorState = 'idle' | 'typing' | 'analyzing' | 'explaining' | 'celebrating' | 'thinking';

// Interface for frontend message state
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

// ✅ Helper function to convert frontend messages to API history format
const getApiHistory = (messages: Message[]): ChatMessagePart[] => {
  return messages
    // Filter out typing indicators or temporary messages if necessary
    .filter(msg => msg.id !== 'typing' && msg.id !== 'streaming')
    .map(msg => ({
      // Map 'assistant' role to 'bot' for the API
      role: msg.role === 'assistant' ? 'assistant' : 'user',
      content: msg.content,
    }));
};


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
  const [isDetectionActive, setIsDetectionActive] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // --- useEffect hooks for loading/saving history, scrolling, text size ---
  // (Keep these exactly as they were)
  useEffect(() => { /* Load history */
    const savedMessages = localStorage.getItem(STORAGE_KEY);
    if (savedMessages) { try { setMessages(JSON.parse(savedMessages)); } catch (e) { console.error('Error loading chat history:', e); } }
  }, []);
  useEffect(() => { /* Save history */
    if (messages.length > 0) { localStorage.setItem(STORAGE_KEY, JSON.stringify(messages)); }
  }, [messages]);
  useEffect(() => { /* Auto-scroll */
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);
  useEffect(() => { /* Apply text size */
    document.documentElement.style.fontSize = `${textSize}px`;
  }, [textSize]);


  // --- Emotion/Detection Handlers ---
  // (Keep these exactly as they were)
  const handleEmotionUpdate = (emotion: string, confidence: number) => {
    setRobotEmotion(emotion as EmotionState);
  };
  const handleStartDetection = async () => {
     try { await api.startEmotionDetection(); setIsDetectionActive(true); toast.success('Emotion detection started'); } catch (e) { console.error('Failed to start detection:', e); toast.error('Failed to start emotion detection'); }
  };
  const handleStopDetection = async () => {
     try { await api.stopEmotionDetection(); setIsDetectionActive(false); toast.success('Emotion detection stopped'); } catch (e) { console.error('Failed to stop detection:', e); toast.error('Failed to stop emotion detection'); }
  };


  // --- sendMessage Function (Main logic trigger) ---
  const sendMessage = async (content: string) => {
    if (isGuest && !incrementGuestCount()) return;

     if (emotionDetection && !isDetectionActive) {
    const start = confirm("Would you like to enable emotion detection (requires camera access)?");
    if (start) {
      try {
        await handleStartDetection();
      } catch (e) {
        console.error("Failed to auto-start detection:", e);
      }
    }
  }

    const userMessage: Message = {
      id: Date.now().toString(), role: 'user', content, timestamp: Date.now(),
    };

    // Store the messages *before* making the API call to get the latest history
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages); // Update state immediately for UI responsiveness
    setIsLoading(true);

    const emotion = getLatestEmotion();
    setRobotEmotion(emotion as EmotionState);
    setRobotBehavior('analyzing');

    // ✅ Prepare history *after* adding the new user message to the state array
    const historyForApi = getApiHistory(updatedMessages);

    try {
      // ✅ Pass the correctly formatted history
      await handleStreamingMessage(content, emotion, historyForApi);
      setRobotBehavior('celebrating');
      setTimeout(() => setRobotBehavior('idle'), 2000);
    } catch (error) {
      console.error('Streaming error, falling back to regular chat:', error);
      // ✅ Pass the correctly formatted history to the fallback
      await handleRegularMessage(content, emotion, historyForApi);
      setRobotBehavior('idle');
    } finally {
      setIsLoading(false);
    }
  };

  // --- handleStreamingMessage Function ---
  const handleStreamingMessage = async (
    content: string, // User's current message (not needed here, history includes it)
    emotion: string,
    historyForApi: ChatMessagePart[] // ✅ Receive formatted history
  ) => {
    let fullResponse = '';

    setMessages((prev) => [...prev, {
      id: 'typing', role: 'assistant', content: '', timestamp: Date.now(), isTyping: true
    }]);

    try {
      // ✅ Use the passed historyForApi
      const stream = await streamChatMessage(content, emotion, historyForApi);

      // Remove typing indicator and add placeholder for streaming response
      let streamMessageId = 'streaming-' + Date.now(); // Give it a unique temp ID
      setMessages((prev) => {
        const newMessages = prev.filter(msg => msg.id !== 'typing');
        return [...newMessages, {
          id: streamMessageId, role: 'assistant', content: '', timestamp: Date.now(),
          emotion, provider: 'streaming' // Initial provider
        }];
      });

      // Process stream
      for await (const chunk of stream) {
        if (chunk.error) {
             console.error("Stream returned an error chunk:", chunk.content);
             toast.error(`Stream Error: ${chunk.content}`);
             // Remove the placeholder message on error
              setMessages((prev) => prev.filter(msg => msg.id !== streamMessageId));
             throw new Error(chunk.content || "Streaming failed"); // Trigger fallback
        }

        if (chunk.content) {
          fullResponse += chunk.content;
          setMessages((prev) => prev.map(msg =>
            msg.id === streamMessageId
              ? { ...msg, content: fullResponse, emotion: chunk.emotion_used || emotion, provider: chunk.provider || msg.provider } // Update content, emotion, provider
              : msg
          ));
        }

        if (chunk.done) {
          // Finalize the streaming message: update ID, clear typing flag
          setMessages((prev) => prev.map(msg =>
            msg.id === streamMessageId
              ? { ...msg, id: Date.now().toString(), isTyping: false } // Final ID
              : msg
          ));
          break; // Exit loop
        }
      }
    } catch (streamError) {
      console.error('Streaming failed:', streamError);
      // Clean up typing/streaming indicators if stream fails early
      setMessages((prev) => prev.filter(msg => msg.id !== 'typing' && msg.id !== 'streaming'));
      throw streamError; // Re-throw to trigger fallback in sendMessage
    }
  };

  // --- handleRegularMessage Function (Fallback) ---
  const handleRegularMessage = async (
      content: string, // User's current message
      emotion: string,
      historyForApi: ChatMessagePart[] // ✅ Receive formatted history
    ) => {
    try {
      // ✅ Pass the correctly formatted history
      const response = await api.sendChatMessage({
        message: content, // Send the current message again for context if needed by API design
        emotion: emotion,
        history: historyForApi, // Pass the formatted history
      });

      if (response.reply) {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(), role: 'assistant', content: response.reply,
          timestamp: Date.now(), emotion: response.emotion_used, provider: response.provider || 'api-fallback'
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } else {
         // Use error message from handleResponse if available
         const errorDetail = response.error || 'Failed to get valid response from backend';
         console.error('Non-streaming error:', errorDetail);
         toast.error(`Error: ${errorDetail}. Using demo mode.`);
         throw new Error(errorDetail); // Trigger demo response
      }
    } catch (error) {
       console.error('Error sending non-streaming message:', error);
       // Use toast if not already shown by handleResponse
       if (!(error instanceof Error && error.message.startsWith('HTTP error'))) {
            toast.error('Failed to send message. Using demo mode.');
       }

      // Demo response (keep as fallback for total failure)
      const demoResponse: Message = {
        id: (Date.now() + 1).toString(), role: 'assistant',
        content: `I received your message: "${content}"\n\n**Demo Mode**: Backend connection unavailable...`, // Shortened for brevity
        timestamp: Date.now(), emotion: emotion, provider: 'demo'
      };
      setTimeout(() => { setMessages((prev) => [...prev, demoResponse]); }, 1000);
    }
  };

  // --- handleVoiceMessage, handleLogout, clearHistory ---
  // (Keep these exactly as they were)
   const handleVoiceMessage = async (audioBlob: Blob) => {
       const formData = new FormData();
       formData.append('audio', audioBlob, 'recording.wav');
       try {
           const response = await api.sendVoiceMessage(formData); // Use updated API method
           if (response.data?.text) {
               sendMessage(response.data.text); // Send transcribed text to chat
           } else {
               throw new Error(response.error || 'Failed to process voice message');
           }
       } catch (error: any) {
           console.error('Error processing voice message:', error);
           toast.error(error.message || 'Voice processing unavailable');
       }
   };
   const handleLogout = () => { logout(); navigate('/login'); };
   const clearHistory = () => { setMessages([]); localStorage.removeItem(STORAGE_KEY); toast.success('Chat history cleared'); };


  // --- JSX Return ---
  // (Keep the entire JSX structure exactly as it was)
  return (
    <div className="min-h-screen bg-background flex flex-col relative overflow-hidden">
      {/* Backgrounds */}
      <div className="fixed inset-0 bg-gradient-to-br from-primary/5 via-background to-accent/5 pointer-events-none" />
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-transparent to-transparent pointer-events-none" />

      {/* Robot Avatar */}
      <div className="fixed bottom-24 right-8 w-48 h-48 z-40 glass-effect rounded-2xl border-primary/30 p-2 animate-fade-in shadow-lg">
        <RobotAvatar emotion={robotEmotion} behavior={robotBehavior} isActive={isLoading} />
      </div>

      {/* Settings */}
      <SettingsModal
        emotionDetection={emotionDetection} onEmotionDetectionChange={setEmotionDetection}
        textSize={textSize} onTextSizeChange={setTextSize}
        darkMode={darkMode} onDarkModeChange={setDarkMode}
      />

       {/* Emotion Indicator */}
       {/* Ensure this component uses the useEmotionPoll hook internally now */}
      <EmotionIndicator
        enabled={emotionDetection && isDetectionActive}
        // Remove onEmotionUpdate if the indicator now reads directly
        // onEmotionUpdate={handleEmotionUpdate}
      />

       {/* Webcam Preview */}
       {/* Ensure API_BASE_URL is imported correctly here */}
      <WebcamPreview
        enabled={emotionDetection} isActive={isDetectionActive}
        onStart={handleStartDetection} onStop={handleStopDetection}
      />

      {/* Header */}
      <header className="relative border-b border-border/50 backdrop-blur-xl">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            {/* Logo & Title */}
            <div className="flex items-center gap-3">
               <div className="w-10 h-10 rounded-xl bg-primary/20 border border-primary/50 flex items-center justify-center glow-primary">
                 <Bot className="w-6 h-6 text-primary" />
               </div>
               <div>
                 <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                   Emotion-Aware Coding Assistant
                 </h1>
                 <p className="text-xs text-muted-foreground">
                   {isGuest ? `Guest Mode: ${guestMessageCount}/20 msgs` : user?.email || 'AI Help'}
                   {emotionDetection && ` • Emotion: ${robotEmotion}`} {/* Display current robot emotion */}
                 </p>
               </div>
            </div>
            {/* Controls */}
            <div className="flex items-center gap-2">
               {emotionDetection && (
                 <Button variant={isDetectionActive ? "destructive" : "default"} size="sm" onClick={isDetectionActive ? handleStopDetection : handleStartDetection}>
                   {isDetectionActive ? 'Stop Detection' : 'Start Detection'}
                 </Button>
               )}
              <VoiceControls onVoiceMessage={handleVoiceMessage} />
              <Button variant="ghost" size="icon" onClick={() => navigate('/profile')} title="Profile"><User className="w-5 h-5" /></Button>
              <Button variant="ghost" size="icon" onClick={handleLogout} title="Logout"><LogOut className="w-5 h-5" /></Button>
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
                   <h2 className="text-2xl font-bold mb-2">Welcome...</h2>
                   <p className="text-muted-foreground max-w-md">Ask me anything...</p>
                 </div>
              </div>
            ) : (
              <>
                {messages.map((msg) => (
                  <ChatMessage key={msg.id} role={msg.role} content={msg.content} isTyping={msg.isTyping} />
                ))}
              </>
            )}
            <div ref={messagesEndRef} /> {/* Anchor for scrolling */}
          </div>
        </div>
      </main>

      {/* Message Input Footer */}
      <footer className="relative border-t border-border/50 backdrop-blur-xl">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <MessageInput onSendMessage={sendMessage} disabled={isLoading} />
          {messages.length > 0 && (
            <div className="flex justify-center mt-2">
              <button onClick={clearHistory} className="text-xs text-muted-foreground hover:text-primary transition-colors">
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

