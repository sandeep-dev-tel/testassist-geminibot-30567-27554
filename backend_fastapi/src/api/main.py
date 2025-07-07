"""
FastAPI Reverse Proxy for TestAssist Gemini Bot.

This backend now acts as a reverse proxy/relay that forwards chat, user, and file requests
to the external API endpoint:
    https://vscode-internal-48644-beta.beta01.cloud.kavia.ai:3001

All business logic (chat, user, conversation, file upload, etc.) is handled by the remote backend.
This instance simply forwards requests and returns responses transparently.

Author: AI Code Generation Proxy Adapter
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from dotenv import load_dotenv

# Load env variables from .env
load_dotenv()

# External backend API base URL for forwarding requests
API_BASE_URL = "https://vscode-internal-48644-beta.beta01.cloud.kavia.ai:3001"

# ---- FastAPI App instantiation and Reverse Proxy Endpoints ----

app = FastAPI(
    title="TestAssist Gemini Bot API Proxy",
    description="Reverse proxy REST API for forwarding all requests to the central chatbot backend.",
    version="1.0.1",
    openapi_tags=[
        {"name": "proxy", "description": "Proxy endpoints redirect to remote backend"},
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict this for security if needed.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PUBLIC_INTERFACE
@app.get("/", tags=["proxy"], summary="Proxy: Health check")
async def root_proxy():
    """Reverse proxies health check to remote backend."""
    async with httpx.AsyncClient(timeout=10) as ac:
        try:
            r = await ac.get(f"{API_BASE_URL}/")
            return r.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

# PUBLIC_INTERFACE
@app.post("/chat/", tags=["proxy"], summary="Proxy: chat endpoint")
async def chat_proxy(request: Request):
    """
    Proxies POST /chat/ calls to remote backend.
    """
    data = await request.body()
    headers = dict(request.headers)
    async with httpx.AsyncClient(timeout=30) as ac:
        try:
            r = await ac.post(f"{API_BASE_URL}/chat/", content=data, headers=headers)
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

# PUBLIC_INTERFACE
@app.get("/chat/history", tags=["proxy"], summary="Proxy: conversation history")
async def chat_history_proxy(request: Request):
    headers = dict(request.headers)
    async with httpx.AsyncClient(timeout=30) as ac:
        try:
            r = await ac.get(f"{API_BASE_URL}/chat/history", headers=headers)
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

# PUBLIC_INTERFACE
@app.post("/auth/token", tags=["proxy"], summary="Proxy: authentication token")
async def auth_token_proxy(request: Request):
    data = await request.body()
    headers = dict(request.headers)
    async with httpx.AsyncClient(timeout=30) as ac:
        try:
            r = await ac.post(f"{API_BASE_URL}/auth/token", content=data, headers=headers)
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

# PUBLIC_INTERFACE
@app.get("/auth/profile", tags=["proxy"], summary="Proxy: user profile")
async def auth_profile_proxy(request: Request):
    headers = dict(request.headers)
    async with httpx.AsyncClient(timeout=30) as ac:
        try:
            r = await ac.get(f"{API_BASE_URL}/auth/profile", headers=headers)
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

# PUBLIC_INTERFACE
@app.post("/files/answers", tags=["proxy"], summary="Proxy: upload answer file")
async def files_answers_proxy(request: Request):
    # Forward multipart form-data for file upload
    headers = dict(request.headers)
    form = await request.form()
    files = []
    for key, field in form.multi_items():
        if hasattr(field, "filename"):
            files.append((key, (field.filename, await field.read(), field.content_type)))
        else:
            files.append((key, str(field)))
    async with httpx.AsyncClient(timeout=60) as ac:
        try:
            r = await ac.post(f"{API_BASE_URL}/files/answers", files=files, headers=headers)
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

# PUBLIC_INTERFACE
@app.get("/docs/ws", tags=["proxy"], summary="Proxy: WebSocket usage note")
async def ws_usage_note_proxy(request: Request):
    headers = dict(request.headers)
    async with httpx.AsyncClient(timeout=10) as ac:
        try:
            r = await ac.get(f"{API_BASE_URL}/docs/ws", headers=headers)
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

# Global catch-all for other errors
@app.exception_handler(Exception)
async def proxy_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Unhandled proxy error: {exc}"}
    )
