# API Routes Structure

This directory contains the refactored API routes, organized by separation of concerns.

## Directory Structure

```
api/
├── routes/
│   ├── __init__.py              # Main router that combines all sub-routers
│   ├── auth_routes.py           # Authentication and OAuth routes
│   ├── upload_routes.py         # File upload and processing routes
│   ├── websocket_routes.py      # WebSocket real-time communication
│   ├── results_routes.py        # Analysis and refinement results
│   └── project_routes.py        # Project and SRS document management
└── ws_store.py                  # WebSocket connections store (existing)
```

## Route Modules

### 1. `auth_routes.py`
**Prefix:** `/auth`  
**Purpose:** User authentication and authorization

**Endpoints:**
- `POST /auth/signup` - Email/password signup
- `POST /auth/login` - Email/password login
- `GET /auth/google` - Initiate Google OAuth
- `GET /auth/google/callback` - Google OAuth callback
- `GET /auth/google/signup` - Google signup flow
- `GET /auth/google/callback/signup` - Google signup callback
- `GET /auth/google/login` - Google login flow
- `GET /auth/google/callback/login` - Google login callback

### 2. `upload_routes.py`
**Prefix:** None  
**Purpose:** File uploads and workflow processing

**Endpoints:**
- `POST /upload` - Upload document and start analysis workflow
- `POST /process` - Start processing without file upload
- `POST /get_conv_id` - Get current conversation ID

**Features:**
- Registers projects for WebSocket communication
- Parses uploaded documents
- Initiates background analysis workflows
- Maintains conversation tracking

### 3. `websocket_routes.py`
**Prefix:** None  
**Purpose:** Real-time bidirectional communication

**Endpoints:**
- `WS /ws/{conv_id}` - WebSocket connection for specific conversation

**Features:**
- Accepts WebSocket connections
- Stores connection in global `ws_connections` dictionary
- Handles disconnections gracefully

### 4. `results_routes.py`
**Prefix:** None  
**Purpose:** Fetch analysis and refinement results

**Endpoints:**
- `GET /requirements_file` - Get raw requirements file
- `GET /cdn_results` - Get Conflict/Dependency/Neutral analysis results
- `GET /refinement_results` - Get requirement refinement results
- `POST /update_requirement` - Update a requirement's text

**Features:**
- Transforms backend results to frontend-compatible format
- Handles both file-based and in-memory results
- Provides requirement classification and analysis data

### 5. `project_routes.py`
**Prefix:** `/projects`  
**Purpose:** Project and SRS document management

**Endpoints:**
- `GET /projects/{project_id}/srs` - Get SRS document
- `POST /projects/{project_id}/srs` - Save SRS document HTML
- `POST /projects/{project_id}/requirements/bulk_create` - Bulk save requirements

**Features:**
- Manages SRS documents (both HTML and structured formats)
- Handles requirement persistence to MongoDB
- Fetches related sections and mappings

## Migration Guide

### Before (old `routes.py`):
```python
from api.routes import router
app.include_router(router, prefix="/api")
```

### After (new structure):
```python
from api.routes import router
app.include_router(router, prefix="/api")
```

**No changes required to your main application file!** The new `__init__.py` exports the same combined router.

## Benefits of This Structure

1. **Separation of Concerns**: Each file handles a specific domain
2. **Easier Navigation**: Find routes quickly based on functionality
3. **Better Maintainability**: Smaller files are easier to understand and modify
4. **Team Collaboration**: Multiple developers can work on different route files without conflicts
5. **Clear Dependencies**: Each module imports only what it needs
6. **Testing**: Easier to write focused unit tests for each module

## Dependencies

Each route module manages its own dependencies:
- **Auth routes**: OAuth, bcrypt, session management
- **Upload routes**: File handling, orchestrator, document parsing
- **WebSocket routes**: WebSocket connections store
- **Results routes**: Shared state, result transformations
- **Project routes**: Database operations, HTTP client for internal API calls

## Configuration

Environment variables (from `.env`):
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
- `UPLOAD_DIR` - Directory for uploaded files (default: `./uploads`)

## Common Patterns

### Database Dependency
```python
def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.mongodb
```

### Background Tasks
```python
asyncio.create_task(orchestrator.start_agent(...))
```

### WebSocket Communication
```python
from api.ws_store import ws_connections
await ws_connections[conv_id].send_json(data)
```

## Future Enhancements

Consider adding:
- `middleware/` - Authentication middleware
- `dependencies/` - Shared dependency functions
- `validators/` - Request validation logic
- `exceptions/` - Custom exception handlers
- `utils/` - Shared utility functions specific to routes
