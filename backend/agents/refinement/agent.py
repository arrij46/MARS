"""
refinement_agent.py
Complete Refinement Agent with CDN Selection preprocessing,
Atomic Statement Generation, LLM Refinement, and Classification.
"""

import asyncio
import re
import json
import os
from typing import List, Dict, Tuple

# Base agent import
from agents.base_agent import BaseAgent

# Refinement pipeline components
from agents.refinement.atomic import AtomicStatementGenerator
from agents.refinement.llm_reasoner import LLMReasoner
from agents.refinement.classification import classify_requirements

# CDN Selection module
from agents.refinement.cdnSelection import CDNSelector

# For saving results to database
# from api.routes.project_routes import  send_requirements_to_route
# from databaseSchema.schema import BulkCreateRequirementsRequest


class RefinementAgent(BaseAgent):
    """
    Refinement Agent that processes requirements through a complete pipeline:
    1. CDN Selection (resolve conflicts/duplicates)
    2. Atomic Statement Generation
    3. LLM Refinement
    4. Classification
    """
    
    def __init__(self):
        super().__init__(name="Refinement", exchange="agents-exchange", queue="Refinement")
        self.ORCHESTRATOR_QUEUE = "Orchestrator"
        
        # Initialize pipeline components
        self.atomic_generator = AtomicStatementGenerator()
        self.llm = LLMReasoner()
        self.cdn_selector = CDNSelector()
        self.final_requirements = None
        self.conv_id = None
        # Ensure results directory exists
        os.makedirs("./agents/refinement/results", exist_ok=True)

    async def handle_message(self, msg: dict):
        """
        Refinement agent stages:

            initial pass --> cdn_selection + atomic generation
            middle pass  --> cdn_selection only
            final pass   --> cdn_selection + classification
        """

        conv_id = msg.get("conv_id", "unknown")
        self.conv_id = conv_id
        payload = msg.get("payload", {}) or {}

        cdn_pairs_path   = payload.get("cdn_results_path")
        issues_remaining = payload.get("issues_remaining")
        loop_count       = payload.get("loop_count")
        project_description = payload.get("input_doc", "")

        print(f"\n{'='*80}")
        print(f"[{self.name}] REFINEMENT AGENT ACTIVATED")
        print(f"{'='*80}")
        print(f"[{self.name}] Conversation ID: {conv_id}")
        print(f"[{self.name}] CDN pairs path: {cdn_pairs_path}")
        print(f"[{self.name}] Loop Count: {loop_count}")
        print(f"[{self.name}] Has project description: {bool(project_description)}")

        #await asyncio.sleep(0.3)

        # ================================
        # PREP WORK
        # ================================
        status = "processing"
        error_msg = None

        atomic_statements = []
        cleaned_requirements = []
        # cleaned_classified = None
        task_text = ""
        atomic_path = f"./agents/refinement/results/atomic_refinement_{conv_id}.json"
        cleaned_path = f"./agents/refinement/results/cdn_cleaned_{conv_id}.json"
        # final_output_path = f"./agents/refinement/results/cleaned_classified_refinement_{conv_id}.json"

        # ======================================================================
        # STEP 1 — CDN SELECTION PREPROCESSING (runs on every pass)
        # ======================================================================
        try:
            if cdn_pairs_path and os.path.exists(cdn_pairs_path):
                print(f"\n{'='*80}")
                print(f"[{self.name}] STEP 1: CDN SELECTION PREPROCESSING")
                print(f"{'='*80}\n")

                with open(cdn_pairs_path, "r", encoding="utf-8") as f:
                    cdn_data = json.load(f)

                # Extract pairs
                pairs = []
                siamese_results = cdn_data.get("siamese_results", {})

                for cluster_id, cluster_pairs in siamese_results.items():
                    for pair_obj in cluster_pairs:
                        final_label = pair_obj.get("validation_info", {}).get("final_label", "neutral")

                        pairs.append({
                            "req1": pair_obj.get("req1", ""),
                            "req2": pair_obj.get("req2", ""),
                            "label": final_label,
                            "confidence": pair_obj.get("confidence", 0.0)
                        })

                print(f"[{self.name}] Loaded {len(pairs)} pairs from {len(siamese_results)} clusters")

                # Run CDN selection
                cleaned_requirements = await asyncio.to_thread(
                    self.preprocess_with_cdn_selection,
                    pairs,
                    project_description
                )

                print(f"[{self.name}] CDN Selection complete --> {len(cleaned_requirements)} remain")

                # Store cleaned requirements
                with open(cleaned_path, "w", encoding="utf-8") as f:
                    json.dump({"requirements": cleaned_requirements}, f, indent=2, ensure_ascii=False)

                print(f"[{self.name}] Saved CDN-cleaned requirements --> {cleaned_path}")

                # Prepare raw text for later steps
                task_text = "\n".join(r.get("text", "") for r in cleaned_requirements)

            else:
                print(f"[{self.name}] No valid CDN pairs input. Skipping CDN preprocessing.")

        except Exception as e:
            print(f"[{self.name}] Error in CDN selection stage: {e}")
            error_msg = str(e)
            import traceback; traceback.print_exc()

        # ======================================================================
        # STEP 2 — ATOMIC GENERATION (ONLY on initial pass)
        # ======================================================================
        if loop_count in ["initial", "one"] and task_text:
            try:
                print(f"\n{'='*80}")
                print(f"[{self.name}] STEP 2: ATOMIC GENERATION")
                print(f"{'='*80}\n")

                # Build structured input — same as before
                reqs_for_atomization = [
                    {
                        "id":     r.get("id"),
                        "req_id": r.get("req_id", f"REQ-{r.get('id')}"),
                        "text":   r.get("text", ""),
                        "origin": r.get("origin", "extracted"),
                    }
                    for r in cleaned_requirements
                ]

                # Build origin lookup — unchanged
                origin_lookup = {str(r["id"]): r["origin"] for r in reqs_for_atomization}

                print(f"[{self.name}] Sending {len(reqs_for_atomization)} requirements for atomization")

                nlp_results = self.atomic_generator.process_requirements(reqs_for_atomization)

                flat_statements = []
                back_refs = []   # (result_index, statement_index)
                for i, result in enumerate(nlp_results):
                    for j, stmt in enumerate(result["atomic_statements"]):
                        flat_statements.append(stmt)
                        back_refs.append((i, j))

                print(f"[{self.name}] Running grammar correction on {len(flat_statements)} atomic statements")
                corrected_flat = await asyncio.to_thread(self.llm.fix_grammar, flat_statements)

                # Write corrected strings back into nlp_results
                for k, (i, j) in enumerate(back_refs):
                    nlp_results[i]["atomic_statements"][j] = corrected_flat[k]

                final_reqs = []
                print([r["id"] for r in reqs_for_atomization])
                new_id_counter = max(int(r["id"]) for r in reqs_for_atomization) + 1

                for result in nlp_results:
                    original_origin = origin_lookup.get(str(result["original_id"]), "extracted")

                    if not result["was_compound"] or len(result["atomic_statements"]) == 1:
                        # Not broken up — preserve as-is with origin tag
                        final_reqs.append({
                            "id":            int(result["original_id"].split("-")[-1]),  
                            "req_id":        result["original_id"],
                            "text":          result["atomic_statements"][0],
                            "origin":        original_origin,
                            "parent_req_id": None,
                            "parent_text":   None,
                        })
                    else:
                        # Was compound — assign new IDs, attach lineage to each child
                        for atomic_text in result["atomic_statements"]:
                            final_reqs.append({
                                "id":            new_id_counter,
                                "req_id":        f"REQ-{new_id_counter}",
                                "text":          atomic_text,
                                "origin":        [original_origin, "atomized"],
                                "parent_req_id": result["original_id"],
                                "parent_text":   result["original_text"],
                            })
                            new_id_counter += 1

                atomic_statements = final_reqs
                print(f"[{self.name}] Atomization complete: {len(atomic_statements)} requirements "
                        f"(from {len(reqs_for_atomization)} original)")

                self.save_to_json(atomic_statements, conv_id, atomic_path)

            except Exception as e:
                print(f"[{self.name}] Error in atomic stage: {e}")
                error_msg = str(e)
                import traceback; traceback.print_exc()
    # ======================================================================
        # STEP 3 — CLASSIFICATION (ONLY on final pass)
        # ======================================================================
        if loop_count in ["final", "one"]:
            try:
                print(f"\n{'='*80}")
                print(f"[{self.name}] STEP 3: CLASSIFICATION")
                print(f"{'='*80}\n")

                # Ensure atomic exists
                if not os.path.exists(atomic_path):
                    with open(atomic_path, "w", encoding="utf-8") as f:
                        json.dump({"requirements": []}, f, indent=2, ensure_ascii=False)

                classified_path = f"./agents/refinement/results/classified_refinement_{conv_id}.json"

                classified = classify_requirements(
                    input_path=cleaned_path if loop_count  in ["final", "one"] else atomic_path,
                    output_path=classified_path
                )

                print(f"[{self.name}] Final cleaned classification saved --> {classified_path}") # instead of final_output_path, send the direct output of classification (before llm cleaning) for better transparency and to avoid issues with llm cleaning in final pass
                status = "done"
              

            except Exception as e:
                print(f"[{self.name}] Error in final classification: {e}")
                error_msg = str(e)
                import traceback; traceback.print_exc()
        else:
             task_text = [req.strip() for req in task_text.split("\n") if req.strip()]

        # ======================================================================
        # SEND RESPONSE
        # ======================================================================
        print("[Refinement] Status: ",True if loop_count in ["final", "one"] else False )
        await self.send_message(
            receiver="Orchestrator",
            payload={
                "status": status,
                "from": self.name,
                "analysis_complete": True if loop_count in ["final", "one"] else False,
                "cleaned_classified": (
                    classified if loop_count in ["final", "one"]  # dont  use llm output at all, instead of cleaned_classified, to avoid issues with llm cleaning in final pass and to provide more transparency into the process. the raw output of classification (even if messy) is more informative than an empty/garbage cleaned output when llm cleaning fails.
                    else atomic_statements if loop_count == "initial" 
                    else task_text
                ),                
                "results_path": classified_path if loop_count in ["final", "one"] else atomic_path,# instead of final_output_path, send the direct output of classification (before llm cleaning) for better transparency and to avoid issues with llm cleaning in final pass
                "error": error_msg
            },
            type_="confirm",
            conv_id=conv_id
        )



    def preprocess_with_cdn_selection(
        self, 
        pairs: List[Dict], 
        project_description: str
    ) -> List[Dict]:
        """
        Preprocess CDN classified pairs to produce a clean, flat list of requirements.
        ...
        """
        # (unchanged implementation)
        # ... same as before ...
        # Renumber IDs sequentially
        # Note: keep id as integer for downstream consumers
        duplicates = []
        conflicts = []
        neutrals = []
        
        all_requirements = {}
        req_id_counter = 1
        
        for pair in pairs:
            req1_text = pair.get("req1", "")
            req2_text = pair.get("req2", "")
            label = pair.get("label", "neutral")
            
            req1 = {"id": f"REQ-{req_id_counter:03d}", "text": req1_text}
            req_id_counter += 1
            req2 = {"id": f"REQ-{req_id_counter:03d}", "text": req2_text}
            req_id_counter += 1
            
            if req1_text and req1_text not in all_requirements:
                all_requirements[req1_text] = req1
            if req2_text and req2_text not in all_requirements:
                all_requirements[req2_text] = req2
            
            if label == "duplicate":
                duplicates.append([
                    all_requirements.get(req1_text, req1),
                    all_requirements.get(req2_text, req2)
                ])
            elif label == "conflict":
                conflicts.append([
                    all_requirements.get(req1_text, req1),
                    all_requirements.get(req2_text, req2)
                ])
            else:
                if req1_text:
                    neutrals.append(all_requirements.get(req1_text, req1))
                if req2_text:
                    neutrals.append(all_requirements.get(req2_text, req2))
        
        selected_from_conflicts = []
        selected_from_duplicates = []
        
        if conflicts:
            selected_from_conflicts, _ = self.cdn_selector.resolve_conflicts(
                conflicts, project_description
            )
        
        if duplicates:
            selected_from_duplicates, _ = self.cdn_selector.resolve_duplicates(
                duplicates, project_description
            )
        
        selected_texts = set()
        final_requirements = []
        
        for req in selected_from_conflicts:
            req_text = req.get("text", "")
            if req_text and req_text not in selected_texts:
                selected_texts.add(req_text)
                final_requirements.append(req)
        
        for req in selected_from_duplicates:
            req_text = req.get("text", "")
            if req_text and req_text not in selected_texts:
                selected_texts.add(req_text)
                final_requirements.append(req)
        
        for req in neutrals:
            req_text = req.get("text", "")
            if req_text and req_text not in selected_texts:
                selected_texts.add(req_text)
                final_requirements.append(req)
        
        for idx, req in enumerate(final_requirements, 1):
            req["id"] = idx
        
        return final_requirements

    async def start_agent(self):
        """Start the agent and listen for messages on the queue"""
        print(f"\n{'='*80}")
        print(f"[{self.name}] AGENT STARTING")
        print(f"{'='*80}")
        print(f"[{self.name}] Queue: '{self.queue}'")
        print(f"[{self.name}] Exchange: '{self.exchange}'")
        print(f"[{self.name}] Waiting for messages...")
        print(f"{'='*80}\n")
        
        await self.message_broker.consume_queue(self.queue, self.handle_message)
 
# helper function to save results to JSON
    def save_to_json(self, statements: List[dict], conv_id: str, path):
        output = {
            "requirements": statements
        }
        with open(path, "w", encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"[{self.name}] Saved refinement results to: {path}")