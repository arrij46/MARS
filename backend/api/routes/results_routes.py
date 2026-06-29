"""
Results routes for fetching analysis and refinement results.
"""
import json
import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from datetime import datetime

from databaseSchema.db_instance import get_db_instance
from orchestrator.shared_state import get_shared_state
from databaseSchema.schema import UpdateRequirementRequest
from agents.userStory.utils.pdf_generator import generate_user_story_pdf

# Initialize router
router = APIRouter(tags=["Results"])


@router.get("/requirements_file")
async def get_requirements_file(conv_id: str = None):
    """Get requirements file for a conversation (defaults to last registered project)."""
    from api.routes.upload_routes import conversation_id
    active_id = conv_id or conversation_id
    if not active_id:
        return {"requirements": [], "clusters": []}
    path_req = f"./agents/refinement/results/classified_refinement_{active_id}.json"
    path_cluster = f"./agents/document/results/requirement_clusters_{active_id}.json"

    data={}
    if os.path.exists(path_req):
        with open(path_req, "r", encoding="utf-8") as f:
            data["requirements"] = json.load(f)
    
    if os.path.exists(path_cluster):
        with open(path_cluster, "r", encoding="utf-8") as f:
            data["clusters"] = json.load(f)
    if data:
        return data    
    else:
        print("[API] path not found")
        return {"requirements": [], "clusters": []}


@router.get("/cdn_results")
async def get_cdn_results():
    """Get CDN (Conflict/Dependency/Neutral) analysis results from the most recent workflow"""
    shared_state = get_shared_state()
    
    if not shared_state.conversations:
        return {"status": "processing", "message": "No analysis completed yet"}
    
    # Get the most recent conversation ID
    most_recent_conv_id = list(shared_state.conversations.keys())[-1]
    conv = shared_state.conversations[most_recent_conv_id]
    
    # Check if CDN results are available
    cdn_results_path = conv.get("cdn_results_path")
    cdn_results = conv.get("cdn_results")
    
    if cdn_results_path and os.path.exists(cdn_results_path):
        try:
            with open(cdn_results_path, "r", encoding="utf-8") as f:
                results_data = json.load(f)
            
            transformed_results = transform_cdn_results_for_frontend(results_data)
            return {
                "status": "completed",
                "conv_id": most_recent_conv_id,
                **transformed_results
            }
        except Exception as e:
            print(f"[API] Error loading results: {e}")
            return {"status": "error", "message": f"Error loading results: {str(e)}"}
    elif cdn_results:
        transformed_results = transform_cdn_results_for_frontend(cdn_results)
        return {
            "status": "completed",
            "conv_id": most_recent_conv_id,
            **transformed_results
        }
    else:
        return {"status": "processing", "message": "Analysis in progress"}


@router.get("/cdn_results/{conv_id}")
async def get_cdn_results(conv_id: str):
    """Get CDN analysis results for a specific conversation"""
    cdn_results_path = f"./agents/cdn/results/cdn_results_{conv_id}.json"

    if not os.path.exists(cdn_results_path):
        return {"status": "error", "message": f"Results file not found for conv_id: {conv_id}"}

    try:
        with open(cdn_results_path, "r", encoding="utf-8") as f:
            results_data = json.load(f)

        transformed_results = transform_cdn_results_for_frontend(results_data)
        return {
            "status": "completed",
            "conv_id": conv_id,
            **transformed_results
        }
    except Exception as e:
        print(f"[API] Error loading results: {e}")
        return {"status": "error", "message": f"Error loading results: {str(e)}"}
    

@router.get("/cdn_requirements_comparison/{conv_id}")
async def get_cdn_requirements_comparison(conv_id: str):
    """
    Compare original CDN requirements with refined requirements.
    Extracts ONLY valid requirement statements from both sources,
    ignoring headings, labels, metadata, and structural noise.
    """

    import os
    import re
    import json

    # =========================
    # FILE PATHS
    # =========================

    cdn_results_file = f"./agents/cdn/data/cdn_initial_input_{conv_id}.json"
    refined_file = f"./agents/refinement/results/cdn_cleaned_{conv_id}.json"

    # =========================
    # REQUIREMENT VALIDATION
    # =========================

    # Keywords that strongly suggest a valid requirement statement
    REQUIREMENT_KEYWORDS = re.compile(
        r"\b(shall|should|must|can|allow|provide|enable|support|ensure|maintain|"
        r"restrict|display|enforce|validate|encrypt|connect|communicate|implement|"
        r"replicate|guarantee|log|notify|generate|extract|export|upload|download)\b",
        re.IGNORECASE,
    )

    # Patterns that mark a line as structural noise to discard
    NOISE_PATTERNS = [
        re.compile(r"^\s*\[.*?\]\s*$"),               # [Cluster 1], [Section]
        re.compile(r"^={3,}"),                         # ===== separators
        re.compile(r"^-{3,}"),                         # --- separators
        re.compile(r"^\s*#+\s"),                        # ## Markdown headings
        re.compile(r"^\s*cluster\s*[:\d]", re.I),      # Cluster: / Cluster 1
        re.compile(r"^\s*requirements?\s*[:\d]", re.I),# Requirements: label
        re.compile(r"^\s*(section|heading|title)\s*:", re.I),
        re.compile(r"^\s*\*\s*$"),                     # lone bullet
        re.compile(r"^\s*\d+\.\s*$"),                  # lone number "1."
        re.compile(r"^\s*req[-_]?\d+\s*$", re.I),      # Req-1 / R1
    ]

    def is_noise(text: str) -> bool:
        """Return True if the text is structural noise, not a requirement."""
        stripped = text.strip()
        if not stripped:
            return True
        for pattern in NOISE_PATTERNS:
            if pattern.match(stripped):
                return True
        # Very short text is almost certainly a label/heading
        if len(stripped.split()) < 5:
            return True
        return False

    def is_valid_requirement(text: str) -> bool:
        """Return True only if text looks like a real requirement sentence."""
        if is_noise(text):
            return False
        return bool(REQUIREMENT_KEYWORDS.search(text))

    # =========================
    # TEXT CLEANING
    # =========================

    # Prefixes to strip from requirement text
    PREFIX_PATTERNS = [
        re.compile(r"^\d+[\.\)]\s+"),          # "1. " / "1) "
        re.compile(r"^Req[-_]?\d+\s*:\s*", re.I),  # "Req-1: " / "Req1:"
        re.compile(r"^R\d+\s*:\s*", re.I),     # "R1: "
        re.compile(r"^[-*•]\s+"),               # bullet symbols
        re.compile(r"^\[.*?\]\s*"),             # leading [label]
    ]

    def clean_text(text: str) -> str:
        """Strip numbering, bullets, and extra whitespace; preserve original casing."""
        text = text.strip()
        for pattern in PREFIX_PATTERNS:
            text = pattern.sub("", text).strip()
        # Collapse multiple spaces
        text = re.sub(r" {2,}", " ", text)
        return text

    def normalize(text: str) -> str:
        """Lowercase + strip punctuation for comparison only."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s]", "", text)    # remove punctuation
        text = re.sub(r"\s+", " ", text)
        return text

    # =========================
    # JSON RECURSIVE EXTRACTION
    # =========================

    REQUIREMENT_KEYS = {"text", "requirement", "content", "statement"}
    SKIP_KEYS = {"cluster", "heading", "title", "type", "metadata", "id",
                 "cluster_id", "req_number", "status"}

    def extract_from_json(obj) -> list[str]:
        """
        Recursively walk any JSON structure and collect strings
        found under recognised requirement keys, or bare strings
        that pass the validity check.
        """
        results = []

        if isinstance(obj, str):
            cleaned = clean_text(obj)
            if is_valid_requirement(cleaned):
                results.append(cleaned)

        elif isinstance(obj, list):
            for item in obj:
                results.extend(extract_from_json(item))

        elif isinstance(obj, dict):
            # Prioritise known requirement keys
            for key in REQUIREMENT_KEYS:
                if key in obj:
                    val = obj[key]
                    if isinstance(val, str):
                        cleaned = clean_text(val)
                        if is_valid_requirement(cleaned):
                            results.append(cleaned)
                    else:
                        results.extend(extract_from_json(val))

            # Recurse into other keys, skipping structural ones
            for key, val in obj.items():
                if key in REQUIREMENT_KEYS or key in SKIP_KEYS:
                    continue
                results.extend(extract_from_json(val))

        return results

    # =========================
    # LOAD & EXTRACT: ORIGINAL
    # =========================

    if not os.path.exists(cdn_results_file):
        return {
            "status": "error",
            "message": f"CDN results file not found: {cdn_results_file}",
        }

    original_requirements_raw: list[str] = []
    ignored_original = 0

    try:
        with open(cdn_results_file, "r", encoding="utf-8") as f:
            cdn_data = json.load(f)

        # Use the same recursive extractor for the original file too
        original_requirements_raw = extract_from_json(cdn_data)

    except json.JSONDecodeError:
        # Fallback: treat as plain text (legacy format)
        try:
            with open(cdn_results_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                cleaned = clean_text(line)
                if is_valid_requirement(cleaned):
                    original_requirements_raw.append(cleaned)
                else:
                    ignored_original += 1

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error reading CDN results: {str(e)}",
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error reading CDN results: {str(e)}",
        }

    # Deduplicate while preserving order
    seen = set()
    original_requirements: list[dict] = []
    for req in original_requirements_raw:
        key = normalize(req)
        if key not in seen:
            seen.add(key)
            original_requirements.append({
                "req_number": len(original_requirements) + 1,
                "requirement": req,
                "cluster_id": "N/A",
            })

    # =========================
    # LOAD & EXTRACT: REFINED
    # =========================

    refined_requirements_raw: list[str] = []
    ignored_refined = 0

    if os.path.exists(refined_file):
        try:
            with open(refined_file, "r", encoding="utf-8") as f:
                refined_data = json.load(f)

            refined_requirements_raw = extract_from_json(refined_data)

        except Exception as e:
            print(f"[API] Error reading refined file: {e}")
    else:
        print(f"[API] Refined file not found: {refined_file}")

    # Deduplicate refined list
    seen_refined = set()
    refined_requirements: list[str] = []
    for req in refined_requirements_raw:
        key = normalize(req)
        if key not in seen_refined:
            seen_refined.add(key)
            refined_requirements.append(req)

    # =========================
    # DEBUG LOGS
    # =========================

    print(f"[CDN Compare] Original extracted: {len(original_requirements)}")
    print(f"[CDN Compare] Refined extracted:  {len(refined_requirements)}")
    print(f"[CDN Compare] Original ignored:   {ignored_original}")
    print(f"[CDN Compare] Refined ignored:    {ignored_refined}")
    if original_requirements:
        print(f"[CDN Compare] Sample original[0]: {original_requirements[0]['requirement']}")
    if refined_requirements:
        print(f"[CDN Compare] Sample refined[0]:  {refined_requirements[0]}")

    # =========================
    # NORMALIZED REFINED SET
    # =========================

    refined_normalized: list[str] = [normalize(r) for r in refined_requirements]

    # =========================
    # MATCHING HELPERS
    # =========================

    def token_overlap_ratio(a: str, b: str) -> float:
        """
        Jaccard-style token overlap between two normalised strings.
        Returns a float in [0, 1].
        """
        tokens_a = set(a.split())
        tokens_b = set(b.split())
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union)

    SIMILARITY_THRESHOLD = 0.72  # tune as needed

    def matches_any_refined(original_norm: str) -> bool:
        """
        Two-stage match:
        1. Exact normalized match (or substring containment)
        2. Token-overlap similarity fallback
        """
        # Stage 1 – exact / containment
        for ref_norm in refined_normalized:
            if original_norm == ref_norm:
                return True
            # Containment in either direction (handles slight trimming)
            if original_norm in ref_norm or ref_norm in original_norm:
                return True

        # Stage 2 – similarity fallback
        for ref_norm in refined_normalized:
            if token_overlap_ratio(original_norm, ref_norm) >= SIMILARITY_THRESHOLD:
                return True

        return False

    # =========================
    # COMPARE
    # =========================

    comparison_results = []

    for orig in original_requirements:
        original_text = orig["requirement"]
        original_norm = normalize(original_text)
        exists = matches_any_refined(original_norm)

        comparison_results.append({
            "req_number": orig["req_number"],
            "requirement": original_text,
            "cluster_id": orig["cluster_id"],
            "exists_in_refined": exists,
            "status": "kept" if exists else "removed",
        })

    # =========================
    # RESPONSE
    # =========================

    return {
        "status": "completed",
        "conv_id": conv_id,
        "original_count": len(original_requirements),
        "refined_count": len(refined_requirements),
        "kept_count": sum(1 for r in comparison_results if r["status"] == "kept"),
        "removed_count": sum(1 for r in comparison_results if r["status"] == "removed"),
        "requirements": comparison_results,
    }

@router.get("/refinement_results")
async def get_refinement_results():
    """Get refinement results from the most recent workflow"""
    shared_state = get_shared_state()

    if not shared_state.conversations:
        return {"status": "processing", "message": "No refinement completed yet"}

    most_recent_conv_id = list(shared_state.conversations.keys())[-1]
    conv = shared_state.conversations[most_recent_conv_id]

    refinement_results_path = conv.get("refinement_results_path")
    refinement_results = conv.get("refinement_results")
    results_data = None

    # Try reading from file first
    if refinement_results_path and os.path.exists(refinement_results_path):
        try:
            with open(refinement_results_path, "r", encoding="utf-8") as f:
                results_data = json.load(f)
        except Exception as e:
            print(f"[API] Error loading refinement results from file: {e}")
    else:
        print(f"[API] Refinement results file not found at: {refinement_results_path}")

    # Fallback to cached payload from agent
    if results_data is None and refinement_results:
        results_data = refinement_results

    if not results_data or "requirements" not in results_data:
        return {"status": "processing", "message": "Refinement in progress"}

    transformed_results = transform_refinement_for_frontend(results_data)

    return {
        "status": "completed",
        "conv_id": most_recent_conv_id,
        **transformed_results
    }


@router.post("/update_requirement")
async def update_requirement(req: UpdateRequirementRequest):
    """Update a requirement's text in the refinement results file"""
    shared_state = get_shared_state()
    
    if not shared_state.conversations:
        raise HTTPException(status_code=400, detail="No active conversation")

    most_recent_conv_id = list(shared_state.conversations.keys())[-1]
    conv = shared_state.conversations[most_recent_conv_id]

    path = conv.get("refinement_results_path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Results file not found")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        requirements = data.get("requirements", [])
        if req.index < 0 or req.index >= len(requirements):
            raise HTTPException(status_code=400, detail="Invalid requirement index")

        # Update the text
        requirements[req.index]["text"] = req.newText

        # Write back to file
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Also update in-memory state
        conv["refinement_results"]["requirements"] = requirements

        return {"status": "success", "updated_requirement": requirements[req.index]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------- Helper Functions -----------------

def transform_cdn_results_for_frontend(results_data: dict) -> dict:
    """Transform CDN analyzer results to frontend format"""
    siamese_results = results_data.get("siamese_results", {})
    
    # Flatten all pairs from all clusters
    all_pairs = []
    for cluster_id, pairs in siamese_results.items():
        for pair in pairs:
            # Ensure predicted_class is capitalized correctly
            predicted_class = pair.get("predicted_class", "Neutral")
            predicted_class = predicted_class.capitalize()
            
            all_pairs.append({
                "idx1": pair.get("idx1"),
                "idx2": pair.get("idx2"),
                "req1": pair.get("req1"),
                "req2": pair.get("req2"),
                "predicted_class": predicted_class,
                "confidence": pair.get("confidence", 0.0),
                "all_probabilities": pair.get("all_probabilities", {})
            })
    
    return {
        "siamese_results": siamese_results,
        "all_pairs": all_pairs,
        "metadata": results_data.get("metadata", {})
    }


def transform_refinement_for_frontend(results_data: dict) -> dict:
    """
    Transform refinement results JSON to frontend format:
    {
      "Functional": [{"id":..., "text":...}, ...],
      "Non-Functional": {
          "Performance": [...],
          "Security": [...],
          "Reliability": [...],
          "Usability": [...],
          "Other": [...]
      }
    }
    """
    output = {
        "Functional": [],
        "Non-Functional": {
            "Performance": [],
            "Security": [],
            "Reliability": [],
            "Usability": [],
            "Other": []
        }
    }
    
    requirements = results_data.get("requirements", [])

    for req in requirements:
        if not isinstance(req, dict):
            continue

        req_id = req.get("id")
        req_text = req.get("text")
        req_type = req.get("type")
        req_subtype = req.get("subtype") or "Other"

        if req_type == "Functional":
            output["Functional"].append({"id": req_id, "text": req_text})
        elif req_type == "Non-Functional":
            if req_subtype not in output["Non-Functional"]:
                output["Non-Functional"][req_subtype] = []
            output["Non-Functional"][req_subtype].append({"id": req_id, "text": req_text})

    return output


@router.get("/user_story/download")
async def download_user_story(conv_id: str = None):
    """Download the generated user story PDF"""
    from api.routes.upload_routes import conversation_id as global_conv_id
    shared_state = get_shared_state()
    
    # Use provided conv_id or fall back to global conversation_id
    active_conv_id = conv_id or global_conv_id
    
    if not active_conv_id:
        raise HTTPException(status_code=400, detail="No conversation ID available")
    
    # Get user story results from shared state
    user_story_results = shared_state.conversations.get(active_conv_id, {}).get("user_story_results", {})
    
    if not user_story_results:
        raise HTTPException(status_code=404, detail="User story results not found. Please generate user stories first.")
    
    pdf_path = user_story_results.get("pdf_path")
    
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="User story PDF file not found")
    
    print(f"[API] Downloading user story PDF from: {pdf_path}")
    
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"user_stories_{active_conv_id}.pdf"
    )

@router.get("/user_stories_file/{conv_id}")
async def get_user_stories_file(conv_id: str):
    """Get the generated user stories JSON file"""

    shared_state = get_shared_state()

    if not conv_id:
        return JSONResponse(
            status_code=400,
            content={"error": "No conversation ID provided"}
        )

    user_story_results = shared_state.conversations.get(conv_id, {}).get("user_story_results", {})

    print(f"[API] Fetching user story results for conversation ID: {conv_id}")
    print(f"[API] User story results found: {bool(user_story_results)}")
    #print(f"[API] User story results: {user_story_results}")

    if not user_story_results:
        return JSONResponse(
            status_code=404,
            content={"error": "User story results not found. Please generate user stories first."}
        )

    file_data = user_story_results.get("file_data") or {}
    user_stories = (
        file_data.get("user_stories")
        or user_story_results.get("user_stories")
        or []
    )
    # file_data.metadata contains pipeline output metadata; keep it when available.
    metadata_from_file = file_data.get("metadata") or {}

    return {
        "status": "completed",
        "conv_id": conv_id,
        "user_stories": user_stories,
        "metadata": {
            **metadata_from_file,
            **user_story_results.get("metadata", {}),
            "project_name": (
                user_story_results.get("project_name")
                or metadata_from_file.get("project_name")
                or "User Stories Report"
            )
        }
    }

@router.get("/evaluation_results/{conv_id}")
async def get_evaluation_results(conv_id: str):
    """Return evaluation results JSON for a conversation"""

    file_path = f"agents/userStory/results/evaluation_{conv_id}.json"

    if not os.path.exists(file_path):
        return JSONResponse(
            status_code=404,
            content={"error": "Evaluation results not found"}
        )

    with open(file_path, "r") as f:
        data = json.load(f)

    return {
        "status": "completed",
        "conv_id": conv_id,
        "evaluations": data.get("story_level_results", [])
    }

# save the summary report to db
async def add_report_to_project(conv_id: str): 
    """
    Adds or updates the 'report' field of a project in the 'projects' collection.
    Reads the report from a local JSON file.
    """
    db = get_db_instance()
    report_file_path = f"./results/final_summary_report_{conv_id}.json"

    try:
        with open(report_file_path, "r", encoding="utf-8") as f:
            report_data = json.load(f)
    except Exception as e:
        print(f"[API] Failed to load report JSON: {e}")
        return {"success": False, "error": "Failed to read report file"}

    result = await db.projects.update_one(
        {"project_id": conv_id},
        {
            "$set": {
                "report": report_data,
                "updated_at": datetime.now()
            }
        },
        upsert=False
    )

    if result.matched_count:
        print(f"[API] Report added/updated for project {conv_id}")
        return {"success": True}
    else:
        print(f"[API] Project {conv_id} not found. Cannot add report.")
        return {"success": False, "error": "Project not found"}


