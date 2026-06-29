"""
Authentication routes for user signup, login, and Google OAuth.
JWT tokens are issued on every login (manual + Google) and stored on the frontend.
"""
import os
import httpx 
from datetime import datetime, timedelta
from dotenv import load_dotenv
from passlib.hash import bcrypt
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError
from fastapi import APIRouter, HTTPException, Depends, status, Body
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.requests import Request
from authlib.integrations.starlette_client import OAuth
from jose import jwt, JWTError

from databaseSchema.schema import SignupRequest, LoginRequest

load_dotenv()

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ── JWT Config ───────────────────────────────────────────────
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

security = HTTPBearer()

# ── JWT Helpers ──────────────────────────────────────────────

def create_access_token(user_id: str, email: str, name: str) -> str:
    payload = {
        "sub": user_id,           # subject = user_id
        "email": email,
        "name": name,
        "exp": datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ── Auth Dependency ───────────

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Use this as a Depends() in any route that needs to know who the user is.
    Example:
        @router.get("/api/templates")
        async def get_templates(user = Depends(get_current_user)):
            user_id = user["sub"]
    """
    return decode_token(credentials.credentials)


# ── OAuth Setup ──────────────────────────────────────────────

CONF_URL = "https://accounts.google.com/.well-known/openid-configuration"
oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url=CONF_URL,
    client_kwargs={"scope": "openid email profile", "timeout": 30}
)


# ── DB Dependency ────────────────────────────────────────────

def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.mongodb


# ── Google OAuth ─────────────────────────────────────────────

@router.get("/google")
async def login_via_google(request: Request):
    redirect_uri = "http://localhost:8000/api/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri,_external=True)
     


@router.get("/google/callback")
async def google_callback(request: Request):
    try:
        code = request.query_params.get("code")

        # Manually exchange code for token using httpx
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
                    "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
                    "redirect_uri": "http://localhost:8000/api/auth/google/callback",
                    "grant_type": "authorization_code",
                }
            )
            token_data = token_response.json()

            # Get user info
            userinfo_response = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"}
            )
            userinfo = userinfo_response.json()

        email = userinfo["email"]
        name = userinfo.get("name", "")
        google_id = userinfo.get("sub")

        db = request.app.mongodb
        user = await db["users"].find_one({"email": email})

        if not user:
            result = await db["users"].insert_one({
                "name": name,
                "email": email,
                "google_id": google_id,
                "password": None
            })
            user_id = str(result.inserted_id)
        else:
            user_id = str(user["_id"])

        jwt_token = create_access_token(user_id, email, name)
        return RedirectResponse(url=f"http://localhost:5173/dashboard?token={jwt_token}")

    except Exception as e:
        print(f"[Google OAuth Error]: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=400)


# @router.get("/google")
# async def login_via_google(request: Request):
#     redirect_uri = "http://localhost:8000/api/auth/google/callback"
#     return await oauth.google.authorize_redirect(request, redirect_uri)


# @router.get("/google/callback")
# async def google_callback(request: Request):
#     try:
#         token = await oauth.google.authorize_access_token(request)
#         userinfo = token.get("userinfo") or await oauth.google.parse_id_token(request, token)

#         email = userinfo["email"]
#         name = userinfo.get("name", "")
#         google_id = userinfo.get("sub")

#         db = request.app.mongodb
#         user = await db["users"].find_one({"email": email})

#         if not user:
#             result = await db["users"].insert_one({
#                 "name": name,
#                 "email": email,
#                 "google_id": google_id,
#                 "password": None
#             })
#             user_id = str(result.inserted_id)
#         else:
#             user_id = str(user["_id"])

#         # Create JWT and pass it to frontend via URL param
#         jwt_token = create_access_token(user_id, email, name)
#         request.session["user"] = {"email": email, "name": name}

#         return RedirectResponse(url=f"http://localhost:5173/dashboard?token={jwt_token}")

#     except Exception as e:
#         print(f"[Google OAuth Error]: {e}")  # ← add this
#         import traceback
#         traceback.print_exc()               # ← add this
#         return JSONResponse({"error": str(e)}, status_code=400)


@router.get("/google/signup")
async def google_signup(request: Request):
    redirect_uri = "http://localhost:8000/api/auth/google/callback/signup"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback/signup")
async def google_signup_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        userinfo = token.get("userinfo") or await oauth.google.parse_id_token(request, token)

        email = userinfo["email"]
        name = userinfo.get("name", "")
        google_id = userinfo.get("sub")

        db = request.app.mongodb
        user = await db["users"].find_one({"email": email})
        if user:
            return RedirectResponse(url="http://localhost:5173/auth?mode=login&msg=User+already+exists")

        result = await db["users"].insert_one({
            "name": name,
            "email": email,
            "google_id": google_id,
            "password": None
        })

        jwt_token = create_access_token(str(result.inserted_id), email, name)
        request.session["user"] = {"email": email, "name": name}

        return RedirectResponse(url=f"http://localhost:5173/dashboard?token={jwt_token}")

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.get("/google/login")
async def google_login(request: Request):
    """Initiate Google OAuth login flow"""
    redirect_uri = "http://localhost:8000/api/auth/google/callback/login"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback/login")
async def google_login_callback(request: Request):
    """Handle Google OAuth login callback"""
    try:
        token = await oauth.google.authorize_access_token(request)
        userinfo = token.get("userinfo") or await oauth.google.parse_id_token(request, token)

        email = userinfo["email"]
        name = userinfo.get("name", "")

        db = request.app.mongodb
        user = await db["users"].find_one({"email": email})

        if not user:
            return RedirectResponse(url="http://localhost:5173/auth?mode=signup&msg=Please+signup+first")

        jwt_token = create_access_token(str(user["_id"]), email, name)
        request.session["user"] = {"email": email, "name": name}

        return RedirectResponse(url=f"http://localhost:5173/dashboard?token={jwt_token}")

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


# ── Manual Auth ──────────────────────────────────────────────

@router.post("/signup")
async def signup(payload: SignupRequest = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        result = await db["users"].insert_one({
            "name": payload.name,
            "email": payload.email,
            "password": bcrypt.hash(payload.password),
        })
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="User with this email already exists")

    jwt_token = create_access_token(str(result.inserted_id), payload.email, payload.name)

    return {
        "message": "Signup successful!",
        "token": jwt_token,                   # ← frontend stores this
        "user": {
            "id": str(result.inserted_id),
            "name": payload.name,
            "email": payload.email
        },
    }


@router.post("/login")
async def login(payload: LoginRequest = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    user = await db["users"].find_one({"email": payload.email})

    if not user or not bcrypt.verify(payload.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    jwt_token = create_access_token(str(user["_id"]), user["email"], user["name"])

    return {
        "message": "Login successful!",
        "token": jwt_token,                   # ← frontend stores this
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"]
        },
    }


# ── Get Current User ─────────────────────────────────────────

@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    return {"user": {"id": user["sub"], "email": user["email"], "name": user["name"]}}



# """
# Authentication routes for user signup, login, and Google OAuth.
# """
# import os
# from dotenv import load_dotenv
# from passlib.hash import bcrypt
# from motor.motor_asyncio import AsyncIOMotorDatabase
# from pymongo.errors import DuplicateKeyError
# from fastapi import APIRouter, HTTPException, Depends, status, Body
# from fastapi.responses import JSONResponse, RedirectResponse
# from starlette.requests import Request
# from authlib.integrations.starlette_client import OAuth

# from databaseSchema.schema import SignupRequest, LoginRequest

# # Initialize environment variables
# load_dotenv()

# # Initialize router
# router = APIRouter(prefix="/auth", tags=["Authentication"])

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
#     """Get MongoDB database from FastAPI app"""
#     return request.app.mongodb


# # ----------------- Google OAuth Routes -----------------
# @router.get("/google")
# async def login_via_google(request: Request):
#     """Initiate Google OAuth flow"""
#     redirect_uri = "http://localhost:8000/api/auth/google/callback"
#     return await oauth.google.authorize_redirect(request, redirect_uri)


# @router.get("/google/callback")
# async def google_callback(request: Request):
#     """Handle Google OAuth callback"""
#     try:
#         token = await oauth.google.authorize_access_token(request)
#         userinfo = token.get("userinfo") or await oauth.google.parse_id_token(request, token)

#         email = userinfo["email"]
#         name = userinfo.get("name", "")
#         google_id = userinfo.get("sub")

#         db = request.app.mongodb
#         user = await db["users"].find_one({"email": email})
#         if not user:
#             await db["users"].insert_one({
#                 "name": name,
#                 "email": email,
#                 "google_id": google_id,
#                 "password": None
#             })

#         request.session["user"] = {"email": email, "name": name}
#         return RedirectResponse(url="http://localhost:5173/dashboard")
#     except Exception as e:
#         return JSONResponse({"error": str(e)}, status_code=400)


# @router.get("/google/signup")
# async def google_signup(request: Request):
#     """Initiate Google OAuth signup flow"""
#     redirect_uri = "http://localhost:8000/api/auth/google/callback/signup"
#     return await oauth.google.authorize_redirect(request, redirect_uri)


# @router.get("/google/callback/signup")
# async def google_signup_callback(request: Request):
#     """Handle Google OAuth signup callback"""
#     try:
#         token = await oauth.google.authorize_access_token(request)
#         userinfo = token.get("userinfo") or await oauth.google.parse_id_token(request, token)

#         email = userinfo["email"]
#         name = userinfo.get("name", "")
#         google_id = userinfo.get("sub")

#         db = request.app.mongodb
#         user = await db["users"].find_one({"email": email})
#         if user:
#             return RedirectResponse(url="http://localhost:5173/auth?mode=login&msg=User+already+exists")

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


# @router.get("/google/login")
# async def google_login(request: Request):
#     """Initiate Google OAuth login flow"""
#     redirect_uri = "http://localhost:8000/api/auth/google/callback/login"
#     return await oauth.google.authorize_redirect(request, redirect_uri)


# @router.get("/google/callback/login")
# async def google_login_callback(request: Request):
#     """Handle Google OAuth login callback"""
#     try:
#         token = await oauth.google.authorize_access_token(request)
#         userinfo = token.get("userinfo") or await oauth.google.parse_id_token(request, token)

#         email = userinfo["email"]
#         name = userinfo.get("name", "")

#         db = request.app.mongodb
#         user = await db["users"].find_one({"email": email})
#         if not user:
#             return RedirectResponse(url="http://localhost:5173/auth?mode=signup&msg=Please+signup+first")

#         request.session["user"] = {"email": email, "name": name}
#         return RedirectResponse(url="http://localhost:5173/dashboard")
#     except Exception as e:
#         return JSONResponse({"error": str(e)}, status_code=400)


# # ----------------- Email/Password Authentication -----------------
# @router.post("/signup")
# async def signup(
#     payload: SignupRequest = Body(...),
#     db: AsyncIOMotorDatabase = Depends(get_db),
# ):
#     """Register a new user with email and password"""
#     try:
#         await db["users"].insert_one({
#             "name": payload.name,
#             "email": payload.email,
#             "password": bcrypt.hash(payload.password),
#         })
#     except DuplicateKeyError:
#         raise HTTPException(
#             status_code=status.HTTP_409_CONFLICT,
#             detail="User with this email already exists"
#         )

#     return {
#         "message": "Signup successful!",
#         "user": {"name": payload.name, "email": payload.email},
#     }


# @router.post("/login")
# async def login(
#     payload: LoginRequest = Body(...),
#     db: AsyncIOMotorDatabase = Depends(get_db),
# ):
#     """Login with email and password"""
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
