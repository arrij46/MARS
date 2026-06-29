from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import date
from api.routes.auth_routes import get_current_user, get_db
from databaseSchema.schema import TitlePageResponse, TitlePageUpdate

router = APIRouter(prefix="/titlePage", tags=["Title Page"])



@router.get("/{project_id}", response_model=TitlePageResponse)
async def get_title_page(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user=Depends(get_current_user),
):
    # 1. Fetch SRS document
    srs = await db["srs_documents"].find_one({"project_id": project_id})
    if not srs:
        raise HTTPException(status_code=404, detail="SRS document not found")

    # 2. Fetch project to get user_id
    project = await db["projects"].find_one({"project_id": project_id})

    # 3. Match project.user_id (plain string) to users._id (ObjectId) to get author name
    author = "<author>"
    if project:
        user_id_str = project.get("user_id")
        if user_id_str:
            user_doc = await db["users"].find_one({"_id": ObjectId(user_id_str)})
            if user_doc:
                author = user_doc.get("name") or user_doc.get("email") or "<author>"

    today = date.today().strftime("%B %d, %Y")

    # 4. Pull values using actual field names from srs_documents schema
    title    = srs.get("srs_json", {}).get("title", "<Project>")
    version  = srs.get("version", "1.0")
    date_str = srs["created_at"].strftime("%B %d, %Y") if srs.get("created_at") else today
    org      = srs.get("title_page_org", "")

    return TitlePageResponse(
        title=title,
        version=version,
        date=date_str,
        org=org,
        author=author,
    )



@router.patch("/{project_id}")
async def update_title_page(
    project_id: str,
    body: TitlePageUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user=Depends(get_current_user),
):
    srs = await db["srs_documents"].find_one({"project_id": project_id})
    if not srs:
        raise HTTPException(status_code=404, detail="SRS document not found")

    update_fields = {}

    if body.org is not None:
        update_fields["title_page_org"] = body.org
    if body.title is not None:
        update_fields["srs_json.title"] = body.title

    if not update_fields:
        return {"message": "Nothing to update"}

    await db["srs_documents"].update_one(
        {"project_id": project_id},
        {"$set": update_fields},
    )

    return {"message": "Title page updated successfully"}