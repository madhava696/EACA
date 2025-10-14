// glow-gossip/src/components/ChatMessage.tsx
import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Bot, User } from 'lucide-react';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  isTyping?: boolean;
}

export const ChatMessage = ({ role, content, isTyping = false }: ChatMessageProps) => {
  const [displayedContent, setDisplayedContent] = useState('');
  const [isAnimating, setIsAnimating] = useState(isTyping);

  useEffect(() => {
    if (isTyping && role === 'assistant') {
      setIsAnimating(true);
      let index = 0;
      const interval = setInterval(() => {
        if (index < content.length) {
          setDisplayedContent(content.slice(0, index + 1));
          index++;
        } else {
          setIsAnimating(false);
          clearInterval(interval);
        }
      }, 30);
      return () => clearInterval(interval);
    } else {
      setDisplayedContent(content);
    }
  }, [content, isTyping, role]);

  const isBot = role === 'assistant';

  return (
    <div className={`flex gap-3 mb-4 animate-fade-in ${isBot ? 'justify-start' : 'justify-end'}`}>
      {isBot && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 border border-primary/50 flex items-center justify-center glow-primary">
          <Bot className="w-5 h-5 text-primary" />
        </div>
      )}
      
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isBot
            ? 'glass-effect border-primary/30'
            : 'bg-primary text-primary-foreground glow-primary'
        }`}
      >
        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {displayedContent}
          </ReactMarkdown>
        </div>
        {isAnimating && (
          <span className="inline-block w-2 h-4 ml-1 bg-primary animate-typing rounded" />
        )}
      </div>

      {!isBot && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-accent/20 border border-accent/50 flex items-center justify-center">
          <User className="w-5 h-5 text-accent" />
        </div>
      )}
    </div>
  );
};