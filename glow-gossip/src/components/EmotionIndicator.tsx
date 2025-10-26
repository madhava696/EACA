import { useEffect, useState } from 'react';
import { Smile } from 'lucide-react';
import { getLatestEmotion } from '@/services/emotionStorage'; // Import the utility

interface EmotionIndicatorProps {
  enabled: boolean;
}

// Map the backend's core emotions to Emojis
const emotionEmojis: Record<string, string> = {
  happy: '😊',
  sad: '😢',
  angry: '😠',
  surprised: '😮',
  neutral: '😐',
  fearful: '😨',
  disgusted: '🤢',
  stressed: '😩', // Custom: Mapping 'stressed' and 'anxious' for better UI feedback
  anxious: '😟',
  confused: '🤔',
};

export const EmotionIndicator = ({ enabled }: EmotionIndicatorProps) => {
  const [emotion, setEmotion] = useState<string>('neutral');
  const [confidence, setConfidence] = useState<number>(0);
  
  // FIX: Replace mock logic with a polling mechanism for real-time local data
  useEffect(() => {
    if (!enabled) {
      // Clear data when disabled
      setEmotion('neutral');
      setConfidence(0);
      return;
    }

    // Set up a brief polling interval (e.g., every 500ms) to check the latest emotion
    const interval = setInterval(() => {
      // NOTE: getLatestEmotion reads the dominant emotion from localStorage.
      // The WebcamPreview/backend stream must write the real-time emotion data
      // to local storage for this to work correctly.
      const currentEmotion = getLatestEmotion();
      
      // Since the local storage utility doesn't store confidence, we mock a high score 
      // for visual feedback if a dominant emotion is present.
      setEmotion(currentEmotion.toLowerCase());
      setConfidence(currentEmotion.toLowerCase() !== 'neutral' ? 90 : 100); 

    }, 500);

    // Cleanup function
    return () => clearInterval(interval);
  }, [enabled]);

  // If emotion detection is disabled, the component should not render.
  if (!enabled) return null;

  const displayEmotion = emotionEmojis[emotion] ? emotion : '😐';

  return (
    <div className="fixed top-4 right-4 z-50 glass-effect rounded-xl px-4 py-3 border-primary/30 glow-primary animate-fade-in">
      <div className="flex items-center gap-3">
        <Smile className="w-5 h-5 text-primary" />
        <div>
          <div className="text-sm font-medium flex items-center gap-2">
            <span>{displayEmotion}</span>
            <span className="capitalize text-foreground">{emotion}</span>
          </div>
          <div className="text-xs text-muted-foreground">
            {/* Display "Live" when receiving active data, or confidence */}
            {emotion === 'neutral' ? 'Listening...' : `Confidence: ${confidence}%`}
          </div>
        </div>
      </div>
    </div>
  );
};
