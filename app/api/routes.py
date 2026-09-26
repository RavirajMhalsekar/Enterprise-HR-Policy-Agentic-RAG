from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Response, status
from pydantic import BaseModel, Field
from app.core.config import get_settings
from app.core.auth import (
    User,
    LoginRequest,
    authenticate_user,
    create_access_token,
    get_current_user,
    get_current_admin_user,
)
from app.core.rate_limit import check_rate_limit
from app.rag.workflow import ask
from app.rag.vectorstore import add_documents
from app.services.ingestion import load_file, chunk_documents, SUPPORTED
from app.services.audit import write_audit

router = APIRouter(prefix="/api")

settings = get_settings()


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=3000)


@router.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}


@router.post("/login")
def login(payload: LoginRequest, response: Response):
    user = authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    token = create_access_token(user)
    response.set_cookie(
        key=settings.jwt_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )
    return {
        "status": "ok",
        "message": "Login successful",
        "user": {"username": user.username, "role": user.role},
    }


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key=settings.jwt_cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
    )
    return {"status": "ok", "message": "Successfully logged out."}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "role": current_user.role}


@router.post("/chat")
def chat(payload: ChatRequest, current_user: User = Depends(get_current_user)):
    # Rate limit: max 20 requests/hr per authenticated user (only for non-admin)
    if current_user.role != "admin":
        check_rate_limit(
            key=f"chat:{current_user.username}",
            max_requests=settings.chat_rate_limit,
            window_seconds=settings.chat_rate_window_seconds,
        )

    try:
        result = ask(payload.question)
        write_audit(payload.question, result["source_used"], result.get("trace", []))
        return {
            "answer": result["answer"],
            "source_used": result["source_used"],
            "trace": result.get("trace", []),
            "citations": result.get("citations", []),
            "rewritten_query": result.get("current_query", payload.question),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    current_admin: User = Depends(get_current_admin_user),
):
    # Rate limit: max 5 requests/minute per admin user
    check_rate_limit(
        key=f"ingest:{current_admin.username}",
        max_requests=settings.ingest_rate_limit,
        window_seconds=settings.ingest_rate_window_seconds,
    )

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED:
        raise HTTPException(status_code=400, detail=f"Supported: {', '.join(sorted(SUPPORTED))}")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / Path(file.filename).name
    dest.write_bytes(await file.read())

    docs = load_file(dest)
    chunks = chunk_documents(docs)
    ids = add_documents(chunks)
    return {
        "message": "Document indexed",
        "file": dest.name,
        "chunks": len(chunks),
        "ids_created": len(ids),
    }
