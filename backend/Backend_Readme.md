# MARS Backend Architecture - Complete Workflow Explanation

## Overview
MARS (Multi-Agent Requirement Engineering System) is a **FastAPI-based backend** that orchestrates multiple specialized agents to process requirements documents through various analysis phases. The system uses **RabbitMQ** for asynchronous Agent-to-Agent (A2A) communication and **LangGraph/LangChain** for AI-powered processing.

---

## 1. Technology Stack

### Core Framework
- **FastAPI** - REST API framework (port 8000)- **Uvicorn** - ASGI server (async Python web server)
- **Python 3.8+** - Backend language

### Async Communication
- **RabbitMQ** - Message broker for agent communication
- **aio-pika** - Async Python RabbitMQ client

### AI/ML Libraries
- **LangGraph** - Agent workflow orchestration
- **LangChain** - LLM integration framework
- **OpenAI/Anthropic** - LLM providers
- **PyTorch + BERT** - Siamese model for requirement analysis
- **Transformers** - Transformer models

### Data Handling
- **Pydantic** - Data validation
- **python-docx** - DOCX file parsing
- **PyPDF2** - PDF file parsing

---

### FSARC & Stanford CoreNLP (Local dependency)

FSARC (Finer Semantic Analysis-based Requirement Conflict Detector) is included under `backend/agents/cdn/FSARC` but its CoreNLP models and the Java server are NOT committed to this repository. To run FSARC you must install a few local/system dependencies and provide the CoreNLP distribution locally.

Prerequisites
- **Java JDK 11+** installed and `java` available on `PATH`.

Python dependencies (already included in `backend/requirements.txt`)
- `requests` (HTTP client) — used to call the CoreNLP server
- `psutil` — used to manage/terminate the spawned CoreNLP process
- `PyYAML` — used to read `rules.yml` and `dict.yml`

Stanford CoreNLP (manual steps)
1. Download the CoreNLP package (recommended):

  - URL: https://nlp.stanford.edu/software/stanford-corenlp-latest.zip

2. Extract the ZIP to a local directory (for example `C:/tools/stanford-corenlp` or `~/stanford-corenlp`).

3. Update the FSARC config path `CoreNLP_path` in `backend/agents/cdn/FSARC/config.py` to point to the extracted CoreNLP directory (the directory that contains the `.jar` files). Example:

  ```python
  # backend/agents/cdn/FSARC/config.py
  CoreNLP_path = r"C:\tools\stanford-corenlp\stanford-corenlp-4.5.6"
  ```

4. Ensure the CoreNLP English models are present (they are included in the ZIP download). If you prefer not to let FSARC start the server itself, you can start the server manually from the CoreNLP directory:

  ```bash
  cd /path/to/stanford-corenlp
  java -Xmx8g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLPServer -port 9999
  ```

5. By default FSARC will attempt to start its own CoreNLP server on `http://localhost:9999` using the configured `CoreNLP_path`. Make sure port `9999` is available and not blocked by a firewall.

Testing the CoreNLP server

After starting the server (manually or via FSARC), test it:

```bash
curl -X POST 'http://localhost:9999/?properties={"annotators":"tokenize,ssplit,pos,lemma,ner,parse,depparse","outputFormat":"json"}' -d 'This is a test sentence.'
```

If you get JSON back, CoreNLP is running and FSARC can call it.

Notes
- FSARC reads `rules.yml` and `dict.yml` (they are included under `backend/agents/cdn/FSARC`). Do NOT remove those files.
- Because the CoreNLP distribution is large, it is intentionally excluded from the repo. Add the path in `config.py` to tell FSARC where to find it.
- If you run into permission or Java memory issues, reduce/increase `-Xmx` in `backend/agents/cdn/FSARC/FSARC/nlp.py` or run the server manually with a tuned `-Xmx` value.
- Use this command to run fsarc :
`java -mx4g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLPServer   -port 9000 -timeout 15000`
---

## 2. Project Structure

```
backend/
├── main.py                          # Entry point - FastAPI app initialization
├── server.js                        # Express.js server (legacy/supporting)
├── index.js                         # Node.js index (legacy/supporting)
├── requirements.txt                 # Python dependencies
├── package.json                     # Node.js dependencies
│
├── api/                             # FastAPI routes
│   └── routes.py                    # Endpoint handlers
│
├── core/                            # Core system modules
│   └── rabbitmq.py                  # RabbitMQ initialization
│
├── common/                          # Shared utilities
│   └── a2a.py                       # Agent-to-Agent messaging (RabbitMQ wrapper)
│
├── agents/                          # Multi-agent system
│   ├── base_agent.py                # Abstract base class for all agents
│   ├── elicitation/
│   │   ├── agent.py                 # Elicitation agent (initial processing)
│   │   └── helpers.py               # Helper functions
│   ├── cdn/                         # Conflict Detection & Nomination
│   │   ├── agent.py                 # CDN agent (main logic)
│   │   ├── CD-ClusterSiameseAnalyzer.py  # Clustering-based analyzer
│   │   ├── CD-SiameseAnalyzer.py        # Direct pairwise analyzer
│   │   ├── cdn_terminal.py          # Terminal interface
│   │   └── siameseModel/            # Pre-trained Siamese BERT model
│   │       └── model.py             # Model definition
│   ├── refinement/
│   │   ├── agent.py                 # Refinement agent
│   │   └── helpers.py               # Helper functions
│   ├── document/
│   │   ├── agent.py                 # Document generation agent
│   │   └── helpers.py               # Helper functions
│   └── user_story/
│       ├── agent.py                 # User story generation agent
│       └── helpers.py               # Helper functions
│
├── orchestrator/                    # Workflow orchestration
│   ├── orchestrator.py              # Main workflow orchestrator
│   └── shared_state.py              # Global state management for conversations
│
├── utils/                           # Utility functions
│   ├── document_parser.py           # Document text extraction & parsing
│   └── runPython.js                 # Node.js Python subprocess runner
│
├── data/                            # Data files
│   └── *.json                       # Test data & configurations
│
├── model/                           # Pre-trained models
│   ├── siamese_model.pth            # PyTorch model weights
│   ├── bert_config/                 # BERT configuration
│   └── tokenizer/                   # BERT tokenizer
│
├── results/                         # Analysis results output
│   ├── *.json                       # JSON format results
│   └── *.txt                        # Text format results
│
└── uploads/                         # User uploaded documents
    └── *                            # Temporary storage for uploaded files
```

---

### Architecture
┌─────────────────────────────────────┐
│   FastAPI (Public REST Interface)   │  ← Only this exposes APIs
│   - /api/upload                     │
│   - /api/results                    │
│   - /api/process                    │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│   Orchestrator (Internal Router)    │  ← Manages workflow
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│   5 Agents (Internal Workers)       │  ← No public APIs
│   - Elicitation                     │
│   - CDN                             │
│   - Refinement                      │
│   - Document                        │
│   - User Story                      │
└─────────────────────────────────────┘




## 3. Complete Workflow When Running `main.py`

### Step 0: Server Initialization (FastAPI Startup)
```
$ python main.py
```

When you run `main.py`, the FastAPI app starts with a **lifespan context manager** that handles startup/shutdown:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP PHASE:
    print("Starting MARS FYP Backend...")
    
    # 1. Initialize RabbitMQ
    await initialize_rabbitmq()
    
    # 2. Start all 5 agents as background tasks
    agent_tasks.append(asyncio.create_task(start_elicitation()))
    agent_tasks.append(asyncio.create_task(start_cdn()))
    agent_tasks.append(asyncio.create_task(start_refinement()))
    agent_tasks.append(asyncio.create_task(start_document()))
    agent_tasks.append(asyncio.create_task(start_user_story()))
    
    # All agents are now listening on their respective RabbitMQ queues
    
    yield  # Server is now ready to accept requests
    
    # SHUTDOWN PHASE: Cancel all agent tasks
```

**Result**: Server runs on `http://0.0.0.0:8000` with all 5 agents active and listening.

---

### Step 1: API Routes Available

The FastAPI server exposes the following endpoints:

#### Health Check
```
GET /api/health
Response: {"status": "ok", "message": "Backend is running"}
```

#### Upload Document & Start Workflow
```
POST /api/upload
Content-Type: multipart/form-data
Files: .txt, .docx, .pdf

1. Saves file to uploads/ directory
2. Extracts text content
3. Parses requirements structure
4. Starts workflow automatically
5. Returns immediately with status
```

#### Trigger Workflow Without Document
```
POST /api/process
Body: {"message": "start"}

Starts workflow without document (agents process with has_document=False)
```

#### Retrieve Results
```
GET /api/results
Returns: CDN analysis results with siamese classification
```

#### Authentication (Demo)
```
POST /api/signup    - Register user
POST /api/login     - Login user
```

---

### Step 2: Complete Workflow Execution Flow

When a document is uploaded via `/api/upload` or workflow triggered via `/api/process`:

#### **Phase 1: Orchestrator Initialization**
```
1. Generate unique conversation ID: conv-uuid-xxx
2. Store document in SharedState if provided
3. Create inbox queue for receiving agent replies
4. Start background consumer task
```

#### **Phase 2: Sequential Agent Calls**

**STEP 1 → Elicitation Agent**
```
Orchestrator sends:
  TO: Elicitation (via RabbitMQ queue "Elicitation")
  MESSAGE: {
    sender: "Orchestrator",
    receiver: "Elicitation",
    type: "inform",
    payload: {"task": "initial elicit"},
    conv_id: "conv-xxx"
  }

Elicitation agent receives:
  - Processes message
  - Simulates work (asyncio.sleep(0.5))
  - Sends reply back to Orchestrator queue

Orchestrator receives:
  - Waits for reply (timeout: 10 seconds)
  - Stores in conversation state
```

**STEP 2 → CDN (Conflict Detection & Nomination) Agent**
```
Orchestrator sends:
  TO: CDN
  MESSAGE: {payload: {"task": "cdn work", "has_document": True}}

CDN agent receives:
  1. Checks if document is available
  2. If NOT in cache:
     - Sends document REQUEST to Orchestrator
     - Orchestrator responds with parsed requirements
     - Loads requirements into memory
  3. Initializes DirectClusteringSiameseAnalyzer
  4. Runs conflict detection using Siamese BERT model:
     - Creates requirement pairs
     - Computes embeddings
     - Clusters requirements
     - Classifies pairs (Duplicate/Conflict/Orthogonal/Neutral)
  5. Saves results to results/cdn_results_{conv_id}.json
  6. Sends reply with results path to Orchestrator

Orchestrator receives and stores results path in SharedState
```

**STEP 3 → Refinement-CDN Loop (2 iterations)**
```
For iteration 1 and 2:
  
  SUBSTEP 3a → Refinement Agent
    Orchestrator: "refine pass 1"
    Refinement: Simulates refinement work, replies "done"
  
  SUBSTEP 3b → CDN Agent Again
    Orchestrator: "cdn pass 1" (with has_document=True)
    CDN: Processes again, sends results
    
  (Repeat for iteration 2)
```

**STEP 4 → Document & User Story Agents (Parallel)**
```
Orchestrator sends BOTH simultaneously:
  - TO: Document     MESSAGE: {"task": "create doc"}
  - TO: User_Story   MESSAGE: {"task": "create user stories"}

Both agents process in parallel:
  Document agent: Creates documentation
  User_Story agent: Generates user stories

Orchestrator waits for BOTH replies (order independent)
```

#### **Phase 3: Workflow Completion**
```
All agent replies collected and stored
Orchestrator prints:
  ✓ Workflow complete!
  ✓ Total messages received: 9
  ✓ Conv_id: conv-xxx

Results accessible via GET /api/results endpoint
```

---

## 4. Agent Deployment & Architecture

### Agent Pattern

Each agent follows this pattern:

```python
# 1. Define agent identity
AGENT_NAME = "AgentName"
ORCHESTRATOR_QUEUE = "Orchestrator"
EXCHANGE = "agents-exchange"

# 2. Define message handler
async def handle_message(msg: dict):
    conv_id = msg.get("conv_id")
    payload = msg.get("payload")
    
    # Process work
    await do_work()
    
    # Send reply back to Orchestrator
    reply = A2AMessage(
        sender=AGENT_NAME,
        receiver="Orchestrator",
        type="confirm",
        payload={"status": "done", "from": AGENT_NAME},
        conv_id=conv_id
    ).dict()
    
    await publish_message(EXCHANGE, ORCHESTRATOR_QUEUE, reply)

# 3. Start agent listener
async def start_agent():
    print(f"[{AGENT_NAME}] Agent started and listening on queue '{AGENT_NAME}'")
    await consume_queue(AGENT_NAME, handle_message)
```

### The 5 Agents

| Agent | Purpose | Status |
|-------|---------|--------|
| **Elicitation** | Initial requirement extraction & elicitation | Mock/Placeholder |
| **CDN** | Conflict Detection & Nomination using Siamese BERT | Fully Implemented |
| **Refinement** | Requirement refinement and improvement | Mock/Placeholder |
| **Document** | Generate final requirement documents | Mock/Placeholder |
| **User_Story** | Convert requirements to user stories | Mock/Placeholder |

### How Agents Are Deployed

1. **At Server Startup** (`main.py` lifespan):
   ```python
   agent_tasks.append(asyncio.create_task(start_elicitation()))
   agent_tasks.append(asyncio.create_task(start_cdn()))
   # ... etc for all 5 agents
   ```

2. **Agents Run as Background Tasks**:
   - Each agent runs in its own asyncio task
   - Each agent listens to its own RabbitMQ queue
   - Agents are non-blocking and concurrent

3. **Lifecycle Management**:
   - On server startup: All agents start listening
   - During shutdown: All agent tasks are cancelled gracefully
   - Agents never stop listening (infinite loop via `consume_queue`)

4. **Scalability**:
   - Can run multiple instances of same agent
   - RabbitMQ handles load balancing across instances
   - Horizontal scaling ready

---

## 5. RabbitMQ & Message Communication

### RabbitMQ Setup

**Connection Details**:
```
RABBITMQ_URL = "amqp://guest:guest@127.0.0.1/"  # Default
EXCHANGE = "agents-exchange"  # Direct exchange
QUEUES = ["Orchestrator", "Elicitation", "CDN", "Refinement", "Document", "User_Story"]
```

### Message Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         RabbitMQ Broker                         │
│                    (agents-exchange, DIRECT)                    │
└─────────────────────────────────────────────────────────────────┘
         ↑                                              ↑
         │                                              │
    PUBLISH                                      CONSUME
    (routing_key)                              (queue binding)
         │                                              │
    ┌────┴──────────┐                      ┌──────────┴───────┐
    │  Orchestrator │◄───────────────────►│ Agent Listeners  │
    │   (Sender)    │                      │ (Elicitation,    │
    │               │                      │  CDN, Document,  │
    │  Publishes    │                      │  Refinement,     │
    │  Messages to: │                      │  User_Story)     │
    │   - "CDN"     │                      │                  │
    │   - "Elicit"  │                      │  Each agent:     │
    │   - "Refine"  │                      │  await consume_  │
    │   - "Doc"     │                      │  queue()         │
    │   - "UserStory"                      │                  │
    └───────────────┘                      └──────────────────┘
         ↑
         │
    REPLIES
    (routing_key="Orchestrator")
         │
    ┌────┴──────────┐
    │     Agents    │
    │   (Reply)     │
    │               │
    │  Send back to │
    │  Orchestrator │
    │  queue        │
    └───────────────┘
```

### A2A Message Structure

All messages follow this structure (defined in `common/a2a.py`):

```python
class A2AMessage(BaseModel):
    sender: str              # "Orchestrator" or Agent name
    receiver: str            # "Orchestrator" or Agent name
    type: str                # "inform", "request", "confirm", "error"
    payload: Dict[str, Any]  # Actual message data
    conv_id: str             # Conversation identifier (UUID)
```

### Example Message Flow

**Orchestrator → CDN Agent**:
```json
{
  "sender": "Orchestrator",
  "receiver": "CDN",
  "type": "inform",
  "payload": {
    "task": "cdn work",
    "has_document": true
  },
  "conv_id": "conv-abc-123-xyz"
}
```

**CDN Agent → Orchestrator (Reply)**:
```json
{
  "sender": "CDN",
  "receiver": "Orchestrator",
  "type": "confirm",
  "payload": {
    "status": "done",
    "from": "CDN",
    "has_document": true,
    "analysis_complete": true,
    "results_path": "/results/cdn_results_conv-abc-123-xyz.json",
    "clusters_count": 5,
    "total_pairs": 24
  },
  "conv_id": "conv-abc-123-xyz"
}
```

---

## 6. FastAPI Endpoints in Detail

### Location: `api/routes.py`

#### **1. GET /api/health**
```
Purpose: Health check
Returns: {"status": "ok", "message": "Backend is running"}
No parameters
```

#### **2. POST /api/upload**
```
Purpose: Upload document and start workflow

Request:
  Content-Type: multipart/form-data
  File: upload a .txt, .docx, .pdf file

Process:
  1. Validate file extension
  2. Save to uploads/ directory
  3. Extract text using document_parser.py
  4. Parse requirements structure
  5. Start workflow in background via run_workflow()
  6. Return immediately (non-blocking)

Response:
  {
    "status": "success",
    "message": "File uploaded and workflow started",
    "analysis": {
      "message": "Analysis started successfully",
      "saved_json": "uploads/filename.ext",
      "requirements_count": 25
    }
  }
```

#### **3. GET /api/results**
```
Purpose: Get analysis results

Query Parameters: None

Process:
  1. Retrieve most recent conversation from SharedState
  2. Load CDN results from file
  3. Transform results to frontend format
  4. Return all pairs with classifications

Response:
  {
    "status": "completed",
    "conv_id": "conv-abc-123",
    "siamese_results": {cluster_data},
    "all_pairs": [
      {
        "req1_number": 1,
        "req2_number": 2,
        "req1_text": "As a user...",
        "req2_text": "As a user...",
        "predicted_class": "Duplicate",
        "confidence": 0.95,
        "all_probabilities": {...}
      }
    ],
    "metadata": {...}
  }
```

#### **4. POST /api/process**
```
Purpose: Trigger workflow without uploading document

Request:
  {
    "message": "start"
  }

Response:
  {
    "status": "processing started",
    "message": "Workflow initiated"
  }
```

#### **5. POST /api/signup** (Demo)
```
Purpose: User registration

Request:
  {
    "username": "user123",
    "password": "pass123",
    "name": "User Name"
  }

Response:
  {
    "message": "Signup successful",
    "user": {"username": "user123"}
  }
```

#### **6. POST /api/login** (Demo)
```
Purpose: User login

Request:
  {
    "username": "user123",
    "password": "pass123"
  }

Response:
  {
    "message": "Login successful",
    "user": {"username": "user123"}
  }
```

---

## 7. The CDN Agent in Detail

### Most Complex Agent - Fully Implemented

**File**: `agents/cdn/agent.py`

#### Responsibilities:
1. Receive document from orchestrator
2. Initialize Siamese BERT model
3. Perform requirement clustering
4. Classify requirement pairs
5. Save results (JSON + TXT)

#### Implementation Details:

```python
# Pre-loads model on startup
async def start_agent():
    global _global_analyzer
    
    # Pre-load expensive model at startup
    _global_analyzer = DirectClusteringSiameseAnalyzer(
        model_dir="model",  # Contains: siamese_model.pth, bert_config, tokenizer
        dropout_rate=0.3,
        pooling_strategy='mean'
    )
    
    # Start listening
    await consume_queue("CDN", handle_message)
```

#### Model Architecture (Siamese BERT):
```
Input Requirements
        ↓
  Tokenization (BERT tokenizer)
        ↓
  BERT Embedding Layer
        ↓
  Mean Pooling
        ↓
  Requirement Embeddings (768-dim vectors)
        ↓
  K-means Clustering (groups similar reqs)
        ↓
  Pairwise Comparison (Siamese network)
        ↓
  Classification Head
        ↓
  Output: [Duplicate, Conflict, Orthogonal, Neutral]
        ↓
  Save Results (clusters + classifications)
```

#### Data Files Used:
```
Input:
  - Model: model/siamese_model.pth (PyTorch weights)
  - BERT: model/bert_config/config.json + model/tokenizer/*
  - Requirements: JSON with requirement list

Output:
  - results/cdn_results_conv-abc.json (structured results)
  - results/cdn_results_conv-abc.txt (readable text)
```

---

## 8. Shared State & State Management

**File**: `orchestrator/shared_state.py`

### Global State Pattern

```python
@dataclass
class SharedState:
    conversations: Dict[str, Dict[str, Any]] = {}
    
    # Each conversation stores:
    {
        "conv_id": "conv-xxx",
        "document_path": "/uploads/file.pdf",
        "parsed_requirements": [{...}, {...}],
        "cdn_results": {siamese_results},
        "cdn_results_path": "/results/cdn_results_conv-xxx.json",
        "metadata": {...}
    }

def get_shared_state() -> SharedState:
    global _shared_state
    if _shared_state is None:
        _shared_state = SharedState()
    return _shared_state
```

### Usage:
```python
# Store document
shared_state = get_shared_state()
shared_state.store_document(conv_id, path, requirements)

# Retrieve for agent
doc = shared_state.get_document(conv_id)

# Store CDN results
shared_state.store_cdn_results(conv_id, results_path, data)

# Retrieve results for API
results = shared_state.get_cdn_results(conv_id)
```

---

## 9. Document Parsing

**File**: `utils/document_parser.py`

Supports multiple formats:
- **.txt** - Plain text (line-by-line parsing)
- **.docx** - Word documents (python-docx library)
- **.pdf** - PDF files (PyPDF2 library)

### Output Structure:
```python
{
    "requirements": [
        {
            "id": 1,
            "text": "The system shall...",
            "source": "document.pdf",
            "type": "functional"  # or "non-functional"
        },
        {
            "id": 2,
            "text": "The system must be...",
            "source": "document.pdf",
            "type": "non-functional"
        }
    ],
    "metadata": {
        "total_count": 25,
        "parsing_timestamp": "2025-11-30T10:30:00",
        "source_file": "requirements.pdf"
    }
}
```

---

## 10. Complete Request-Response Example

### Scenario: Upload a requirements document

**1. User uploads file**:
```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@requirements.pdf"
```

**2. Server processes request**:
```
FastAPI receives upload
├─ Saves to: uploads/requirements.pdf
├─ Extracts text content
├─ Parses requirements (25 requirements found)
├─ Calls run_workflow() in background
└─ Returns immediately

Response (HTTP 200):
{
  "status": "success",
  "message": "File uploaded and workflow started",
  "analysis": {
    "message": "Analysis started successfully",
    "saved_json": "uploads/requirements.pdf",
    "requirements_count": 25
  }
}
```

**3. Workflow executes in background**:
```
Orchestrator:
├─ conv_id: "conv-1234-5678"
├─ Store document in SharedState
│
├─ STEP 1: Send to Elicitation
│  └─ Elicitation replies "done"
│
├─ STEP 2: Send to CDN
│  ├─ CDN requests document from Orchestrator
│  ├─ Receives 25 requirements
│  ├─ Loads Siamese BERT model
│  ├─ Creates embeddings for 25 requirements
│  ├─ Clusters into 4 groups
│  ├─ Analyzes 120+ pairs
│  ├─ Classifies as: Duplicate, Conflict, Orthogonal, Neutral
│  └─ Saves results to: results/cdn_results_conv-1234.json
│
├─ STEP 3: Refinement-CDN loop (2 iterations)
│  ├─ Refinement replies "done"
│  └─ CDN analyzes again
│
└─ STEP 4: Document & User Story (parallel)
   ├─ Document agent replies "done"
   └─ User_Story agent replies "done"

Results stored in SharedState
```

**4. User checks results**:
```bash
curl -X GET "http://localhost:8000/api/results"
```

**Response**:
```json
{
  "status": "completed",
  "conv_id": "conv-1234-5678",
  "siamese_results": {
    "0": [
      {
        "req1_number": 1,
        "req2_number": 3,
        "req1_text": "System shall store user data",
        "req2_text": "System shall save user information",
        "predicted_class": "Duplicate",
        "confidence": 0.97
      }
    ],
    "1": [...]
  },
  "all_pairs": [...],
  "metadata": {...}
}
```

---

## 11. FastAPI Location Summary

```
FastAPI Endpoints:
├─ GET  /api/health              → health_check()
├─ POST /api/upload              → upload_file()         [MAIN ENTRY]
├─ GET  /api/results             → get_results()         [RETRIEVE RESULTS]
├─ POST /api/process             → process_message()
├─ POST /api/signup              → signup()
└─ POST /api/login               → login()

All located in: backend/api/routes.py
Defined in: FastAPI router
Included in: app.include_router(api_router, prefix="/api")
Started by: uvicorn.run("main:app", host="0.0.0.0", port=8000)
```

---

## 12. Key Files Reference

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app initialization & agent startup |
| `api/routes.py` | All HTTP endpoints |
| `core/rabbitmq.py` | RabbitMQ connection init |
| `common/a2a.py` | RabbitMQ messaging interface |
| `orchestrator/orchestrator.py` | Workflow orchestration logic |
| `orchestrator/shared_state.py` | Conversation state storage |
| `agents/*/agent.py` | Individual agent implementations |
| `agents/cdn/agent.py` | Complex CDN agent with ML model |
| `agents/cdn/CD-ClusterSiameseAnalyzer.py` | Siamese BERT analyzer |
| `utils/document_parser.py` | Document text extraction |
| `requirements.txt` | Python dependencies |

---

## 13. Startup Sequence (Step-by-step)

```
1. User runs: python main.py

2. FastAPI app created with lifespan context manager

3. Uvicorn server starts on 0.0.0.0:8000

4. STARTUP PHASE:
   ├─ Initialize RabbitMQ connection
   ├─ Declare agents-exchange (DIRECT)
   └─ Start all 5 agents as background tasks:
      ├─ start_elicitation()
      ├─ start_cdn()  [Pre-loads model here - 30-60 seconds]
      ├─ start_refinement()
      ├─ start_document()
      └─ start_user_story()

5. Each agent calls consume_queue("AgentName", handler)
   └─ Now listening on its queue indefinitely

6. Server ready to accept requests
   ├─ POST /api/upload           → Start workflow
   ├─ GET  /api/results          → Get results
   └─ Other endpoints available

7. When server stops (Ctrl+C):
   ├─ SHUTDOWN PHASE
   ├─ Cancel all agent tasks
   ├─ Close RabbitMQ connections
   └─ Exit gracefully
```

---

## 14. Concurrency Model

### Async Concurrency
- **FastAPI**: Handles 100+ concurrent HTTP requests
- **Agents**: Run concurrently via asyncio tasks
- **Workflows**: Multiple conversations can run in parallel (different conv_ids)

### Example: 2 Users Upload Simultaneously
```
User A uploads file
  └─ Workflow A started with conv_id: conv-aaa-111
     └─ Messages queued for agents with conv_id

User B uploads file
  └─ Workflow B started with conv_id: conv-bbb-222
     └─ Messages queued for agents with conv_id

Both workflows execute concurrently:
  - Different conversations tracked separately
  - Agents handle both via conv_id routing
  - Results stored separately in SharedState
```

---

## Summary

**MARS Backend Architecture**:
1. **FastAPI** exposes REST endpoints for upload, results, etc.
2. **Orchestrator** manages workflow execution and agent sequencing
3. **5 Agents** process requirements in parallel/sequential order
4. **RabbitMQ** provides reliable message passing between orchestrator and agents
5. **CDN Agent** performs AI-powered requirement analysis using Siamese BERT
6. **SharedState** maintains conversation context across all agents
7. **Results** stored and served to frontend via API

**Key Technologies**: FastAPI, RabbitMQ, AsyncIO, LangGraph, PyTorch, BERT

**Entry Point**: Run `python main.py` → Server starts → Upload document → Workflow executes → Results available via API
