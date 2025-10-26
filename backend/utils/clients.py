# backend/utils/clients.py
import os
import logging
from dotenv import load_dotenv

# Load .env variables specifically for client initialization if needed
# Make sure this runs before any client is accessed
load_dotenv(dotenv_path="backend/.env")

logger = logging.getLogger("backend.clients")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

groq_client = None

def get_groq_client():
    """
    Initializes and returns the Groq client instance.
    Lazy loads the client upon first request.
    """
    global groq_client
    if not groq_client and GROQ_API_KEY:
        try:
            from groq import Groq
            logger.info("Initializing Groq client...")
            groq_client = Groq(api_key=GROQ_API_KEY)
            logger.info("Groq client initialized successfully.")
        except ImportError:
             logger.error("Groq library not installed. Cannot initialize client.")
             groq_client = None
        except Exception as e:
            logger.error(f"Groq client initialization failed: {e}")
            groq_client = None
    elif not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not found in environment variables. Groq client cannot be initialized.")
        groq_client = None

    return groq_client

# Optional: Initialize Ollama client here too if needed elsewhere
# try:
#     import ollama
#     # ollama_client = ollama.Client(...) # Example
# except ImportError:
#     ollama = None
#     logger.warning("Ollama library not installed.")
