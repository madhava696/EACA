import { useState } from 'react';
import { Video, VideoOff, Minimize2, Maximize2 } from 'lucide-react';
import { Button } from './ui/button';
// ✅ Corrected import name: API_BASE_URL
import { API_BASE_URL } from '@/services/api';

interface WebcamPreviewProps {
  enabled: boolean;
  isActive: boolean;
  onStart: () => void;
  onStop: () => void;
}

export const WebcamPreview = ({ enabled, isActive, onStart, onStop }: WebcamPreviewProps) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!enabled) return null;

  return (
    <div
      className={`fixed bottom-20 right-4 z-40 glass-effect rounded-xl overflow-hidden border-primary/30 glow-primary transition-all duration-300 ${
        isExpanded ? 'w-96 h-72' : 'w-48 h-36'
      }`}
    >
      <div className="relative w-full h-full">
        {isActive ? (
          <>
            <img
              // ✅ Corrected variable name: API_BASE_URL
              src={`${API_BASE_URL}/video_feed`} // Corrected endpoint path based on emotion_face.py
              alt="Live Emotion Stream"
              className="w-full h-full object-cover"
              // Add error handling for the image stream
              onError={(e) => {
                  console.error("Error loading video stream:", e);
                  // Optionally display a placeholder or message
                  (e.target as HTMLImageElement).style.display = 'none'; // Hide broken image
              }}
            />

            <div className="absolute top-2 left-2 flex items-center gap-2 bg-red-500/80 text-white px-2 py-1 rounded text-xs">
              <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
              Camera Active
            </div>
          </>
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center bg-muted gap-2">
            <VideoOff className="w-8 h-8 text-muted-foreground" />
            <p className="text-xs text-muted-foreground">Camera Off</p>
          </div>
        )}

        <div className="absolute top-2 right-2 flex gap-2">
          <Button
            size="icon"
            variant="secondary"
            className="w-8 h-8 opacity-80 hover:opacity-100"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? (
              <Minimize2 className="w-4 h-4" />
            ) : (
              <Maximize2 className="w-4 h-4" />
            )}
          </Button>
          <Button
            size="icon"
            variant="secondary"
            className="w-8 h-8 opacity-80 hover:opacity-100"
            onClick={isActive ? onStop : onStart}
          >
            {isActive ? (
              <VideoOff className="w-4 h-4" />
            ) : (
              <Video className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};
