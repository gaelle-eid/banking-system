import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pypdf import PdfReader
import io

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.embeddings import get_embedding, chunk_text
from app.models.models import KnowledgeDocument, KnowledgeChunk, User, UserRole
from app.schemas.knowledge import KnowledgeDocumentOut

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def extract_text(filename: str, contents: bytes) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(contents))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return contents.decode("utf-8", errors="ignore")


@router.post("/upload", response_model=KnowledgeDocumentOut, dependencies=[Depends(require_role(UserRole.admin))])
async def upload_document(
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".pdf", ".txt", ".md"):
        raise HTTPException(status_code=400, detail="Only PDF, TXT, and MD files are supported")

    contents = await file.read()
    text = extract_text(file.filename, contents)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract any text from this file")

    document = KnowledgeDocument(title=title, filename=file.filename, uploaded_by=current_user.id)
    db.add(document)
    await db.flush()

    chunks = chunk_text(text)
    for i, chunk in enumerate(chunks):
        try:
            embedding = await get_embedding(chunk)
        except Exception as e:
            print(f"EMBEDDING ERROR: {type(e).__name__}: {e}")
            embedding = None
        db.add(KnowledgeChunk(document_id=document.id, content=chunk, embedding=embedding, chunk_index=i))

    await db.commit()
    await db.refresh(document)
    return document


@router.get("", response_model=list[KnowledgeDocumentOut], dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc()))
    return result.scalars().all()


@router.delete("/{document_id}", dependencies=[Depends(require_role(UserRole.admin))])
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks_result = await db.execute(select(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id))
    for chunk in chunks_result.scalars().all():
        await db.delete(chunk)

    await db.delete(document)
    await db.commit()
    return {"status": "deleted"}