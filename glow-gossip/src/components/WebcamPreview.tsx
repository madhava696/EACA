import { useEffect, useRef, useState } from 'react';
import { Video, VideoOff, Minimize2, Maximize2 } from 'lucide-react';
import { Button } from './ui/button';

interface WebcamPreviewProps {
  enabled: boolean;
  backendUrl?: string;
}

export const WebcamPreview = ({ enabled, backendUrl = '/video_feed' }: WebcamPreviewProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isActive, setIsActive] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);

  useEffect(() => {
    if (enabled && !stream) {
      startWebcam();
    } else if (!enabled && stream) {
      stopWebcam();
    }

    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, [enabled]);

  const startWebcam = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 },
        audio: false,
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
      setIsActive(true);
    } catch (error) {
      console.error('Error accessing webcam:', error);
      setIsActive(false);
    }
  };

  const stopWebcam = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    }
    setIsActive(false);
  };

  if (!enabled) return null;

  return (
    <div
      className={`fixed bottom-20 right-4 z-40 glass-effect rounded-xl overflow-hidden border-primary/30 glow-primary transition-all duration-300 ${
        isExpanded ? 'w-96 h-72' : 'w-48 h-36'
      }`}
    >
      <div className="relative w-full h-full">
        {isActive ? (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-muted">
            <VideoOff className="w-8 h-8 text-muted-foreground" />
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
            onClick={() => {
              if (isActive) {
                stopWebcam();
              } else {
                startWebcam();
              }
            }}
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
