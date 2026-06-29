"""
Ollama client for single-requirement user story generation.

Simplified version with better error handling for small models.
"""
import json
import logging
from typing import List, Optional, Dict, Any
import requests
from pydantic import ValidationError

from agents.userStory.models import (
    Requirement, 
    RequirementBatch, 
    UserStory,
    OllamaResponse
)

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for Ollama API with single-requirement processing mode."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = 300
        self.project_description = None
        
    def is_available(self) -> bool:
        """Check if Ollama server is running."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def process_batch(self, batch: RequirementBatch, project_description: str = None) -> OllamaResponse:
        """
        Process a batch of requirements using single-requirement mode.
        """
        self.project_description = project_description
        print("[Ollama] 🔄 Processing requirements individually")
        
        all_stories: List[Dict[str, Any]] = []
        failed_requirements = []
        
        print(f"[Ollama] Processing {len(batch.requirements)} requirements")
        
        for i, req in enumerate(batch.requirements, 1):
            print(f"[Ollama] Requirement {req.id} ({i}/{len(batch.requirements)})")
            
            try:
                # Process single requirement - now always returns stories (fallback if needed)
                single_stories = self._process_single_requirement(req, batch.type)
                
                if single_stories:
                    story_dicts = [story.dict() for story in single_stories]
                    all_stories.extend(story_dicts)
                    print(f"[Ollama] ✓ Generated {len(single_stories)} stories for {req.id}")
                else:
                    # This shouldn't happen since fallback is now inside _process_single_requirement
                    failed_requirements.append(req.id)
                    print(f"[Ollama] ⚠️ No stories generated for {req.id}")
                    
            except Exception as e:
                logger.error(f"Error processing requirement {req.id}: {e}")
                failed_requirements.append(req.id)
                print(f"[Ollama] ✗ Exception for {req.id}: {e}")
        
        # Build response
        response_data = {
            "stories": all_stories,
            "batch_id": batch.batch_id,
            "requirement_ids": [req.id for req in batch.requirements],
            "failed_requirements": failed_requirements
        }
        
        print(f"[Ollama] Batch complete: {len(all_stories)} total stories, {len(failed_requirements)} failed")
        
        return OllamaResponse(**response_data)
    
    def _process_single_requirement(self, requirement: Requirement, requirement_type: str) -> List[UserStory]:
        """
        Process a single requirement with extremely simple prompt.
        """
        # Ultra-simple prompt with project context
        project_context = f"Project Context:\n{self.project_description}\n\n" if self.project_description else ""
        
        if requirement_type == "FR":
            prompt = f"""Generate 1-2 user stories from the requirement. Return ONLY valid JSON. Do NOT include explanations or extra text.

{project_context}Requirement:
                {requirement.text}

                Follow STRICT user story structure to satisfy quality evaluation rules.

                User story format:
                As a [role], I want to [single action], so that [specific benefit].

                Rules:
                - Use EXACTLY this structure.
                - Use exactly ONE role.
                - Use exactly ONE action.
                - The action must describe ONE capability only.
                - Do NOT use conjunctions in the action (no "and", "or", "&").
                - Do NOT create multiple features in one story.
                - The benefit must be specific and meaningful.
                - The benefit must NOT contain conjunctions.
                - Do NOT use vague phrases like:
                accomplish my task
                perform my work
                use the system
                improve experience
                handle operations
                - Avoid vague words like:
                very, fast, quickly, some, many, etc
                - Keep the action under 20 words.
                - Keep the benefit short and concrete.
                - Use plain natural language.

                Output JSON format:
                {{"stories":[{{"requirement_id":"{requirement.id}","user_story_id":"US-1","type":"FR","text":"As a [role], I want to [single action], so that [specific benefit]."}}]}}
                """
        else:
            prompt = f"""Generate 1-2 non-functional requirement user stories. Return ONLY valid JSON. Do NOT include explanations or extra text.

{project_context}Requirement:
                {requirement.text}

                Rules:
                - Use one clear system capability per statement.
                - Do NOT combine multiple requirements.
                - Avoid vague terms like:
                very, fast, quickly, some, many, etc
                - Keep the statement precise and measurable if possible.

                Output format:
                {{"stories":[{{"requirement_id":"{requirement.id}","user_story_id":"NFR-1","type":"NFR","text":"The system shall [single specific requirement]."}}]}}
                """
        # Call Ollama API
        response_text = self._call_ollama_api(prompt)
        
        if not response_text or len(response_text.strip()) < 20:
            print(f"[Ollama] Response too short or empty, using fallback")
            return self._generate_fallback_stories(requirement, requirement_type)
        
        # Parse response
        parsed_stories = self._parse_ollama_response(response_text, requirement.id, requirement_type)
        
        # If parsing failed, use fallback
        if not parsed_stories:
            print(f"[Ollama] Parsing failed, using fallback")
            return self._generate_fallback_stories(requirement, requirement_type)
        
        return parsed_stories

    def _generate_fallback_stories(self, requirement: Requirement, requirement_type: str) -> List[UserStory]:
        """
        Generate basic fallback stories when model fails.
        """
        stories = []
        
        if requirement_type == "FR":
            # Create a basic functional story
            story = UserStory(
                requirement_id=requirement.id,
                user_story_id=f"US-1",
                type="FR",
                text=f"As a user, I want {requirement.text.lower()} so that I can accomplish my task."
            )
            stories.append(story)
        else:
            # Create a basic non-functional story
            story = UserStory(
                requirement_id=requirement.id,
                user_story_id=f"NFR-1",
                type="NFR",
                text=f"The system shall {requirement.text.lower()} according to specified requirements."
            )
            stories.append(story)
        
        return stories
    
    def _call_ollama_api(self, prompt: str) -> Optional[str]:
        """Call Ollama API with timeout."""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "max_tokens": 300
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120  # Increased from 30 to 120 seconds
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Ollama API timeout after 120 seconds")
            return None
        except Exception as e:
            logger.error(f"Ollama API error: {str(e)}")
            return None
    
    def _parse_ollama_response(self, response_text: str, requirement_id: str, requirement_type: str = "FR") -> List[UserStory]:
        """
        Parse Ollama response - extremely forgiving parser.
        """
        if not response_text or len(response_text) < 10:
            return []
        
        # Clean the response
        text = response_text.strip()
        
        # Try to find JSON object
        try:
            # Find first { and last }
            start = text.find('{')
            end = text.rfind('}')
            
            if start == -1 or end == -1 or end <= start:
                return []
            
            json_str = text[start:end+1]
            
            # Remove any markdown or extra text
            if json_str.startswith('```json'):
                json_str = json_str[7:]
            if json_str.startswith('```'):
                json_str = json_str[3:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]
            
            json_str = json_str.strip()
            
            # Parse JSON
            data = json.loads(json_str)
            
            # Get stories array - try multiple keys
            stories_data = []
            if isinstance(data, dict):
                stories_data = data.get("stories", [])
                if not stories_data and "user_stories" in data:
                    stories_data = data["user_stories"]
            
            if not stories_data:
                return []
            
            # Convert to UserStory objects
            valid_stories = []
            for idx, story_dict in enumerate(stories_data):
                try:
                    if not isinstance(story_dict, dict):
                        continue
                    
                    # Ensure required fields
                    story_dict["requirement_id"] = requirement_id
                    
                    if "user_story_id" not in story_dict:
                        story_type = story_dict.get("type", requirement_type)
                        story_dict["user_story_id"] = f"{story_type}-{idx+1}"
                    
                    if "type" not in story_dict:
                        story_dict["type"] = "FR"
                    
                    if "text" not in story_dict or not story_dict["text"]:
                        continue
                    
                    story = UserStory(**story_dict)
                    valid_stories.append(story)
                    
                except Exception:
                    continue
            
            return valid_stories
            
        except json.JSONDecodeError:
            return []
        except Exception:
            return []