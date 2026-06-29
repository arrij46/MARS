import asyncio
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import motor.motor_asyncio

from agents.base_agent import BaseAgent
from orchestrator.shared_state import get_shared_state

# Import user story pipeline components
from agents.userStory.main import UserStoryPipeline
from agents.userStory import config

from agents.userStory.AQUSA_URQ_Evaluation import evaluate_user_stories

class UserStoryAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="User_Story", exchange="agents-exchange", queue="User_Story")
        self.shared_state = get_shared_state()
        
        # Ensure results directory exists
        self.results_dir = Path("./agents/userStory/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.evaluation_dir = Path("./agents/userStory/results")
        self.evaluation_dir.mkdir(parents=True, exist_ok=True)
        
        # MongoDB connection will be set by main.py
        self.db = None

    def set_database(self, db):
        """Set the MongoDB database connection."""
        self.db = db
        print(f"[{self.name}] Database connection set")

    async def fetch_project_description(self, project_id: str) -> Optional[str]:
        """Fetch project description from MongoDB."""
        if self.db is None:
            print(f"[{self.name}] Warning: Database not available for project lookup")
            return None
        
        try:
            project = await self.db["projects"].find_one({"_id": project_id})
            if project and "description" in project:
                description = project.get("description", "")
                print(f"[{self.name}] Project description fetched: {len(description)} characters")
                return description
            else:
                print(f"[{self.name}] Project {project_id} not found or has no description")
                return None
        except Exception as e:
            print(f"[{self.name}] Error fetching project description: {str(e)}")
            return None

    async def handle_message(self, msg: dict):
        """Handle incoming A2A message and generate user stories"""
        conv_id = msg.get("conv_id", "unknown")
        payload = msg.get("payload", {})
        task = payload.get("task", "")
        
        print(f"\n{'='*80}")
        print(f"[{self.name}] USER STORY AGENT ACTIVATED")
        print(f"{'='*80}")
        print(f"[{self.name}] Conversation ID: {conv_id}")
        print(f"[{self.name}] Task: {task}")
        
        try:
            # Step 1: Get refinement results from shared state
            print(f"[{self.name}] Step 1: Retrieving refinement results")
            refinement_results = self.shared_state.get_refinement_results(conv_id)
            
            if not refinement_results:
                error_msg = "No refinement results found. Please ensure refinement agent has completed processing."
                print(f"[{self.name}] ERROR: {error_msg}")
                await self.send_message(
                    receiver="Orchestrator",
                    payload={
                        "status": "error",
                        "from": self.name,
                        "error": error_msg
                    },
                    type_="error",
                    conv_id=conv_id
                )
                return
            
            # Step 2: Extract requirements from refinement results
            print(f"[{self.name}] Step 2: Extracting requirements from refinement results")
            requirements = self._extract_requirements(refinement_results)
            
            if not requirements:
                error_msg = "No requirements found in refinement results."
                print(f"[{self.name}] ERROR: {error_msg}")
                await self.send_message(
                    receiver="Orchestrator",
                    payload={
                        "status": "error",
                        "from": self.name,
                        "error": error_msg
                    },
                    type_="error",
                    conv_id=conv_id
                )
                return
            
            print(f"[{self.name}] Extracted {len(requirements)} requirements")
            
            # Step 3: Fetch project description for LLM context
            print(f"[{self.name}] Step 3: Fetching project description")
            project_description = await self.fetch_project_description(conv_id)
            if project_description:
                self.shared_state.store_project_description(conv_id, project_description)
                print(f"[{self.name}] Project description stored in shared state")
            else:
                print(f"[{self.name}] No project description available, proceeding without context")
            
            # Step 4: Convert requirements to pipeline input format
            print(f"[{self.name}] Step 4: Converting requirements to pipeline format")
            input_data = self._convert_to_pipeline_format(requirements)
            
            # Step 5: Create temporary input file
            input_file = self.results_dir / f"input_requirements_{conv_id}.json"
            output_file = self.results_dir / f"user_stories_{conv_id}.json"
            
            print(f"[{self.name}] Step 5: Writing input file: {input_file}")
            with open(input_file, "w", encoding="utf-8") as f:
                json.dump(input_data, f, indent=2, ensure_ascii=False)
            
            # Step 6: Run the user story generation pipeline
            print(f"[{self.name}] Step 6: Running user story generation pipeline")
            print(f"[{self.name}] (This may take several moments...)")
            
            # Run pipeline in thread pool to avoid blocking event loop
            pipeline = UserStoryPipeline(
                api_key=config.OPENROUTER_API_KEY,
                strict_validation=config.STRICT_VALIDATION,
                project_description=project_description
            )
            
            # Run pipeline in thread since it's synchronous
            # Pipeline now handles JSON and PDF generation internally
            await asyncio.to_thread(pipeline.run, str(input_file), str(output_file))
            
            # Step 7: Verify artifacts exist
            print(f"[{self.name}] Step 7: Verifying generated artifacts")
            if not output_file.exists():
                raise FileNotFoundError(f"JSON output file not found: {output_file}")
            
            # PDF should be auto-generated by pipeline
            pdf_file = Path(str(output_file).replace('.json', '.pdf'))
            
            # Step 8: Read JSON output
            print(f"[{self.name}] Step 8: Reading user stories from JSON")
            with open(output_file, "r", encoding="utf-8") as f:
                output_data = json.load(f)
            
            total_stories = len(output_data.get("user_stories", []))
            print(f"[{self.name}] Successfully read {total_stories} user stories from JSON")
            
            # Step 9: Run AQUSA + URQ Evaluation
            print(f"[{self.name}] Step 9: Running AQUSA + URQ evaluation")

            try:
                evaluation_results = evaluate_user_stories(output_data)

                evaluation_file = self.evaluation_dir / f"evaluation_{conv_id}.json"

                with open(evaluation_file, "w", encoding="utf-8") as ef:
                    json.dump(evaluation_results, ef, indent=2, ensure_ascii=False)

                print(f"[{self.name}] Evaluation saved: {evaluation_file}")

            except Exception as eval_error:
                print(f"[{self.name}] ❌ Evaluation failed: {eval_error}")
                evaluation_results = None
                evaluation_file = None



            # Step 10: Verify PDF exists
            pdf_exists = False
            if pdf_file.exists():
                pdf_exists = True
                print(f"[{self.name}] PDF verified: {pdf_file}")
            else:
                print(f"[{self.name}] ⚠️  PDF not found at: {pdf_file}")
            
            # Step 11: Store results in shared state
            print(f"[{self.name}] Step 11: Storing results in shared state")
            self.shared_state.store_user_story_results(conv_id, {
            "user_stories_path": str(output_file),
            "user_stories": output_data,
            "total_user_stories": total_stories,
            "total_requirements": output_data.get("metadata", {}).get("total_requirements", 0),
            "pdf_path": str(pdf_file) if pdf_exists else None,

            # NEW
            "evaluation_path": str(evaluation_file) if evaluation_file else None,
            "evaluation_results": evaluation_results
        })
            # Step 12: Save stories to db
            print(f"[{self.name}] Step 12: Saving user stories to database")
            try:
                if self.db is not None:
                    user_stories_collection = self.db["user_stories"]
                    db_entry = {
                        "project_id": conv_id,  
                        "user_stories": output_data.get("user_stories", []),
                        "metadata": output_data.get("metadata", {}),
                        "evaluation_results": evaluation_results if evaluation_results else None
                    }
                    await user_stories_collection.insert_one(db_entry)
                    print(f"[{self.name}] User stories saved to database")
            except Exception as db_error:
                print(f"[{self.name}] Failed to save user stories to database: {db_error}")
            # Step 13: Send completion signal to orchestrator
            # ONLY after both JSON and PDF are verified to exist
            print(f"[{self.name}] Step 13: Sending completion signal to orchestrator")
            await self.send_message(
                receiver="Orchestrator",
                payload={
                    "status": "COMPLETED",
                    "from": self.name,
                    "json_path": str(output_file),
                    "pdf_path": str(pdf_file) if pdf_exists else None,
                    "evaluation_path": str(evaluation_file) if evaluation_file else None,
                    "evaluation_summary": evaluation_results.get("summary_metrics") if evaluation_results else None,
                    "story_count": total_stories,
                    "total_user_stories": total_stories,
                    "total_requirements": output_data.get("metadata", {}).get("total_requirements", 0),
                    "user_stories": output_data.get("user_stories", []),
                    "metadata": output_data.get("metadata", {})
                },
                type_="confirm",
                conv_id=conv_id
            )
            
            print(f"[{self.name}] ✓ User story generation completed successfully!")
            print(f"[{self.name}] Generated {total_stories} user stories")
            print(f"[{self.name}] JSON: {output_file}")
            print(f"[{self.name}] PDF: {pdf_file if pdf_exists else '(Not generated)'}")
            print(f"{'='*80}\n")
            
        except Exception as e:
            error_msg = f"Error generating user stories: {str(e)}"
            print(f"[{self.name}] ❌ ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            
            # Send error signal to orchestrator
            await self.send_message(
                receiver="Orchestrator",
                payload={
                    "status": "FAILED",
                    "from": self.name,
                    "error": error_msg
                },
                type_="error",
                conv_id=conv_id
            )
    
    def _extract_requirements(self, refinement_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract requirements from refinement results.
        Can come from cleaned_classified dict or from file_path.
        """
        requirements = []
        
        # Try to get from cleaned_classified first
        cleaned_classified = refinement_results.get("cleaned_classified")
        if cleaned_classified:
            if isinstance(cleaned_classified, dict) and "requirements" in cleaned_classified:
                requirements = cleaned_classified["requirements"]
            elif isinstance(cleaned_classified, list):
                requirements = cleaned_classified
        
        # If not found, try to load from file
        if not requirements:
            results_path = refinement_results.get("results_path")
            if results_path and os.path.exists(results_path):
                try:
                    with open(results_path, "r", encoding="utf-8") as f:
                        file_data = json.load(f)
                        if isinstance(file_data, dict) and "requirements" in file_data:
                            requirements = file_data["requirements"]
                        elif isinstance(file_data, list):
                            requirements = file_data
                except Exception as e:
                    print(f"[{self.name}] Warning: Could not load requirements from file {results_path}: {e}")
        
        # Also try file_data if available
        if not requirements:
            file_data = refinement_results.get("file_data")
            if file_data:
                if isinstance(file_data, dict) and "requirements" in file_data:
                    requirements = file_data["requirements"]
                elif isinstance(file_data, list):
                    requirements = file_data
        
        return requirements
    
    def _convert_to_pipeline_format(self, requirements: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, str]]]:
        """
        Convert requirements from refinement format to pipeline input format.
        Pipeline expects: {"requirements": [{"id": "R1", "type": "FR", "text": "..."}]}
        """
        converted = []
        
        for req in requirements:
            # Extract id, type, and text
            req_id = req.get("id", "")
            req_type = req.get("type", "FR")
            req_text = req.get("text", "")
            
            # Validate required fields
            if not req_id or not req_text:
                print(f"[{self.name}] Warning: Skipping requirement with missing id or text: {req}")
                continue
            
            # Ensure type is FR or NFR
            if req_type.upper() not in ["FR", "NFR"]:
                # Try to infer from subtype or default to FR
                req_type = "FR"
            
            converted.append({
                "id": str(req_id),
                "type": req_type.upper(),
                "text": str(req_text)
            })
        
        return {"requirements": converted}

    async def start_agent(self):
        """Start the agent and listen for messages"""
        print(f"[{self.name}] Agent started and listening on queue '{self.queue}'")
        await self.message_broker.consume_queue(self.queue, self.handle_message)

if __name__ == "__main__":
    import asyncio
    agent = UserStoryAgent()  # inherits from BaseAgent
    asyncio.run(agent.start_agent())
