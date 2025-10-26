import { useState, useEffect, useCallback } from 'react';
import { setEmotion } from '@/services/emotionStorage';

// Define the shape of the data returned by the backend's /api/emotion/latest endpoint
interface EmotionData {
  dominant_emotion: string;
  score: number;
}

const API_BASE_URL = 'http://127.0.0.1:8000';
const POLLING_INTERVAL = 1000; // Poll every 1 second

export const useEmotionPoll = (enabled: boolean) => {
  const [currentEmotion, setCurrentEmotion] = useState('neutral');
  const [currentConfidence, setCurrentConfidence] = useState(0);

  const fetchEmotion = useCallback(async () => {
    if (!enabled) return;

    try {
      // NOTE: This endpoint uses the global cache updated by the background CV stream.
      const response = await fetch(`${API_BASE_URL}/api/emotion/latest`);
      
      if (!response.ok) throw new Error('Network response was not ok');

      const data: EmotionData = await response.json();

      if (data.dominant_emotion) {
        const emotion = data.dominant_emotion.toLowerCase();
        
        // 1. Update local storage for chat context (used by Index.tsx)
        setEmotion(emotion);
        
        // 2. Update local state for indicator display
        setCurrentEmotion(emotion);
        setCurrentConfidence(data.score * 100);
      }
    } catch (error) {
      console.error('Error fetching emotion data:', error);
      // Fallback for network error
      setCurrentEmotion('neutral');
      setCurrentConfidence(0);
    }
  }, [enabled]);

  useEffect(() => {
    if (enabled) {
      // Fetch immediately on enable
      fetchEmotion();

      // Start the polling interval
      const intervalId = setInterval(fetchEmotion, POLLING_INTERVAL);
      
      // Cleanup function to stop polling when disabled or component unmounts
      return () => clearInterval(intervalId);
    } else {
      // If disabled, reset emotion state and clear local storage entry
      setCurrentEmotion('neutral');
      setCurrentConfidence(0);
      setEmotion('neutral'); // Ensure chat doesn't use stale emotion when camera is off
    }
  }, [enabled, fetchEmotion]);

  return { currentEmotion, currentConfidence };
};
