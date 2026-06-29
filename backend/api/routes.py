# # api/routes.py
# import asyncio
# from datetime import datetime
# import os
# import uuid
# import json
# import shutil
# from pathlib import Path
# from dotenv import load_dotenv

# # authentication
# import httpx
# from passlib.hash import bcrypt
# from motor.motor_asyncio import AsyncIOMotorDatabase
# from pymongo.errors import DuplicateKeyError
# from fastapi import WebSocket, APIRouter, HTTPException, UploadFile, File, Depends, status, Body
# from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
# from databaseSchema.schema import BulkCreateRequirementsRequest, SignupRequest, LoginRequest, ProcessRequest, UpdateRequirementRequest

# # OAuth for Google OAuth2
# from authlib.integrations.starlette_client import OAuth
# from starlette.requests import Request

# # orchestrator
# from orchestrator.shared_state import get_shared_state
# from orchestrator.orchestrator import OrchestratorAgent
# from utils.document_parser import extract_text, parse_document_structure
# from agents.userStory.utils.pdf_generator import generate_user_story_pdf
# from api.ws_store import ws_connections

# # Initialize environment variables
# load_dotenv()

# # Initialize router 
# router = APIRouter()

# # Initialize OAuth
# CONF_URL = "https://accounts.google.com/.well-known/openid-configuration"

# oauth = OAuth()
# oauth.register(
#     name="google",
#     client_id=os.environ.get("GOOGLE_CLIENT_ID"),
#     client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
#     server_metadata_url=CONF_URL,
#     client_kwargs={"scope": "openid email profile"}
# )
# # ----------------- Database Dependency -----------------
# def get_db(request: Request) -> AsyncIOMotorDatabase:
#     return request.app.mongodb  # get MongoDB client from FastAPI app

# # ---------------- Google OAuth Routes -----------------
# @router.get("/auth/google")
# async def login_via_google(request: Request):
#     redirect_uri = "http://localhost:8000/api/auth/google/callback"
#     return await oauth.google.authorize_redirect(request, redirect_uri)

# # ---------------- Google OAuth Callback -----------------
# @router.get("/auth/google/callback")
# async def google_callback(request: Request):
#     try:
#         # This fetches the token and ID token
#         token = await oauth.google.authorize_access_token(request)
#         userinfo = token.get("userinfo") or await oauth.google.parse_id_token(request, token)

#         # userinfo now contains: email, name, picture, sub (Google ID)
#         email = userinfo["email"]
#         name = userinfo.get("name", "")
#         google_id = userinfo.get("sub")

#         # Here: check if user exists in your DB, create if not
#         db = request.app.mongodb
#         user = await db["users"].find_one({"email": email})
#         if not user:
#             await db["users"].insert_one({
#                 "name": name,
#                 "email": email,
#                 "google_id": google_id,
#                 "password": None  # no password for Google login
#             })

#         # You can store user info in session or generate your JWT
#         request.session["user"] = {"email": email, "name": name}

#         return RedirectResponse(url="http://localhost:5173/dashboard")  # frontend route
#     except Exception as e:
#         return JSONResponse({"error": str(e)}, status_code=400)


# # ---------------- Google Signup -----------------
# @router.get("/auth/google/signup")
# async def google_signup(request: Request):
#     redirect_uri = "http://localhost:8000/api/auth/google/callback/signup"
#     return await oauth.google.authorize_redirect(request, redirect_uri)


# @router.get("/auth/google/callback/signup")
# async def google_signup_callback(request: Request):
#     try:
#         token = await oauth.google.authorize_access_token(request)
#         userinfo = token.get("userinfo") or await oauth.google.parse_id_token(request, token)

#         email = userinfo["email"]
#         name = userinfo.get("name", "")
#         google_id = userinfo.get("sub")

#         db = request.app.mongodb
#         user = await db["users"].find_one({"email": email})
#         if user:
#             # User already exists → cannot signup
#             return RedirectResponse(url="http://localhost:5173/auth?mode=login&msg=User+already+exists")

#         # Create new user
#         await db["users"].insert_one({
#             "name": name,
#             "email": email,
#             "google_id": google_id,
#             "password": None
#         })

#         request.session["user"] = {"email": email, "name": name}
#         return RedirectResponse(url="http://localhost:5173/dashboard")
#     except Exception as e:
#         return JSONResponse({"error": str(e)}, status_code=400)


# # ---------------- Google Login -----------------
# @router.get("/auth/google/login")
# async def google_login(request: Request):
#     redirect_uri = "http://localhost:8000/api/auth/google/callback/login"
#     return await oauth.google.authorize_redirect(request, redirect_uri)


# @router.get("/auth/google/callback/login")
# async def google_login_callback(request: Request):
#     try:
#         token = await oauth.google.authorize_access_token(request)
#         userinfo = token.get("userinfo") or await oauth.google.parse_id_token(request, token)

#         email = userinfo["email"]
#         name = userinfo.get("name", "")

#         db = request.app.mongodb
#         user = await db["users"].find_one({"email": email})
#         if not user:
#             # User does not exist → cannot login
#             return RedirectResponse(url="http://localhost:5173/auth?mode=signup&msg=Please+signup+first")

#         request.session["user"] = {"email": email, "name": name}
#         return RedirectResponse(url="http://localhost:5173/dashboard")
#     except Exception as e:
#         return JSONResponse({"error": str(e)}, status_code=400)

# # ---------------- SIGNUP -----------------
# @router.post("/signup")
# async def signup(
#     payload: SignupRequest = Body(...),
#     db: AsyncIOMotorDatabase = Depends(get_db),
# ):
#     try:
#         await db["users"].insert_one({
#             "name": payload.name,
#             "email": payload.email,
#             "password": bcrypt.hash(payload.password),
#         })
#     except DuplicateKeyError:
#         # Duplicate email / unique index violation
#         raise HTTPException(
#             status_code=status.HTTP_409_CONFLICT,
#             detail="User with this email already exists"
#         )

#     return {
#         "message": "Signup successful!",
#         "user": {"name": payload.name, "email": payload.email},
#     }


# # ---------------- LOGIN -----------------
# @router.post("/login")
# async def login(
#     payload: LoginRequest = Body(...),
#     db: AsyncIOMotorDatabase = Depends(get_db),
# ):
#     user = await db["users"].find_one({"email": payload.email})

#     if not user or not bcrypt.verify(payload.password, user["password"]):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid email or password"
#         )

#     return {
#         "message": "Login successful!",
#         "user": {"name": user["name"], "email": user["email"]},
#     }

# orchestrator = OrchestratorAgent()

# # ----------------- File Uploads -----------------
# UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str((Path(__file__).resolve().parents[1] / "uploads"))))
# UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# # ----------------- WebSocket Management -----------------
# conversation_id = ""
# active_projects = set()

# def register_project(conv_id: str):
#     active_projects.add(conv_id)
#     global conversation_id
#     conversation_id = conv_id
#     print(f"[API] Project registered for WS: {conv_id}")


# @router.websocket("/ws/{conv_id}")
# async def websocket_endpoint(websocket: WebSocket, conv_id: str):
#     await websocket.accept()
#     ws_connections[conv_id] = websocket
#     print(f"[API] WebSocket connected for project: {conv_id}")

#     try:
#         while True:
#             await websocket.receive_text()
#     except:
#         ws_connections.pop(conv_id, None)
#         print(f"[API] WebSocket disconnected for project: {conv_id}")



# @router.post("/get_conv_id")
# async def get_conv_id():
#     print("[API] sending conversation ID to frontend: ", conversation_id)
#     return JSONResponse({
#         "conv_id": conversation_id
#     })

# @router.get("/requirements_file")
# async def get_requirements_file():
#     global conversation_id
#     path = f"./agents/refinement/results/cleaned_classified_refinement_{conversation_id}.json"
#     if os.path.exists(path):
#         with open(path, "r", encoding="utf-8") as f:
#             data = json.load(f)
#         # print("[API] file exists: ", data)

#         return data
#     else: 
#         print("[API] path not found")
#         return {"requirements": []}


# # Upload endpoint
# @router.post("/upload")
# async def upload_file(file: UploadFile = File(...), conv_id: str = None):
#     try:
#         conv_id = conv_id or f"conv-{uuid.uuid4()}"
#         register_project(conv_id)  # register WS before workflow

#         # Save uploaded file
#         file_path = UPLOAD_DIR / file.filename
#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)
#         print(f"[API] File uploaded: {file_path}")

#         # Parse document
#         text = extract_text(str(file_path), file.filename)
#         input_doc = parse_document_structure(text)
#         print(f"[API] Document parsed: {len(input_doc.get('requirements', []))} requirements")

#         # Notify frontend workflow started
#         await orchestrator.send_progress(conv_id, {"step": "workflow_started", "message": "Workflow started, animation screen active"})

#         # Start workflow in background
#         asyncio.create_task(orchestrator.start_agent(document_path=str(file_path), input_doc=input_doc, conv_id=conv_id))

#         return JSONResponse({
#             "status": "success",
#             "message": "File uploaded and workflow started",
#             "conv_id": conv_id,
#             "requirements_count": len(input_doc.get("requirements", []))
#         })

#     except Exception as e:
#         print(f"[API] Upload error: {e}")
#         raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
# # Process route (without file)
# @router.post("/process")
# async def process_message(payload: ProcessRequest, conv_id: str = None):
#     try:
#         conv_id = conv_id or f"conv-{uuid.uuid4()}"

#         # Notify frontend
#         await orchestrator.send_progress(conv_id, {
#             "step": "workflow_started",
#             "message": "Workflow started (no document)"
#         })

#         # Start workflow in background
#         asyncio.create_task(orchestrator.start_agent(conv_id=conv_id))

#         return {"status": "processing started", "conv_id": conv_id}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# # GET /results route - Get analysis results
# @router.get("/cdn_results")
# async def get_results():
#     """Get analysis results from the most recent workflow"""
#     shared_state = get_shared_state()
    
#     # Get the most recent conversation (last one in the dict)
#     if not shared_state.conversations:
#         return {"status": "processing", "message": "No analysis completed yet"}
    
#     # Get the most recent conversation ID
#     most_recent_conv_id = list(shared_state.conversations.keys())[-1]
#     conv = shared_state.conversations[most_recent_conv_id]
    
#     # Check if CDN results are available
#     cdn_results_path = conv.get("cdn_results_path")
#     cdn_results = conv.get("cdn_results")
    
#     if cdn_results_path and os.path.exists(cdn_results_path):
#         # Load fresh results from file
#         try:
#             with open(cdn_results_path, "r", encoding="utf-8") as f:
#                 results_data = json.load(f)
            
#             # Transform results to match frontend expectations
#             # The analyzer saves: {"siamese_results": {"0": [...], "1": [...]}}
#             # Frontend expects: {"siamese_results": {...}} with pairs having predicted_class
#             transformed_results = transform_cdn_results_for_frontend(results_data)
#             #print("hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",transformed_results)
#             return {
#                 "status": "completed",
#                 "conv_id": most_recent_conv_id,
#                 **transformed_results
#             }
#         except Exception as e:
#             print(f"[API] Error loading results: {e}")
#             return {"status": "error", "message": f"Error loading results: {str(e)}"}
#     elif cdn_results:
#         # Use cached results
#         transformed_results = transform_cdn_results_for_frontend(cdn_results)
#         return {
#             "status": "completed",
#             "conv_id": most_recent_conv_id,
#             **transformed_results
#         }
#     else:
#         return {"status": "processing", "message": "Analysis in progress"}

# # GET /refinement/results route - Get refinement results
# @router.get("/refinement_results")
# async def get_refinement_results():
#     """Get refinement results from the most recent workflow"""
#     shared_state = get_shared_state()

#     # Get the most recent conversation
#     if not shared_state.conversations:
#         return {"status": "processing", "message": "No refinement completed yet"}

#     most_recent_conv_id = list(shared_state.conversations.keys())[-1]
#     conv = shared_state.conversations[most_recent_conv_id]

#     refinement_results_path = conv.get("refinement_results_path")
#     refinement_results = conv.get("refinement_results")  # cached results
#     results_data = None

#     # Try reading from file first
#     if refinement_results_path and os.path.exists(refinement_results_path):
#         try:
#             with open(refinement_results_path, "r", encoding="utf-8") as f:
#                 results_data = json.load(f)
#         except Exception as e:
#             print(f"[API] Error loading refinement results from file: {e}")
#     else:
#         print(f"[API] Refinement results file not found at: {refinement_results_path}")

#     # Fallback to cached payload from agent
#     if results_data is None and refinement_results:
#         # Agent sends {'requirements': [...]}, use it directly
#         results_data = refinement_results

#     if not results_data or "requirements" not in results_data:
#         return {"status": "processing", "message": "Refinement in progress"}

#     # Transform results to frontend format
#     transformed_results = transform_refinement_for_frontend(results_data)
#     #print("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",transformed_results)

#     return {
#         "status": "completed",
#         "conv_id": most_recent_conv_id,
#         **transformed_results
#     }

# @router.get("/user_story/download")
# async def download_user_story():
#     """Download the generated user story PDF"""
#     global conversation_id
#     shared_state = get_shared_state()
    
#     if not conversation_id:
#         raise HTTPException(status_code=400, detail="No conversation ID available")
    
#     # Get user story results from shared state
#     user_story_results = shared_state.conversations.get(conversation_id, {}).get("user_story_results", {})
    
#     if not user_story_results:
#         raise HTTPException(status_code=404, detail="User story results not found. Please generate user stories first.")
    
#     pdf_path = user_story_results.get("pdf_path")
    
#     if not pdf_path or not os.path.exists(pdf_path):
#         raise HTTPException(status_code=404, detail="User story PDF file not found")
    
#     print(f"[API] Downloading user story PDF from: {pdf_path}")
    
#     return FileResponse(
#         path=pdf_path,
#         media_type="application/pdf",
#         filename=f"user_stories_{conversation_id}.pdf"
#     )


# def transform_refinement_for_frontend(results_data: dict) -> dict:
#     """
#     Transform refinement results JSON to frontend format:
#     {
#       "Functional": [{"id":..., "text":...}, ...],
#       "Non-Functional": {
#           "Performance": [...],
#           "Security": [...],
#           "Reliability": [...],
#           "Usability": [...],
#           "Other": [...]
#       }
#     }
#     """
#     output = {
#         "Functional": [],
#         "Non-Functional": {
#             "Performance": [],
#             "Security": [],
#             "Reliability": [],
#             "Usability": [],
#             "Other": []
#         }
#     }
#     # Get list of requirements from file or agent
#     requirements = results_data.get("requirements", [])
#     # requirements = results_data["requirements"]

#     for req in requirements:
#         # Ensure req is a dict
#         if not isinstance(req, dict):
#             continue

#         req_id = req.get("id")
#         req_text = req.get("text")
#         req_type = req.get("type")
#         req_subtype = req.get("subtype") or "Other"

#         if req_type == "Functional":
#             output["Functional"].append({"id": req_id, "text": req_text})
#         elif req_type == "Non-Functional":
#             if req_subtype not in output["Non-Functional"]:
#                 output["Non-Functional"][req_subtype] = []
#             output["Non-Functional"][req_subtype].append({"id": req_id, "text": req_text})

#     return output


# def transform_cdn_results_for_frontend(results_data: dict) -> dict:
#     """Transform analyzer results to frontend format"""
#     siamese_results = results_data.get("siamese_results", {})
    
#     # Flatten all pairs from all clusters
#     all_pairs = []
#     for cluster_id, pairs in siamese_results.items():
#         for pair in pairs:
#             # Ensure predicted_class is capitalized correctly
#             predicted_class = pair.get("predicted_class", "Neutral")
#             # Capitalize first letter
#             predicted_class = predicted_class.capitalize()
            
#             all_pairs.append({
#                 "idx1": pair.get("idx1"),
#                 "idx2": pair.get("idx2"),
#                 "req1": pair.get("req1"),
#                 "req2": pair.get("req2"),
#                 "predicted_class": predicted_class,
#                 "confidence": pair.get("confidence", 0.0),
#                 "all_probabilities": pair.get("all_probabilities", {})
#             })
    
#     return {
#         "siamese_results": siamese_results,
#         "all_pairs": all_pairs,
#         "metadata": results_data.get("metadata", {})
#     }




# @router.post("/update_requirement")
# async def update_requirement(req: UpdateRequirementRequest):
#     shared_state = get_shared_state()
#     # Get latest conversation
#     if not shared_state.conversations:
#         raise HTTPException(status_code=400, detail="No active conversation")

#     most_recent_conv_id = list(shared_state.conversations.keys())[-1]
#     conv = shared_state.conversations[most_recent_conv_id]

#     # Read the file
#     path = conv.get("refinement_results_path")
#     if not path or not os.path.exists(path):
#         raise HTTPException(status_code=404, detail="Results file not found")

#     try:
#         with open(path, "r", encoding="utf-8") as f:
#             data = json.load(f)

#         requirements = data.get("requirements", [])
#         if req.index < 0 or req.index >= len(requirements):
#             raise HTTPException(status_code=400, detail="Invalid requirement index")

#         # Update the text
#         requirements[req.index]["text"] = req.newText

#         # Write back to file
#         with open(path, "w", encoding="utf-8") as f:
#             json.dump(data, f, indent=2)

#         # Also update in-memory state
#         conv["refinement_results"]["requirements"] = requirements

#         return {"status": "success", "updated_requirement": requirements[req.index]}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/projects/{project_id}/srs")
# async def get_srs_document(project_id: str, db: AsyncIOMotorDatabase = Depends(get_db),):
#         # 1️⃣ Check if HTML already exists
#     srs = await db["srs_documents"].find_one({"project_id": project_id})

#     if srs and "html" in srs:
#         return {
#             "mode": "html",
#             "html": srs["html"]
#         }
#     else:
#         # 1️⃣ Fetch SRS document
#         srs = await db["srs_documents"].find_one({"project_id": project_id})
#         if not srs:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="SRS document not found"
#             )

#         srs_id = str(srs["_id"])
#         project = await db["projects"].find_one({"_id": project_id})
#         print("Fetched project:", project)

#         title = project["title"] if project and "title" in project else "untitled"

#         # 2️⃣ Fetch sections (ordered)
#         sections_cursor = db["srs_sections"].find(
#             {"srs_id": srs_id}
#         ).sort("order_index", 1)

#         sections = []
#         async for section in sections_cursor:
#             section["_id"] = str(section["_id"])
#             sections.append(section)

#         # 3️⃣ Fetch section-requirement mappings
#         section_ids = [s["_id"] for s in sections]

#         mappings_cursor = db["section_requirement_map"].find(
#             {"section_id": {"$in": section_ids}}
#         )

#         mappings = []
#         req_ids = set()

#         async for m in mappings_cursor:
#             m["_id"] = str(m["_id"])
#             mappings.append(m)
#             req_ids.add(m["req_id"])

#         # 4️⃣ Fetch requirements
#         requirements_cursor = db["requirements"].find(
#             {"_id": {"$in": list(req_ids)}}
#         )

#         requirements = []
#         async for r in requirements_cursor:
#             r["_id"] = str(r["_id"])
#             requirements.append(r)

#         # 5️⃣ Final response
#         return {
#             "srs": {
#                 "srs_id": srs_id,
#                 "project_id": srs["project_id"],
#                 "template": srs["template"],
#                 "version": srs["version"]
#             },
#             "title": title,
#             "sections": sections,
#             "mappings": mappings,
#             "requirements": requirements
#         }



# # save updated text
# @router.post("/projects/{project_id}/srs")
# async def save_srs_document(
#     project_id: str,
#     payload: dict,
#     db: AsyncIOMotorDatabase = Depends(get_db),
# ):
#     html = payload.get("html")

#     if not html:
#         raise HTTPException(status_code=400, detail="HTML is required")

#     await db["srs_documents"].update_one(
#         {"project_id": project_id},
#         {
#             "$set": {
#                 "html": html,
#                 "updated_at": datetime.now()
#             }
#         },
#         upsert=True
#     )

#     return {"status": "saved"}


# # save requirements to database
# @router.post("/projects/{project_id}/requirements/bulk_create")
# async def save_requirements_bulk(payload: BulkCreateRequirementsRequest,  db: AsyncIOMotorDatabase = Depends(get_db),):
#     """
#     Save a list of requirements to MongoDB in bulk.
#     Can be called directly by the agent.
#     """
#     if not payload.requirements:
#         raise HTTPException(status_code=400, detail="No requirements provided")

#     requirements_collection = db["requirements"]
#     # Prepare documents for MongoDB
#     documents = [
#         {
#             "project_id": req.project_id,
#             "req_id": req.req_id,
#             "text": req.text,
#             "type": req.type,
#             "subtype": req.subtype,
#             "created_at": datetime.now(),  # UTC timestamp
#         }
#         for req in payload.requirements
#     ]
#     try:
#         # Insert into MongoDB
#         result = await requirements_collection.insert_many(documents)
#         print(f"[API] Inserted {len(result.inserted_ids)} requirements into database.")
#         return {
#             "message": "Requirements saved successfully",
#             "inserted_count": len(result.inserted_ids),
#             "requirement_ids": [str(_id) for _id in result.inserted_ids],
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error saving requirements: {str(e)}")

 
# async def send_requirements_to_route(payload: dict, project_id: str):
#     async with httpx.AsyncClient() as client:
#         response = await client.post(
#             f"http://localhost:8000/api/projects/{project_id}/requirements/bulk_create",
#             json=payload  # payload must be JSON-serializable (dict)
#         )
#         response.raise_for_status()
#         return response.json()