"""
Token-aware batch builder for requirements.
"""
from typing import List
from collections import defaultdict

from agents.userStory import config
from agents.userStory.models import Requirement, RequirementBatch
from agents.userStory.utils import TokenEstimator


class BatchBuilder:
    """Builds token-aware batches from requirements."""
    
    def __init__(self):
        self.token_estimator = TokenEstimator()
    
    def build_batches(self, requirements: List[Requirement]) -> List[RequirementBatch]:
        """
        Build token-aware batches from requirements.
        
        Groups requirements by type (FR/NFR) and creates batches
        that stay within token limits.
        """
        # Separate FR and NFR
        fr_requirements = [r for r in requirements if r.type == "FR"]
        nfr_requirements = [r for r in requirements if r.type == "NFR"]
        
        batches = []
        
        # Build FR batches
        if fr_requirements:
            fr_batches = self._build_type_batches(
                fr_requirements, 
                "FR",
                config.FR_MAX_BATCH_SIZE,
                config.MAX_PROMPT_TOKENS_PER_BATCH
            )
            batches.extend(fr_batches)
        
        # Build NFR batches
        if nfr_requirements:
            nfr_batches = self._build_type_batches(
                nfr_requirements,
                "NFR",
                config.MAX_BATCH_SIZE,
                config.MAX_PROMPT_TOKENS_PER_BATCH
            )
            batches.extend(nfr_batches)
        
        print(f"Created {len(batches)} token-aware batches from {len(requirements)} requirements")
        return batches
    
    def _build_type_batches(
        self,
        requirements: List[Requirement],
        req_type: str,
        max_batch_size: int,
        max_tokens: int
    ) -> List[RequirementBatch]:
        """Build batches for a specific requirement type."""
        batches = []
        current_batch = []
        current_tokens = 0
        batch_counter = 1
        
        # Sort by token count (optional)
        req_with_tokens = [(req, self._estimate_req_tokens(req)) for req in requirements]
        
        for req, req_tokens in req_with_tokens:
            # Check if adding this requirement would exceed limits
            if (len(current_batch) >= max_batch_size or 
                current_tokens + req_tokens > max_tokens):
                
                if current_batch:  # Save current batch
                    batch_id = f"BATCH-{batch_counter:03d}"
                    batches.append(RequirementBatch(
                        batch_id=batch_id,
                        type=req_type,
                        requirements=current_batch,
                        estimated_tokens=current_tokens
                    ))
                    print(f"Created batch {batch_id}: {len(current_batch)} requirements, ~{current_tokens} prompt tokens")
                    
                    batch_counter += 1
                    current_batch = []
                    current_tokens = 0
            
            # Add requirement to current batch
            current_batch.append(req)
            current_tokens += req_tokens
        
        # Add final batch
        if current_batch:
            batch_id = f"BATCH-{batch_counter:03d}"
            batches.append(RequirementBatch(
                batch_id=batch_id,
                type=req_type,
                requirements=current_batch,
                estimated_tokens=current_tokens
            ))
            print(f"Created batch {batch_id}: {len(current_batch)} requirements, ~{current_tokens} prompt tokens")
        
        return batches
    
    def _estimate_req_tokens(self, requirement: Requirement) -> int:
        """Estimate token count for a single requirement."""
        # Base prompt template overhead
        base_overhead = 50  # Approximate tokens for prompt structure
        
        # Requirement text tokens
        text_tokens = self.token_estimator.estimate_tokens(requirement.text)
        
        return base_overhead + text_tokens