"""
OpenRouter API client for user story generation.
"""
import json
import time
import logging
from typing import Optional, Dict, Any
import requests

from agents.userStory.models import RequirementBatch, OpenRouterResponse
from agents.userStory import config

logger = logging.getLogger(__name__)


class GPT4Client:
    """Client for OpenRouter API."""
    
    def __init__(self, api_key: str, model: str = None, project_description: str = None):
        self.api_key = api_key
        self.model = model or config.GPT_MODEL
        self.base_url = config.OPENROUTER_URL
        self.timeout = 300
        self.project_description = project_description
        
    def process_batch(self, batch: RequirementBatch) -> OpenRouterResponse:
        """
        Process a batch of requirements through OpenRouter.
        """
        prompt = self._build_batch_prompt(batch)
        
        response_text = self._call_openrouter_api(prompt)
        
        if not response_text:
            raise RuntimeError("OpenRouter API returned empty response")
        
        return self._parse_response(response_text, batch)
    
    def _build_batch_prompt(self, batch: RequirementBatch) -> str:
        """Build prompt for batch processing."""
        
        # Add project context if available
        project_context = f"Project Context:\n{self.project_description}\n\n" if self.project_description else ""
        
        if batch.type == "FR":
            system_prompt = f"""You are a business analyst generating user stories for multiple functional requirements.
{project_context}For each requirement, generate 1-3 user stories.
                Output must be valid JSON with EXACTLY this structure - the top-level key MUST be "stories":
                {{
                "stories": [
                    {{
                    "requirement_id": "R1",
                    "user_story_id": "US-1",
                    "type": "FR",
                    "text": "As a [role], I want to [action] so that [benefit]."
                    }}
                ]
                }}

                Requirements to process:"""
        else:
            system_prompt = f"""You are a business analyst generating user stories for multiple non-functional requirements.
{project_context}For each requirement, generate 1-3 user stories.
                Output must be valid JSON with EXACTLY this structure - the top-level key MUST be "stories":
                {{
                "stories": [
                    {{
                    "requirement_id": "R1",
                    "user_story_id": "US-1",
                    "type": "NFR",
                    "text": "As a [role], I want to [action] so that [benefit]."
                    }}
                ]
                }}

                Requirements to process:"""
        
        # Add requirements to prompt
        requirements_text = ""
        for req in batch.requirements:
            requirements_text += f"\n{req.id}: {req.text}\n"
        
        prompt = f"""{system_prompt}
{requirements_text}

Generate user stories for these requirements. Return ONLY the JSON object:"""
        
        return prompt
    
    def _call_openrouter_api(self, prompt: str) -> Optional[str]:
        """Call OpenRouter API with the prompt."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Add optional headers if configured
            if config.OPENROUTER_HTTP_REFERER:
                headers["HTTP-Referer"] = config.OPENROUTER_HTTP_REFERER
            if config.OPENROUTER_X_TITLE:
                headers["X-Title"] = config.OPENROUTER_X_TITLE
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": config.FR_MAX_RESPONSE_TOKENS if "FR" in prompt else config.MAX_RESPONSE_TOKENS,
                "temperature": 0.3,
                "response_format": {"type": "json_object"}
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"OpenRouter API error: {str(e)}")
            return None
    
    def _parse_response(self, response_text: str, batch: RequirementBatch) -> OpenRouterResponse:
        """Parse OpenRouter response."""
        try:
            # Try to parse JSON
            data = json.loads(response_text)
            
            # Ensure stories field exists
            if "stories" not in data:
                data = {"stories": data.get("user_stories", [])}
            
            return OpenRouterResponse(
                stories=data.get("stories", []),
                batch_id=batch.batch_id,
                requirement_ids=[req.id for req in batch.requirements]
            )
            
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON from OpenRouter: {e}")