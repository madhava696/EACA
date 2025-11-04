# backend/utils/chat_helpers.py
import asyncio
import json
import logging
import time
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List, Any

# --- Import necessary components ---
from backend.utils.clients import get_groq_client # To access the Groq client

# --- Configuration (Consider moving to a config file or main settings) ---
MAX_HISTORY = int(os.getenv("MAX_HISTORY", 10))
TIMEOUT_GROQ = int(os.getenv("TIMEOUT_GROQ", 20))

# --- Logger ---
logger = logging.getLogger("backend.chat_helpers")

# --- Thread Executor (Can be shared, initialized here or passed in) ---
# If you initialize it in main.py, you might need to pass it to functions here.
# For simplicity, let's assume it's okay to initialize one here if needed,
# or better yet, import the one from main.py if structure allows without circular imports.
# Let's assume an executor is available/passed if needed by sync functions called async.
# We'll use asyncio.to_thread for potentially blocking sync calls within async functions if needed.
# However, Groq's stream itself might be iterable async or sync, needs careful handling.
# The original main.py used run_in_executor for the sync Groq client. Let's keep that pattern.
executor = ThreadPoolExecutor()


# --- Helper Functions (Moved from main.py) ---

def get_emotion_aware_system_prompt(emotion: str) -> str:
    """ Returns different system prompts based on detected emotion """
    emotion = (emotion or "neutral").lower()
    # Add detailed prompt logic back here based on emotion...
    if "stressed" in emotion or "anxious" in emotion or "fearful" in emotion:
        return """You are an empathetic and patient coding assistant. The user appears stressed or anxious.
        - Use a calm, reassuring tone and short, clear sentences.
        - Break down the problem into the absolutely smallest, manageable steps.
        - Offer specific encouragement, focusing only on the current task."""
    elif "angry" in emotion or "disgusted" in emotion:
        return """You are a patient and professional coding assistant. The user appears highly frustrated.
        - Respond calmly and focus only on practical, technical solutions.
        - Acknowledge the frustration professionally ("I see this is frustrating") but do not dwell on it.
        - Provide concise, solution-focused steps to debug the current issue."""
    elif "sad" in emotion:
        return """You are a compassionate coding assistant. The user appears sad or discouraged.
        - Use a gentle, supportive tone and validate their feelings.
        - Offer encouraging reinforcement, reminding them of progress made.
        - Suggest a simple, quick win task before tackling anything large."""
    elif "happy" in emotion or "surprised" in emotion:
        return """You are an enthusiastic and engaging coding assistant. The user appears happy or excited.
        - Match their positive energy and use encouraging, upbeat language.
        - Celebrate their success and suggest ambitious next steps to build on their enthusiasm.
        - Be responsive to their excitement."""
    elif "confused" in emotion:
        return """You are a clear and patient coding assistant. The user appears confused.
        - Prioritize clear, simple explanations and define any technical jargon used.
        - Use analogies or step-by-step numbered lists for clarity.
        - Focus on verifying their foundational understanding before moving forward."""
    else: # neutral or default
        return """You are a highly capable, focused, and helpful coding assistant.
        - Provide direct, accurate coding help and technical explanations.
        - Maintain a professional yet encouraging tone.
        - Ensure all answers are concise, clear, and relevant to the user's query."""


def enhance_response_with_emotion(response: str, emotion: str) -> str:
    """ Adds emotion-aware Markdown elements to the AI response """
    emotion = (emotion or "neutral").lower()
    # Add detailed enhancement logic back here based on emotion...
    if "stressed" in emotion or "anxious" in emotion or "fearful" in emotion:
        response += "\n\n💡 **Tip**: Don't let anxiety take over. Debugging is a skill of patience. You got this!"
    elif "sad" in emotion:
        response += "\n\n💫 **Keep Going**: Small wins add up. Celebrate the next time a single line of code works!"
    elif "confused" in emotion:
        response += "\n\n🤔 **Need Clarity?**: Just ask me to re-explain the last concept using a different example."
    elif "happy" in emotion:
        response += " 🎉"
    return response


async def generate_groq_stream(client, messages, emotion: str):
    """ Generate streaming response from Groq """
    def sync_groq_call(): # Inner function for executor
        # Ensure the client object passed is the initialized Groq client
        return client.chat.completions.create(
            model="llama-3.1-8b-instant", messages=messages, temperature=0.7,
            stream=True, timeout=TIMEOUT_GROQ
        )
    try:
        # Run the synchronous API call in the executor
        stream = await asyncio.get_event_loop().run_in_executor(
            executor,
            sync_groq_call
        )

        full_response = ""
        # Iterate through the synchronous stream iterator carefully
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_response += content
                # Yield each chunk formatted as Server-Sent Event (SSE)
                yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
            # Give asyncio a chance to breathe within the sync iteration
            await asyncio.sleep(0.001)

        # Enhance the final combined response
        enhanced_response = enhance_response_with_emotion(full_response, emotion)
        # Find the enhancement part added
        final_chunk_content = enhanced_response[len(full_response):]

        # Send the enhancement as a separate content chunk if it exists
        if final_chunk_content:
            yield f"data: {json.dumps({'content': final_chunk_content, 'done': False})}\n\n"
            await asyncio.sleep(0.001) # Small sleep after last content

        # Send the final 'done' signal with metadata
        yield f"data: {json.dumps({'content': '', 'done': True, 'provider': 'groq', 'emotion_used': emotion})}\n\n"

    except Exception as e:
        error_msg = f"Error in Groq stream generation: {str(e)}"
        logger.error(error_msg, exc_info=True) # Log full traceback
        # Send an error signal back to the client
        yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"


async def generate_fallback_stream(message: str, emotion: str):
    """ Generate streaming fallback response """
    emotion = (emotion or "neutral").lower()
    responses = []
    provider = "fallback-neutral"

    # Add detailed fallback responses back here based on emotion...
    if "stressed" in emotion or "anxious" in emotion or "fearful" in emotion:
        responses = [
            "I sense some stress in your tone... ",
            "Let's take this step-by-step and simplify the problem. ",
            "What specific part are you working on right now?",
            "\n\n💡 Remember: Even experienced developers encounter challenges."
        ]
        provider = "fallback-stressed"
    elif "happy" in emotion or "surprised" in emotion:
        responses = [
            "Great! I love that positive energy! ",
            "Tell me what you want to build next — ",
            "let's channel that excitement into something amazing! 🎉"
        ]
        provider = "fallback-happy"
    elif "confused" in emotion:
        responses = [
            "No worries — confusion is just the first step toward understanding. ",
            "Let's break it down together. ",
            "Where did you get stuck? 🤔"
        ]
        provider = "fallback-confused"
    elif "sad" in emotion:
        responses = [
            "I notice you might be feeling down. ",
            "Remember that every developer faces challenges. ",
            "Let's work through this together — ",
            "what's troubling you? 💫"
        ]
        provider = "fallback-sad"
    elif "angry" in emotion or "disgusted" in emotion:
        responses = [
            "I understand this might be frustrating. ",
            "Let's approach this calmly and systematically. ",
            "What specific issue is causing the most trouble?"
        ]
        provider = "fallback-angry"
    else: # neutral or default
        responses = [
            "Thanks for reaching out! ",
            "I'm here to help with your coding questions. ",
            "What would you like to work on today? 😊"
        ]
        provider = "fallback-neutral"

    # Stream each part with delays to simulate typing
    for part in responses:
        yield f"data: {json.dumps({'content': part, 'done': False})}\n\n"
        await asyncio.sleep(0.05) # Small delay for natural typing effect

    # Send the final 'done' signal
    yield f"data: {json.dumps({'content': '', 'done': True, 'provider': provider, 'emotion_used': emotion})}\n\n"
