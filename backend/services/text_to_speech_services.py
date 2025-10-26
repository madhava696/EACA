# backend/services/text_to_speech_services.py
import os
import io
import time
import asyncio
import logging
from typing import BinaryIO, Any
from groq import Groq
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("tts_services")
executor = ThreadPoolExecutor()

# Note: Groq API client is lazily loaded in main.py, but we define the type here
GroqClient = Any

async def generate_tts_audio(text: str, client: GroqClient) -> BinaryIO:
    """
    Generates audio data (MP3) from text using the Groq TTS API.
    Returns a BytesIO stream of the MP3 data.
    """
    
    # Mock fallback for when Groq client is not available
    if not client:
        # Simulate a WAV file header and short audio data
        logger.warning("Groq client not available. Using mock TTS audio.")
        mock_wav_header = b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
        mock_data = f"Saying: {text[:20]}".encode('utf-8')
        audio_stream = io.BytesIO(mock_wav_header + mock_data)
        audio_stream.seek(0)
        return audio_stream

    try:
        # Groq TTS model (using the synchronous Groq library)
        def sync_tts_call():
            # Use Kore voice, as it's a firm/professional voice suitable for a coding assistant.
            return client.audio.speech.create(
                model="tts-1",
                voice="Kore",
                input=text,
                response_format="mp3"
            )

        # Run the synchronous Groq call in a thread pool executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(executor, sync_tts_call)

        # The response is a Groq.audio.Audio class which has a stream_to_file method
        # or can be read directly if needed. We convert it to BytesIO.
        audio_stream = io.BytesIO()
        for chunk in response.iter_bytes(1024):
            audio_stream.write(chunk)
        
        audio_stream.seek(0)
        return audio_stream

    except Exception as e:
        logger.error(f"Groq TTS Error: {e}")
        # Fallback to the mock audio if the API call fails
        return await generate_tts_audio("TTS service failed. Check API key.", None)
