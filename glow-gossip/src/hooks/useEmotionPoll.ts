import { useEffect, useState } from "react";
import { api } from "@/services/api";  // Ensure api has a getEmotionStatus() endpoint

export function useEmotionPoll(enabled: boolean, interval = 1500) {
  const [emotion, setEmotion] = useState("neutral");

  useEffect(() => {
    if (!enabled) return;

    let isCancelled = false;
    const fetchEmotion = async () => {
      try {
        const res = await api.getEmotionStatus(); // Should return { emotion: "happy" }
        if (!isCancelled && res?.emotion) {
          setEmotion(res.emotion);
          localStorage.setItem("latest_emotion", res.emotion); // Optional
        }
      } catch (err) {
        console.error("Failed to fetch emotion:", err);
      }
    };

    fetchEmotion();
    const intervalId = setInterval(fetchEmotion, interval);

    return () => {
      isCancelled = true;
      clearInterval(intervalId);
    };
  }, [enabled, interval]);

  return emotion;
}
