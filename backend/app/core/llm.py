from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize LLM instances (lazy loading)
_gemini_llm = None
_openai_llm = None


def get_gemini_llm(model: str = None):
    """
    Get Gemini LLM instance
    
    Args:
        model: Model name (defaults to settings.LLM_MODEL)
    
    Returns:
        Gemini LLM instance
    """
    global _gemini_llm
    
    model = model or "gemini-2.5-flash"
    
    if _gemini_llm is not None:
        return _gemini_llm
    
    try:
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not set in environment variables")
        
        _gemini_llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )
        logger.info(f"Initialized Gemini LLM with model: {model}")
        return _gemini_llm
    except Exception as e:
        logger.error(f"Error initializing Gemini LLM: {e}")
        raise


def get_openai_llm(model: str = None):
    """
    Get OpenAI LLM instance
    
    Args:
        model: Model name (defaults to gpt-4o-mini)
    
    Returns:
        OpenAI LLM instance
    """
    global _openai_llm
    
    model = model or settings.LLM_MODEL or "gpt-4o-mini"
    
    if _openai_llm is not None:
        return _openai_llm
    
    try:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in environment variables")
        
        _openai_llm = ChatOpenAI(
            model=model,
            api_key=settings.OPENAI_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )
        logger.info(f"Initialized OpenAI LLM with model: {model}")
        return _openai_llm
    except Exception as e:
        logger.error(f"Error initializing OpenAI LLM: {e}")
        raise


def get_llm(model: str = None, provider: str = None):
    """
    Get LLM instance based on provider setting
    
    Args:
        model: Model name (optional, uses provider default)
        provider: LLM provider - "gemini" or "openai" (defaults to settings.LLM_PROVIDER)
    
    Returns:
        LLM instance (Gemini or OpenAI)
    """
    # Use provided provider or default from settings
    provider = provider or settings.LLM_PROVIDER or "openai"
    
    logger.info(f"Getting LLM with provider: {provider}")
    
    if provider.lower() == "gemini":
        return get_gemini_llm(model)
    elif provider.lower() == "openai":
        return get_openai_llm(model)
    else:
        logger.warning(f"Unknown provider '{provider}', defaulting to OpenAI")
        return get_openai_llm(model)


def reset_llm():
    """Reset LLM instances (useful for switching providers)"""
    global _gemini_llm, _openai_llm
    _gemini_llm = None
    _openai_llm = None
    logger.info("Reset all LLM instances")

