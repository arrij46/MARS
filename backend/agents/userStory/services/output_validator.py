"""
Output validation service for user story generation.

Handles validation of LLM outputs against global requirements,
aggregation of stories across batches, and completeness checking.
"""
from typing import List, Dict, Set, Optional, Any, Union
from collections import defaultdict

from agents.userStory import config
from agents.userStory.models import UserStory, Requirement, RequirementBatch, OllamaResponse, OpenRouterResponse


class OutputValidator:
    """Validates and aggregates user story outputs."""
    
    def __init__(self, strict: bool = True):
        self.strict = strict
        self.global_requirement_ids: Set[str] = set()
        self.global_requirements: List[Requirement] = []
        
    def set_global_requirements(self, requirements: List[Requirement]):
        """Set global requirements for validation."""
        self.global_requirements = requirements
        self.global_requirement_ids = {req.id for req in requirements}
        print(f"[OutputValidator] Global requirement set: {len(self.global_requirement_ids)} unique IDs")
    
    def validate_batch_output(
        self,
        batch: RequirementBatch,
        response_data: Union[dict, OpenRouterResponse, OllamaResponse],
        batch_index: int = None
    ) -> List[UserStory]:
        """
        Validate batch output from LLM.
        
        Returns empty list if validation fails but graceful fallback is enabled.
        """
        try:
            # Handle different response types
            if hasattr(response_data, 'stories'):
                # It's an OpenRouterResponse or OllamaResponse object
                stories_data = response_data.stories
            elif isinstance(response_data, dict):
                # It's a dict
                stories_data = response_data.get("stories", [])
            else:
                print(f"[OutputValidator] ⚠️ Unknown response type: {type(response_data)}")
                return []
            
            print(f"[OutputValidator] Batch {batch.batch_id}: Validating {len(stories_data) if stories_data else 0} stories")
            
            if not stories_data:
                print(f"[OutputValidator] ⚠️ Batch {batch.batch_id} returned no stories")
                return []
            
            # Convert to UserStory objects
            user_stories = []
            for i, story_data in enumerate(stories_data):
                try:
                    # Handle if story_data is already a UserStory object
                    if isinstance(story_data, UserStory):
                        story = story_data
                    elif isinstance(story_data, dict):
                        story = UserStory(**story_data)
                    else:
                        print(f"[OutputValidator] ⚠️ Story at index {i} has invalid type: {type(story_data)}")
                        continue
                    
                    # Validate requirement_id exists in global set
                    if story.requirement_id not in self.global_requirement_ids:
                        print(f"[OutputValidator] ⚠️ Story references requirement '{story.requirement_id}' which is not in project. Skipping.")
                        continue
                    
                    # Validate story text is not empty
                    if not story.text or story.text.strip() == "":
                        print(f"[OutputValidator] ⚠️ Story has empty text. Skipping.")
                        continue
                    
                    # Validate user_story_id format (basic check)
                    if not story.user_story_id or len(story.user_story_id.strip()) == 0:
                        print(f"[OutputValidator] ⚠️ Story missing user_story_id. Skipping.")
                        continue
                    
                    user_stories.append(story)
                    
                except Exception as e:
                    print(f"[OutputValidator] ⚠️ Invalid story at index {i}: {e}")
                    if self.strict and not config.ENABLE_GRACEFUL_FALLBACK:
                        raise
                    continue
            
            # Log validation summary
            stories_by_req = defaultdict(list)
            for story in user_stories:
                stories_by_req[story.requirement_id].append(story)
            
            print(f"[OutputValidator] ✓ Batch {batch.batch_id}: Validated {len(user_stories)} stories across {len(stories_by_req)} requirements")
            
            return user_stories
            
        except Exception as e:
            print(f"[OutputValidator] ✗ Batch {batch.batch_id} validation failed: {e}")
            
            # If graceful fallback is enabled, return empty list
            if config.ENABLE_GRACEFUL_FALLBACK:
                print(f"[OutputValidator] → Returning empty stories for batch {batch.batch_id} (graceful fallback)")
                return []
            else:
                raise

    def aggregate_all_stories(self, all_batch_stories: List[List[UserStory]]) -> List[UserStory]:
        """
        Aggregate stories from all batches and deduplicate.
        
        Deduplication is based on (requirement_id, user_story_id, text) to avoid
        exact duplicates across batches.
        """
        all_stories = []
        seen_stories = set()
        
        for batch_stories in all_batch_stories:
            for story in batch_stories:
                # Create unique key for deduplication
                story_key = (story.requirement_id, story.user_story_id, story.text)
                
                if story_key not in seen_stories:
                    seen_stories.add(story_key)
                    all_stories.append(story)
        
        print(f"[Aggregation] Merged {sum(len(b) for b in all_batch_stories)} stories → {len(all_stories)} unique stories")
        return all_stories
    
    def validate_completeness(
        self,
        batches: List[RequirementBatch],
        user_stories: List[UserStory]
    ):
        """
        Validate that all requirements have at least one user story.
        
        Raises ValueError if requirements are missing and strict mode is enabled.
        """
        # Get requirements that have stories
        requirements_with_stories = {story.requirement_id for story in user_stories}
        
        # Find missing requirements
        all_requirement_ids = set()
        for batch in batches:
            for req in batch.requirements:
                all_requirement_ids.add(req.id)
        
        missing_requirements = all_requirement_ids - requirements_with_stories
        
        if missing_requirements:
            missing_list = sorted(list(missing_requirements))[:10]  # Show first 10
            msg = f"Missing user stories for {len(missing_requirements)} requirements: {missing_list}"
            
            if len(missing_requirements) > 10:
                msg += f" and {len(missing_requirements) - 10} more"
            
            if self.strict and not config.ENABLE_GRACEFUL_FALLBACK:
                raise ValueError(msg)
            else:
                print(f"[OutputValidator] ⚠️  {msg}")
                # Don't raise error if graceful fallback is enabled
                return
        else:
            print(f"[OutputValidator] ✓ All {len(all_requirement_ids)} requirements have at least one user story")
    
    def get_statistics(self, user_stories: List[UserStory]) -> Dict[str, Any]:
        """Get statistics about generated user stories."""
        stats = {
            "total_user_stories": len(user_stories),
            "by_type": defaultdict(int),
            "by_requirement": defaultdict(int)
        }
        
        for story in user_stories:
            stats["by_type"][story.type] += 1
            stats["by_requirement"][story.requirement_id] += 1
        
        # Convert defaultdicts to regular dicts
        stats["by_type"] = dict(stats["by_type"])
        stats["by_requirement"] = dict(stats["by_requirement"])
        
        return stats