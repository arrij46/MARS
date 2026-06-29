"""
File handling utilities for user story pipeline.
"""
import json
from pathlib import Path
from typing import Any, Dict

from agents.userStory.models import RequirementsInput, UserStoriesOutput


class FileHandler:
    """Handles file operations for the pipeline."""
    
    def read_requirements(self, file_path: str) -> RequirementsInput:
        """Read and parse requirements from JSON file."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Requirements file not found: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"Loaded JSON from {file_path}")
        
        # Handle different input formats
        if isinstance(data, dict) and "requirements" in data:
            requirements_data = data["requirements"]
        elif isinstance(data, list):
            requirements_data = data
        else:
            raise ValueError(f"Unexpected JSON format in {file_path}")
        
        # Convert to Requirement objects
        from agents.userStory.models import Requirement
        requirements = []
        for req_data in requirements_data:
            if isinstance(req_data, dict):
                req = Requirement(**req_data)
                requirements.append(req)
            else:
                raise ValueError(f"Invalid requirement format: {req_data}")
        
        print(f"Successfully loaded {len(requirements)} requirements")
        return RequirementsInput(requirements=requirements)
    
    def write_user_stories(self, file_path: str, output: UserStoriesOutput):
        """Write user stories to JSON file."""
        path = Path(file_path)
        
        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict and write
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(output.dict(), f, indent=2, ensure_ascii=False)
        
        print(f"Successfully wrote output to {file_path}")