"""
FastAPI backend for TestAssist Gemini Bot.

*** NOTE: Requires a running PostgreSQL instance ***
- Must be accessible via environment variables: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME.
- See /database_container/README.md and the Compose example for details.
- If DB is unavailable, routes depending on the DB will return HTTP 503 Service Unavailable.

To run a local dev DB: see database_container/ (docker-compose recommended).
"""

import os
import logging
import socket
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, Body, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, TIMESTAMP, JSON
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, Session
from datetime import datetime, timedelta
import jwt
import hashlib

# Load env variables from .env
load_dotenv()

# === Startup Debug for 502 Diagnosis ===
def _diagnose_startup():
    """
    Prints diagnostic info to help troubleshoot 502 Bad Gateway:
    - Checks if port is available
    - Tests database connection
    - Dumps key environment variables
    """
    PORT = int(os.getenv("PORT", "3001"))
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "chatbotdb")
    DB_USER = os.getenv("DB_USER", "chatbotuser")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "chatbotpass")
    logger = logging.getLogger("uvicorn.error")
    # Port check
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("0.0.0.0", PORT))
        sock.close()
        port_status = "free"
    except Exception as e:
        port_status = f"in use or blocked: {e}"
    # DB check
    db_message = ""
    try:
        engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}", pool_pre_ping=True)
        with engine.connect() as conn:
            _ = conn.execute("SELECT 1")
        db_message = "Database connection Succeeded"
    except Exception as e:
        db_message = f"Database connection FAILED: {e}"
    logger.error(
        f"STARTUP DIAG: Port {PORT} status: {port_status}; {db_message}; Env: DB_HOST={DB_HOST} DB_PORT={DB_PORT} DB_USER={DB_USER} DB_NAME={DB_NAME}"
    )

# Call at startup for extra diagnostics
_diagnose_startup()

# === Request Logging Middleware (added for debugging frontend-backend connectivity) ===
class RequestLoggingMiddleware:
    """
    Logs incoming request details to backend logs for debugging frontend-backend connectivity.
    """
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("uvicorn.access")

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            req_method = scope["method"]
            req_path = scope["path"]
            client_host = scope.get("client", ["?"])[0]
            headers = {k.decode(): v.decode() for k, v in scope.get("headers", [])}
            self.logger.info(
                f"INCOMING REQUEST from {client_host}: {req_method} {req_path} | Headers: {headers}"
            )
        await self.app(scope, receive, send)

# === Database Setup ===
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "chatbotdb")
DB_USER = os.getenv("DB_USER", "chatbotuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "chatbotpass")
ANSWER_FILE_PATH = os.getenv("ANSWER_FILE_PATH", "answers.txt")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"

# Google Gemini configuration - replace this stub with real implementation
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_KEY = os.getenv("AIzaSyBqYe2aZFs3P4sl_V1vC32NdJV1Ebzv4MU")

Base = declarative_base()

def get_db():
    """
    Dependency for getting a DB session.
    Handles connection errors gracefully — so API endpoints return informative error if DB unavailable.
    """
    try:
        engine = create_engine(
            f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
            pool_pre_ping=True,
        )
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        yield db
    except Exception as e:
        logger = logging.getLogger("uvicorn.error")
        logger.error(f"Database connection FAILED in get_db(): {e}")
        # Raise a 503 Service Unavailable if DB can't be reached
        raise HTTPException(
            status_code=503,
            detail="Database unavailable: could not connect. Ensure PostgreSQL is running and reachable via DB_HOST and DB_PORT."
        )
    finally:
        try:
            db.close()
        except Exception:
            pass

# === Database Models ===

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(128))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"))
    sender = Column(String(16), nullable=False)  # 'user' or 'bot'
    content = Column(Text, nullable=False)
    gemini_response = Column(JSON, default=None)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    conversation = relationship("Conversation", back_populates="messages")

# === Pydantic Schemas (For API requests/responses) ===

class MessageCreate(BaseModel):
    content: str = Field(..., description="Message sent by user.")

class MessageOut(BaseModel):
    id: int
    sender: str
    content: str
    gemini_response: Optional[Dict[str, Any]]
    created_at: datetime
    # conversation_id intentionally left out for chat display
    class Config:
        orm_mode = True

class ConversationOut(BaseModel):
    id: int
    title: Optional[str]
    created_at: datetime
    messages: List[MessageOut]
    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    username: str = Field(..., description="Username for new user.")
    password: str = Field(..., description="Password for new user.")

class Token(BaseModel):
    access_token: str
    token_type: str

class UserProfile(BaseModel):
    id: int
    username: str
    created_at: datetime
    class Config:
        orm_mode = True

# === Authentication Utilities ===

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def hash_password(password: str):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str):
    return hash_password(plain_password) == hashed_password

def get_user_from_token(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Validate JWT token and return current user if authenticated."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    user = db.query(User).filter_by(username=username).first()
    if user is None:
        raise credentials_exception
    return user

# For unauthenticated mode, always use a dummy user id
DUMMY_USER_ID = 1

# === Gemini Integration (Stub, replace with true implementation) ===

class GeminiAPI:
    """Stub for Gemini-compatible response engine. Replace with real Google Gemini integration."""
    def __init__(self, answer_data: List[str]):
        self.answer_data = answer_data

    def get_answer(self, question: str, history: List[Dict]) -> str:
        if self.answer_data:
            for answer in self.answer_data:
                if answer.lower() in question.lower():
                    return answer
            return self.answer_data[0]
        # Fallback: echo
        return f"Echo (Gemini stub): {question}"

def load_answers_from_txt(file_path: str) -> List[str]:
    """Load .txt file into list of possible answers for in-context retrieval."""
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

# Instantiate Gemini engine (loaded once at startup)
answer_data = load_answers_from_txt(ANSWER_FILE_PATH)
gemini = GeminiAPI(answer_data=answer_data)

# === FastAPI App Setup ===

app = FastAPI(
    title="TestAssist Gemini Bot API",
    description="Backend API to handle user interactions, Google Gemini-powered chat, and answer retrieval for Test Engineers.",
    version="1.0.0",
    openapi_tags=[
        {"name": "health", "description": "Health check endpoint"},
        {"name": "auth", "description": "User authentication and profile"},
        {"name": "chat", "description": "Chat endpoints"},
        {"name": "history", "description": "Chat and conversation history"},
        {"name": "files", "description": "Answer file ingestion"},
    ]
)

# Add request logging middleware first (catches every request, before CORS or auth)
app.add_middleware(RequestLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Health Check ===
# PUBLIC_INTERFACE
@app.get("/", tags=["health"], summary="Ping backend", description="Health check for backend API.")
def health_check():
    """Ping the backend FastAPI service."""
    return {"message": "Healthy"}

# === User Signup / Authentication Endpoints ===

if AUTH_ENABLED:
    # PUBLIC_INTERFACE
    @app.post("/auth/signup", response_model=Token, tags=["auth"], summary="User signup")
    def signup(user: UserCreate = Body(...), db: Session = Depends(get_db)):
        """Register a new user and return access token."""
        if db.query(User).filter(User.username == user.username).first():
            raise HTTPException(status_code=400, detail="Username already exists")
        db_user = User(username=user.username, password_hash=hash_password(user.password))
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        token = create_access_token({"sub": db_user.username})
        return {"access_token": token, "token_type": "bearer"}

    # PUBLIC_INTERFACE
    @app.post("/auth/token", response_model=Token, tags=["auth"], summary="Obtain JWT token")
    def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
        """Authenticate and get JWT token."""
        user = db.query(User).filter(User.username == form_data.username).first()
        if not user or not verify_password(form_data.password, user.password_hash):
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        token = create_access_token({"sub": user.username})
        return {"access_token": token, "token_type": "bearer"}

    # PUBLIC_INTERFACE
    @app.get("/auth/profile", response_model=UserProfile, tags=["auth"], summary="Get user profile")
    def get_profile(user: User = Depends(get_user_from_token)):
        """Returns profile info for authenticated user.

        NOTE: This endpoint requires database availability on startup.
        If PostgreSQL is not running or unreachable, all DB-backed endpoints will fail with HTTP 503.
        """
        # Return a Pydantic UserProfile (do not return raw SQLAlchemy User)
        return UserProfile(
            id=user.id, username=user.username, created_at=user.created_at
        )
else:
    # Dummy endpoints for unauthenticated mode
    @app.post("/auth/token", response_model=Token, tags=["auth"], summary="Obtain JWT token")
    def login_dummy():
        """Returns a dummy token; no authentication performed."""
        token = create_access_token({"sub": "guest"})
        return {"access_token": token, "token_type": "bearer"}

    @app.get("/auth/profile", response_model=UserProfile, tags=["auth"], summary="Get guest profile")
    def get_profile_dummy():
        """Returns a guest profile."""
        return UserProfile(id=DUMMY_USER_ID, username="guest", created_at=datetime.utcnow())

# === Chat & Conversation Endpoints ===

# Setup logging for error tracking
logger = logging.getLogger("uvicorn.error")

# PUBLIC_INTERFACE
@app.post("/chat/", response_model=MessageOut, tags=["chat"], summary="Send user message", description="Submit a chat message. Starts a new conversation if no conversation_id is provided.")
def send_message(
    message: MessageCreate,
    conversation_id: Optional[int] = Body(None, description="Conversation to append message to"),
    user: User = Depends(get_user_from_token) if AUTH_ENABLED else None,
    db: Session = Depends(get_db),
):
    """
    Handles a message from the user: stores it, calls Gemini API for response, and stores bot reply.
    Enhanced: Improved exception handling, logs error details, returns a more informative error message to the user.
    """
    try:
        # Determine which user ID to use (auth or dummy)
        if AUTH_ENABLED:
            user_id = user.id
        else:
            user_id = DUMMY_USER_ID
            # Ensure the dummy user exists
            if not db.query(User).filter_by(id=DUMMY_USER_ID).first():
                db_dummy = User(id=DUMMY_USER_ID, username="guest", password_hash=None)
                db.add(db_dummy)
                db.commit()
        # Handle new conversation
        if not conversation_id:
            conversation = Conversation(user_id=user_id, title=None)
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
        else:
            conversation = db.query(Conversation).filter_by(id=conversation_id).first()
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        # Store user's message
        msg = Message(conversation_id=conversation.id, sender="user", content=message.content)
        db.add(msg)
        db.commit()
        db.refresh(msg)

        # Gather chat history for context (recent N messages)
        recent_messages = db.query(Message).filter(Message.conversation_id == conversation.id).order_by(Message.created_at).all()
        dialog_history = [
            {"sender": m.sender, "content": m.content, "created_at": m.created_at.isoformat()} for m in recent_messages
        ]

        # Get Gemini bot answer
        bot_resp_txt = gemini.get_answer(message.content, dialog_history)
        bot_msg = Message(
            conversation_id=conversation.id,
            sender="bot",
            content=bot_resp_txt,
            gemini_response={"answer": bot_resp_txt},
        )
        db.add(bot_msg)
        db.commit()
        db.refresh(bot_msg)
        return MessageOut(
            id=bot_msg.id,
            sender=bot_msg.sender,
            content=bot_msg.content,
            gemini_response=bot_msg.gemini_response,
            created_at=bot_msg.created_at
        )
    except HTTPException as he:
        # Allow FastAPI HTTPException to propagate as usual for client errors
        logger.warning(f"User error in /chat/: {he.detail}", exc_info=True)
        raise
    except Exception as e:
        # For unexpected errors (DB, GeminiAPI, etc), log stack trace and return informative message
        logger.error(f"Unexpected error in /chat/: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"A server error occurred: {str(e)}. Please contact support with this message.",
        )

# PUBLIC_INTERFACE
@app.get("/chat/history", response_model=List[ConversationOut], tags=["history"], summary="Get conversation history")
def get_history(
    user: User = Depends(get_user_from_token) if AUTH_ENABLED else None,
    db: Session = Depends(get_db)
):
    """
    Returns a list of user's conversations with messages.
    """
    if AUTH_ENABLED:
        user_id = user.id
    else:
        user_id = DUMMY_USER_ID
    conversations = db.query(Conversation).filter_by(user_id=user_id).order_by(Conversation.created_at.desc()).all()
    results = []
    for conv in conversations:
        messages = db.query(Message).filter_by(conversation_id=conv.id).order_by(Message.created_at).all()
        results.append(
            ConversationOut(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                messages=[
                    MessageOut(
                        id=m.id,
                        sender=m.sender,
                        content=m.content,
                        gemini_response=m.gemini_response,
                        created_at=m.created_at
                    ) for m in messages
                ]
            )
        )
    return results

# PUBLIC_INTERFACE
@app.post("/files/answers", tags=["files"], summary="Upload new .txt answer file", description="Upload and reload the answer .txt for Gemini context.")
async def upload_answers(file: UploadFile = File(...)):
    """
    Accepts a new answer file (.txt) and reloads the Gemini answer context on the server.
    """
    # Only accept .txt files
    if not file.filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported")
    file_path = ANSWER_FILE_PATH
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)
    # Reload answer data for Gemini
    global gemini
    new_answers = load_answers_from_txt(file_path)
    gemini = GeminiAPI(answer_data=new_answers)
    return {"detail": "Answers uploaded and Gemini context reloaded."}

# === Swagger/Docs - WebSocket Usage Note (if needed) ===

@app.get("/docs/ws", tags=["health"], summary="WebSocket usage note for API docs")
def websocket_usage_note():
    """There is no websocket connection currently implemented. All communication is via REST API."""
    return {"detail": "No WebSocket support. Use REST endpoints."}

# --- Global error handling middleware for better user and logging feedback ---

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catches all unhandled exceptions and logs details, returns informative error JSON."""
    logger.error(f"Unhandled exception at {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}. If this persists, contact support."},
    )

# === Create Tables On Startup ===

@app.on_event("startup")
def on_startup():
    """Create all database tables if they do not exist.

    If PostgreSQL is unavailable at startup, logs a clear message and continues.
    API endpoints requiring the DB will provide a user-friendly error if necessary.
    """
    try:
        engine = create_engine(
            f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
            pool_pre_ping=True,
        )
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger = logging.getLogger("uvicorn.error")
        logger.error(
            f"Database connection FAILED during table creation. Backend will start, "
            f"but all DB routes will return 503 until PostgreSQL is available: {e}\n"
            f"Ensure PostgreSQL is running at DB_HOST={DB_HOST} DB_PORT={DB_PORT} "
            f"with expected DB_NAME/DB_USER/DB_PASSWORD."
        )
