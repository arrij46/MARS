"""
File upload and processing routes for document analysis workflow.
"""
import asyncio
from datetime import datetime
from groq import Groq
from motor.motor_asyncio import AsyncIOMotorDatabase
from api.routes.auth_routes import get_current_user
import os
import shutil
import uuid
from typing import Set
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, UploadFile, File, Depends, Form
from fastapi.responses import JSONResponse

from orchestrator.shared_state import get_shared_state
from databaseSchema.schema import ProcessRequest
from orchestrator.orchestrator import OrchestratorAgent
from api.routes.auth_routes import get_db
from utils.document_parser import extract_text, parse_document_structure

from pydantic import BaseModel
from typing import List

# Initialize router
router = APIRouter(tags=["File Upload"])

# Initialize orchestrator
orchestrator = OrchestratorAgent()

# File upload configuration
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str((Path(__file__).resolve().parents[2] / "uploads"))))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Track active projects and current conversation ID
active_projects = set()
conversation_id = ""

# Global set to keep task references
background_tasks: Set[asyncio.Task] = set()


async def register_project(conv_id: str, db: AsyncIOMotorDatabase, title: str = None, description:str = None, user_id: str = None):
    """
    Register a project in the database and for WebSocket communication.
    Creates an entry in the 'projects' collection.
    """
    # Add to active projects for WebSocket
    active_projects.add(conv_id)
    global conversation_id
    conversation_id = conv_id
    
    # Check if project already exists in DB
    existing_project = await db["projects"].find_one({"project_id": conv_id})
    
    if not existing_project:
        # Create new project entry in database
        project_doc = {
            "project_id": conv_id,
            "user_id": user_id or "anonymous",
            "title": title or f"Project {conv_id[:8]}",
            "description": description or "",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        await db["projects"].insert_one(project_doc)
        print(f"[API] Project created in DB: {conv_id}")
    else:
        # Keep dashboard in sync when the same project is re-registered (e.g. elicitation end)
        update_fields = {"updated_at": datetime.now()}
        if title is not None:
            update_fields["title"] = title
        if description is not None:
            update_fields["description"] = description
        if user_id:
            update_fields["user_id"] = user_id
        await db["projects"].update_one(
            {"project_id": conv_id},
            {"$set": update_fields},
        )
        print(f"[API] Project already exists in DB (updated metadata): {conv_id}")
    
    print(f"[API] Project registered for WS: {conv_id}")
    return conv_id


@router.post("/upload")
async def upload_file(
    request: Request = None,
    file: UploadFile = File(...),
    conv_id: str = None,
    title: str = Form(None),
    description: str = Form(""),
    user=Depends(get_current_user)
):
    """
    Upload a document file and start the orchestrator immediately.
    The orchestrator will buffer progress messages until the WebSocket connects.
    """
    try:
        conv_id = conv_id or f"conv-{uuid.uuid4()}"
        db = get_db(request)

        await register_project(
            conv_id=conv_id,
            db=db,
            title=title or file.filename.rsplit('.', 1)[0],
            description=description,
            user_id=user["sub"]
        )

        shared_state = get_shared_state()

        # Store project description in shared state
        shared_state.store_project_description(conv_id, description)

        # Also store title in metadata (no new variable introduced)
        conv = shared_state.get_conversation(conv_id)
        conv["metadata"]["title"] = title or file.filename.rsplit('.', 1)[0]

        # Save uploaded file
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"[API] File uploaded: {file_path}")

        # Parse document
        text = extract_text(str(file_path), file.filename)
        input_doc = parse_document_structure(text)
        # Inject UI title/description into input_doc
        input_doc["title"] = title or file.filename.rsplit('.', 1)[0]
        input_doc["summary"] = description
        print(f"[API] Document parsed: {len(input_doc.get('requirements', []))} requirements")

        # Store in shared state
        shared_state.store_document(conv_id, str(file_path), input_doc)

        # Start orchestrator immediately — WS not connected yet, messages will be buffered
        task = asyncio.create_task(orchestrator.start_agent(
            document_path=str(file_path),
            input_doc=input_doc,
            conv_id=conv_id
        ))
        task.add_done_callback(lambda t: print(f"[API] Workflow task done (conv={conv_id})"))

        return JSONResponse({
            "status":             "success",
            "message":            "File uploaded and workflow started",
            "conv_id":            conv_id,
            "requirements_count": len(input_doc.get("requirements", []))
        })

    except Exception as e:
        print(f"[API] Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
### Additional route for elicitation continuation ###

class ElicitedData(BaseModel):
    title: str
    summary: str
    requirements: List[str]

@router.post("/upload_elicited")
async def upload_elicited_document(
    request: Request,
    payload: ElicitedData,
    conv_id: str = None,
    user=Depends(get_current_user)
):
    """
    Ends elicitation by taking collected requirements, formatting them into a file, 
    and starting the document analysis workflow.
    """
    try:
        conv_id = conv_id or f"conv-{uuid.uuid4()}"
        db = get_db(request)
        
        # Register the project
        await register_project(
            conv_id=conv_id, 
            db=db, 
            title=payload.title, 
            description= payload.summary,
            user_id=user["sub"]
        )



        shared_state = get_shared_state()

        shared_state.store_project_description(conv_id, payload.summary)

        conv = shared_state.get_conversation(conv_id)
        conv["metadata"]["title"] = payload.title

        # Format and save the physical file
        file_name = f"{payload.title.replace(' ', '_')}_elicited.txt"
        file_path = UPLOAD_DIR / file_name
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"Title: {payload.title}\n\n")
            f.write(f"Summary Description:\n{payload.summary}\n\n")
            f.write("List of Requirements:\n")
            for i, req in enumerate(payload.requirements, 1):
                f.write(f"{i}. {req}\n")
                
        print(f"[API] Elicited document formatted and saved: {file_path}")

        # Construct the parsed input_doc manually so we don't need to re-parse it
        input_doc = {
            "title": payload.title,
            "summary": payload.summary,
            "requirements": [
                {
                    "id": i, 
                    "req_id": f"REQ-{i}",
                    "text": req, 
                    "origin": "elicited",
                    "parent_req_id": None,
                    "parent_text": None
                    } for i, req in enumerate(payload.requirements, 1)]
        }

        # Notify frontend
        await orchestrator.send_progress(conv_id, {
            "step": "workflow_started",
            "message": "Elicitation complete. Workflow started from elicited document."
        })

        # Start orchestrator
        task = asyncio.create_task(orchestrator.start_agent(
            document_path=str(file_path),
            input_doc=input_doc,
            conv_id=conv_id
        ))
        
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

        return {
            "status": "success", 
            "conv_id": conv_id, 
            "requirements_count": len(payload.requirements)
        }

    except Exception as e:
        print(f"[API] Elicited upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process elicited data: {str(e)}")

### ---------------------------------------------------------------------------------------------

@router.post("/process")
async def process_message(payload: ProcessRequest, conv_id: str = None):
    """
    Start processing workflow without a file upload.
    Used for text-based input or continuation of existing conversations.
    """
    try:
        conv_id = conv_id or f"conv-{uuid.uuid4()}"

        # Notify frontend
        await orchestrator.send_progress(conv_id, {
            "step": "workflow_started",
            "message": "Workflow started (no document)"
        })

        # Start workflow in background
        asyncio.create_task(orchestrator.start_agent(conv_id=conv_id))

        return {"status": "processing started", "conv_id": conv_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get_conv_id")
async def get_conv_id():
    """Get the current conversation ID"""
    print("[API] sending conversation ID to frontend: ", conversation_id)
    return JSONResponse({
        "conv_id": conversation_id
    })


#  test route for chatbot integration
client = Groq(api_key=os.getenv("GROQ_API_KEY_DOCUMENT_ACCOUNT2"))
@router.post("/chatbot/chat")
async def chat(payload: dict):
    user_query = payload.get("message", "")
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0.7,
        messages=[
            {"role": "user", "content": f"You are an assistive agent, help the user by answering to the question in context to a IEEE-FORMAT SRS DOCUMENT. Don't make up any information on your own Just assist like a chatbot. Answer only based on the information you have. If you don't know the answer, say you don't know. Answer to the query keeping in mind that the user will ask questions in context to writing an IEEE-FORMAT SRS DOCUMENT. Answer to this query: {user_query}"}
        ]
    )
    
    return {"reply": response.choices[0].message.content.strip()}



@router.get("/fetch_projects")
async def get_projects(request: Request, user=Depends(get_current_user)):
    db = get_db(request)
    projects = await db.projects.find(
        {"user_id": user["sub"]}
    ).sort("created_at", -1).to_list(100)
    
    for p in projects:
        p["_id"] = str(p["_id"])
        p["created_at"] = p["created_at"].isoformat()
        p["updated_at"] = p["updated_at"].isoformat()
        # Ensure frontend gets a consistent project payload.
        # Current DB uses `project_id` as the conversation identifier.
        p["conv_id"] = p.get("conv_id") or p.get("project_id")
        p["project_id"] = p.get("project_id") or p.get("conv_id")
        p["name"] = p.get("name") or p.get("title") or p.get("project_id")
        p["report"] = p.get("report", None)  # Include report if it exists
    
    return JSONResponse({"projects": projects})