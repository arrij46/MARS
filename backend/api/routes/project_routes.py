"""
Project and SRS document routes for managing project data and requirements.
"""
import os
import json
from datetime import datetime
from typing import Dict, Any, List
from flask import jsonify
import httpx
from api.routes.auth_routes import get_current_user

from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import APIRouter, HTTPException, Depends, status
from starlette.requests import Request
from bson import ObjectId

from agents.document.next_word_prediction.next_word_predictor import NextWordPredictor
from databaseSchema.schema import (
    BulkCreateRequirementsRequest,
    UpdateRequirementRequest
)

# Initialize router
router = APIRouter(prefix="/projects", tags=["Projects"])

# Initialize next word predictor (load model and tokenizer once)
predictor = NextWordPredictor(
    "./agents/document/next_word_prediction/next_word_prediction_model.keras",
    "./agents/document/next_word_prediction/tokenizer.pkl"
)

# ----------------- Database Dependency -----------------
def get_db(request: Request) -> AsyncIOMotorDatabase:
    """Get MongoDB database from FastAPI app"""
    return request.app.mongodb


# ----------------- SRS Document Routes -----------------

# this route is called from the document agent to save the generated SRS JSON directly to the database, 
# bypassing the usual API route that expects raw text input from the frontend.
#  The agent sends a fully-formed SRS JSON, which this route saves as-is without additional parsing or transformation.
@router.post("/{project_id}/srs/save")
async def save_srs_from_agent(
    project_id: str,
    payload: dict,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Agent calls this to save the already-parsed SRS JSON.
    Payload: The JSON returned from convert_srs_to_json()
    """
    try:
        srs_json = payload.get('srs_json')  # Already parsed JSON from agent
        if isinstance(srs_json, str):
            srs_json = json.loads(srs_json)
            
        project_description = payload.get("project_description", "")
        project_title = payload.get("project_title", "")

        # Check if project exists
        project = await db["projects"].find_one({"project_id": project_id})

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project_oid = project_id
        
        # Check if SRS already exists
        existing_srs = await db["srs_documents"].find_one({"project_id": project_id})
        
        if existing_srs:
            srs_id = await _update_srs(db, existing_srs["_id"], srs_json, project_oid)
        else:
            srs_id = await _create_srs(db, srs_json, project_oid)
        
        return {
            "status": "success",
            "srs_id": srs_id,
            "message": "SRS saved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error saving SRS: {str(e)}")

# this route is called from the frontend to fetc the srs from db
@router.get("/{project_id}/srs")
async def get_srs_document(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user=Depends(get_current_user)
):
    try:
        srs = await db["srs_documents"].find_one({"project_id": project_id})

        if not srs:
            raise HTTPException(status_code=404, detail="SRS document not found")

        # If user-edited HTML exists, return that
        if srs.get("html"):
            return {"mode": "html", "html": srs["html"]}

        # Return raw srs_json for frontend rendering
        return {"mode": "json", "srs_json": srs["srs_json"]}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching SRS: {str(e)}")


# this route is called when user updates and saves an update document
@router.post("/{project_id}/srs/html")
async def save_srs_html(
    project_id: str,
    payload: dict,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Save rendered HTML version of SRS (for caching).
    Frontend can call this after rendering to cache the HTML.
    """
    html = payload.get("html")
    
    if not html:
        raise HTTPException(status_code=400, detail="HTML is required")
    
    result = await db["srs_documents"].update_one(
        {"project_id": project_id},
        {
            "$set": {
                "html": html,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="SRS document not found")
    
    return {"status": "saved"}


# ----------------- Requirements Routes -----------------

@router.get("/{project_id}/requirements")
async def get_project_requirements(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user=Depends(get_current_user)
):
    """Get all requirements for a project"""
    try:
        requirements_cursor = db["requirements"].find({
            "project_id": project_id
        }).sort("req_id", 1)
        
        requirements = []
        async for req in requirements_cursor:
            req["_id"] = str(req["_id"])
            req["project_id"] = str(req["project_id"])
            req["srs_document_id"] = str(req["srs_document_id"])
            req.pop("change_history", None)
            requirements.append(req)
        
        return {
            "requirements": requirements,
            "count": len(requirements)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching requirements: {str(e)}")



def _build_source_label(req: dict) -> str:
    origin = req.get("origin")
    origins = origin if isinstance(origin, list) else [origin]

    if "atomized" in origins:
        base = "elicited" if "elicited" in origins else "extracted"
        parent_text = req.get("parent_text") or ""
        snippet = (parent_text[:80] + "...") if len(parent_text) > 80 else parent_text
        return f"Atomized from {base} requirement: \"{snippet}\""
    elif "elicited" in origins:
        return "Elicited during requirements conversation"
    else:
        return "Extracted from input document"
    
def _load_lineage_map(conv_id: str) -> dict:
    """
    Loads atomic_refinement file and returns a lookup dict keyed by req_id.
    Returns empty dict if file not found.
    """
    path = f"./agents/refinement/results/atomic_refinement_{conv_id}.json"
    if not os.path.exists(path):
        print(f"[RTM] No atomic refinement file found at {path}, lineage will be empty")
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    lineage_map = {}
    for req in data.get("requirements", []):
        req_id = req.get("req_id")
        if req_id:
            lineage_map[req_id] = {
                "origin":        req.get("origin", "extracted"),
                "parent_req_id": req.get("parent_req_id"),
                "parent_text":   req.get("parent_text")
            }

    print(f"[RTM] Loaded lineage for {len(lineage_map)} requirements from atomic file")
    return lineage_map


@router.post("/{project_id}/requirements/bulk_create")
async def save_requirements_bulk(
    project_id: str,
    payload: BulkCreateRequirementsRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if not payload.requirements:
        raise HTTPException(status_code=400, detail="No requirements provided")

    srs = await db["srs_documents"].find_one({"project_id": project_id})
    if not srs:
        raise HTTPException(status_code=404, detail="SRS document not found. Create SRS first.")

    # Load lineage from atomic refinement file using project_id as conv_id
    lineage_map = _load_lineage_map(project_id)

    documents = []
    for req in payload.requirements:
        # Pull lineage for this req — falls back gracefully if not found
        lineage = lineage_map.get(req.req_id, {})
        origin = lineage.get("origin", "extracted")

        documents.append({
            "id":               req.id,
            "req_id":           req.req_id,
            "project_id":       project_id,
            "srs_document_id":  srs["_id"],
            "feature_id":       getattr(req, 'feature_id', None),
            "feature_name":     getattr(req, 'feature_name', None),
            "text":             req.text,
            "type":             req.type,
            "subtype":          req.subtype,
            "priority":         getattr(req, 'priority', "medium"),
            "status":           "active",
            "version":          1,
            "created_at":       datetime.utcnow(),
            "updated_at":       datetime.utcnow(),

            # --- lineage fields ---
            "origin":           origin if isinstance(origin, list) else [origin],
            "parent_req_id":    lineage.get("parent_req_id"),
            "parent_text":      lineage.get("parent_text"),
            "source_label":     _build_source_label({"origin": origin, "parent_text": lineage.get("parent_text")}),

            "change_history": [{
                "version":      1,
                "text":         req.text,
                "updated_at":   datetime.utcnow(),
                "change_reason": "Initial creation"
            }]
        })

    try:
        result = await db["requirements"].insert_many(documents)

        total_reqs = await db["requirements"].count_documents({"srs_document_id": srs["_id"]})
        await db["srs_documents"].update_one(
            {"_id": srs["_id"]},
            {"$set": {
                "stats.total_requirements": total_reqs,
                "updated_at": datetime.utcnow()
            }}
        )

        return {
            "message":          "Requirements saved successfully",
            "inserted_count":   len(result.inserted_ids),
            "requirement_ids":  [str(_id) for _id in result.inserted_ids]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving requirements: {str(e)}")
    

# ----------------- Helper Functions -----------------

async def _create_srs(db: AsyncIOMotorDatabase, srs_json: Dict[str, Any], project_id: str) -> str:

    srs_doc = {
        "project_id": project_id,
        "title": srs_json.get("title", "Untitled"),
        "srs_json": srs_json,              # ← store raw JSON as-is
        "version": "1.0.0",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "stats": {
            "total_features": 0,
            "total_requirements": 0
        }
    }

    requirements = []
    feature_counter = 1
    req_counter = 0

    for section_key, section_value in srs_json.get("sections", {}).items():
        if not isinstance(section_value, dict):
            continue

        # Detect features section
        is_features = any(
            isinstance(v, dict) and "functional_requirements" in v
            for v in section_value.values()
        )

        if is_features:
            for feature_name, feature_data in section_value.items():
                if not isinstance(feature_data, dict):
                    continue

                feature_id = f"FEAT-{feature_counter:03d}"

                for req in feature_data.get("functional_requirements", []):
                    req_counter += 1
                    if isinstance(req, dict):
                        req_id = req.get("id", f"REQ-{req_counter:03d}")
                        req_text = req.get("text", "")
                    else:
                        req_id = f"REQ-{req_counter:03d}"
                        req_text = str(req)

                    requirements.append({
                        "req_id": req_id,
                        "project_id": project_id,
                        "feature_id": feature_id,
                        "feature_name": feature_name,
                        "text": req_text,
                        "type": "functional",
                        "subtype": "general",
                        "priority": "medium",
                        "status": "active",
                        "version": 1,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    })
                feature_counter += 1

    srs_doc["stats"]["total_features"] = feature_counter - 1
    srs_doc["stats"]["total_requirements"] = req_counter

    result = await db["srs_documents"].insert_one(srs_doc)
    srs_id = result.inserted_id

    for req in requirements:
        req["srs_document_id"] = str(srs_id)

    if requirements:
        await db["requirements"].insert_many(requirements)

    await db["projects"].update_one(
        {"project_id": project_id},
        {"$set": {"updated_at": datetime.utcnow()}}
    )

    return str(srs_id)

async def _update_srs(db: AsyncIOMotorDatabase, srs_id,
                      srs_json: Dict[str, Any], project_id: str) -> str:

    await db["srs_documents"].update_one(
        {"_id": srs_id},
        {"$set": {
            "srs_json": srs_json,
            "title": srs_json.get("title", "Untitled"),
            "updated_at": datetime.utcnow(),
        }, "$unset": {"html": ""}}
    )

    # Re-extract requirements from scratch
    await db["requirements"].delete_many({"srs_document_id": str(srs_id)})

    requirements = []
    feature_counter = 1
    req_counter = 0

    for section_key, section_value in srs_json.get("sections", {}).items():
        if not isinstance(section_value, dict):
            continue

        is_features = any(
            isinstance(v, dict) and "functional_requirements" in v
            for v in section_value.values()
        )

        if is_features:
            for feature_name, feature_data in section_value.items():
                if not isinstance(feature_data, dict):
                    continue

                feature_id = f"FEAT-{feature_counter:03d}"

                for req in feature_data.get("functional_requirements", []):
                    req_counter += 1
                    if isinstance(req, dict):
                        req_id = req.get("id", f"REQ-{req_counter:03d}")
                        req_text = req.get("text", "")
                    else:
                        req_id = f"REQ-{req_counter:03d}"
                        req_text = str(req)

                    requirements.append({
                        "req_id": req_id,
                        "project_id": project_id,
                        "srs_document_id": str(srs_id),
                        "feature_id": feature_id,
                        "feature_name": feature_name,
                        "text": req_text,
                        "type": "functional",
                        "subtype": "general",
                        "priority": "medium",
                        "status": "active",
                        "version": 1,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    })
                feature_counter += 1

    if requirements:
        await db["requirements"].insert_many(requirements)

    return str(srs_id)

# async def _update_srs(db: AsyncIOMotorDatabase, srs_id, 
#                      srs_json: Dict[str, Any], project_id: str) -> str:
#     """Update existing SRS document"""
    
#     # Get existing requirements using srs_id (this is MongoDB _id, already ObjectId)
#     existing_reqs = await db["requirements"].find({"srs_document_id": str(srs_id)}).to_list(None)
#     existing_req_ids = {req["req_id"] for req in existing_reqs}
    
#     update_doc = {
#         "title": srs_json["title"],
#         "updated_at": datetime.utcnow(),
#         "sections": {},
#         "features": {}
#     }
    
#     new_requirements = []
#     feature_counter = 1
#     new_req_counter = 0
    
#     # Process sections
#     for section_key, section_value in srs_json["sections"].items():
#         if section_key.startswith("4_"):
#             for feature_name, feature_data in section_value.items():
#                 feature_id = f"FEAT-{feature_counter:03d}"
                
#                 update_doc["features"][feature_name] = {
#                     "feature_id": feature_id,
#                     "order": feature_counter,
#                     "description": _clean_text(feature_data.get("description", "")),
#                     "functional_overview": feature_data.get("functional_overview", [])
#                 }
                
#                 # Check for new requirements
#                 if "functional_requirements" in feature_data:
#                     for req in feature_data["functional_requirements"]:
#                         if req["id"] not in existing_req_ids:
#                             new_req_counter += 1
#                             new_requirements.append({
#                                 "req_id": req["id"],
#                                 "project_id": project_id,  # String, not ObjectId
#                                 "srs_document_id": str(srs_id),
#                                 "feature_id": feature_id,
#                                 "feature_name": feature_name,
#                                 "text": req["text"],
#                                 "type": "functional",
#                                 "subtype": "general",
#                                 "priority": "medium",
#                                 "status": "active",
#                                 "version": 1,
#                                 "created_at": datetime.utcnow(),
#                                 "updated_at": datetime.utcnow(),
#                                 "change_history": [{
#                                     "version": 1,
#                                     "text": req["text"],
#                                     "updated_at": datetime.utcnow(),
#                                     "change_reason": "Added in update"
#                                 }]
#                             })
                
#                 feature_counter += 1
#         else:
#             update_doc["sections"][section_key] = section_value
    
#     # Update stats
#     total_reqs = len(existing_req_ids) + new_req_counter
#     update_doc["stats"] = {
#         "total_features": feature_counter - 1,
#         "total_requirements": total_reqs
#     }
    
#     # Update document and clear HTML cache
#     await db["srs_documents"].update_one(
#         {"_id": srs_id},
#         {"$set": update_doc, "$unset": {"html": ""}}
#     )
    
#     # Insert new requirements
#     if new_requirements:
#         await db["requirements"].insert_many(new_requirements)
    
#     return str(srs_id)


def _clean_text(text: str) -> str:
    """Clean text by removing extra whitespace"""
    if isinstance(text, str):
        return " ".join(text.split()).strip()
    return ""


def _clean_text(text: str) -> str:
    """Clean text by removing extra whitespace"""
    if isinstance(text, str):
        return " ".join(text.split()).strip()
    return ""

# # ----------------- Helper Functions -----------------

async def send_requirements_to_route(payload: dict, project_id: str):
    """
    Helper function to send requirements to the bulk create endpoint.
    Used by agents to save requirements programmatically.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://localhost:8000/api/projects/{project_id}/requirements/bulk_create",
            json=payload
        )
        response.raise_for_status()
        return response.json()







# route for autocomplete for editor

@router.post("/srs/autocomplete")
async def autocomplete_srs(request: Request):    
    """
    Receives JSON: { "text": "last 4 words" }
    Returns JSON: { "suggestion": "predicted next words" }
    """
    data = await request.json()
    if not data or "text" not in data:
        return jsonify({"suggestion": ""}), 400

    input_text = data["text"]

    # Call your predictor (predict next 1 or 2 words)
    suggestion = predictor.predict_next(input_text, num_words=2)

    # Return only the newly predicted words
    suggestion_only = suggestion[len(input_text):].strip()

    return {"suggestion": suggestion_only}