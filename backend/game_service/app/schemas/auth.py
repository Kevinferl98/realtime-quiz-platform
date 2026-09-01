from pydantic import BaseModel

class WSTicketResponse(BaseModel):
    ticket: str
    expires_in: int = 10