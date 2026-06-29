from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import Optional
from api.routes.auth_routes import get_current_user, get_db
from orchestrator.shared_state import get_shared_state
from databaseSchema.schema import TemplateCreate, LinkTemplateRequest

router = APIRouter(prefix="/templates", tags=["Templates"])


# ── Save Template ────────────────────────────────────────────

@router.post("/saveTemplate")
async def save_template(
    template: TemplateCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user=Depends(get_current_user)
):
    try:


         # Check if template with same name already exists for this user
        existing = await db["templates"].find_one({
            "user_id": user["sub"],
            "name": template.name
        })
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"A template named '{template.name}' already exists."
            )

        template_doc = {
            **template.model_dump(),
            "user_id": user["sub"],        # ← from JWT token
            "created_at": datetime.utcnow(),
        }

        result = await db["templates"].insert_one(template_doc)

        return {
            "id": str(result.inserted_id),
            "message": "Template saved successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save template: {str(e)}")


# ── Get User's Templates ─────────────────────────────────────
@router.get("/getUserTemplates")
async def get_user_templates(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user=Depends(get_current_user)
):
    try:
        cursor = db["templates"].find({"user_id": user["sub"]})
        templates = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            templates.append(doc)
        return templates

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch templates: {str(e)}")
    

# ── Link Template to Project ─────────────────────────────────────
@router.post("/linkToProject")
async def link_template_to_project(
    req: LinkTemplateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user=Depends(get_current_user)
):
    try:
        await db["templates"].update_one(
            {"_id": ObjectId(req.template_id), "user_id": user["sub"]},
            {"$set": {"project_id": req.project_id}}
        )
        return {"message": "Template linked to project"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Called by frontend after template saved/selected ──
@router.post("/templateReady/{project_id}")
async def template_ready(
    project_id: str,
    user=Depends(get_current_user)
):
    shared_state = get_shared_state()
    shared_state.signal_template_ready(project_id)
    return {"message": "Template ready signal sent"}

# ──────────────────────────────────────────────────────────────
# ── called by document agent via httpx, and also called by the frontend to get the fonts ──
@router.get("/forProject/{project_id}")
async def get_template_for_project(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    try:
        # First — try project-specific template
        template_doc = await db["templates"].find_one({"project_id": project_id})

        # Fallback — most recently saved template
        if not template_doc:
            template_doc = await db["templates"].find_one(
                {},
                sort=[("created_at", -1)]
            )

        if not template_doc:
            raise HTTPException(status_code=404, detail="No template found")

        template_doc.pop("_id", None)
        return template_doc

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))