export interface EmotionEntry {
  emotion: string;
  time: string;
}

export interface EmotionData {
  latestEmotion: string;
  history: EmotionEntry[];
}

const EMOTION_STORAGE_KEY = 'emotion_data';

export function setEmotion(emotion: string): void {
  const data = getEmotionData();
  data.latestEmotion = emotion;
  data.history.push({
    emotion,
    time: new Date().toISOString(),
  });
  // Keep only last 100 entries
  if (data.history.length > 100) {
    data.history = data.history.slice(-100);
  }
  localStorage.setItem(EMOTION_STORAGE_KEY, JSON.stringify(data));
}

export function getLatestEmotion(): string {
  const data = getEmotionData();
  return data.latestEmotion || 'neutral';
}

export function getEmotionData(): EmotionData {
  try {
    const stored = localStorage.getItem(EMOTION_STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    console.error('Error parsing emotion data:', error);
  }
  return {
    latestEmotion: 'neutral',
    history: [],
  };
}

export function deleteLocalEmotionData(): void {
  localStorage.removeItem(EMOTION_STORAGE_KEY);
}

