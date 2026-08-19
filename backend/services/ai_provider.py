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

    def _handle_exception(self, e: Exception, provider_name: str):
        err_msg = str(e)
        logger.error(f"[AI] {provider_name} request failed: {err_msg}")
        
        # Check standard HTTP status codes via openai API error
        from openai import RateLimitError, APIConnectionError, APITimeoutError, APIStatusError
        
        cooldown = 60
        is_recoverable = False
        
        if isinstance(e, RateLimitError):
            is_recoverable = True
            cooldown = self._parse_reset_headers(e)
            logger.warning(f"[AI] {provider_name} quota/rate limit reached")
        elif isinstance(e, APITimeoutError) or isinstance(e, APIConnectionError):
            is_recoverable = True
            logger.warning(f"[AI] {provider_name} connection/timeout error detected")
        elif isinstance(e, APIStatusError):
            # Do NOT fall back for 400 (bad request), 401 (unauthorized), 403 (forbidden)
            if e.status_code in [429, 500, 502, 503, 504]:
                is_recoverable = True
                cooldown = self._parse_reset_headers(e)
                if e.status_code == 429:
                    logger.warning(f"[AI] {provider_name} quota/rate limit reached")
            else:
                # Configuration or request format errors (400, 401, 403) -> propagate directly
                raise HTTPException(
                    status_code=e.status_code,
                    detail=f"{provider_name} API request failed with configuration error: {err_msg}"
                )
        elif "quota" in err_msg.lower() or "limit" in err_msg.lower() or "exhausted" in err_msg.lower() or "rate" in err_msg.lower() or "resource_exhausted" in err_msg.lower():
            is_recoverable = True
            logger.warning(f"[AI] {provider_name} quota/rate limit reached")
            
        if is_recoverable:
            raise RecoverableProviderError(f"{provider_name} encountered a recoverable error: {err_msg}", cooldown_seconds=cooldown)
        
        # Propagate programming, format, or credential errors directly
        raise e

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
        client, initial_model = self.get_client_and_model()
        
        is_gemini_api = False
        if hasattr(client, "base_url") and "generativelanguage" in str(client.base_url):
            is_gemini_api = True
            
        models_to_try = [initial_model]
        if is_gemini_api:
            # Real valid Gemini model names - ordered by preference (newest/best first)
            models_to_try = [
                "gemini-2.5-flash",          # Latest & fastest
                "gemini-2.0-flash",          # Stable previous gen
                "gemini-1.5-flash",          # Widely available fallback
                "gemini-1.5-pro",            # High intelligence fallback
            ]
            
        last_exception = None
        for model in models_to_try:
            try:
                logger.info(f"[AI] Gemini attempting model: {model}")
                response = client.chat.completions.create(
                    model=model,
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
                    raise RecoverableProviderError(f"Gemini model {model} returned an empty response.", cooldown_seconds=60)
                    
                extracted_data = json.loads(raw_content)
                if isinstance(extracted_data, dict):
                    extracted_data["ai_provider"] = "Gemini"
                logger.info(f"[AI] Gemini request successful with model: {model}")
                return extracted_data
            except Exception as e:
                err_msg = str(e).lower()
                is_quota = "quota" in err_msg or "limit" in err_msg or "exhausted" in err_msg or "rate" in err_msg or "resource_exhausted" in err_msg or "429" in err_msg
                is_model_invalid = "not found" in err_msg or "does not exist" in err_msg or "invalid model" in err_msg or "404" in err_msg
                if (is_quota or is_model_invalid) and len(models_to_try) > 1:
                    reason = "rate limit/quota" if is_quota else "model not found"
                    logger.warning(f"[AI] Gemini model {model} skipped ({reason}). Trying next...")
                    last_exception = e
                    continue
                else:
                    self._handle_exception(e, "Gemini")
                    
        if last_exception:
            # If we exhausted all models (due to rate limits or 404 not found), 
            # we must raise RecoverableProviderError to trigger Groq fallback,
            # instead of letting _handle_exception raise a fatal HTTPException.
            logger.warning(f"[AI] All Gemini models failed. Last error: {str(last_exception)}. Falling back to Groq...")
            raise RecoverableProviderError(f"All Gemini models failed: {str(last_exception)}", cooldown_seconds=60)
        else:
            raise RecoverableProviderError("All Gemini models failed to respond.", cooldown_seconds=60)

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
        return client, "llama-3.3-70b-versatile"

    def extract(self, industry: str, text: str, response_schema: dict, system_prompt: str, user_prompt: str) -> dict:
        try:
            client, model_name = self.get_client_and_model()
            logger.info("[AI] Groq request started")
            
            schema_instruction = f"\n\nYou MUST return a JSON object strictly matching this JSON schema structure:\n{json.dumps(response_schema.get('schema', response_schema))}"
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt + schema_instruction},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={
                    "type": "json_object"
                },
                temperature=0.0,
                timeout=30.0
            )
            
            raw_content = response.choices[0].message.content
            if not raw_content:
                raise RecoverableProviderError("Groq returned an empty response.", cooldown_seconds=60)
                
            extracted_data = json.loads(raw_content)
            if isinstance(extracted_data, dict):
                extracted_data["ai_provider"] = "Groq"
            logger.info("[AI] Groq request successful")
            return extracted_data
            
        except Exception as e:
            self._handle_exception(e, "Groq")

class MistralProvider(AIProvider):
    def get_client_and_model(self) -> tuple[OpenAI, str]:
        mistral_key = os.environ.get("MISTRAL_API_KEY")
        if not mistral_key or mistral_key.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Mistral API key is missing. Please set MISTRAL_API_KEY in backend/.env."
            )
            
        client = OpenAI(
            api_key=mistral_key,
            base_url="https://api.mistral.ai/v1"
        )
        return client, "mistral-large-latest"

    def extract(self, industry: str, text: str, response_schema: dict, system_prompt: str, user_prompt: str) -> dict:
        try:
            client, model_name = self.get_client_and_model()
            logger.info("[AI] Mistral request started")
            
            schema_instruction = f"\n\nYou MUST return a JSON object strictly matching this JSON schema structure:\n{json.dumps(response_schema.get('schema', response_schema))}"
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt + schema_instruction},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={
                    "type": "json_object"
                },
                temperature=0.0,
                timeout=30.0
            )
            
            raw_content = response.choices[0].message.content
            if not raw_content:
                raise RecoverableProviderError("Mistral returned an empty response.", cooldown_seconds=60)
                
            extracted_data = json.loads(raw_content)
            if isinstance(extracted_data, dict):
                extracted_data["ai_provider"] = "Mistral"
            logger.info("[AI] Mistral request successful")
            return extracted_data
            
        except Exception as e:
            self._handle_exception(e, "Mistral")

class AIProviderManager:
    _gemini_status = "AVAILABLE"
    _gemini_cooldown_until: Optional[datetime] = None
    
    _groq_status = "AVAILABLE"
    _groq_cooldown_until: Optional[datetime] = None
    
    _gemini_provider = GeminiProvider()
    _groq_provider = GroqProvider()
    _mistral_provider = MistralProvider()
    
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
    def mark_groq_unavailable(cls, cooldown_seconds: int):
        cls._groq_status = "TEMPORARILY_UNAVAILABLE"
        cls._groq_cooldown_until = datetime.utcnow() + timedelta(seconds=cooldown_seconds)
        logger.warning(f"[AI] Groq marked TEMPORARILY_UNAVAILABLE until {cls._groq_cooldown_until.isoformat()} UTC (cooldown: {cooldown_seconds}s)")

    @classmethod
    def mark_groq_available(cls):
        cls._groq_status = "AVAILABLE"
        cls._groq_cooldown_until = None
        logger.info("[AI] Groq marked AVAILABLE")

    @classmethod
    def is_groq_available(cls) -> bool:
        if cls._groq_status == "TEMPORARILY_UNAVAILABLE":
            if cls._groq_cooldown_until and datetime.utcnow() > cls._groq_cooldown_until:
                logger.info("[AI] Groq cooldown reset window elapsed. Eligible for retry.")
                return True
            return False
        return True

    @classmethod
    def extract(cls, industry: str, text: str, response_schema: dict, system_prompt: str, user_prompt: str) -> dict:
        # Step 1: Detect Gemini availability
        use_gemini = cls.is_gemini_available()
        
        if use_gemini:
            logger.info("[AI] Primary provider: Gemini")
            try:
                result = cls._gemini_provider.extract(industry, text, response_schema, system_prompt, user_prompt)
                
                # Cooldown switchback if Gemini recovered
                if cls._gemini_status == "TEMPORARILY_UNAVAILABLE":
                    logger.info("[AI] Gemini retry successful")
                    logger.info("[AI] Switching primary provider back to Gemini")
                    cls.mark_gemini_available()
                    
                return result
            except RecoverableProviderError as rpe:
                logger.warning(f"[AI] Gemini recoverable failure: {str(rpe)}. Cooldown seconds: {rpe.cooldown_seconds}")
                cls.mark_gemini_unavailable(rpe.cooldown_seconds)
                logger.warning("[AI] Switching to fallback provider: Groq")
                # Fall through to try Groq fallback
        else:
            logger.info("[AI] Gemini is cooling down. Trying fallback: Groq")
            
        # Step 2: Try Groq availability
        use_groq = cls.is_groq_available()
        if use_groq:
            logger.info("[AI] Try provider: Groq")
            try:
                result = cls._groq_provider.extract(industry, text, response_schema, system_prompt, user_prompt)
                
                # Cooldown switchback if Groq recovered
                if cls._groq_status == "TEMPORARILY_UNAVAILABLE":
                    logger.info("[AI] Groq retry successful")
                    logger.info("[AI] Resetting Groq fallback status to AVAILABLE")
                    cls.mark_groq_available()
                    
                return result
            except RecoverableProviderError as rpe:
                logger.warning(f"[AI] Groq recoverable failure: {str(rpe)}. Cooldown seconds: {rpe.cooldown_seconds}")
                cls.mark_groq_unavailable(rpe.cooldown_seconds)
                logger.warning("[AI] Switching to second fallback provider: Mistral")
                # Fall through to try Mistral fallback
        else:
            logger.info("[AI] Groq is cooling down. Trying second fallback: Mistral")
            
        # Step 3: Try Mistral fallback
        logger.info("[AI] Try provider: Mistral")
        try:
            return cls._mistral_provider.extract(industry, text, response_schema, system_prompt, user_prompt)
        except Exception as mistral_err:
            logger.error(f"[AI] All providers (Gemini, Groq, Mistral) failed.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI processing is temporarily unavailable. Please try again later."
            )
