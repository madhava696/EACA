import { useEffect, useState } from 'react';
import { Smile } from 'lucide-react';

interface EmotionIndicatorProps {
  enabled: boolean;
}

const emotionEmojis: Record<string, string> = {
  happy: '😊',
  sad: '😢',
  angry: '😠',
  surprised: '😮',
  neutral: '😐',
  fearful: '😨',
  disgusted: '🤢',
};

export const EmotionIndicator = ({ enabled }: EmotionIndicatorProps) => {
  const [emotion, setEmotion] = useState<string>('neutral');
  const [confidence, setConfidence] = useState<number>(0);

  useEffect(() => {
    if (!enabled) return;

    // Placeholder: Connect to backend /video_feed endpoint for real emotion data
    // For now, simulate emotion detection
    const interval = setInterval(() => {
      const emotions = Object.keys(emotionEmojis);
      const randomEmotion = emotions[Math.floor(Math.random() * emotions.length)];
      setEmotion(randomEmotion);
      setConfidence(Math.floor(Math.random() * 30) + 70); // 70-100%
    }, 3000);

    return () => clearInterval(interval);
  }, [enabled]);

  if (!enabled) return null;

  return (
    <div className="fixed top-4 right-4 z-50 glass-effect rounded-xl px-4 py-3 border-primary/30 glow-primary animate-fade-in">
      <div className="flex items-center gap-3">
        <Smile className="w-5 h-5 text-primary" />
        <div>
          <div className="text-sm font-medium flex items-center gap-2">
            <span>{emotionEmojis[emotion]}</span>
            <span className="capitalize text-foreground">{emotion}</span>
          </div>
          <div className="text-xs text-muted-foreground">
            Confidence: {confidence}%
          </div>
        </div>
      </div>
    </div>
  );
};
