from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize LLM (lazy loading)
_llm = None


def get_llm():
    """Lazy load LLM"""
    global _llm
    if _llm is None:
        try:
            _llm = ChatGoogleGenerativeAI(
                model=settings.LLM_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS
            )
            logger.info(f"Initialized LLM with model: {settings.LLM_MODEL}")
        except Exception as e:
            logger.error(f"Error initializing LLM: {e}")
            # Fallback to gemini-1.5-pro
            _llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-pro",
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS
            )
            logger.info("Using fallback model: gemini-1.5-pro")
    return _llm
