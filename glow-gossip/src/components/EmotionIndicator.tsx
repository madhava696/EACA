import { useEffect, useState } from 'react';
import { Activity } from 'lucide-react';
import { api } from '@/services/api';
import { setEmotion as setStoredEmotion } from '@/services/emotionStorage';

interface EmotionIndicatorProps {
  enabled: boolean;
  onEmotionUpdate?: (emotion: string, confidence: number) => void;
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

export const EmotionIndicator = ({ enabled, onEmotionUpdate }: EmotionIndicatorProps) => {
  const [emotion, setEmotion] = useState<string>('neutral');
  const [confidence, setConfidence] = useState<number>(0);

  useEffect(() => {
    if (!enabled) return;

    const interval = setInterval(async () => {
      try {
        const data = await api.getLatestEmotion();
        if (data.emotion) {
          setEmotion(data.emotion);
          setConfidence(data.confidence);
          setStoredEmotion(data.emotion);
          onEmotionUpdate?.(data.emotion, data.confidence);
        }
      } catch (err) {
        console.error('Failed to fetch emotion:', err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [enabled, onEmotionUpdate]);

  if (!enabled) return null;

  return (
    <div className="fixed top-4 right-4 z-50 glass-effect rounded-xl px-4 py-3 border-primary/30 glow-primary animate-fade-in">
      <div className="flex items-center gap-3">
        <Activity className="w-5 h-5 text-primary animate-pulse" />
        <div>
          <div className="text-sm font-medium flex items-center gap-2">
            <span>{emotionEmojis[emotion] || '😐'}</span>
            <span className="capitalize text-foreground">{emotion}</span>
          </div>
          {confidence > 0 && (
            <div className="text-xs text-muted-foreground">
              {(confidence * 100).toFixed(0)}% confident
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
