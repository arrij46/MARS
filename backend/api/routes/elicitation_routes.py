"""
Elicitation API routes for chatbot interaction.
"""
import asyncio
import json
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Depends, Query, Form
from pydantic import BaseModel
from agents.elicitation.agent import ElicitationAgent
from utils.document_parser import parse_document_structure
from orchestrator.orchestrator import OrchestratorAgent
from orchestrator.shared_state import get_shared_state
from api.routes.upload_routes import UPLOAD_DIR, background_tasks, register_project
from api.routes.auth_routes import get_db, get_current_user

# Initialize router
router = APIRouter(tags=["Elicitation"])

# Initialize agent instance for API calls
agent = ElicitationAgent()
orchestrator = OrchestratorAgent()

class BaselineRequest(BaseModel):
    baseline_text: str

class ChatRequest(BaseModel):
    message: str

class EditRequirementRequest(BaseModel):
    index: int
    new_text: str

@router.post("/elicitation/start")
async def start_elicitation(
    request: Request,
    conv_id: str = Form(None),
    title: str = Form(...),
    description: str = Form(...),
    user=Depends(get_current_user),
):
    """
    Start a new elicitation session and register the project like /api/upload does.
    """
    import uuid

    shared_state = get_shared_state()

    conv_id = conv_id or f"conv-{uuid.uuid4()}"

    shared_state.store_project_description(conv_id, description)
    conv = shared_state.get_conversation(conv_id)
    conv["metadata"]["title"] = title

    db = get_db(request)
    await register_project(
        conv_id=conv_id,
        db=db,
        title=title,
        description=description,
        user_id=user["sub"],
    )

    try:
        agent.start_session(conv_id)
        return {
            "status": "success",
            "message": "Elicitation session started",
            "conv_id": conv_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")

@router.post("/elicitation/baseline")
async def collect_baseline(conv_id: str, request: BaselineRequest):
    """
    Collect baseline system information.
    """
    try:
        result = await agent.collect_baseline_info(conv_id, request.baseline_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to collect baseline: {str(e)}")

@router.post("/elicitation/chat")
async def chat_message(conv_id: str, request: ChatRequest):
    """
    Send a chat message to the elicitation agent.
    """
    try:
        result = await agent.chat_message(conv_id, request.message)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@router.delete("/elicitation/requirement")
async def delete_requirement_endpoint(conv_id: str, index: int = Query(...)):
    """
    Endpoint to handle deleting a requirement from the UI.
    """
    try:
        # Assuming delete_requirement is a synchronous method on the agent.
        # If it's async in your implementation, add 'await' before agent.delete_requirement
        success, message = agent.delete_requirement(conv_id, index)
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
            
        return {"status": "success", "message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete requirement: {str(e)}")

@router.put("/elicitation/requirement")
async def edit_requirement_endpoint(conv_id: str, req_data: EditRequirementRequest):
    """
    Endpoint to handle editing a requirement from the UI.
    """
    try:
        # Assuming edit_requirement is a synchronous method on the agent.
        # If it's async in your implementation, add 'await' before agent.edit_requirement
        success, message = agent.edit_requirement(conv_id, req_data.index, req_data.new_text)
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
            
        return {"status": "success", "message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to edit requirement: {str(e)}")

@router.post("/elicitation/end")
async def end_elicitation(
    conv_id: str, 
    request: Request,
    user=Depends(get_current_user) # Require authenticated user
):
    """
    End the elicitation session, save requirements to JSON, and trigger workflow continuation.
    """
    try:
        result = await agent.end_session(conv_id)
        
        # Get the session data
        session = result
        
        # Save to JSON file
        json_data = {
            "project_title": session['project_title'],
            "project_description": session['project_description'],
            "requirements": session['requirements_list']
        }
        json_path = UPLOAD_DIR / f"elicited_requirements_{conv_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)
        print(f"[API] Saved elicited requirements to JSON: {json_path}")
        
        # Create text file for workflow continuation
        text_content = f"{session['project_title']}\n\nSummary\n{session['project_description']}\n\nRequirements\n"
        for i, req in enumerate(session['requirements_list'], 1):
            text_content += f"{i}. {req}\n"
        
        file_path = UPLOAD_DIR / f"elicited_{conv_id}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text_content)
        
        # Parse document (same shape as upload pipeline)
        input_doc = parse_document_structure(text_content)
        input_doc["title"] = session["project_title"]
        input_doc["summary"] = session["project_description"]

        shared_state = get_shared_state()
        shared_state.store_project_description(conv_id, session["project_description"])
        conv = shared_state.get_conversation(conv_id)
        conv["metadata"]["title"] = session["project_title"]
        shared_state.store_document(conv_id, str(file_path), input_doc)

        db = get_db(request)
        await register_project(
            conv_id=conv_id,
            db=db,
            title=session["project_title"],
            description=session["project_description"],
            user_id=user["sub"],
        )
        
        # Start workflow
        await orchestrator.send_progress(conv_id, {
            "step": "workflow_started", 
            "message": "Workflow started from elicitation"
        })
        
        task = asyncio.create_task(orchestrator.start_agent(
            document_path=str(file_path),
            input_doc=input_doc,
            conv_id=conv_id
        ))
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)
        
        # Inject the conv_id so the frontend can actually read it!
        result["conv_id"] = conv_id
        result["status"] = "success"
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end session: {str(e)}")