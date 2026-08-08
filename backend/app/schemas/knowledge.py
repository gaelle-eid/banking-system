from pydantic import BaseModel
from datetime import datetime


class KnowledgeDocumentOut(BaseModel):
    id: str
    title: str
    filename: str
    uploaded_by: str
    created_at: datetime

    class Config:
        from_attributes = True