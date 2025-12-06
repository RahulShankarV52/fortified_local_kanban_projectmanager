#What the API Request/Response looks like
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# 1. Base User Schema (Shared properties)
class UserBase(BaseModel):
    email: EmailStr

# 2. Schema for CREATING a user (Input)
class UserCreate(UserBase):
    password: str 

# 3. Schema for READING a user (Output)
class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        # This tells Pydantic to read data even if it's an ORM object
        from_attributes = True

# 4. Schema for JWT Token Response
class Token(BaseModel):
    access_token: str
    token_type: str

# --- BOARD SCHEMAS ---
class BoardBase(BaseModel):
    title: str

class BoardCreate(BoardBase):
    pass

class BoardResponse(BoardBase):
    id: int
    owner_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class AttachmentResponse(BaseModel):
    id: int
    filename: str
    file_size: int
    uploaded_at: datetime

    class Config:
        from_attributes = True

# --- CARD SCHEMAS ---
class CardCreate(BaseModel):
    title: str
    description: Optional[str] = None
    column_id: int
    position: int = 0

class ChecklistItemCreate(BaseModel):
    content: str

class ChecklistItemUpdate(BaseModel):
    is_completed: bool

class ChecklistItemResponse(BaseModel):
    id: int
    content: str
    is_completed: bool
    
    class Config:
        from_attributes = True

class CardResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    column_id: int
    position: int
    attachments: list[AttachmentResponse] = [] 
    checklist: list[ChecklistItemResponse] = []
    
    class Config:
        from_attributes = True

# --- COLUMNS ---
class ColumnCreate(BaseModel):
    title: str

class ColumnResponse(BaseModel):
    id: int
    title: str
    position: int
    board_id: int
    
    class Config:
        from_attributes = True
