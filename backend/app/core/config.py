from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union, Optional
import json


class Settings(BaseSettings):
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Google Gemini API
    GOOGLE_API_KEY: Optional[str] = None
    
    # OpenAI API
    OPENAI_API_KEY: Optional[str] = None
    
    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "accounting_automation"
    
    # SQL Database
    DATABASE_URL: str = "mysql+pymysql://root:1234@localhost:3306/ledger_db"
    
    # CORS - can be comma-separated string or JSON array in .env
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://localhost:3000"
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from env variable"""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            # Try JSON first
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            # Fall back to comma-separated string
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    # LLM Settings
    LLM_PROVIDER: str = "openai"  # "gemini" or "openai"
    LLM_MODEL: str = "gpt-4o-mini"  # Default model for the selected provider
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096
    
    # OCR Settings
    OCR_ENGINE: str = "tesseract"  # tesseract or easyocr

    # Our company configuration (used for perspective-aware analysis)
    OUR_COMPANY_NAME: Optional[str] = None
    
    # JWT Secret Key (for HS256 algorithm - symmetric key, not public/private keys)
    SECRET_KEY: str = "your-secret-key-change-in-production-use-a-random-string-here"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env file


settings = Settings()

