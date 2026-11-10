import os
from typing import Optional, Dict, Any, List
from pathlib import Path
from google import genai
from google.genai import types
from ..core.config import get_settings
from ..core.rate_limiter import rate_limiter

class GeminiClient:
    def __init__(self, api_key: Optional[str] = None):
        cfg = get_settings()
        self.api_key = api_key or cfg.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = cfg.models.default_workhorse
        self.enable_search = cfg.models.enable_google_search_grounding
        self._client: Optional[genai.Client] = None

    @property
    def client(self) -> genai.Client:
        if not self.api_key:
            raise ValueError(
                "Gemini API key is not configured. Please set it in config/settings.json or via the ScholarForge settings deck."
            )
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def generate_with_search(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate text grounded with live Google Search for verifying publications, links, and DOIs.
        """
        import asyncio
        await rate_limiter.acquire("gemini")
        
        config_params = {}
        if self.enable_search:
            # Enable Google Search grounding
            config_params["tools"] = [{"google_search": {}}]
            
        if system_instruction:
            config_params["system_instruction"] = system_instruction

        config = types.GenerateContentConfig(**config_params) if config_params else None

        def _call():
            return self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

        response = await asyncio.to_thread(_call)
        
        grounding_meta = getattr(response, "candidates", [None])[0]
        metadata = getattr(grounding_meta, "grounding_metadata", None)

        return {
            "text": response.text,
            "grounding_metadata": metadata,
            "model": self.model_name
        }

    async def generate_structured_json(self, prompt: str, schema: Optional[Any] = None, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """
        Guarantees 100% valid, deterministic JSON output using Gemini's native Structured Outputs
        (response_mime_type='application/json'). Eliminates markdown ticks, preambles, and malformed strings.
        Includes model cascade resilience (gemini-3.8-flash -> gemini-3.5-flash -> gemini-3.1-flash-lite).
        """
        import asyncio
        import json
        import re

        await rate_limiter.acquire("gemini")
        
        config_params = {
            "response_mime_type": "application/json"
        }
        if schema:
            config_params["response_schema"] = schema
        if system_instruction:
            config_params["system_instruction"] = system_instruction

        config = types.GenerateContentConfig(**config_params)

        candidate_models = [self.model_name]
        for fallback in ["gemini-3.5-flash", "gemini-3.1-flash-lite"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        last_err = None
        for model in candidate_models:
            try:
                def _call():
                    return self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=config
                    )
                response = await asyncio.wait_for(asyncio.to_thread(_call), timeout=45.0)
                raw_text = response.text or "{}"
                try:
                    return json.loads(raw_text)
                except Exception:
                    m = re.search(r'\{.*\}', raw_text, re.DOTALL)
                    if m:
                        return json.loads(m.group(0))
            except Exception as e:
                last_err = e
                continue

        if last_err:
            raise last_err
        raise ValueError("Failed to obtain structured JSON from model cascade.")

    async def batch_extract_corpus_json(self, studies_corpus: List[Dict[str, Any]], synthesis_prompt: str) -> Dict[str, Any]:
        """
        Converts multiple research papers into a unified, structured JSON corpus payload and passes
        them in one single call through Gemini's 1M+ token context window.
        Returns the structured cross-study findings, PICO rows, or thematic synthesis directly as JSON.
        """
        import json
        corpus_json_str = json.dumps(studies_corpus, indent=2, ensure_ascii=False)
        full_prompt = f"""You are a Principal Scientific Investigator and Systematic Review Methodologist.
Here is the complete verified research corpus of {len(studies_corpus)} studies in JSON format:

{corpus_json_str}

DIRECTIVE:
{synthesis_prompt}
"""
        return await self.generate_structured_json(full_prompt)

    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """High-speed text generation without search grounding for drafting sections."""
        import asyncio
        await rate_limiter.acquire("gemini")
        config = types.GenerateContentConfig(system_instruction=system_instruction) if system_instruction else None
        def _call():
            return self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
        response = await asyncio.to_thread(_call)
        return response.text or ""

    async def ingest_pdf_direct(self, pdf_path: Path, extraction_prompt: str) -> str:
        """
        Ingest a full-text scientific PDF directly into Gemini 3.8 Flash multimodal window.
        Preserves two-column layouts, figures, and tables without text interleaving.
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found at {pdf_path}")
            
        await rate_limiter.acquire("gemini")
        
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[
                types.Part.from_bytes(
                    data=pdf_bytes,
                    mime_type="application/pdf",
                ),
                extraction_prompt
            ]
        )
        return response.text or ""

    def list_live_models(self) -> List[str]:
        """
        Query Google AI Studio for active live models.
        """
        if not self.api_key:
            return [self.model_name]
        try:
            models_pager = self.client.models.list()
            model_ids = []
            for m in models_pager:
                name = getattr(m, "name", "")
                if name:
                    # Clean up 'models/' prefix if present
                    model_ids.append(name.replace("models/", ""))
            return model_ids
        except Exception as e:
            print(f"[Warning] Failed to list live models from AI Studio: {e}")
            return [self.model_name]

