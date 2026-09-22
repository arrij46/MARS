# 🚀 MARS - Multi-Agent Requirement Engineering System

> **An intelligent multi-agent system for automated software requirement analysis, conflict detection, and documentation generation using AI-powered agents and machine learning.**

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Quick Start](#quick-start)
- [System Architecture](#system-architecture)
- [Workflow](#workflow)
- [API Endpoints](#api-endpoints)
- [Configuration](#configuration)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

**MARS (Multi-Agent Requirement Engineering System)** is an intelligent platform that automates the software requirement engineering process through:

1. **Multi-Agent Architecture** - 5 specialized agents working together
2. **AI-Powered Analysis** - Siamese BERT model for requirement classification
3. **Conflict Detection** - Automated detection of duplicate/conflicting requirements
4. **Smart Orchestration** - LangGraph-based workflow management
5. **Asynchronous Processing** - RabbitMQ-based agent communication
6. **Modern UI** - React + Vite frontend with real-time analysis

### The Problem MARS Solves

- **Manual requirement analysis is time-consuming** → MARS automates it
- **Detecting duplicates/conflicts requires domain expertise** → AI model does this
- **Document parsing is error-prone** → Supports .txt, .pdf, .docx automatically
- **Multi-step workflows need coordination** → Agents orchestrate seamlessly

---

## ✨ Key Features

### 🤖 Multi-Agent System
- **Elicitation Agent**: Initial requirement extraction
- **CDN Agent**: Conflict Detection & Nomination (ML-powered)
- **Refinement Agent**: Requirement refinement and improvement
- **Document Agent**: Generate finalized requirement documents
- **User Story Agent**: Convert requirements to user stories

### 🔬 AI/ML Capabilities
- **Siamese BERT Model**: Deep learning-based requirement comparison
- **Automatic Clustering**: Group similar requirements
- **Classification**: Duplicate, Conflict, Orthogonal, Neutral
- **Semantic Analysis**: Understand requirement relationships

### 📄 Document Support
- PDF files
- Word documents (.docx)
- Plain text (.txt)
- Automatic text extraction and requirement parsing

### 🔄 Async Processing
- Non-blocking API endpoints
- Background workflow execution
- Real-time status updates
- Horizontal scalability

### 📊 Results & Analysis
- Detailed requirement pair analysis
- Confidence scores for classifications
- JSON structured output
- Visual dashboard integration

---

## 🛠 Tech Stack

### Backend
- **FastAPI** - High-performance REST API framework
- **Python 3.8+** - Core language
- **RabbitMQ** - Asynchronous message broker
- **LangGraph/LangChain** - Agent orchestration
- **PyTorch + BERT** - ML model for requirement analysis
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server

### Frontend
- **React 18+** - UI library
- **Vite** - Build tool & dev server
- **React Router** - Client-side routing
- **Bootstrap** - UI components
- **React Icons** - Icon library
- **Axios/Fetch** - HTTP client

### Database & Storage
- **In-Memory State** - SharedState for conversation tracking
- **JSON Files** - Result persistence
- **File System** - Document storage

### DevOps & Deployment
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration
- **Nginx** - Reverse proxy

---

## 📁 Project Structure

```
MARS-MultiAgentRequirementEngineeringSystem/
│
├── backend/
│   ├── main.py                          # FastAPI entry point
│   ├── requirements.txt                 # Python dependencies
│   │
│   ├── api/
│   │   └── routes.py                    # REST endpoints
│   │
│   ├── agents/                          # Multi-agent system
│   │   ├── base_agent.py                # Abstract base class
│   │   ├── elicitation/agent.py
│   │   ├── cdn/
│   │   │   ├── agent.py
│   │   │   ├── CD-ClusterSiameseAnalyzer.py
│   │   │   └── siameseModel/model.py
│   │   ├── refinement/agent.py
│   │   ├── document/agent.py
│   │   └── user_story/agent.py
│   │
│   ├── orchestrator/                    # Workflow coordination
│   │   ├── orchestrator.py              # Main orchestrator
│   │   └── shared_state.py              # Conversation state
│   │
│   ├── core/
│   │   └── rabbitmq.py                  # RabbitMQ setup
│   │
│   ├── common/
│   │   └── a2a.py                       # Agent-to-Agent messaging
│   │
│   ├── utils/
│   │   └── document_parser.py           # Document parsing
│   │
│   ├── model/                           # Pre-trained models
│   │   ├── siamese_model.pth
│   │   ├── bert_config/
│   │   └── tokenizer/
│   │
│   ├── data/                            # Test data
│   ├── results/                         # Analysis results
│   └── uploads/                         # User uploads
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   │
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── elicitation.jsx
│   │   │   ├── requirementList.jsx
│   │   │   ├── AuthenticationPage.jsx
│   │   │   └── landing-page.jsx
│   │   ├── components/
│   │   │   ├── Popup.jsx
│   │   │   ├── modelAnimation.jsx
│   │   │   ├── AttachmentComponent.jsx
│   │   │   └── elicitation-page/
│   │   └── style/
│   │       └── *.css
│   │
│   └── public/
│       └── assets/
│
├── MidReport-FYP01/                     # FYP documentation
├── ml/                                  # ML training code
│   ├── ModelTraining/
│   │   ├── train.py
│   │   ├── model.py
│   │   └── dataset.py
│   └── Dataset/
│
├── BACKEND_ARCHITECTURE_EXPLANATION.md  # Detailed backend docs
└── PROJECT_README.md                    # This file
```

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8+
- Node.js 14+
- RabbitMQ 3.8+
- Git

### Backend Setup

#### 1. Clone Repository
```bash
git clone https://github.com/arrij46/MARS-MultiAgentRequirementEngineeringSystem.git
cd MARS-MultiAgentRequirementEngineeringSystem
```

#### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python -m venv venv
source venv/bin/activate
```

#### 3. Install Python Dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### 4. Start RabbitMQ

**Option A: Using Docker (Recommended)**
```bash
docker run -d \
  --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  rabbitmq:3-management
```

**Option B: Local Installation**
```bash
# macOS (with Homebrew)
brew services start rabbitmq

# Linux (Ubuntu/Debian)
sudo systemctl start rabbitmq-server

# Windows (with RabbitMQ installed)
rabbitmq-service start
```

#### 5. Start Backend Server
```bash
cd backend
python main.py
```

Expected output shows all agents starting successfully.

### Frontend Setup

#### 1. Install Dependencies
```bash
cd frontend
npm install
```

#### 2. Create Environment File
Create `frontend/.env`:
```env
VITE_API_URL=http://localhost:8000
```

#### 3. Start Development Server
```bash
npm run dev
```

---

## ⚡ Quick Start

### 1. Start All Services

**Terminal 1 - Backend:**
```bash
cd backend
python main.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 3 - RabbitMQ** (if local installation):
```bash
rabbitmq-server
```

### 2. Access Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **RabbitMQ Console**: http://localhost:15672 (guest/guest)

### 3. Test the System

#### Upload a Document
1. Navigate to http://localhost:5173
2. Click "Upload" button
3. Select a .txt, .pdf, or .docx file
4. Click "Analyze"
5. Wait for processing (10-25 seconds)
6. View results on "Requirement List" page

#### Using cURL
```bash
# Upload document
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@requirements.pdf"

# Check results
curl -X GET "http://localhost:8000/api/results"

# Health check
curl -X GET "http://localhost:8000/api/health"
```

---

## 🏗 System Architecture

### Component Overview

```
Frontend (React)  ←HTTP→  Backend API (FastAPI)  ←RabbitMQ→  Agents
   (5173)              (8000)                        (5672)
```

### Workflow Sequence

```
1. User Upload Document
   ↓
2. FastAPI receives & parses document
   ↓
3. Orchestrator starts workflow (conv_id)
   ↓
4. Elicitation Agent processes
   ↓
5. CDN Agent runs ML analysis
   ↓
6. Refinement-CDN Loop (2 iterations)
   ↓
7. Document + User Story Agents (parallel)
   ↓
8. Results stored in SharedState
   ↓
9. Frontend retrieves via /api/results
```

---

## 🔄 Complete Workflow

### Phase 1: Upload & Parse
- User uploads document (PDF/DOCX/TXT)
- Backend extracts text content
- Parses into requirement list
- Generates unique conversation ID

### Phase 2: Agent Processing

#### Step 1: Elicitation
- Validates requirements
- Passes to next agent

#### Step 2: CDN (Main ML Analysis)
- Groups similar requirements
- Runs Siamese BERT model
- Classifies pairs: Duplicate/Conflict/Orthogonal/Neutral
- Generates confidence scores

#### Step 3: Refinement-CDN Loop (x2)
- Refines requirements
- Re-analyzes with CDN
- Iterates for improvement

#### Step 4: Document & User Story (Parallel)
- Document Agent: Generates documentation
- User Story Agent: Creates user stories

### Phase 3: Results Delivery
- All results stored in SharedState
- Frontend polls `/api/results`
- Displays in interactive dashboard

---

## 📡 API Endpoints

### Base URL: `http://localhost:8000/api`

#### Health Check
```
GET /api/health
```

#### Upload Document
```
POST /api/upload
Content-Type: multipart/form-data
Body: file (binary)

Response: {
  "status": "success",
  "message": "File uploaded and workflow started",
  "analysis": {
    "requirements_count": 25,
    "saved_json": "uploads/filename.ext"
  }
}
```

#### Get Results
```
GET /api/results

Response: {
  "status": "completed",
  "conv_id": "conv-xxxx",
  "siamese_results": {...},
  "all_pairs": [...],
  "metadata": {...}
}
```

#### Start Workflow (No Document)
```
POST /api/process
Body: {"message": "start"}
```

#### Authentication
```
POST /api/signup
POST /api/login
```

Full API documentation available at: `http://localhost:8000/docs`

---

## ⚙️ Configuration

### Environment Variables

**Backend** (`backend/.env`):
```env
RABBITMQ_URL=amqp://guest:guest@127.0.0.1/
PYTHONUNBUFFERED=1
```

**Frontend** (`frontend/.env`):
```env
VITE_API_URL=http://localhost:8000
```

### RabbitMQ Setup

**Exchange**: `agents-exchange` (DIRECT)

**Queues** (auto-created):
- Orchestrator
- Elicitation
- CDN
- Refinement
- Document
- User_Story

---

## 🧪 Testing

### Manual Testing

```bash
# 1. Test backend health
curl http://localhost:8000/api/health

# 2. Create test file
echo "REQ-001: System shall authenticate users" > test.txt
echo "REQ-002: System shall validate credentials" >> test.txt

# 3. Upload file
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@test.txt"

# 4. Wait 15 seconds, then check results
curl http://localhost:8000/api/results
```

### Frontend Testing

1. Open http://localhost:5173
2. Try all workflow pages
3. Upload test documents
4. Verify result visualization

---

## 🐳 Docker Deployment

### Using Docker Compose

```yaml
version: '3.8'
services:
  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      RABBITMQ_URL: amqp://guest:guest@rabbitmq/
    depends_on:
      - rabbitmq

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    environment:
      VITE_API_URL: http://localhost:8000
    depends_on:
      - backend
```

### Deploy
```bash
docker-compose up --build
```

---

## 📊 Performance

### Typical Times
- Document parsing: 0.5-2s
- Elicitation: 0.5s
- CDN analysis (25 reqs): 5-10s
- Total workflow: 10-25s

### Scalability
- Concurrent users: 100+
- Requirements per doc: 100+
- Max file size: 50 MB

---

## 📚 Documentation

- **Backend Details**: `BACKEND_ARCHITECTURE_EXPLANATION.md`
- **API Swagger**: http://localhost:8000/docs
- **FYP Report**: `MidReport-FYP01/`
- **ML Training**: `ml/Readme`

---

## 🐛 Troubleshooting

### RabbitMQ Connection Failed
```bash
# Check if running
docker ps | grep rabbitmq

# Restart if needed
docker restart rabbitmq
```

### Port Already in Use
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/macOS
lsof -i :8000
kill -9 <PID>
```

### Model Loading Error
Use CPU instead of GPU in `agents/cdn/agent.py`

---

## 🤝 Contributing

1. Fork repository
2. Create feature branch: `git checkout -b feature/name`
3. Make changes and test
4. Commit: `git commit -m "Add feature"`
5. Push: `git push origin feature/name`
6. Create Pull Request

---

## 📝 License

Part of Final Year Project (FYP) at **FAST-NUCES**

**Author**: arrij46

---

## 📞 Support

- **Issues**: https://github.com/arrij46/MARS-MultiAgentRequirementEngineeringSystem/issues
- **Organization**: FAST-NUCES

---

**Happy Requirement Engineering! 🚀**

*For detailed technical documentation, see `BACKEND_ARCHITECTURE_EXPLANATION.md`*
