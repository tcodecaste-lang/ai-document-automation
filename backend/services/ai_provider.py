# backend/services/ai_provider.py

import os
import re
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from openai import OpenAI
from fastapi import HTTPException, status
from backend.config.industries import INDUSTRIES

logger = logging.getLogger("ai_provider")
# Set logging level to INFO to ensure printout
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class RecoverableProviderError(Exception):
    """Exception raised for rate limits, quota issues, or transient provider errors."""
    def __init__(self, message: str, cooldown_seconds: int = 60):
        super().__init__(message)
        self.cooldown_seconds = cooldown_seconds

class AIProvider:
    def extract(self, industry: str, text: str, response_schema: dict, system_prompt: str, user_prompt: str) -> dict:
        raise NotImplementedError()

class GeminiProvider(AIProvider):
    def get_client_and_model(self) -> tuple[OpenAI, str]:
        gemini_key = os.environ.get("GEMINI_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")
        
        api_key = None
        is_gemini = False
        
        if gemini_key:
            api_key = gemini_key
            is_gemini = True
        elif openai_key:
            api_key = openai_key
            if openai_key.strip().startswith("AIzaSy"):
                is_gemini = True
                
        if not api_key:
            # Configuration/Application error: do NOT make it a recoverable error
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gemini/OpenAI API key is missing. Please set GEMINI_API_KEY in backend/.env."
            )
            
        if is_gemini:
            client = OpenAI(
                api_key=api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            model_name = "gemini-3.5-flash"
        else:
            client = OpenAI(api_key=api_key)
            model_name = "gpt-4o-mini"
            
        return client, model_name

    def extract(self, industry: str, text: str, response_schema: dict, system_prompt: str, user_prompt: str) -> dict:
        try:
            client, model_name = self.get_client_and_model()
            logger.info("[AI] Gemini request started")
            
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": response_schema
                },
                temperature=0.0,
                timeout=30.0
            )
            
            raw_content = response.choices[0].message.content
            if not raw_content:
                raise RecoverableProviderError("Gemini returned an empty response.", cooldown_seconds=60)
                
            extracted_data = json.loads(raw_content)
            logger.info("[AI] Gemini request successful")
            return extracted_data
            
        except Exception as e:
            # Check if this error is recoverable (429, timeout, transient network)
            self._handle_exception(e)

    def _handle_exception(self, e: Exception):
        err_msg = str(e)
        logger.error(f"[AI] Gemini request failed: {err_msg}")
        
        # Check standard HTTP status codes via openai API error
        from openai import RateLimitError, APIConnectionError, APITimeoutError, APIStatusError
        
        cooldown = 60
        is_recoverable = False
        
        if isinstance(e, RateLimitError):
            is_recoverable = True
            cooldown = self._parse_reset_headers(e)
            logger.warning("[AI] Gemini quota/rate limit reached")
        elif isinstance(e, APITimeoutError) or isinstance(e, APIConnectionError):
            is_recoverable = True
            logger.warning("[AI] Gemini connection/timeout error detected")
        elif isinstance(e, APIStatusError):
            # Do NOT fall back for 400 (bad request), 401 (unauthorized), 403 (forbidden)
            if e.status_code in [429, 500, 502, 503, 504]:
                is_recoverable = True
                cooldown = self._parse_reset_headers(e)
                if e.status_code == 429:
                    logger.warning("[AI] Gemini quota/rate limit reached")
            else:
                # Configuration or request format errors (400, 401, 403) -> propagate directly
                raise HTTPException(
                    status_code=e.status_code,
                    detail=f"Gemini API request failed with configuration error: {err_msg}"
                )
        elif "quota" in err_msg.lower() or "limit" in err_msg.lower() or "exhausted" in err_msg.lower() or "rate" in err_msg.lower() or "resource_exhausted" in err_msg.lower():
            is_recoverable = True
            logger.warning("[AI] Gemini quota/rate limit reached")
            
        if is_recoverable:
            raise RecoverableProviderError(f"Gemini encountered a recoverable error: {err_msg}", cooldown_seconds=cooldown)
        
        # Propagate programming, format, or credential errors directly
        raise e

    def _parse_reset_headers(self, e: Exception) -> int:
        if hasattr(e, "response") and e.response is not None:
            headers = e.response.headers
            
            # 1. retry-after
            retry_after = headers.get("retry-after")
            if retry_after:
                try:
                    return int(retry_after)
                except ValueError:
                    pass
            
            # 2. x-ratelimit-reset
            reset_time = headers.get("x-ratelimit-reset")
            if reset_time:
                try:
                    val = float(reset_time)
                    if val > 1600000000:
                        diff = val - time.time()
                        if diff > 0:
                            return int(diff)
                except ValueError:
                    seconds = 0
                    match_s = re.search(r'([\d.]+)\s*s', reset_time)
                    match_m = re.search(r'(\d+)\s*m', reset_time)
                    match_h = re.search(r'(\d+)\s*h', reset_time)
                    if match_s:
                        seconds += float(match_s.group(1))
                    if match_m:
                        seconds += int(match_m.group(1)) * 60
                    if match_h:
                        seconds += int(match_h.group(1)) * 3600
                    if seconds > 0:
                        return int(seconds)
                        
        return 60  # default rate-limit cooldown seconds

class GroqProvider(AIProvider):
    def get_client_and_model(self) -> tuple[OpenAI, str]:
        groq_key = os.environ.get("GROQ_API_KEY")
        if not groq_key or groq_key.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Groq API key is missing. Please set GROQ_API_KEY in backend/.env."
            )
            
        client = OpenAI(
            api_key=groq_key,
            base_url="https://api.groq.com/openai/v1"
        )
        # Using Llama 3.3 70B as standard fallback
        return client, "llama-3.3-70b-specdec"

    def extract(self, industry: str, text: str, response_schema: dict, system_prompt: str, user_prompt: str) -> dict:
        try:
            client, model_name = self.get_client_and_model()
            logger.info("[AI] Groq request started")
            
            # Groq fully supports structured output json_schema
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": response_schema
                },
                temperature=0.0,
                timeout=30.0
            )
            
            raw_content = response.choices[0].message.content
            if not raw_content:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Groq returned an empty response."
                )
                
            extracted_data = json.loads(raw_content)
            logger.info("[AI] Groq request successful")
            return extracted_data
            
        except Exception as e:
            logger.error(f"[AI] Groq request failed: {str(e)}")
            raise e

class AIProviderManager:
    _gemini_status = "AVAILABLE"
    _gemini_cooldown_until: Optional[datetime] = None
    
    _gemini_provider = GeminiProvider()
    _groq_provider = GroqProvider()
    
    @classmethod
    def mark_gemini_unavailable(cls, cooldown_seconds: int):
        cls._gemini_status = "TEMPORARILY_UNAVAILABLE"
        cls._gemini_cooldown_until = datetime.utcnow() + timedelta(seconds=cooldown_seconds)
        logger.warning(f"[AI] Gemini marked TEMPORARILY_UNAVAILABLE until {cls._gemini_cooldown_until.isoformat()} UTC (cooldown: {cooldown_seconds}s)")

    @classmethod
    def mark_gemini_available(cls):
        cls._gemini_status = "AVAILABLE"
        cls._gemini_cooldown_until = None
        logger.info("[AI] Gemini marked AVAILABLE")

    @classmethod
    def is_gemini_available(cls) -> bool:
        if cls._gemini_status == "TEMPORARILY_UNAVAILABLE":
            if cls._gemini_cooldown_until and datetime.utcnow() > cls._gemini_cooldown_until:
                logger.info("[AI] Gemini cooldown reset window elapsed. Eligible for retry.")
                return True
            return False
        return True

    @classmethod
    def extract(cls, industry: str, text: str, response_schema: dict, system_prompt: str, user_prompt: str) -> dict:
        # Step 1: Detect Primary availability
        use_gemini = cls.is_gemini_available()
        
        if use_gemini:
            logger.info("[AI] Primary provider: Gemini")
            try:
                result = cls._gemini_provider.extract(industry, text, response_schema, system_prompt, user_prompt)
                
                # Cooldown switchback: if it was TEMPORARILY_UNAVAILABLE but succeeded now, reset status
                if cls._gemini_status == "TEMPORARILY_UNAVAILABLE":
                    logger.info("[AI] Gemini retry successful")
                    logger.info("[AI] Switching primary provider back to Gemini")
                    cls.mark_gemini_available()
                    
                return result
            except RecoverableProviderError as rpe:
                logger.warning(f"[AI] Gemini recoverable failure. Cooldown seconds: {rpe.cooldown_seconds}")
                cls.mark_gemini_unavailable(rpe.cooldown_seconds)
                logger.warning("[AI] Switching to fallback provider: Groq")
                
                # Attempt fallback immediately
                try:
                    return cls._groq_provider.extract(industry, text, response_schema, system_prompt, user_prompt)
                except Exception as groq_err:
                    logger.error(f"[AI] Both Gemini and Groq providers failed.")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="AI processing is temporarily unavailable. Please try again later."
                    )
        else:
            logger.info("[AI] Gemini is cooling down. Routing request directly to Groq fallback.")
            try:
                return cls._groq_provider.extract(industry, text, response_schema, system_prompt, user_prompt)
            except Exception as groq_err:
                logger.error(f"[AI] Fallback Groq provider failed during Gemini cooldown.")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="AI processing is temporarily unavailable. Please try again later."
                )
