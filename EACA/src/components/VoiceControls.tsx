import { useState, useRef } from 'react';
import { Mic, MicOff, Volume2 } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';

interface VoiceControlsProps {
  onVoiceMessage: (audioBlob: Blob) => void;
  backendUrl?: string;
}

export const VoiceControls = ({ onVoiceMessage, backendUrl = '/api' }: VoiceControlsProps) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        onVoiceMessage(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      toast.success('Recording started');
    } catch (error) {
      console.error('Error starting recording:', error);
      toast.error('Failed to start recording');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      toast.success('Recording stopped');
    }
  };

  const playTTS = async (text: string) => {
    try {
      setIsPlaying(true);
      // Placeholder: Connect to backend /api/tts endpoint
      const response = await fetch(`${backendUrl}/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });

      if (!response.ok) throw new Error('TTS failed');

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      
      audio.onended = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(audioUrl);
      };
      
      audio.play();
    } catch (error) {
      console.error('Error playing TTS:', error);
      setIsPlaying(false);
      toast.error('Text-to-speech unavailable');
    }
  };

  return (
    <div className="flex gap-2">
      <Button
        size="icon"
        variant={isRecording ? 'destructive' : 'secondary'}
        onClick={isRecording ? stopRecording : startRecording}
        className={isRecording ? 'animate-pulse-glow' : ''}
      >
        {isRecording ? (
          <MicOff className="w-5 h-5" />
        ) : (
          <Mic className="w-5 h-5" />
        )}
      </Button>
      
      <Button
        size="icon"
        variant="secondary"
        onClick={() => playTTS('This is a test message')}
        disabled={isPlaying}
      >
        <Volume2 className={`w-5 h-5 ${isPlaying ? 'animate-pulse' : ''}`} />
      </Button>
    </div>
  );
};
