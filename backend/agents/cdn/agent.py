"""
cdn_agent.py

CDN Agent with integrated validation.
Runs Siamese neural network classifier and applies rule-based validation.
"""

import asyncio
import os
import json
import sys
from pathlib import Path
from agents.base_agent import BaseAgent
from typing import Dict
from pathlib import Path
import concurrent.futures

from agents.cdn.fsarc import FSARCService

# Set current directory paths for imports
_current_dir = Path(__file__).parent
_backend_dir = _current_dir.parent.parent
sys.path.insert(0, str(_current_dir))
sys.path.insert(0, str(_backend_dir))

# Setup backend.siameseModel module path for imports
if 'backend' not in sys.modules:
    import types
    sys.modules['backend'] = types.ModuleType('backend')
if 'backend.siameseModel' not in sys.modules:
    import types
    sys.modules['backend.siameseModel'] = types.ModuleType('backend.siameseModel')
    import importlib.util
    model_spec = importlib.util.spec_from_file_location(
        "backend.siameseModel.model",
        str(_current_dir / "siameseModel" / "model.py")
    )
    model_module = importlib.util.module_from_spec(model_spec)
    sys.modules['backend.siameseModel.model'] = model_module
    model_spec.loader.exec_module(model_module)

# Load analyzer dynamically
try:
    import importlib.util
    analyzer_spec = importlib.util.spec_from_file_location(
        "CD_ClusterSiameseAnalyzer",
        str(_current_dir / "CD-ClusterSiameseAnalyzer.py")
    )
    analyzer_module = importlib.util.module_from_spec(analyzer_spec)
    sys.modules["CD_ClusterSiameseAnalyzer"] = analyzer_module
    analyzer_spec.loader.exec_module(analyzer_module)
    DirectClusteringSiameseAnalyzer = analyzer_module.DirectClusteringSiameseAnalyzer
    print(f"[CDN] Successfully loaded DirectClusteringSiameseAnalyzer")
except Exception as e:
    print(f"[CDN] Error loading analyzer: {e}")
    import traceback
    traceback.print_exc()
    raise

# Import validator components
try:
    from requirement_validator import RequirementValidator, HybridDecisionEngine
    print(f"[CDN] Successfully loaded RequirementValidator")
except ImportError as e:
    print(f"[CDN] Error loading validator: {e}")
    print(f"[CDN] Make sure requirement_validator.py is in the same directory")
    raise


class CDNAgent(BaseAgent):
    """
    CDN Agent - Conflict and Duplicate Detection using Neural Networks + Validation
    
    Pipeline:
    1. Run Siamese neural network classifier on requirement pairs
    2. Apply rule-based validator to verify predictions
    3. Use hybrid decision engine to produce final corrected labels
    4. Output results in same format as original (backward compatible)
    """
    
    def __init__(self):
        super().__init__(name="CDN", exchange="agents-exchange", queue="CDN")
        self.ORCHESTRATOR_QUEUE = "Orchestrator"
        self._analyzer = None
        self._validator = RequirementValidator()
        self._decision_engine = HybridDecisionEngine()

    async def handle_message(self, msg: dict):
        """Handle incoming A2A messages"""
        conv_id = msg.get("conv_id", "unknown")
        payload = msg.get("payload", {})
        document = payload.get("document")
        refinement_results = payload.get("refinement_results")
        print("[CDN] Refinement results recieved: ", refinement_results)
        print("[CDN] Recieved document for analysis", document)

        print(f"[{self.name}] Received task: {payload.get('task', 'unknown')}")

        if document or refinement_results:

            print(f"[{self.name}] Document included — running CDN analysis for conv={conv_id}")
            try:
                if document:    
                    results = await self.run_cdn_analysis_fsarc(document, conv_id, "initial")
                elif refinement_results:
                    results = await self.run_cdn_analysis_fsarc(refinement_results, conv_id, "intermediate")
                await self.send_message(
                    receiver="Orchestrator",
                    payload={
                        "status": "done",
                        "from": self.name,
                        "has_document": True,
                        "analysis_complete": True,
                        "cdn_results_path": results.get("cdn_results_path"),
                        "clusters_count": results.get("clusters_count", 0),
                        "total_pairs": results.get("total_pairs", 0),
                        "validated_pairs": results.get("validated_pairs", 0),
                        "corrections_made": results.get("corrections_made", 0),
                        "issues_remaining":results.get("issues_remaining", 0)
                    },
                    type_="confirm",
                    conv_id=conv_id
                )
            except Exception as e:
                print(f"[{self.name}] Error during CDN analysis: {str(e)}")
                import traceback
                traceback.print_exc()
                await self.send_message(
                    receiver="Orchestrator",
                    payload={"status": "error", "from": self.name, "error": str(e)},
                    type_="error",
                    conv_id=conv_id
                )
        else:
            print(f"[{self.name}] No document provided — running lightweight/no-doc mode")
            await asyncio.sleep(0.5)
            await self.send_message(
                receiver="Orchestrator",
                payload={"status": "done", "from": self.name, "has_document": False},
                type_="confirm",
                conv_id=conv_id
            )

    async def run_cdn_analysis(self, document: dict, conv_id: str, state) -> dict:
        """
        Run complete CDN analysis pipeline with validation.
        
        Steps:
        1. Initialize Siamese analyzer
        2. Run neural network classification
        3. Apply rule-based validation
        4. Produce corrected results
        5. Save to JSON (same format as original)
        """
        print(f"[{self.name}] Starting CDN analysis for conv={conv_id}")

        # Initialize analyzer if not already done
        if self._analyzer is None:
            model_dir = str(_current_dir / "model")
            if not os.path.exists(model_dir):
                model_dir = "model"
            self._analyzer = DirectClusteringSiameseAnalyzer(
                model_dir=model_dir, 
                dropout_rate=0.3, 
                pooling_strategy='mean'
            )
            print(f"[{self.name}] Analyzer instance created")

        analyzer = self._analyzer
        requirements_data = []
        total_requirements = 0
        # Prepare input JSON file
        if state == "initial":
            requirements_data = {"requirements": document.get("requirements", [])}
            total_requirements = len(requirements_data["requirements"])

        elif state == "intermediate":
            # document is already {"requirements": cleaned}

            cleaned = document.get("cleaned_classified", [])
            requirements_data = {"requirements": cleaned}
            total_requirements = len(cleaned)


        print(f"[CDN] requirements recieved by CDN from state: {state} {requirements_data}, \n\ntotal requirements: {total_requirements}")

        temp_json_path = str(_current_dir / "data" / f"cdn_analysis_{conv_id}.json")
        os.makedirs(os.path.dirname(temp_json_path), exist_ok=True)
        
        if state == "intermediate":
            cleaned_list = document.get("cleaned_classified", [])
            print("[CDN]cleaned list: ",cleaned_list)
            # Convert strings → objects with id + text
            structured_requirements = [
                {"id": i + 1, "text": req}
                for i, req in enumerate(cleaned_list)
            ]

            requirements_data = {"requirements": structured_requirements}
            total_requirements = len(structured_requirements)

        with open(temp_json_path, "w", encoding="utf-8") as f:
            json.dump(requirements_data, f, indent=2, ensure_ascii=False)

        print(f"[{self.name}] Created requirements file: {temp_json_path}")
                
        # Output directory
        try:
            results_dir = _current_dir / "results"
            os.makedirs(results_dir, exist_ok=True)
            output_file = str(results_dir / f"cdn_results_{conv_id}.txt")
        except Exception as e:
            print(f"[{self.name}] Error creating CDN results directory: {e}")
            raise    

        # Run Siamese analysis in thread pool
        print(f"[{self.name}] Running Siamese neural network classifier...")
        import concurrent.futures
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            await loop.run_in_executor(
                executor,
                analyzer.run_complete_analysis,
                temp_json_path,
                output_file,
                None
            )

        # Get original Siamese results
        original_siamese_results = getattr(analyzer, 'siamese_results', {})
        #print(f"[{self.name}] 11111111111111111 Retrieved original Siamese results: {original_siamese_results}")

        original_pairs_count = sum(len(pairs) for pairs in original_siamese_results.values())
        print(f"[{self.name}] ML classification complete: {original_pairs_count} pairs analyzed")
        
        # Apply validation and correction
        print(f"[{self.name}] Applying rule-based validation...")
        corrected_siamese_results = self._decision_engine.validate_and_correct_results(
            original_siamese_results, 
            self._validator
        )
        #print(f"[{self.name}] 22222222222222222 Corrected Siamese results after validation: {corrected_siamese_results}")
        
        # Count corrections made
        corrections_made = 0
        for cluster_id, pairs in corrected_siamese_results.items():
            for pair in pairs:
                if pair.get("validation_info", {}).get("was_corrected", False):
                    corrections_made += 1

        # Collect metadata
        clusters_count = len(set(analyzer.clusters.values())) if analyzer.clusters else 0
        total_pairs = sum(len(pairs) for pairs in corrected_siamese_results.values())

        duplicate_count = 0
        conflict_count = 0

        for pair_list in corrected_siamese_results.values():  # each value is a list of pair objects
            for item in pair_list:
                final_label = (
                    item.get("validation_info", {}).get("final_label", "").lower()
                )
                if final_label == "duplicate":
                    duplicate_count += 1
                elif final_label == "conflict":
                    conflict_count += 1   


        issues_remaining = duplicate_count + conflict_count             

        # Save corrected results to JSON (SAME FORMAT AS ORIGINAL)
        json_output_file = str(results_dir / f"cdn_results_{conv_id}.json")
        final_output = {
            "metadata": {
                "total_requirements": total_requirements,
                "total_clusters": clusters_count,
                "clustering_method": "kmeans_direct",
                "validation_applied": True,
                "total_pairs_validated": total_pairs,
                "corrections_made": corrections_made
            },
            "clusters": analyzer.clusters_output if hasattr(analyzer, 'clusters_output') else {},
            "siamese_results": corrected_siamese_results  # CORRECTED RESULTS WITH VALIDATION INFO
        }
        
        with open(json_output_file, "w", encoding="utf-8") as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)

        print(f"[{self.name}] Saved corrected results to: {json_output_file}")


        print(f"[{self.name}] Analysis complete:")
        print(f"  - Clusters: {clusters_count}")
        print(f"  - Pairs validated: {total_pairs}")
        print(f"  - Corrections made: {corrections_made}")
        
        return {
            "cdn_results_path": json_output_file,
            "text_results_path": output_file,
            "clusters_count": clusters_count,
            "total_pairs": total_pairs,
            "validated_pairs": total_pairs,
            "corrections_made": corrections_made,
            "siamese_results": corrected_siamese_results,
            "issues_remaining": issues_remaining
        }

    async def run_cdn_analysis_fsarc(self, document: dict, conv_id: str, state) -> dict:
        print(f"[{self.name}] Starting CDN+FSARC analysis for conv={conv_id}")

        # -----------------------------
        # 1. Initialize Siamese Analyzer
        # -----------------------------
        if self._analyzer is None:
            model_dir = str(Path(__file__).parent / "model")
            if not os.path.exists(model_dir):
                model_dir = "model"

            self._analyzer = DirectClusteringSiameseAnalyzer(
                model_dir=model_dir,
                dropout_rate=0.3,
                pooling_strategy="mean",
            )
            print(f"[{self.name}] Analyzer initialized")

        analyzer = self._analyzer
        fsarc = FSARCService()

        # -----------------------------
        # 2. Prepare + normalize requirements (CDN output boundary)
        # -----------------------------
        raw_requirements = []
        if state == "initial":
            raw_requirements = document.get("requirements", [])
        else:
            raw_requirements = document.get("cleaned_classified", [])

        requirements = []
        if isinstance(raw_requirements, list):
            for i, r in enumerate(raw_requirements):
                if isinstance(r, dict):
                    text = r.get("text") or r.get("requirement") or r.get("content") or ""
                    rid = r.get("id", i + 1)
                else:
                    text = r
                    rid = i + 1
                text = (text or "").strip()
                if text:
                    requirements.append({"id": rid, "text": text})

        total_requirements = len(requirements)
        if total_requirements == 0:
            print(f"[{self.name}] CDN+FSARC skipped (no requirements) conv={conv_id}")
            return {
                "conv_id": conv_id,
                "fsarc_labels": [],
                "confidence_scores": [],
                "trace": {
                    "stage": "cdn_to_fsarc",
                    "reason": "empty_or_malformed_requirements",
                    "requirements_in": type(raw_requirements).__name__,
                    "requirements_count": 0,
                },
            }
        temp_json = ''
        if state == "initial":
            temp_json =  Path(__file__).parent / "data" / f"cdn_initial_input_{conv_id}.json"
        else:
            temp_json = Path(__file__).parent / "data" / f"cdn_input_{conv_id}.json"
        temp_json.parent.mkdir(exist_ok=True)
        with open(temp_json, "w", encoding="utf-8") as f:
            json.dump({"requirements": requirements}, f, indent=2, ensure_ascii=False)

        # -----------------------------
        # 3. Run Siamese NN (non-blocking)
        # -----------------------------
        output_file = Path(__file__).parent / "results" / f"cdn_results_{conv_id}.txt"
        output_file.parent.mkdir(exist_ok=True)

        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            await loop.run_in_executor(
                executor,
                analyzer.run_complete_analysis,
                str(temp_json),
                str(output_file),
                None,
            )

        siamese_results = analyzer.siamese_results or {}
        print(f"[{self.name}] NN completed conv={conv_id}")

        # -----------------------------
        # 4. FSARC semantic validation (FSARC input boundary)
        #    - run FSARC in executor (FSARC is sync + heavy)
        #    - defensive string extraction to avoid FSARC model/patching errors
        # -----------------------------
        def _req_to_text(x) -> str:
            if x is None:
                return ""
            if isinstance(x, str):
                return x.strip()
            if isinstance(x, dict):
                return str(
                    (x.get("text") or x.get("requirement") or x.get("content") or "")
                ).strip()
            return str(x).strip()

        fsarc_connection_failed = False
        async def _fsarc_check_safe(req1_txt: str, req2_txt: str) -> dict:
            if not req1_txt or not req2_txt:
                return {"is_conflict": False, "reason": "empty_req_text"}
            nonlocal fsarc_connection_failed
            if fsarc_connection_failed:
                return {"is_conflict": False, "reason": "fsarc_unavailable"}
            try:
                return await loop.run_in_executor(executor, fsarc.check, req1_txt, req2_txt)
            except Exception as e:
                # Minimal logging: one-line error, preserve trace, never crash pipeline
                err_type = type(e).__name__
                # ConnectionError usually means CoreNLP server isn't running (FSARC uses localhost:9999)
                if err_type == "ConnectionError":
                    fsarc_connection_failed = True
                    print(f"[{self.name}] FSARC unavailable (CoreNLP server?) conv={conv_id}: ConnectionError")
                else:
                    print(f"[{self.name}] FSARC error conv={conv_id}: {err_type}")
                return {"is_conflict": False, "error": type(e).__name__}

        fsarc_labels = []
        confidence_scores = []
        escalated = 0
        fsarc_errors = 0

        # Keep original structure around if other parts of system rely on it,
        # but ensure function returns a single structured dict for agent handoff.
        fsarc_corrected = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for cluster_id, pairs in (siamese_results.items() if isinstance(siamese_results, dict) else []):
                fsarc_corrected[cluster_id] = []
                if not isinstance(pairs, list):
                    continue

                for pair in pairs:
                    if not isinstance(pair, dict):
                        continue

                    predicted = (pair.get("predicted_class") or "").lower().strip()
                    confidence = float(pair.get("confidence") or 0.0)

                    # Normalize req texts to avoid FSARC "patching"/shape failures
                    req1_txt = _req_to_text(pair.get("req1"))
                    req2_txt = _req_to_text(pair.get("req2"))

                    final_label = predicted or "neutral"
                    fsarc_result = None

                    # Only escalate predicted conflict or low-confidence cases into FSARC
                    if final_label == "conflict" or confidence < 0.75:
                        escalated += 1
                        fsarc_result = await _fsarc_check_safe(req1_txt, req2_txt)
                        if fsarc_result.get("error"):
                            fsarc_errors += 1
                        if fsarc_result.get("is_conflict") is True:
                            final_label = "conflict"

                    # Attach minimal provenance to the pair without changing upstream keys
                    pair["final_label"] = final_label
                    if fsarc_result is not None:
                        pair["fsarc"] = fsarc_result

                    fsarc_corrected[cluster_id].append(pair)

                    # Agent-level structured outputs
                    fsarc_labels.append(
                        {
                            "cluster_id": cluster_id,
                            "label": final_label,
                            "req1_text": req1_txt,
                            "req2_text": req2_txt,
                        }
                    )
                    confidence_scores.append(
                        {
                            "cluster_id": cluster_id,
                            "predicted_class": predicted or None,
                            "model_confidence": confidence,
                        }
                    )

        # -----------------------------
        # 5. Persist results (optional, same file naming)
        # -----------------------------
        clusters_count = len(set(analyzer.clusters.values())) if getattr(analyzer, "clusters", None) else 0
        total_pairs = sum(len(v) for v in fsarc_corrected.values()) if fsarc_corrected else 0

        json_output = Path(__file__).parent / "results" / f"cdn_results_{conv_id}.json"
        final_output = {
            "metadata": {
                "conv_id": conv_id,
                "total_requirements": total_requirements,
                "total_clusters": clusters_count,
                "validation_applied": "FSARC",
                "total_pairs": total_pairs,
                "fsarc_escalated_pairs": escalated,
                "fsarc_errors": fsarc_errors,
            },
            "clusters": getattr(analyzer, "clusters_output", {}),
            "siamese_results": fsarc_corrected,
        }
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)

        print(f"[{self.name}] CDN+FSARC analysis complete conv={conv_id}")

        # Return backward-compatible CDN keys for Orchestrator/SharedState,
        # plus structured FSARC handoff fields for downstream consumers.
        conflict_count = sum(1 for x in fsarc_labels if x.get("label") == "conflict")
        duplicate_count = sum(1 for x in fsarc_labels if x.get("label") == "duplicate")
        issues_remaining = conflict_count + duplicate_count

        return {
            # Backward compatible CDN/orchestrator fields (same structure as old run_cdn_analysis)
            "cdn_results_path": str(json_output),
            "text_results_path": str(output_file),  # Required for pipeline compatibility
            "clusters_count": clusters_count,
            "total_pairs": total_pairs,
            "validated_pairs": total_pairs,
            "corrections_made": 0,
            "siamese_results": fsarc_corrected,  # Required for pipeline compatibility
            "conflicts": conflict_count,
            "duplicates": duplicate_count,
            "issues_remaining": issues_remaining,

            # Structured FSARC outputs
            "conv_id": conv_id,
            "fsarc_labels": fsarc_labels,
            "confidence_scores": confidence_scores,
            "trace": {
                "cdn_output": {
                    "requirements_count": total_requirements,
                    "siamese_clusters": len(siamese_results) if isinstance(siamese_results, dict) else 0,
                    "siamese_pairs_total": total_pairs,
                    "results_path": str(json_output),
                },
                "fsarc_input": {
                    "escalation_policy": {"conflict_or_confidence_below": 0.75},
                    "escalated_pairs": escalated,
                },
                "fsarc_output": {
                    "fsarc_errors": fsarc_errors,
                    "fsarc_connection_failed": fsarc_connection_failed,
                },
            },
        }


    async def start_agent(self):
        """Start the agent and listen for messages"""
        print(f"[{self.name}] Pre-loading analyzer model...")
        try:
            model_dir = str(_current_dir / "model")
            if not os.path.exists(model_dir):
                model_dir = "model"
            self._analyzer = DirectClusteringSiameseAnalyzer(
                model_dir=model_dir, 
                dropout_rate=0.3, 
                pooling_strategy='mean'
            )
            print(f"[{self.name}] Model loaded successfully!")
        except Exception as e:
            print(f"[{self.name}] WARNING: Failed to pre-load model: {e}")
            import traceback
            traceback.print_exc()
            self._analyzer = None

        print(f"[{self.name}] Agent started and listening on queue '{self.queue}'")
        await self.message_broker.consume_queue(self.queue, self.handle_message)
