import asyncio
import os
import json
import time
from typing import TypedDict, Optional

from api.routes.results_routes import add_report_to_project
from orchestrator.shared_state import get_shared_state
from api.ws_store import ws_connections
from agents.base_agent import BaseAgent
from api.routes.project_routes import send_requirements_to_route
from databaseSchema.schema import BulkCreateRequirementsRequest
from utils.summary_report_generator import SummaryReport
from agents.document.feature_extractor import extract_features


class WorkflowState(TypedDict):
    conv_id: str
    step: str
    iteration: int


class OrchestratorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Orchestrator", exchange="agents-exchange", queue="Orchestrator")
        self.queue = "Orchestrator"
        self.shared_state = get_shared_state()
        self.report_generator = SummaryReport()

    # ─────────────────────────────────────────
    # WebSocket progress sender (with buffering)
    # ─────────────────────────────────────────
    async def send_progress(self, conv_id: str, message: dict):
        ws = ws_connections.get(conv_id)
        if ws:
            try:
                await ws.send_json(message)
                print(f"[{self.name}] WS → frontend (conv={conv_id}): {message}")
            except Exception as e:
                print(f"[{self.name}] WS send failed, buffering: {e}")
                self.shared_state.buffer_message(conv_id, message)
        else:
            self.shared_state.buffer_message(conv_id, message)
            print(f"[{self.name}] WS not connected, buffered: {message}")

    # ─────────────────────────────────────────
    # Event-driven completion helpers
    # ─────────────────────────────────────────
    async def await_agent_completion(self, conv_id: str, agent_name: str):
        """
        Suspends until the named agent signals it has finished work for this
        conversation. The event must be reset BEFORE sending the message to the
        agent — never after — to avoid missing a fast completion signal.
        """
        event = self.shared_state.get_or_create_event(conv_id, agent_name)
        await event.wait()
        # Reset after we've consumed the signal so it's clean for next use
        self.shared_state.reset_agent_event(conv_id, agent_name)

    # ─────────────────────────────────────────
    # Incoming message handler
    # ─────────────────────────────────────────
    async def handle_message(self, msg: dict):
        """
        Receives every message from the broker and routes it.
        Stores results in shared state, sends WS progress for intermediate
        updates, and fires the completion event when an agent is truly done.
        """
        print(f"[{self.name}] Message received: {json.dumps(msg, indent=2)}")

        conv_id  = msg.get("conv_id")
        sender   = msg.get("sender")
        msg_type = msg.get("type")
        payload  = msg.get("payload", {})
        frm      = payload.get("from")

        # ── Document request (synchronous ask-and-respond) ───────────────────
        if msg_type == "request" and payload.get("request_type") == "document":
            input_doc = self.shared_state.get_document(conv_id)
            await self.send_message(
                receiver=sender,
                payload={"document": input_doc} if input_doc else {"error": "No document available"},
                type_="inform" if input_doc else "error",
                conv_id=conv_id,
            )
            return

        # ── Elicitation ──────────────────────────────────────────────────────
        if sender == "Elicitation" and msg_type in ("confirm", "inform"):
            document_path = payload.get("document_path")
            input_doc     = payload.get("document")
            if document_path and input_doc:
                self.shared_state.store_document(conv_id, document_path, input_doc)
            print(f"[{self.name}] Elicitation complete (conv={conv_id})")
            self.shared_state.signal_agent_complete(conv_id, "Elicitation")
            return

        # ── CDN ───────────────────────────────────────────────────────────────
        if frm == "CDN":
            if payload.get("analysis_complete"):
                results_path     = payload.get("cdn_results_path")
                issues_remaining = payload.get("issues_remaining")
                cdn_data = {
                    "cdn_results_path": results_path,
                    "issues_remaining": issues_remaining,
                    "conv_id":          conv_id,
                }
                if results_path:
                    try:
                        with open(results_path, "r", encoding="utf-8") as f:
                            cdn_data["file_data"] = json.load(f)
                    except Exception as e:
                        print(f"[{self.name}] Error loading CDN results: {e}")

                self.shared_state.store_cdn_results(conv_id, results_path, cdn_data)
                print(f"[{self.name}] CDN complete (conv={conv_id})")
                self.shared_state.signal_agent_complete(conv_id, "CDN")
            return

        # ── Refinement ────────────────────────────────────────────────────────
        if frm == "Refinement":
            results_path       = payload.get("results_path")
            cleaned_classified = payload.get("cleaned_classified") or []
            analysis_complete  = payload.get("analysis_complete", False)
            error_msg          = payload.get("error")

            refinement_data = {
                "full_payload":       payload,
                "results_path":       results_path,
                "cleaned_classified": cleaned_classified,
                "analysis_complete":  analysis_complete,
                "error":              error_msg,
                "conv_id":            conv_id,
            }
            if results_path:
                try:
                    with open(results_path, "r", encoding="utf-8") as f:
                        refinement_data["file_data"] = json.load(f)
                except Exception as e:
                    print(f"[{self.name}] Error loading Refinement results: {e}")

            self.shared_state.store_refinement_results(conv_id, results_path, refinement_data)

            if analysis_complete:
                # Only now send the confirmation/results to the frontend
                await self.send_progress(conv_id, {
                    "step":               "refinement_complete",
                    "message":            "analysis_complete",
                    "cleaned_classified": cleaned_classified,
                    "results_path":       results_path,
                })
                print(f"[{self.name}] Refinement final (conv={conv_id}) — unblocking loop")
            else:
                # Intermediate pass — stay silent to frontend, just unblock the loop
                print(f"[{self.name}] Refinement intermediate (conv={conv_id}) — unblocking loop")

            self.shared_state.signal_agent_complete(conv_id, "Refinement")
            return
        # ── User Story ────────────────────────────────────────────────────────
        if frm == "User_Story":
            user_story_data = {
                "status":      payload.get("status"),
                "json_path":   payload.get("json_path"),
                "pdf_path":    payload.get("pdf_path"),
                "story_count": payload.get("story_count", 0),
                "error":       payload.get("error"),
                "conv_id":     conv_id,
            }
            json_path = user_story_data["json_path"]
            if json_path and os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        user_story_data["file_data"] = json.load(f)
                except Exception as e:
                    print(f"[{self.name}] Error loading User Story JSON: {e}")

            self.shared_state.store_user_story_results(conv_id, user_story_data)
            print(
                f"[{self.name}] User Story complete (conv={conv_id}): "
                f"{user_story_data['story_count']} stories"
            )
            self.shared_state.signal_agent_complete(conv_id, "User_Story")
            return

        # ── Document agent ────────────────────────────────────────────────────
        if sender == "Document":
            self.shared_state.store_document_results(conv_id, payload)
            print(f"[{self.name}] Document agent complete (conv={conv_id})")
            self.shared_state.signal_agent_complete(conv_id, "Document")
            return

        print(f"[{self.name}] Unhandled message from '{sender}' (conv={conv_id})")

    # ─────────────────────────────────────────
    # CDN → Refinement loop
    # ─────────────────────────────────────────
    async def _run_cdn_refinement_loop(self, conv_id: str, input_doc: dict, max_count: int = 3):
        """
        Iterates CDN → Refinement until Refinement signals analysis_complete or
        max iterations is reached.

        The Refinement agent sends exactly ONE message per invocation:
          - loop_count="initial"      → analysis_complete=False  (more passes needed)
          - loop_count="intermediate" → analysis_complete=False  (more passes needed)
          - loop_count="final"/"one"  → analysis_complete=True   (all done)

        So the loop always unblocks after Refinement's single message, then checks
        analysis_complete from shared state to decide whether to continue.
        """
        iteration = 1

        while True:
            print(f"[{self.name}] CDN/Refinement loop iteration {iteration}")

            # Determine pass type — mirrors the logic from Code 1 exactly
            if max_count == 2:
                loop_count = "one"
            elif iteration == 1:
                loop_count = "initial"
            elif iteration >= max_count - 1:
                loop_count = "final"
            else:
                loop_count = "intermediate"

            # ── CDN ──────────────────────────────────────────────────────────
            # Reset BEFORE sending so we cannot miss a fast reply
            self.shared_state.reset_agent_event(conv_id, "CDN")

            if loop_count in ("initial", "one"):
                cdn_payload = {"task": "cdn work", "document": input_doc}
                cdn_msg     = "Sending initial document to CDN agent"
            else:
                refinement_result = self.shared_state.get_refinement_results(conv_id)
                cdn_payload = {
                    "task":               "cdn work",
                    "refinement_results": refinement_result.get("full_payload", refinement_result),
                }
                cdn_msg = "Sending refinement results to CDN agent"

            await self.send_progress(conv_id, {"step": "cdn_start", "message": cdn_msg})
            await self.send_message("CDN", cdn_payload, type_="inform", conv_id=conv_id)
            await self.await_agent_completion(conv_id, "CDN")

            cdn_results      = self.shared_state.get_cdn_results(conv_id)
            cdn_path         = cdn_results.get("cdn_results_path")
            issues_remaining = cdn_results.get("issues_remaining")

            await self.send_progress(conv_id, {
                "step":             "cdn_complete",
                "message":          "CDN analysis complete",
                "cdn_results_path": cdn_path,
            })
            print(f"[{self.name}] CDN path={cdn_path}  issues_remaining={issues_remaining}")

            # ── Refinement ───────────────────────────────────────────────────
            # Reset BEFORE sending — Refinement sends exactly one message then
            self.shared_state.reset_agent_event(conv_id, "Refinement")

            await self.send_progress(conv_id, {
                "step":    "refinement_start",
                "message": "Calling Refinement agent",
            })
            await self.send_message(
                "Refinement",
                {
                    "cdn_results_path": cdn_path,
                    "input_doc":        input_doc["summary"],
                    "issues_remaining": issues_remaining,
                    "loop_count":       loop_count,
                },
                type_="inform",
                conv_id=conv_id,
            )
            # Always unblocks after Refinement's single response message
            await self.await_agent_completion(conv_id, "Refinement")

            refinement_result = self.shared_state.get_refinement_results(conv_id)
            cleaned           = refinement_result.get("cleaned_classified") or []
            cleaned_count     = len(cleaned) if isinstance(cleaned, list) else 0
            analysis_complete = refinement_result.get("analysis_complete", False)

            # await self.send_progress(conv_id, {
            #     "step":          "refinement_complete",
            #     "message":       "Refinement complete",
            #     "cleaned_count": cleaned_count,
            #     "results_path":  refinement_result.get("results_path"),
            # })

            # ── Termination check ────────────────────────────────────────────
            # Primary exit: Refinement itself says it's done (final/one pass)
            if analysis_complete:
                print(f"[{self.name}] Refinement signalled complete — exiting loop")
                break

            # Safety exits: no more work to do, or hard iteration cap reached
            iteration += 1
            if issues_remaining == 0:
                print(f"[{self.name}] No issues remaining — exiting loop")
                break
            elif iteration >= max_count:
                print(f"[{self.name}] Max iterations reached — exiting loop")
                break

    # ─────────────────────────────────────────
    # Document agent
    # ─────────────────────────────────────────
    async def _run_document_agent(self, conv_id: str, input_doc: dict):
        final_requirement_set = self.shared_state.get_refinement_results(conv_id)
        requirements          = final_requirement_set.get("cleaned_classified", {})
        # cleaned_classified may be a list or a dict depending on agent version
        if isinstance(requirements, dict):
            requirements = requirements.get("requirements", [])
        elif not isinstance(requirements, list):
            requirements = []

        functional_reqs = [
            f'{r["id"]}: {r["text"]}'
            for r in requirements
            if r.get("type") == "Functional"
        ]

        clustered_fr = []
        try:
            clustered_fr = await extract_features(
                functional_reqs,
                f"requirement_clusters_{conv_id}.json",
            )
            print(f"[{self.name}] Clustered FR: {clustered_fr}")
        except Exception as e:
            print(f"[{self.name}] Error forming clusters: {e}")

        # Reset BEFORE sending
        self.shared_state.reset_agent_event(conv_id, "Document")
        await self.send_message(
            "Document",
            {
                "final_requirement_set": final_requirement_set,
                "input_doc":             input_doc,
                "clustered_fr":          clustered_fr,
            },
            type_="inform",
            conv_id=conv_id,
        )
        await self.await_agent_completion(conv_id, "Document")

        # Persist requirements to DB
        try:
            final_reqs = self.shared_state.get_refinement_results(conv_id)
            cleaned    = final_reqs.get("file_data") or final_reqs.get("cleaned_classified")
            reqs_list  = cleaned.get("requirements", []) if isinstance(cleaned, dict) else []
            if reqs_list:
                bulk_payload = BulkCreateRequirementsRequest(
                    requirements=[
                        {
                            "project_id": conv_id,
                            "text":       r["text"],
                            "id": str(r["id"]),
                            "req_id":     str(r["id"]),
                            "type":       r.get("type", "functional").lower().replace("-", "_"),
                            "subtype":    r.get("subtype", "Functional"),
                        }
                        for r in reqs_list
                        if r.get("text")
                    ]
                )
                await send_requirements_to_route(bulk_payload.dict(), conv_id)
                print(f"[{self.name}] Requirements persisted to DB (conv={conv_id})")
            else:
                print(f"[{self.name}] No requirements found — skipping DB save")
        except Exception as e:
            print(f"[{self.name}] Error saving requirements: {e}")
            import traceback; traceback.print_exc()

    # ─────────────────────────────────────────
    # User Story agent
    # ─────────────────────────────────────────
    async def _run_user_story_agent(self, conv_id: str):
        # Reset BEFORE sending
        self.shared_state.reset_agent_event(conv_id, "User_Story")
        await self.send_message(
            "User_Story",
            {"task": "create user stories"},
            type_="inform",
            conv_id=conv_id,
        )
        await self.await_agent_completion(conv_id, "User_Story")
        print(f"[{self.name}] User Story agent done (conv={conv_id})")        
             # Generate summary report
        try:
            self.report_generator.build_summary(conv_id)
            try:
                await add_report_to_project(conv_id)
                
                # ✅ OPTIMIZATION: Send WebSocket notification to frontend
                # This signals that the report is ready for immediate display
                await self.send_progress(conv_id, {
                    "step": "report_ready",
                    "message": "Report has been generated and saved",
                    "status": "success",
                    "timestamp": time.time()
                })
                print(f"[{self.name}] Report ready notification sent (conv={conv_id})")
                
            except Exception as e:
                print(f"[{self.name}] Error saving report to DB: {e}")
        except Exception as e:
            print(f"[{self.name}] Error generating summary report: {e}")
    

    # ─────────────────────────────────────────
    # Main entry point
    # ─────────────────────────────────────────
    async def start_agent(
        self,
        document_path: Optional[str] = None,
        input_doc:     Optional[dict] = None,
        conv_id:       str = None,
    ):
        if not conv_id:
            raise ValueError("conv_id is required")

        max_wait = 10
        waited   = 0
        while conv_id not in ws_connections and waited < max_wait:
            await asyncio.sleep(0.2)
            waited += 0.2
        print(f"[{self.name}] WS {'connected' if conv_id in ws_connections else 'NOT connected (timeout)'} after {waited:.1f}s")
    


        # Start the consumer FIRST, then yield so it actually begins listening
        # before any outbound messages are sent.
        async def handler_wrapper(msg: dict):
            await self.handle_message(msg)

        consumer_task = asyncio.create_task(
            self.message_broker.consume_queue(self.queue, handler_wrapper)
        )
        await asyncio.sleep(0)   # yield so consumer_task runs its first iteration

        if document_path and input_doc:
            self.shared_state.store_document(conv_id, document_path, input_doc)

        await self.send_progress(conv_id, {
            "step":    "workflow_started",
            "message": "Workflow started",
        })

        try:
            # Step 1: Elicitation (only if no document provided)
            if not input_doc:
                await self.send_progress(conv_id, {
                    "step":    "elicitation_start",
                    "message": "Calling Elicitation agent",
                })
                # Reset BEFORE sending
                self.shared_state.reset_agent_event(conv_id, "Elicitation")
                await self.send_message(
                    "Elicitation",
                    {"task": "initial elicit"},
                    type_="inform",
                    conv_id=conv_id,
                )
                await self.await_agent_completion(conv_id, "Elicitation")

            input_doc = self.shared_state.get_document(conv_id)

            # Step 2: CDN → Refinement loop
            await self._run_cdn_refinement_loop(
                conv_id=conv_id,
                input_doc=input_doc,
                max_count=3,
            )

            # Step 3: Document + User Story in parallel
            await self.send_progress(conv_id, {
                "step":    "doc_user_story_start",
                "message": "Calling Document & User Story agents",
            })
            await asyncio.gather(
                self._run_document_agent(conv_id, input_doc),
                self._run_user_story_agent(conv_id),
            )

            await self.send_progress(conv_id, {
                "step":    "workflow_complete",
                "message": "Workflow complete, results ready",
            })
            return {"conv_id": conv_id, "status": "completed"}

        finally:
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass



# original with timeouts/old code

# import asyncio
# import os
# import json
# from typing import TypedDict, Optional
# from api.routes.results_routes import add_report_to_project
# from orchestrator.shared_state import get_shared_state
# from api.ws_store import ws_connections
# from  agents.base_agent import BaseAgent  
# from api.routes.project_routes import send_requirements_to_route
# from databaseSchema.schema import BulkCreateRequirementsRequest
# from utils.summary_report_generator import SummaryReport
# from agents.document.feature_extractor import extract_features


# class WorkflowState(TypedDict):
#     conv_id: str
#     step: str
#     inbox: list
#     iteration: int

# class OrchestratorAgent(BaseAgent):
#     def __init__(self):
#         super().__init__(name="Orchestrator", exchange="agents-exchange", queue="Orchestrator")
#         self.queue = "Orchestrator"
#         self.shared_state = get_shared_state()
#         self.report_generator = SummaryReport()

#     # -------------------------
#     # WebSocket progress sender
#     # -------------------------
#     async def send_progress(self, conv_id: str, message: dict):
#         ws = ws_connections.get(conv_id)
#         if ws:
#             try:
#                 await ws.send_json(message)
#                 print(f"[{self.name}] Sent progress to frontend (conv={conv_id}): {message}")
#             except Exception as e:
#                 print(f"[{self.name}] Failed to send WS message: {e}")

#     # -------------------------
#     # Wait for agent reply
#     # -------------------------
#     async def wait_for_agent_reply(self, inbox_queue, agent_name, conv_id, timeout: float = 50.0):
#         """
#         Waits for the next message from an agent for a given conv_id.
#         Returns both intermediate and final messages.
#         """
#         deadline = asyncio.get_event_loop().time() + timeout

#         while True:
#             remaining = deadline - asyncio.get_event_loop().time()
#             if remaining <= 0:
#                 print(f"[{self.name}] Timeout waiting for {agent_name} (conv={conv_id})")
#                 return None

#             try:
#                 reply = await asyncio.wait_for(inbox_queue.get(), timeout=remaining)
#             except asyncio.TimeoutError:
#                 print(f"[{self.name}] Timeout waiting for {agent_name} (conv={conv_id})")
#                 return None

#             # Only messages from expected agent/conv
#             if reply.get("sender") != agent_name or reply.get("conv_id") != conv_id:
#                 await inbox_queue.put(reply)
#                 continue

#             return reply

#     # -------------------------
#     # Handle incoming message
#     # -------------------------
#     async def handle_message(self, msg: dict, inbox_queue: asyncio.Queue):

#         print(f"[{self.name}] Raw message received: {json.dumps(msg, indent=2)}")  # ← add this

#         conv_id = msg.get("conv_id")
#         sender = msg.get("sender")

#         # Document request
#         if msg.get("type") == "request" and msg.get("payload", {}).get("request_type") == "document":
#             input_doc = self.shared_state.get_document(conv_id)
#             await self.send_message(
#                 receiver=sender,
#                 payload={"document": input_doc} if input_doc else {"error": "No document available"},
#                 type_="inform" if input_doc else "error",
#                 conv_id=conv_id
#             )

#         # CDN results
#         elif msg.get("type") == "confirm" and msg.get("payload", {}).get("from") == "CDN":
#             payload = msg.get("payload", {})
#             if payload.get("analysis_complete"):
#                 results_path = payload.get("cdn_results_path")
#                 issues_remaining = payload.get("issues_remaining")
#                 cdn_data = {"cdn_results_path": results_path, "issues_remaining": issues_remaining, "conv_id": conv_id}
#                 if results_path:
#                     try:
#                         with open(results_path, "r", encoding="utf-8") as f:
#                             cdn_data["file_data"] = json.load(f)
#                     except Exception as e:
#                         print(f"[{self.name}] Error loading CDN results: {e}")
#                 self.shared_state.store_cdn_results(conv_id, results_path, cdn_data)

#             try:
#                 await inbox_queue.put(msg)
#             except Exception as e:
#                 print(f"[{self.name}] Failed to enqueue incoming message: {e}")
      
#         # Refinement results
#         elif msg.get("type") in ["confirm", "error"] and msg.get("payload", {}).get("from") == "Refinement":
#             payload = msg.get("payload", {})
#             results_path = payload.get("results_path")
#             cleaned_classified = payload.get("cleaned_classified")
#             error_msg = payload.get("error")
#             analysis_complete = payload.get("analysis_complete", False)

#             refinement_data = {
#                 "results_path": results_path,
#                 "cleaned_classified": cleaned_classified,
#                 "error": error_msg,
#                 "conv_id": conv_id
#             }

#             # Optionally load the JSON file if path is available
#             if results_path:
#                 try:
#                     with open(results_path, "r", encoding="utf-8") as f:
#                         refinement_data["file_data"] = json.load(f)
#                 except Exception as e:
#                     print(f"[{self.name}] Error loading Refinement results: {e}")

#             if analysis_complete:
#                 # Final results
#                 self.shared_state.store_refinement_results(conv_id, results_path, refinement_data)
#                 print(f"[{self.name}] Stored final Refinement results for conv={conv_id}")
#             else:
#                 # Intermediate results
#                 self.shared_state.store_refinement_results(conv_id, results_path, refinement_data)
#                 print(f"[{self.name}] Stored intermediate Refinement results for conv={conv_id}")

#             # Push message to inbox queue for wait loops
#             try:
#                 await inbox_queue.put(msg)
#             except Exception as e:
#                 print(f"[{self.name}] Failed to enqueue incoming message: {e}")
        
#         # User Story results
#         elif msg.get("type") in ["confirm", "error"] and msg.get("payload", {}).get("from") == "User_Story":
#             payload = msg.get("payload", {})
#             status = payload.get("status")
#             json_path = payload.get("json_path")
#             pdf_path = payload.get("pdf_path")
#             story_count = payload.get("story_count", 0)
#             error_msg = payload.get("error")
            
#             user_story_data = {
#                 "status": status,
#                 "json_path": json_path,
#                 "pdf_path": pdf_path,
#                 "story_count": story_count,
#                 "error": error_msg,
#                 "conv_id": conv_id
#             }
            


#             # Load JSON file if path is available
#             if json_path and os.path.exists(json_path):
#                 try:
#                     with open(json_path, "r", encoding="utf-8") as f:
#                         user_story_data["file_data"] = json.load(f)
                        
                    
#                 except Exception as e:
#                     print(f"[{self.name}] Error loading User Story JSON: {e}")
            
#             # Store in shared state
#             self.shared_state.store_user_story_results(conv_id, user_story_data)
#             print(f"[{self.name}] Stored User Story results for conv={conv_id}: {story_count} stories, "
#                   f"JSON={json_path}, PDF={pdf_path}")
            
        

#             # Push message to inbox queue
#             try:
#                 await inbox_queue.put(msg)
#             except Exception as e:
#                 print(f"[{self.name}] Failed to enqueue User Story message: {e}")


#     # -------------------------
#     # Run the workflow
#     # -------------------------
#     async def start_agent(self, document_path: Optional[str] = None, input_doc: Optional[dict] = None, conv_id: str = None):
#         if not conv_id:
#             raise ValueError("conv_id must be provided for persistent project")

#         inbox_queue = asyncio.Queue()

#         # Store document
#         if document_path and input_doc:
#             self.shared_state.store_document(conv_id, document_path, input_doc)
#             await self.send_progress(conv_id, {"step": "workflow_started", "message": "Workflow started, animation screen active"})

#         # Start consumer for agent messages
#         async def handler_wrapper(msg: dict):
#             await self.handle_message(msg, inbox_queue)
#         consumer_task = asyncio.create_task(self.message_broker.consume_queue(self.queue, handler_wrapper))

#         state: WorkflowState = {"conv_id": conv_id, "step": "start", "inbox": [], "iteration": 0}

#         try:
#             # Step 1: Elicitation
#             # Only trigger elicitation if we don't already have a document from the upload routes
#             if not input_doc:
#                 await self.send_progress(conv_id, {"step": "elicitation_start", "message": "Calling Elicitation agent"})
#                 await self.send_message("Elicitation", {"task": "initial elicit"}, type_="inform", conv_id=conv_id )
                
#                 # Increased timeout to 3600s (1 hour) to allow the user time to actually chat!
#                 reply = await self.wait_for_agent_reply(inbox_queue, "Elicitation", conv_id, timeout=3600.0)
#                 if reply: 
#                     state["inbox"].append(reply)
                    
#             # Retrieve the document (it will either be injected via the route, or saved by the elicitation agent)
#             input_doc = self.shared_state.get_document(conv_id)

#             iteration = 1
#             max_count = 3      ############# remove later
#             loop_condition = True
#             refinement_result = None
#             loop_count = "one"
#             input_doc = self.shared_state.get_document(conv_id)  # store once

#             while loop_condition:

#                 print(f"[Orchestrator] Iteration {iteration}")

#                 # -----------------------------------------------------------
#                 # 1) DETERMINE LOOP COUNT / PASS TYPE
#                 # -----------------------------------------------------------
#                 if iteration == 1:
#                     loop_count = "initial"
#                 else:
#                     print(f"[Orchestrator] Refinement results(iter: {iteration}): ", refinement_result)
#                     if iteration == max_count - 1:
#                         loop_count = "final"
 
#                 if max_count == 2:
#                     loop_count = "one"
#                 # -----------------------------------------------------------
#                 # 2) SEND TO CDN AGENT
#                 # -----------------------------------------------------------
#                 if loop_count in ["initial", "one"]:
#                     payload = {"task": "cdn work", "document": input_doc}
#                     msg = "Sending initial document to CDN agent"
#                 elif loop_count == "final":
#                     payload = {"task": "cdn work", "refinement_results": refinement_result}
#                     msg = "Sending refinement results to CDN agent"

#                 await self.send_progress(conv_id, {"step": "cdn_start", "message": msg})
#                 await self.send_message("CDN", payload, type_="inform", conv_id=conv_id)

#                 # -----------------------------------------------------------
#                 # 3) WAIT FOR CDN REPLY
#                 # -----------------------------------------------------------
#                 while True:
#                     reply = await self.wait_for_agent_reply(
#                         inbox_queue, "CDN", conv_id, timeout=50.0
#                     )

#                     if not reply:
#                         break

#                     state["inbox"].append(reply)
#                     payload = reply.get("payload", {})

#                     if payload.get("analysis_complete"):
#                         await self.send_progress(conv_id, {
#                             "step": "cdn_complete",
#                             "message": "CDN analysis complete",
#                             "cdn_results_path": payload.get("cdn_results_path"),
#                         })
#                         break

#                 # -----------------------------------------------------------
#                 # 4) GET CDN RESULTS
#                 # -----------------------------------------------------------
#                 cdn_results = self.shared_state.get_cdn_results(conv_id)
#                 cdninputfile_path = cdn_results.get("cdn_results_path")
#                 issues_remaining = cdn_results.get("issues_remaining")

#                 print(f"[Orchestrator] CDN results path: {cdninputfile_path}")
#                 print(f"[Orchestrator] Issues remaining: {issues_remaining}")

#                 # -----------------------------------------------------------
#                 # 5) SEND TO REFINEMENT AGENT
#                 # -----------------------------------------------------------
#                 await self.send_progress(conv_id, {
#                     "step": "refinement_start",
#                     "message": "Calling Refinement agent"
#                 })

#                 await self.send_message(
#                     "Refinement",
#                     {
#                         "cdn_results_path": cdninputfile_path,
#                         "input_doc": input_doc["summary"],
#                         "issues_remaining": issues_remaining,
#                         "loop_count": loop_count
#                     },
#                     type_="inform",
#                     conv_id=conv_id
#                 )
        
#                 # -----------------------------------------------------------
#                 # 6) WAIT FOR REFINEMENT REPLY
#                 # -----------------------------------------------------------
#                 while True:
#                     reply = await self.wait_for_agent_reply(
#                         inbox_queue, "Refinement", conv_id, timeout=50.0
#                     )

#                     if not reply:
#                         print(f"[Orchestrator] No reply from Refinement, breaking loop")
#                         break

#                     state["inbox"].append(reply)
#                     payload = reply.get("payload", {})

#                     # Store both intermediate and final results
#                     results_path = payload.get("results_path")
#                     cleaned_classified = payload.get("cleaned_classified", [])
#                     if cleaned_classified is None:
#                         cleaned_classified = []
#                     analysis_complete = payload.get("analysis_complete", False)

#                     refinement_result = payload  # update refinement_result to pass to next CDN


#                     # Send to frontend
#                     if analysis_complete == False:
#                         await self.send_progress(conv_id, {
#                             "step": "refinement_progress",
#                             "message": "Intermediate refinement results available",
#                             "cleaned_classified": cleaned_classified,
#                             "results_path": results_path
#                         })
#                     elif analysis_complete ==  True:
#                         print("[Orchestrator] Refinement completed")
#                         await self.send_progress(conv_id, {
#                             "step": "refinement_complete",
#                             "message": "Refinement complete",
#                             "cleaned_count": len(cleaned_classified) if isinstance(cleaned_classified, list) else 0,
#                             "results_path": results_path
#                         })
#                         break


#                 # -----------------------------------------------------------
#                 # 7) CHECK TERMINATION CONDITIONS
#                 # -----------------------------------------------------------
#                 iteration += 1

#                 if issues_remaining == 0:
#                     print("[Orchestrator] No issues remaining → ending loop")
#                     loop_condition = False

#                 elif iteration >= max_count:
#                     print("[Orchestrator] Max iterations reached → ending loop")
#                     loop_condition = False



#             # Step 4: Document Agent and User Story Agent in parallel
#             await self.send_progress(conv_id, {"step": "doc_user_story_start", "message": "Calling Document & User Story agents"})

#             # document agent
#             final_requirement_set = self.shared_state.get_refinement_results(conv_id)
#             input_doc = self.shared_state.get_document(conv_id)

#             # cluster functional requirements before sending to document agent
#             # 1. extract functional requirements
#             requirements = final_requirement_set['cleaned_classified']['requirements']
#             functional_reqs = [req for req in requirements if req['type'] == 'Functional']
#             functional_reqs = [f'{req["id"]}: {req["text"]}' for req in functional_reqs] 
            
#             # 2. extract features using LLM
#             clustered_fr= []
#             try:
#                 clustered_fr = await extract_features(functional_reqs, f'requirement_clusters_{conv_id}.json')
#                 print(f"[{self.name}] Clustered Functional Requirements: {clustered_fr}")
#             except Exception as e:
#                 print(f"[{self.name}] Error in forming clusters: {e}")

#             # 3. pass the clusrered features to the document agent
#             await self.send_message(
#                 "Document",
#                 {"final_requirement_set": final_requirement_set, "input_doc": input_doc, "clustered_fr": clustered_fr},
#                 type_="inform",
#                 conv_id=conv_id
#             )
#             reply2 = await self.wait_for_agent_reply(inbox_queue, "Document", conv_id, timeout=50.0)
#             if reply2:
#                 state["inbox"].append(reply2)
#                 # SRS is now saved — safe to persist requirements
#                 try:
#                     final_reqs = self.shared_state.get_refinement_results(conv_id)
#                     cleaned = final_reqs.get("file_data") or final_reqs.get("cleaned_classified")
#                     if cleaned and cleaned.get("requirements"):
#                         payload = BulkCreateRequirementsRequest(
#                             requirements=[
#                                 {
#                                     "project_id": conv_id,
#                                     "text": r["text"],
#                                     "req_id": str(r["id"]),
#                                     "type": r.get("type", "functional").lower().replace("-", "_"),
#                                     "subtype": r.get("subtype", "Functional"),
#                                 }
#                                 for r in cleaned["requirements"]
#                                 if r.get("text")  # skip any empty entries
#                             ]
#                         )
#                         await send_requirements_to_route(payload.dict(), conv_id)
#                         print(f"[Orchestrator] Requirements saved to DB for conv={conv_id}")
#                     else:
#                         print(f"[Orchestrator] No requirements found in refinement results — skipping save")
#                 except Exception as e:
#                     print(f"[Orchestrator] Error saving requirements: {e}")
#                     import traceback; traceback.print_exc()


#             # user story agent
#             await self.send_message("User_Story", {"task": "create user stories"}, type_="inform", conv_id=conv_id)
#             print(f"[Orchestrator]  Waiting for User_Story reply (conv={conv_id})")  # ← ADD

#             reply1 = await self.wait_for_agent_reply(inbox_queue, "User_Story", conv_id, timeout=100.0)
#             print(f"[Orchestrator] User_Story reply received: {reply1}")  # ← ADD

#             if reply1: 
#                 state["inbox"].append(reply1)

#             print(f"[Orchestrator] Past User_Story block, about to generate report")  # ← ADD


        
#             await self.send_progress(conv_id, {"step": "workflow_complete", "message": "Workflow complete, results ready"})
#             return {"conv_id": conv_id, "status": "completed", "messages_received": len(state["inbox"])}

#         finally:
#             consumer_task.cancel()
#             try: await consumer_task
#             except asyncio.CancelledError: pass

# '''
#             # Cleanup local files but keep WebSocket alive
#             for folder in ["./agents/cdn/data", "./agents/cdn/results", "./agents/refinement/results"]:
#                 if os.path.exists(folder) and os.path.isdir(folder):
#                     for f in os.listdir(folder):
#                         fpath = os.path.join(folder, f)
#                         if os.path.isfile(fpath):
#                             try: os.remove(fpath)
#                             except: pass
#                 else:
#                     print(f"[{self.name}] Cleanup folder does not exist: {folder}")

#                 '''




#             # # Generate summary report
#             # try:
#             #     self.report_generator.build_summary(conv_id)
#             #     try:
#             #         await add_report_to_project(conv_id)
#             #     except Exception as e:
#             #         print(f"[{self.name}] Error saving report to DB: {e}")
#             # except Exception as e:
#             #     print(f"[{self.name}] Error generating summary report: {e}")