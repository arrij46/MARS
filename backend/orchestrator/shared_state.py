from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple
import asyncio

# Global shared state instance
_shared_state: Optional['SharedState'] = None


@dataclass
class SharedState:
    """
    Shared state used by orchestrator + agents to store all conversation
    data such as documents, CDN results, refinement iterations, etc.
    """
    # (conv_id, agent_name) → asyncio.Event to signal when an agent's task is complete (used by handle_message to unblock waiting agents)
    _completion_events: Dict[Tuple[str, str], asyncio.Event] = field(default_factory=dict, init=False)

    # conv_id → dict of stored items
    conversations: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Lock to protect state in async environment (RabbitMQ callbacks)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    # ------------------------------ #
    #   Base conversation handler    #
    # ------------------------------ #
    def get_conversation(self, conv_id: str) -> Dict[str, Any]:
        """Create a new conversation state if missing."""
        if conv_id not in self.conversations:
            self.conversations[conv_id] = {
                "document": None,
                "document_path": None,
                "input_doc": None,
                "elicitation_results": None,
                "cdn_results": None,
                "cdn_results_path": None,
                "refinement_results_path": None,
                "refinement_results": None,  # Latest refinement results
                "refinement_steps": [],       # History of all refinement iterations
                "final_refined_requirements": None,
                "document_results": None,
                "user_story_results": None,
                "final_results": None,
                "final_results_path": None,
                "project_description": None,  # Project description for context
                "template_ready_event": None, # asyncio.Event to signal when template is ready
                "metadata": {},
                "message_buffer": [],
            }
        return self.conversations[conv_id]


        # event management for agent completion signaling (used by handle_message to unblock waiting agents)
    def get_or_create_event(self, conv_id: str, agent_name: str) -> asyncio.Event:
        key = (conv_id, agent_name)
        if key not in self._completion_events:
            self._completion_events[key] = asyncio.Event()
        return self._completion_events[key]

    def signal_agent_complete(self, conv_id: str, agent_name: str):
        """Called by handle_message when a final result arrives."""
        event = self.get_or_create_event(conv_id, agent_name)
        event.set()

    def reset_agent_event(self, conv_id: str, agent_name: str):
        """Reset before re-using an agent in the next loop iteration."""
        key = (conv_id, agent_name)
        if key in self._completion_events:
            self._completion_events[key].clear()


    # ------------------------------ #
    #   Document Storage             #
    # ------------------------------ #
    async def store_document_async(self, conv_id: str, document_path: str, parsed: Dict[str, Any]):
        """Store uploaded document + extracted requirements (async version)."""
        async with self.lock:
            conv = self.get_conversation(conv_id)
            conv["document_path"] = document_path
            conv["input_doc"] = parsed

    def store_document(self, conv_id: str, document_path: str, parsed: Dict[str, Any]):
        """Store uploaded document + extracted requirements (sync version for compatibility)."""
        conv = self.get_conversation(conv_id)
        conv["document_path"] = document_path
        conv["input_doc"] = parsed

    def get_document(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """Get the parsed requirements document."""
        conv = self.get_conversation(conv_id)
        return conv.get("input_doc")

    def get_document_path(self, conv_id: str) -> Optional[str]:
        """Get the path to the uploaded document."""
        conv = self.get_conversation(conv_id)
        return conv.get("document_path")

    # ------------------------------ #
    #   Elicitation Storage          #
    # ------------------------------ #
    def store_elicitation(self, conv_id: str, elicitation_data: Dict[str, Any]):
        """Store elicitation agent results."""
        conv = self.get_conversation(conv_id)
        conv["elicitation_results"] = elicitation_data
        print(f"[SharedState] Elicitation results stored for conv={conv_id}")

    def get_elicitation(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """Get elicitation results."""
        conv = self.get_conversation(conv_id)
        return conv.get("elicitation_results")

    # ------------------------------ #
    #   CDN Analysis Storage         #
    # ------------------------------ #
    async def store_cdn_results_async(self, conv_id: str, results_path: str, results_data: Dict[str, Any]):
        """Store conflict/duplication/negation results (async version)."""
        async with self.lock:
            conv = self.get_conversation(conv_id)
            conv["cdn_results_path"] = results_path
            conv["cdn_results"] = results_data

    def store_cdn_results(self, conv_id: str, results_path: Optional[str], results_data: Dict[str, Any]):
        """Store conflict/duplication/negation results (sync version for compatibility)."""
        conv = self.get_conversation(conv_id)
        conv["cdn_results_path"] = results_path
        conv["cdn_results"] = results_data
        print(f"[SharedState] CDN results stored for conv={conv_id}")

    def get_cdn_results(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """Get CDN analysis results."""
        conv = self.get_conversation(conv_id)
        return conv.get("cdn_results")

    def get_cdn_results_path(self, conv_id: str) -> Optional[str]:
        """Get path to CDN results file."""
        conv = self.get_conversation(conv_id)
        return conv.get("cdn_results_path")

    # ------------------------------ #
    #   Refinement Results           #
    # ------------------------------ #
    def store_refinement_results(self, conv_id: str, results_path: Optional[str], refined_requirements: Dict[str, Any]):
        """
        Store the latest refinement results.
        FIXED: Now uses the conversations dict structure instead of non-existent self.refined
        """
        conv = self.get_conversation(conv_id)
        conv["refinement_results"] = refined_requirements
        conv["refinement_results_path"] = results_path
        print("[SharedState] results saved for refinement: at path", results_path)
        print(f"[SharedState] Refinement results stored for conv={conv_id}")

    def get_refinement_results(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest refinement results.
        FIXED: Now uses the conversations dict structure instead of non-existent self.refined
        """
        conv = self.get_conversation(conv_id)
        return conv.get("refinement_results")

    async def add_refinement_step(self, conv_id: str, step_data: Dict[str, Any]):
        """Append each refinement iteration to history."""
        async with self.lock:
            conv = self.get_conversation(conv_id)
            conv["refinement_steps"].append(step_data)
            print(f"[SharedState] Refinement step added for conv={conv_id}")

    def add_refinement_step_sync(self, conv_id: str, step_data: Dict[str, Any]):
        """Append each refinement iteration to history (sync version)."""
        conv = self.get_conversation(conv_id)
        conv["refinement_steps"].append(step_data)
        print(f"[SharedState] Refinement step added for conv={conv_id}")

    def get_refinement_steps(self, conv_id: str) -> list:
        """Get all refinement iteration history."""
        conv = self.get_conversation(conv_id)
        return conv.get("refinement_steps", [])


    def get_final_refinement(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """Get final refined requirements."""
        conv = self.get_conversation(conv_id)
        return conv.get("final_refined_requirements")

    # ------------------------------ #
    #   Document Generation Results  #
    # ------------------------------ #
    def store_document_results(self, conv_id: str, document_data: Dict[str, Any]):
        """Store Document agent output."""
        conv = self.get_conversation(conv_id)
        conv["document_results"] = document_data
        print(f"[SharedState] Document results stored for conv={conv_id}")

    def get_document_results(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """Get Document agent output."""
        conv = self.get_conversation(conv_id)
        return conv.get("document_results")

    # ------------------------------ #
    #   Project Context              #
    # ------------------------------ #
    def store_project_description(self, conv_id: str, description: str):
        """Store project description for LLM context."""
        conv = self.get_conversation(conv_id)
        conv["project_description"] = description
        print(f"[SharedState] Project description stored for conv={conv_id}")

    def get_project_description(self, conv_id: str) -> Optional[str]:
        """Get project description for LLM context."""
        conv = self.get_conversation(conv_id)
        return conv.get("project_description")

    # ------------------------------ #
    #   User Story Results           #
    # ------------------------------ #
    def store_user_story_results(self, conv_id: str, user_story_data: Dict[str, Any]):
        """Store User Story agent output."""
        conv = self.get_conversation(conv_id)
        conv["user_story_results"] = user_story_data
        print(f"[SharedState] User story results stored for conv={conv_id}")

    def get_user_story_results(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """Get User Story agent output."""
        conv = self.get_conversation(conv_id)
        return conv.get("user_story_results")

    # ------------------------------ #
    #   Final Results                #
    # ------------------------------ #
    def store_final_results(self, conv_id: str, results_path: str, final_data: Dict[str, Any]):
        """Store final aggregated results."""
        conv = self.get_conversation(conv_id)
        conv["final_results_path"] = results_path
        conv["final_results"] = final_data
        print(f"[SharedState] Final results stored for conv={conv_id} at {results_path}")

    def get_final_results(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """Get final aggregated results."""
        conv = self.get_conversation(conv_id)
        return conv.get("final_results")

    def get_final_results_path(self, conv_id: str) -> Optional[str]:
        """Get path to final results file."""
        conv = self.get_conversation(conv_id)
        return conv.get("final_results_path")

    # ------------------------------ #
    #   Generic storage (for A2A)    #
    # ------------------------------ #
    async def store_agent_payload(self, conv_id: str, agent_name: str, payload: Any):
        """
        Universal storage for any agent's output.
        Used by orchestrator when receiving A2A messages.
        """
        async with self.lock:
            conv = self.get_conversation(conv_id)
            conv["metadata"][agent_name] = payload

    def store_agent_payload_sync(self, conv_id: str, agent_name: str, payload: Any):
        """Sync version of store_agent_payload."""
        conv = self.get_conversation(conv_id)
        conv["metadata"][agent_name] = payload

    def get_agent_payload(self, conv_id: str, agent_name: str) -> Any:
        """Get agent-specific payload from metadata."""
        conv = self.get_conversation(conv_id)
        return conv["metadata"].get(agent_name)

    # ------------------------------ #
    #   Utility Methods              #
    # ------------------------------ #
    def get_all_data(self, conv_id: str) -> Dict[str, Any]:
        """Get all data for a conversation."""
        return self.get_conversation(conv_id)

    def clear_conversation(self, conv_id: str):
        """Clear all data for a conversation."""
        if conv_id in self.conversations:
            del self.conversations[conv_id]
            print(f"[SharedState] Cleared conversation {conv_id}")

    def list_conversations(self) -> list:
        """List all conversation IDs."""
        return list(self.conversations.keys())


    # ------------------------------ #
    #   Template Ready Event         #
    # ------------------------------ #
    def create_template_ready_event(self, conv_id: str) -> asyncio.Event:
        """Create and store asyncio.Event — document agent will wait on this"""
        conv = self.get_conversation(conv_id)
        event = asyncio.Event()
        conv["template_ready_event"] = event
        print(f"[SharedState] Template ready event created for conv={conv_id}")
        return event

    def signal_template_ready(self, conv_id: str):
        """Signal that template has been saved — unblocks document agent"""
        conv = self.get_conversation(conv_id)
        event = conv.get("template_ready_event")
        if event:
            event.set()
            print(f"[SharedState] Template ready signal set for conv={conv_id}")
        else:
            print(f"[SharedState] No template event found for conv={conv_id}")

    # ------------------------------ #
    #   Message Buffering            #
    # ------------------------------ #
    def buffer_message(self, conv_id: str, message: dict):
        """Store a progress message when WS is not yet connected."""
        conv = self.get_conversation(conv_id)
        if "message_buffer" not in conv:
            conv["message_buffer"] = []
        conv["message_buffer"].append(message)

    def flush_buffer(self, conv_id: str) -> list:
        """Return and clear all buffered messages for a conv_id."""
        conv = self.get_conversation(conv_id)
        messages = conv.get("message_buffer", [])
        conv["message_buffer"] = []
        return messages
# ------------------------------ #
#   Global instance getter       #
# ------------------------------ #
def get_shared_state() -> SharedState:
    global _shared_state
    if _shared_state is None:
        _shared_state = SharedState()
    return _shared_state


