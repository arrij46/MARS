# agents/userStory/main.py
#Main pipeline orchestration module for MARS User Story Generation Pipeline.

import sys
from typing import List, Tuple, Optional
from pathlib import Path

from agents.userStory import config
from agents.userStory.models import UserStory, OutputMetadata, UserStoriesOutput, RequirementBatch
from agents.userStory.services import BatchBuilder, GPT4Client, OutputValidator
from agents.userStory.utils import FileHandler

# Import Ollama client
try:
    from agents.userStory.services.ollama_client import OllamaClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("⚠️  Warning: Ollama client not available. Install requests: pip install requests")


class UserStoryPipeline:
    
    def __init__(self, api_key: str = None, strict_validation: bool = True, project_description: str = None):
        self.batch_builder = BatchBuilder()
        self.output_validator = OutputValidator(strict=strict_validation)
        self.file_handler = FileHandler()
        self.all_requirement_ids = set()  # Global requirement IDs
        self.project_description = project_description  # Project context for LLM
        
        # Initialize OpenRouter clients (primary and secondary)
        self.primary_client = None
        self.secondary_client = None
        
        if not config.FORCE_OLLAMA:
            # Initialize primary OpenRouter client
            if config.OPENROUTER_API_KEY_PRIMARY:
                self.primary_client = GPT4Client(api_key=config.OPENROUTER_API_KEY_PRIMARY, project_description=project_description)
                print(f"Primary OpenRouter API initialized")
            
            # Initialize secondary OpenRouter client
            if config.OPENROUTER_API_KEY_SECONDARY:
                self.secondary_client = GPT4Client(api_key=config.OPENROUTER_API_KEY_SECONDARY, project_description=project_description)
                print(f"Secondary OpenRouter API initialized")
        
        # Initialize Ollama client if enabled
        self.ollama_client = None
        if OLLAMA_AVAILABLE and (config.ENABLE_OLLAMA_FALLBACK or config.FORCE_OLLAMA):
            self.ollama_client = OllamaClient(
                base_url=config.OLLAMA_BASE_URL,
                model=config.OLLAMA_MODEL
            )
            # Check if Ollama is actually running
            if not self.ollama_client.is_available():
                print(f"⚠️  Warning: Ollama is enabled but not available at {config.OLLAMA_BASE_URL}")
                if config.FORCE_OLLAMA:
                    raise RuntimeError(
                        f"FORCE_OLLAMA is enabled but Ollama is not available at {config.OLLAMA_BASE_URL}. "
                        "Please start Ollama server or disable FORCE_OLLAMA."
                    )
                self.ollama_client = None
            else:
                print(f"Ollama client initialized ({config.OLLAMA_MODEL} at {config.OLLAMA_BASE_URL})")
        
        # Track API usage statistics
        self.api_stats = {
            'primary': 0,
            'secondary': 0,
            'ollama': 0,
            'failed': 0
        }
    
    def run(self, input_path: str, output_path: str) -> None:
        print("=" * 80)
        print("MARS User Story Generation Pipeline - Starting")
        print("=" * 80)
        
        # Display fallback strategy
        strategy = config.get_fallback_strategy()
        print(f"\API Fallback Strategy: {' → '.join(strategy)}")
        
        try:
            # Step 1: Read and validate input
            print("\n[Step 1] Reading requirements from input file")
            requirements_input = self.file_handler.read_requirements(input_path)
            total_requirements = len(requirements_input.requirements)
            print(f"Loaded {total_requirements} requirements")
            
            # CRITICAL: Set global requirement IDs for validation
            self.output_validator.set_global_requirements(requirements_input.requirements)
            self.all_requirement_ids = {req.id for req in requirements_input.requirements}
            
            # Step 2: Build batches
            print("\n[Step 2] Building token-aware batches")
            batches = self.batch_builder.build_batches(
                requirements_input.requirements
            )
            print(f"Created {len(batches)} batches for processing")
            
            # Step 3: Process batches through API with fallback
            print("\n[Step 3] Processing batches through LLM with fallback")
            all_batch_stories, failed_batch_ids = self._process_batches_with_fallback(batches)
            
            # Display API usage statistics
            self._display_api_stats()
            
            # Step 4: Aggregate and deduplicate stories
            print("\n[Step 4] Aggregating user stories from all batches")
            merged_user_stories = self.output_validator.aggregate_all_stories(all_batch_stories)
            print(f"Total merged user stories: {len(merged_user_stories)}")
            
            # Step 5: Validate completeness (skip if graceful fallback with failed batches)
            if not failed_batch_ids or not config.ENABLE_GRACEFUL_FALLBACK:
                print("\n[Step 5] Validating output completeness")
                self.output_validator.validate_completeness(batches, merged_user_stories)
            else:
                print(f"\n[Step 5] Skipping completeness validation "
                      f"({len(failed_batch_ids)} batches deferred)")
            
            # Step 6: Get statistics
            stats = self.output_validator.get_statistics(merged_user_stories)
            print(f"Statistics: {stats}")
            
            # Step 7: Persist JSON output (MUST happen before PDF generation)
            print("\n[Step 6] Persisting user stories to JSON")
            output = self._build_output(
                merged_user_stories,
                total_requirements,
                batches,
                failed_batch_ids
            )
            self.file_handler.write_user_stories(output_path, output)
            print(f"JSON persisted to: {output_path}")
            
            # Step 8: Generate PDF from JSON (MUST happen after JSON is written)
            print("\n[Step 7] Generating PDF from user stories")
            pdf_path = self._generate_pdf_from_json(output_path, merged_user_stories)
            print(f"PDF generated at: {pdf_path}")
            
            # Step 9: Summary
            print("\n" + "=" * 80)
            if failed_batch_ids:
                print("Pipeline completed with warnings!")
                print(f"  Requirements processed: {total_requirements}")
                print(f"  User stories generated: {len(merged_user_stories)}")
                print(f"  Successful batches: {len(batches) - len(failed_batch_ids)}/{len(batches)}")
                print(f"  Failed batches (deferred): {len(failed_batch_ids)}")
            else:
                print("Pipeline completed successfully!")
                print(f"  Requirements processed: {total_requirements}")
                print(f"  User stories generated: {len(merged_user_stories)}")
                print(f"  All {len(batches)} batches processed successfully")
            print(f"  JSON: {output_path}")
            print(f"  PDF: {pdf_path}")
            print("=" * 80)
            
        except Exception as e:
            print(f"\n Pipeline failed: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def _process_batches_with_fallback(
        self, 
        batches: List[RequirementBatch]
    ) -> Tuple[List[List[UserStory]], List[str]]:
        # Process all batches with multi-level fallback support.
        
        #Fallback Strategy:
        #1. Try Primary OpenRouter API
        #2. If fails, try Secondary OpenRouter API
        #3. If fails, try Ollama (if enabled)
        #4. If all fail, handle gracefully or raise error
        
        #Returns:
            #Tuple of (all_batch_stories, failed_batch_ids)
        all_batch_stories = []
        failed_batch_ids = []
        
        for i, batch in enumerate(batches, 1):
            print(
                f"\n  Processing batch {i}/{len(batches)}: "
                f"{batch.batch_id} ({batch.type}, {len(batch.requirements)} reqs, "
                f"~{batch.estimated_tokens} tokens)"
            )
            
            batch_stories = None
            last_error = None
            
            # Get fallback strategy for this batch
            strategy = config.get_fallback_strategy()
            
            # Try each API in fallback order
            for api_type in strategy:
                try:
                    if api_type == 'openrouter_primary':
                        print(f"Trying Primary OpenRouter API...")
                        batch_stories = self._process_batch_client(
                            batch, i, self.primary_client, "Primary OpenRouter"
                        )
                        self.api_stats['primary'] += 1
                        break
                        
                    elif api_type == 'openrouter_secondary':
                        print(f"Trying Secondary OpenRouter API...")
                        batch_stories = self._process_batch_client(
                            batch, i, self.secondary_client, "Secondary OpenRouter"
                        )
                        self.api_stats['secondary'] += 1
                        break
                        
                    elif api_type == 'ollama':
                        print(f"Trying Ollama local model...")
                        batch_stories = self._process_batch_ollama(batch, i)
                        self.api_stats['ollama'] += 1
                        break
                        
                except Exception as e:
                    last_error = e
                    print(f"{api_type.replace('_', ' ').title()} failed: {str(e)}")
                    # Continue to next API in fallback chain
                    continue
            
            # Check if any API succeeded
            if batch_stories is not None:
                all_batch_stories.append(batch_stories)
                print(f"Generated {len(batch_stories)} user stories")
            else:
                # All APIs failed
                error_msg = f"All APIs failed. Last error: {last_error}"
                print(f" Batch {batch.batch_id} failed: {error_msg}")
                self.api_stats['failed'] += 1
                
                # Check if graceful fallback is enabled
                if config.ENABLE_GRACEFUL_FALLBACK:
                    failed_batch_ids.append(batch.batch_id)
                    all_batch_stories.append([])  # Empty list for this batch
                    print(f"Batch deferred (FAILED_PENDING). Continuing with other batches...")
                else:
                    # Strict mode: raise exception and stop pipeline
                    raise Exception(error_msg)
        
        return all_batch_stories, failed_batch_ids
    
    def _process_batch_client(
        self,
        batch: RequirementBatch,
        batch_index: int,
        client: GPT4Client,
        client_name: str
    ) -> List[UserStory]:
        # Process batch using a specific OpenRouter client.
        
        #Args:
        #    batch: Batch to process
        #    batch_index: Index of batch
        #    client: GPT4Client instance
        #    client_name: Name for logging
            
        #Returns:
        #    List of UserStory objects
        
        if not client:
            raise RuntimeError(f"{client_name} not initialized")
        
        response_data = client.process_batch(batch)
        batch_stories = self.output_validator.validate_batch_output(
            batch, response_data, batch_index=batch_index
        )
        return batch_stories
    
    def _process_batch_ollama(
        self, 
        batch: RequirementBatch, 
        batch_index: int
    ) -> List[UserStory]:
        #Process batch using Ollama in single-requirement mode.#
        if not self.ollama_client:
            raise RuntimeError("Ollama client not initialized")
        
        print(f"Ollama processing {len(batch.requirements)} requirements individually")
        
        # Let the Ollama client handle single-requirement processing
        # Pass project description for context
        response_data = self.ollama_client.process_batch(batch, self.project_description)
        
        # Validate the aggregated stories
        batch_stories = self.output_validator.validate_batch_output(
            batch, response_data, batch_index=batch_index
        )
        
        return batch_stories

    
    def _display_api_stats(self):
        #Display API usage statistics.#
        total = sum(self.api_stats.values())
        if total == 0:
            return
        
        print(f"\API Usage Statistics:")
        if self.api_stats['primary'] > 0:
            print(f"  Primary OpenRouter: {self.api_stats['primary']} batches")
        if self.api_stats['secondary'] > 0:
            print(f"  Secondary OpenRouter: {self.api_stats['secondary']} batches")
        if self.api_stats['ollama'] > 0:
            print(f"  Ollama (local): {self.api_stats['ollama']} batches")
        if self.api_stats['failed'] > 0:
            print(f"  Failed: {self.api_stats['failed']} batches")
    
    def _build_output(
        self,
        user_stories: List[UserStory],
        total_requirements: int,
        batches: List[RequirementBatch],
        failed_batch_ids: List[str] = None
    ) -> UserStoriesOutput:
        #Build the output model with metadata.#
        failed_batch_ids = failed_batch_ids or []
        
        # Calculate average batch size (only successful batches)
        successful_batches = [b for b in batches if b.batch_id not in failed_batch_ids]
        avg_batch_size = (
            sum(len(b.requirements) for b in successful_batches) // len(successful_batches)
            if successful_batches else 0
        )
        
        metadata = OutputMetadata(
            total_requirements=total_requirements,
            total_user_stories=len(user_stories),
            batch_size=avg_batch_size,
            model=config.GPT_MODEL,
            failed_batches=failed_batch_ids,
            total_batches=len(batches),
            successful_batches=len(successful_batches)
        )
        
        return UserStoriesOutput(
            user_stories=user_stories,
            metadata=metadata
        )
    
    def _generate_pdf_from_json(self, json_path: str, user_stories: List[UserStory]) -> str:
        
        #Generate PDF from user stories.
        
        #This is called AFTER JSON is written to disk.
        
        #Args:
        #    json_path: Path to the JSON file
        #    user_stories: List of user stories (for PDF generation)
            
        #Returns:
        #    str: Path to the generated PDF
        
        try:
            from agents.userStory.utils.pdf_generator import generate_user_story_pdf
            
            # Create PDF output path
            json_file = Path(json_path)
            pdf_path = json_file.parent / json_file.name.replace('.json', '.pdf')
            
            # Create PDF data structure
            pdf_data = {
                "user_stories": [story.dict() for story in user_stories],
                "metadata": {
                    "total_user_stories": len(user_stories),
                    "generated_at": str(Path(json_path).stat().st_mtime)
                }
            }
            
            # Generate PDF
            pdf_stream = generate_user_story_pdf(
                user_stories_data=pdf_data,
                project_name="User Stories Report"
            )
            
            # Write PDF to disk
            with open(pdf_path, "wb") as f:
                f.write(pdf_stream.getvalue())
            
            print(f"PDF written to: {pdf_path}")
            return str(pdf_path)
            
        except Exception as e:
            print(f"⚠️  Warning: PDF generation failed: {e}")
            print("  Continuing without PDF...")
            return ""


def main():
    
    if len(sys.argv) != 3:
        print("Usage: python main.py <input_file> <output_file>")
        print("\nExample:")
        print("  python main.py requirements.json user_stories.json")
        print("\nEnvironment Variables:")
        print("  OPENROUTER_API_KEY: Primary OpenRouter API key")
        print("  OPENROUTER_API_KEY_SECONDARY: Secondary OpenRouter API key (fallback)")
        print("  GPT_MODEL: Model to use (default: meta-llama/llama-3.3-70b-instruct:free)")
        print("  ENABLE_OLLAMA_FALLBACK: Use Ollama as final fallback (default: true)")
        print("  FORCE_OLLAMA: Use only Ollama, skip OpenRouter (default: false)")
        print("  OLLAMA_BASE_URL: Ollama server URL (default: http://localhost:11434)")
        print("  OLLAMA_MODEL: Ollama model name (default: llama3)")
        print("  LOG_LEVEL: Logging level (default: INFO)")
        print("  ENABLE_LOGGING: Enable logging (default: true)")
        print("\nFallback Strategy:")
        print("  1. Try Primary OpenRouter API")
        print("  2. If fails, try Secondary OpenRouter API (if configured)")
        print("  3. If fails, try Ollama local model (if enabled)")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # Validate API configuration (only if not forcing Ollama)
    if not config.FORCE_OLLAMA:
        if not config.OPENROUTER_API_KEYS:
            print("\n Error: No OpenRouter API keys configured")
            print("\nYou must set at least one of the following:")
            print("  export OPENROUTER_API_KEY='your-primary-api-key'")
            print("  export OPENROUTER_API_KEY_SECONDARY='your-secondary-api-key'")
            print("\nAlternatively, set FORCE_OLLAMA=true to use local Ollama only:")
            print("  export FORCE_OLLAMA=true")
            print("  export OLLAMA_MODEL=llama3")
            sys.exit(1)
        
        # Display configured APIs
        print(f"\nConfigured APIs:")
        if config.OPENROUTER_API_KEY_PRIMARY:
            print(f"  - Primary OpenRouter API")
        if config.OPENROUTER_API_KEY_SECONDARY:
            print(f"  - Secondary OpenRouter API")
        if config.ENABLE_OLLAMA_FALLBACK:
            print(f"  - Ollama (fallback): {config.OLLAMA_MODEL}")
    else:
        print(f"\n Using Ollama only (FORCE_OLLAMA=true)")
        print(f"  Model: {config.OLLAMA_MODEL}")
        print(f"  URL: {config.OLLAMA_BASE_URL}")
    
    try:
        # Initialize and run pipeline
        pipeline = UserStoryPipeline(strict_validation=config.STRICT_VALIDATION)
        pipeline.run(input_file, output_file)
        
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        print(f"\nError: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Validation error: {e}")
        print(f"\nValidation Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        print(f"\nUnexpected Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
