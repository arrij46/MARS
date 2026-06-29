#main.py
import asyncio
import traceback
import uvicorn
import os

from databaseSchema.db_instance import init_db
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

from pymongo.errors import PyMongoError
from dotenv import load_dotenv
import motor.motor_asyncio
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager

from api.routes import router
from core.rabbitmq import initialize_rabbitmq
from agents.elicitation.agent import ElicitationAgent
from agents.cdn.agent import CDNAgent
from agents.refinement.agent import RefinementAgent
from agents.document.agent import DocumentAgent
from agents.userStory.agent import UserStoryAgent
from dotenv import load_dotenv

# # Store background tasks
agent_tasks = []
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI_FINAL") 
ElicitationAgent_instance = ElicitationAgent()
CDNAgent_instance = CDNAgent()
RefinementAgent_instance = RefinementAgent()
DocumentAgent_instance = DocumentAgent()
UserStoryAgent_instance = UserStoryAgent()
orchestrator_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("=" * 60)
    print("Starting MARS FYP Backend...")
    print("=" * 60)
    
    # connect to db
    app.mongodb_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    app.mongodb = app.mongodb_client.get_database("mars")
    init_db(app.mongodb)
    if app.mongodb_client:
        print("Connected to MongoDB!")

    # Set database connection for UserStoryAgent
    UserStoryAgent_instance.set_database(app.mongodb)

    # Initialize RabbitMQ
    await initialize_rabbitmq()
    
    # Start all agents as background tasks
    print("\n[Main] Starting all agents...")
    agent_tasks.append(asyncio.create_task(ElicitationAgent_instance.start_agent()))
    agent_tasks.append(asyncio.create_task(CDNAgent_instance.start_agent()))
    agent_tasks.append(asyncio.create_task(RefinementAgent_instance.start_agent()))
    agent_tasks.append(asyncio.create_task(DocumentAgent_instance.start_agent()))
    agent_tasks.append(asyncio.create_task(UserStoryAgent_instance.start_agent()))
    
    # Print all routes for debugging
    #for route in app.routes:
        #print(route.path)

    # Give agents time to initialize
    await asyncio.sleep(1)
    
    print("\n[Main] All agents started and listening for messages")
    print("=" * 60)
    print("Backend is ready!")
    print("=" * 60 + "\n")

    
    yield
    
    # Shutdown
    print("\n[Main] Shutting down...")
    app.mongodb_client.close()
    print("MongoDB connection closed.")
    for task in agent_tasks:
        task.cancel()
    for task in agent_tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass
    print("[Main] Shutdown complete")


app = FastAPI(title="MARS FYP Backend", lifespan=lifespan, redirect_slashes=False)


app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "your-secret-key"), 
    same_site="lax",        
    https_only=False,      
    max_age=3600,           
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routes
app.include_router(router, prefix="/api")


# ---- Exception Handlers ----
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # exc.errors() returns a list of dicts with the validation problems
    print("Validation error:", exc.errors())

    try:
        body_bytes = await request.body()
        body = body_bytes.decode() if body_bytes else None
    except RuntimeError:
        body = "<stream already consumed>"

    print("Request body:", body)

    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

@app.exception_handler(PyMongoError)
async def mongo_exception_handler(request: Request, exc: PyMongoError):
    print("MongoDB Error:", exc)
    traceback.print_exc()

    return JSONResponse(
        status_code=500,
        content={"detail": "Database error. Please try again later."},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print("Unhandled Error:", exc)
    traceback.print_exc()

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)