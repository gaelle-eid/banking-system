from pydantic import BaseModel


class EmployeeChatRequest(BaseModel):
    message: str


class EmployeeChatResponse(BaseModel):
    reply: str
    conversation_id: str