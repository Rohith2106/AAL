from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize LLM (lazy loading)
_llm = None


def get_llm(model: str = None):
    """
    Get LLM instance (Gemini only)
    
    Args:
        model: Model name (defaults to settings.LLM_MODEL)
    
    Returns:
        LLM instance
    """
    global _llm
    
    # Use provided model or default from settings
    model = model or settings.LLM_MODEL or "gemini-2.5-flash"
    
    # If same model is already initialized, return it
    if _llm is not None:
        return _llm
    
    try:
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not set in environment variables")
        
        _llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )
        logger.info(f"Initialized Gemini LLM with model: {model}")
        return _llm
    except Exception as e:
        logger.error(f"Error initializing LLM: {e}")
        raise
